"""Enriquecimento runtime dos prazos com valores estimados.

Sprint UX-V-2.2.A. A aba ``prazos`` do XLSX é um snapshot histórico com
apenas 4 colunas (``conta``, ``dia_vencimento``, ``banco_pagamento``,
``auto_debito``) e não traz ``valor``. Resultado original: pílulas no
calendário e legenda saíam sempre com R$ 0,00.

Esta unidade cruza cada prazo com o ``extrato`` (últimos 12 meses) e
estima um ``valor_estimado`` por linha, marcando ``origem_valor``:

  - ``"última fatura"``  — quando há boletos recorrentes (>=2 em 12 m
                            com forma_pagamento "Boleto"), usa o último
                            valor.
  - ``"histórico 12m"``   — média absoluta das despesas/impostos
                            casados com a conta nos últimos 12 m.
  - ``"sem dado"``        — sem cruzamento; mantém R$ 0,00 (a spec
                            proíbe inventar dados).

Heurística de matching (por ordem de tentativa):

  1. ``categoria == conta`` (case-insensitive, igualdade exata).
  2. ``local`` contém ``conta`` como substring (fallback fuzzy).

NÃO modifica o XLSX em disco -- enriquecimento é runtime apenas.
"""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

ORIGEM_ULTIMA_FATURA: str = "última fatura"
ORIGEM_HISTORICO: str = "histórico 12m"
ORIGEM_SEM_DADO: str = "sem dado"

JANELA_DIAS_HISTORICO: int = 365
MIN_OCORRENCIAS_BOLETO: int = 2  # boletos recorrentes => "última fatura"

# Nomes que sinalizam que a "conta" é cartão de crédito; nesses casos
# restringimos o matching a lançamentos com "fatura" no local, evitando
# casar com transferências Pix para terceiros que tenham conta no banco.
PALAVRAS_CARTAO: tuple[str, ...] = (
    "nubank",
    "c6",
    "santander",
    "itau",
    "itaú",
    "inter",
    "cartão",
    "cartao",
    "fatura",
)


def _normalizar_data(serie: pd.Series) -> pd.Series:
    """Converte série para datetime tolerante a strings/Timestamps."""
    if pd.api.types.is_datetime64_any_dtype(serie):
        return serie
    return pd.to_datetime(serie, errors="coerce")


def _filtrar_extrato_recente(
    extrato: pd.DataFrame, hoje: date | None = None
) -> pd.DataFrame:
    """Recorta extrato para Despesa/Imposto dos últimos 12 meses."""
    if extrato is None or extrato.empty:
        return pd.DataFrame()
    if "tipo" not in extrato.columns or "data" not in extrato.columns:
        return pd.DataFrame()

    hoje = hoje or date.today()
    inicio = pd.Timestamp(hoje - timedelta(days=JANELA_DIAS_HISTORICO))

    df = extrato.copy()
    df["data"] = _normalizar_data(df["data"])
    df = df.dropna(subset=["data"])
    df = df[df["data"] >= inicio]
    df = df[df["tipo"].isin(["Despesa", "Imposto"])]
    return df


def _conta_parece_cartao(conta: str) -> bool:
    """Heurística: nome da conta sugere cartão de crédito."""
    chave = (conta or "").strip().lower()
    if not chave:
        return False
    return any(p in chave for p in PALAVRAS_CARTAO)


def _matches_da_conta(
    df_recente: pd.DataFrame, conta: str
) -> pd.DataFrame:
    """Devolve linhas que casam a conta por categoria OU por local fuzzy.

    Igualdade case-insensitive na coluna ``categoria`` tem prioridade.
    Se nada casar por categoria, faz fallback para ``local`` contendo a
    conta como substring (case-insensitive).

    Para contas que parecem cartão (Nubank, C6, Santander, ...) o
    matching por ``local`` exige presença da palavra "fatura" para
    evitar casar com Pix/transferências para pessoas que possuem conta
    nesses bancos.
    """
    if df_recente.empty or not conta:
        return df_recente.iloc[0:0]

    chave = conta.strip().lower()
    if not chave:
        return df_recente.iloc[0:0]

    if "categoria" in df_recente.columns:
        cat_norm = df_recente["categoria"].astype(str).str.strip().str.lower()
        por_cat = df_recente[cat_norm == chave]
        if not por_cat.empty:
            return por_cat

    if "local" in df_recente.columns:
        local_norm = df_recente["local"].astype(str).str.lower()
        mascara = local_norm.str.contains(chave, regex=False, na=False)
        if _conta_parece_cartao(conta):
            mascara = mascara & local_norm.str.contains("fatura", regex=False, na=False)
        por_local = df_recente[mascara]
        if not por_local.empty:
            return por_local

    return df_recente.iloc[0:0]


def _estimar_valor(matches: pd.DataFrame) -> tuple[float, str]:
    """A partir das linhas casadas, devolve (valor_estimado, origem).

    - >=2 boletos => última fatura (valor mais recente).
    - >=1 lançamento => média absoluta das ocorrências (histórico 12m).
    - vazio => 0.0 sem_dado.
    """
    if matches.empty or "valor" not in matches.columns:
        return 0.0, ORIGEM_SEM_DADO

    if "forma_pagamento" in matches.columns:
        boletos = matches[matches["forma_pagamento"] == "Boleto"]
        if len(boletos) >= MIN_OCORRENCIAS_BOLETO and "data" in boletos.columns:
            ultimo = boletos.sort_values("data").iloc[-1]
            try:
                return float(abs(ultimo["valor"])), ORIGEM_ULTIMA_FATURA
            except (TypeError, ValueError):
                pass  # noqa: BLE001 -- valor ultimo boleto invalido; cai para media abaixo

    try:
        media = float(matches["valor"].abs().mean())
    except (TypeError, ValueError):
        return 0.0, ORIGEM_SEM_DADO

    if pd.isna(media) or media <= 0:
        return 0.0, ORIGEM_SEM_DADO
    return media, ORIGEM_HISTORICO


def enriquecer_prazos_com_valor(
    prazos: pd.DataFrame,
    extrato: pd.DataFrame,
    hoje: date | None = None,
) -> pd.DataFrame:
    """Adiciona colunas ``valor_estimado`` e ``origem_valor`` ao DataFrame.

    Operação não destrutiva: devolve cópia. Se entrada inválida, devolve
    DataFrame com colunas adicionadas vazias para preservar contrato dos
    consumidores. Mantém todas as outras colunas intactas e na mesma
    ordem.
    """
    if prazos is None or prazos.empty:
        return prazos.copy() if prazos is not None else pd.DataFrame()

    enriquecido = prazos.copy()
    if "conta" not in enriquecido.columns:
        enriquecido["valor_estimado"] = 0.0
        enriquecido["origem_valor"] = ORIGEM_SEM_DADO
        return enriquecido

    df_recente = _filtrar_extrato_recente(extrato, hoje=hoje)

    valores: list[float] = []
    origens: list[str] = []
    for _, row in enriquecido.iterrows():
        conta = row.get("conta", "")
        if pd.isna(conta):
            valores.append(0.0)
            origens.append(ORIGEM_SEM_DADO)
            continue
        matches = _matches_da_conta(df_recente, str(conta))
        valor, origem = _estimar_valor(matches)
        valores.append(valor)
        origens.append(origem)

    enriquecido["valor_estimado"] = valores
    enriquecido["origem_valor"] = origens
    return enriquecido


# "O preço justo é o que a memória honesta lembra, não o que o desejo inventa." -- Aristóteles
