"""Componente de tabela inline para resultado de busca por fornecedor.

Sprint UX-124 -- substitui o antigo botão "Ir para Catalogação filtrada"
(UX-114) por uma `st.dataframe` renderizada diretamente na página de
Busca Global. O dono pediu (feedback 2026-04-27, image 17) que o
resultado apareça onde a busca foi iniciada -- navegar para outra aba
rompe o fluxo da pesquisa.

Padrões canônicos respeitados:

- (l) subregra retrocompatível: roteador, índice e `buscar_global`
  permanecem intocados (UX-114 preservada). Apenas a renderização
  muda quando `rotear()` retorna `kind='fornecedor'`.
- PII: mascarada nas colunas `Local`, `Categoria` e `Documento` (padrão
  Sprint 99 + Sprint UX-114, 4 sítios totais).
- Filtros sidebar (Mês, Pessoa, Forma de pagamento) continuam impactando
  o resultado via filtros aplicados antes da chamada deste componente.
"""

from __future__ import annotations

import re

import pandas as pd

# ---------------------------------------------------------------------------
# PII: mascaramento canônico (CPF, CNPJ, email)
# ---------------------------------------------------------------------------

_RE_CPF = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")
_RE_CNPJ = re.compile(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b")
_RE_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_RE_CPF_CRU = re.compile(r"(?<!\d)\d{11}(?!\d)")
_RE_CNPJ_CRU = re.compile(r"(?<!\d)\d{14}(?!\d)")


def _mascarar_pii(texto: object) -> object:
    """Mascara CPF, CNPJ e email em uma string. Idempotente.

    Aceita qualquer entrada; se não for string utilizável, retorna intacto.
    """
    if not isinstance(texto, str) or not texto:
        return texto
    saida = _RE_CPF.sub("***.***.***-**", texto)
    saida = _RE_CNPJ.sub("**.***.***/****-**", saida)
    saida = _RE_EMAIL.sub("***@***", saida)
    saida = _RE_CPF_CRU.sub("***********", saida)
    saida = _RE_CNPJ_CRU.sub("**************", saida)
    return saida


def _formatar_valor_brl(valor: object) -> str:
    """Formata valor numérico em BRL (R$ 1.234,56). Defensivo."""
    try:
        v = float(valor)
    except (TypeError, ValueError):
        return "--"
    sinal = "-" if v < 0 else ""
    v_abs = abs(v)
    inteiro, decimal = f"{v_abs:.2f}".split(".")
    # Separador de milhar com ponto (PT-BR).
    inteiro_fmt = ""
    for i, ch in enumerate(reversed(inteiro)):
        if i and i % 3 == 0:
            inteiro_fmt = "." + inteiro_fmt
        inteiro_fmt = ch + inteiro_fmt
    return f"{sinal}R$ {inteiro_fmt},{decimal}"


def construir_dataframe_fornecedor(
    nome_fornecedor: str,
    df_extrato: pd.DataFrame,
    *,
    mascarar_pii: bool = True,
) -> pd.DataFrame:
    """Filtra `df_extrato` por fornecedor e devolve DataFrame para `st.dataframe`.

    Match case-insensitive contra `local` (substring). Resultado ordenado
    por `data` decrescente. Colunas finais: Data / Valor / Local /
    Categoria / Banco / Documento.

    Args:
        nome_fornecedor: nome canônico do fornecedor (do roteador).
        df_extrato: DataFrame da aba `extrato` do XLSX.
        mascarar_pii: se True (default), mascara CPF/CNPJ/email em
            `Local` e `Categoria`.

    Returns:
        DataFrame com colunas canônicas. Vazio se `nome_fornecedor` é
        falso ou se `df_extrato` não tem coluna `local`.
    """
    colunas_finais = ["Data", "Valor", "Local", "Categoria", "Banco", "Documento"]
    vazio = pd.DataFrame(columns=colunas_finais)

    if not nome_fornecedor or df_extrato is None or df_extrato.empty:
        return vazio
    if "local" not in df_extrato.columns:
        return vazio

    alvo = str(nome_fornecedor).strip().lower()
    if not alvo:
        return vazio

    df = df_extrato.copy()
    serie_local = df["local"].fillna("").astype(str).str.lower()
    mascara = serie_local.str.contains(re.escape(alvo), na=False, regex=True)
    df = df[mascara]

    if df.empty:
        return vazio

    # Ordena por data decrescente (mais recente primeiro).
    if "data" in df.columns:
        df = df.assign(_data_sort=pd.to_datetime(df["data"], errors="coerce"))
        df = df.sort_values("_data_sort", ascending=False, na_position="last")
        df = df.drop(columns=["_data_sort"])

    saida = pd.DataFrame()
    saida["Data"] = df["data"].astype(str).fillna("--") if "data" in df.columns else "--"
    saida["Valor"] = df["valor"].map(_formatar_valor_brl) if "valor" in df.columns else "--"
    saida["Local"] = df["local"].fillna("").astype(str) if "local" in df.columns else ""
    saida["Categoria"] = (
        df["categoria"].fillna("--").astype(str) if "categoria" in df.columns else "--"
    )
    saida["Banco"] = (
        df["banco_origem"].fillna("--").astype(str) if "banco_origem" in df.columns else "--"
    )
    if "tag_irpf" in df.columns:
        saida["Documento"] = df["tag_irpf"].fillna("--").astype(str).replace("", "--")
    else:
        saida["Documento"] = "--"

    if mascarar_pii:
        for col in ("Local", "Categoria", "Documento"):
            saida[col] = saida[col].map(_mascarar_pii)

    return saida[colunas_finais].reset_index(drop=True)


# "O resultado pertence ao lugar onde a pergunta nasceu." -- Heráclito (parafraseado)
