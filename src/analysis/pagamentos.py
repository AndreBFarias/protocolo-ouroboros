"""Agregações por forma de pagamento (Sprint 79).

Separa a aba `extrato` em três perspectivas úteis para rastreabilidade:

  - Boletos (pagos + esperados a partir da aba `prazos`).
  - Pix (agrupamento por beneficiário).
  - Crédito (faturas por cartão + mês).

Mantém-se Local First: lê apenas os DataFrames já carregados pelo dashboard
(extrato + prazos). Tolerante a colunas ausentes — cada função retorna
DataFrame vazio ou dict vazio em vez de levantar exceção.
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Any

import pandas as pd

if TYPE_CHECKING:  # pragma: no cover -- só para anotações de tipo
    from src.graph.db import GrafoDB

STATUS_PAGO: str = "pago"
STATUS_PENDENTE: str = "pendente"
STATUS_ATRASADO: str = "atrasado"

# Sprint 87.7: abaixo deste número de arestas `documento_de` no grafo,
# a reconciliação via grafo não é representativa e o caller deve cair na
# heurística textual (`carregar_boletos`).
LIMIAR_GRAFO_PADRAO: int = 10


def carregar_boletos(
    extrato: pd.DataFrame,
    prazos: pd.DataFrame | None = None,
    hoje: date | None = None,
) -> pd.DataFrame:
    """Monta DataFrame de boletos — pagos no extrato + esperados em `prazos`.

    Boleto pago é uma linha do extrato com `forma_pagamento='Boleto'`.
    Boleto esperado é cada linha da aba `prazos` com `dia_vencimento` no
    mês corrente que não tem contraparte no extrato (match por
    `conta` ~ `local` + valor +/- 5%).

    Status:
      - pago: existe transação correspondente no extrato
      - pendente: vencimento >= hoje sem transação correspondente
      - atrasado: vencimento < hoje sem transação correspondente
    """
    hoje = hoje or date.today()
    boletos_pagos = _extrair_boletos_pagos(extrato)
    if prazos is None or prazos.empty:
        # Sem aba prazos só há os boletos efetivamente pagos.
        boletos_pagos["status"] = STATUS_PAGO
        return boletos_pagos

    esperados = _projetar_boletos_esperados(prazos, extrato, hoje)

    colunas = ["data", "fornecedor", "valor", "vencimento", "status", "banco_origem"]
    df = pd.concat([boletos_pagos, esperados], ignore_index=True, sort=False)
    for col in colunas:
        if col not in df.columns:
            df[col] = None
    # Normaliza `vencimento` para Timestamp antes de sort. `_extrair_boletos_pagos`
    # grava Timestamp (vindo do extrato); `_projetar_boletos_esperados` grava
    # string ISO (`date.isoformat()`). Sem coerce, `sort_values` levanta
    # TypeError ao comparar tipos diferentes. Inválidos viram NaT e caem no
    # fim via `na_position="last"`.
    df["vencimento"] = pd.to_datetime(df["vencimento"], errors="coerce")
    return df[colunas].sort_values(by="vencimento", na_position="last").reset_index(drop=True)


def _extrair_boletos_pagos(extrato: pd.DataFrame) -> pd.DataFrame:
    if "forma_pagamento" not in extrato.columns:
        return pd.DataFrame()
    df = extrato[extrato["forma_pagamento"].astype(str).str.lower() == "boleto"].copy()
    if df.empty:
        return pd.DataFrame()
    return pd.DataFrame(
        {
            "data": df.get("data"),
            "fornecedor": df.get("local"),
            "valor": df.get("valor").abs() if "valor" in df.columns else None,
            "vencimento": df.get("data"),
            "status": STATUS_PAGO,
            "banco_origem": df.get("banco_origem"),
        }
    )


def _projetar_boletos_esperados(
    prazos: pd.DataFrame, extrato: pd.DataFrame, hoje: date
) -> pd.DataFrame:
    """Para cada linha da aba `prazos`, projeta boleto esperado do mês."""
    if "conta" not in prazos.columns or "dia_vencimento" not in prazos.columns:
        return pd.DataFrame()

    linhas: list[dict[str, Any]] = []
    mes_atual = hoje.replace(day=1)

    for _, prazo in prazos.iterrows():
        conta = str(prazo.get("conta") or "").strip()
        if not conta:
            continue
        dia_raw = prazo.get("dia_vencimento")
        try:
            dia = int(dia_raw)
        except (TypeError, ValueError):
            continue
        try:
            vencimento = mes_atual.replace(day=min(dia, 28))
        except ValueError:
            continue

        foi_pago = _existe_boleto_pago(extrato, conta, mes_atual)
        if foi_pago:
            continue
        status = STATUS_ATRASADO if vencimento < hoje else STATUS_PENDENTE

        linhas.append(
            {
                "data": None,
                "fornecedor": conta,
                "valor": None,
                "vencimento": vencimento.isoformat(),
                "status": status,
                "banco_origem": prazo.get("banco_pagamento"),
            }
        )

    return pd.DataFrame(linhas)


def _existe_boleto_pago(extrato: pd.DataFrame, conta: str, mes_atual: date) -> bool:
    if "mes_ref" not in extrato.columns or "local" not in extrato.columns:
        return False
    mes_ref = mes_atual.strftime("%Y-%m")
    sub = extrato[extrato["mes_ref"].astype(str) == mes_ref]
    if sub.empty:
        return False
    conta_lower = conta.lower()
    mascara = (
        sub["local"]
        .fillna("")
        .astype(str)
        .str.lower()
        .str.contains(conta_lower[:10], na=False, regex=False)
    )
    return bool(mascara.any())


def alertas_vencimento(
    boletos: pd.DataFrame, hoje: date | None = None, dias_aviso: int = 3
) -> list[str]:
    """Gera alertas para boletos com vencimento nos próximos `dias_aviso` dias."""
    if boletos.empty or "vencimento" not in boletos.columns:
        return []
    hoje = hoje or date.today()
    avisos: list[str] = []
    for _, row in boletos.iterrows():
        status = str(row.get("status", "")).lower()
        if status != STATUS_PENDENTE:
            continue
        venc_raw = row.get("vencimento")
        try:
            venc = date.fromisoformat(str(venc_raw)[:10])
        except (ValueError, TypeError):
            continue
        delta = (venc - hoje).days
        if 0 <= delta <= dias_aviso:
            avisos.append(
                f"{row.get('fornecedor', 'Boleto')} vence em {delta} dia(s) "
                f"({venc.isoformat()}) e ainda não foi pago."
            )
    return avisos


def top_beneficiarios_pix(extrato: pd.DataFrame, top_n: int = 20) -> pd.DataFrame:
    """DataFrame com top N beneficiários de Pix por valor absoluto."""
    if "forma_pagamento" not in extrato.columns:
        return pd.DataFrame(columns=["local", "total", "quantidade"])
    pix = extrato[extrato["forma_pagamento"].astype(str).str.lower() == "pix"].copy()
    if pix.empty or "local" not in pix.columns:
        return pd.DataFrame(columns=["local", "total", "quantidade"])
    pix = pix[pix["tipo"].isin(("Despesa", "Imposto"))] if "tipo" in pix.columns else pix
    agrupado = (
        pix.assign(valor_abs=pix["valor"].abs())
        .groupby("local")
        .agg(total=("valor_abs", "sum"), quantidade=("valor_abs", "count"))
        .sort_values("total", ascending=False)
        .head(top_n)
        .reset_index()
    )
    return agrupado


def faturas_credito(extrato: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Agrupa despesas de cartão de crédito por banco e mês."""
    if "forma_pagamento" not in extrato.columns or "banco_origem" not in extrato.columns:
        return {}
    credito = extrato[extrato["forma_pagamento"].astype(str).str.lower() == "crédito"]
    if credito.empty:
        return {}
    credito = credito[credito["tipo"].isin(("Despesa",))] if "tipo" in credito.columns else credito
    resultado: dict[str, pd.DataFrame] = {}
    for banco, df_banco in credito.groupby("banco_origem"):
        if "mes_ref" not in df_banco.columns:
            continue
        agrupado = (
            df_banco.groupby("mes_ref")["valor"].sum().abs().reset_index().sort_values("mes_ref")
        )
        resultado[str(banco)] = agrupado.rename(columns={"valor": "valor_total"})
    return resultado


def _reconciliar_via_grafo(db: "GrafoDB", boleto_node: Any, hoje: date) -> str:
    """Sprint 87.7: decide status de um node `documento` de tipo `boleto_servico`.

    Critério:
      - Se há ao menos uma aresta `documento_de` saindo deste node -> `pago`.
      - Caso contrário, compara `metadata.vencimento` com `hoje`:
          - vencimento < hoje -> `atrasado`
          - vencimento >= hoje -> `pendente`
          - vencimento ausente -> `pendente` (graceful; sem condição de atrasado)
    """
    arestas = db.listar_edges(src_id=boleto_node.id, tipo="documento_de")
    if arestas:
        return STATUS_PAGO

    venc_raw = (boleto_node.metadata or {}).get("vencimento")
    if not venc_raw:
        return STATUS_PENDENTE
    try:
        venc = date.fromisoformat(str(venc_raw)[:10])
    except (TypeError, ValueError):
        return STATUS_PENDENTE
    return STATUS_ATRASADO if venc < hoje else STATUS_PENDENTE


def carregar_boletos_via_grafo(
    db: "GrafoDB",
    prazos: pd.DataFrame | None = None,
    hoje: date | None = None,
    limiar: int = LIMIAR_GRAFO_PADRAO,
) -> pd.DataFrame | None:
    """Sprint 87.7: reconciliação boleto-transação via arestas `documento_de`.

    Varre nodes `documento` com `metadata.tipo_documento == 'boleto_servico'`
    e classifica cada um em `pago` (tem aresta `documento_de`) ou
    `pendente`/`atrasado` (sem aresta, vencimento no futuro ou no passado).

    Retorna `None` -- sentinela que sinaliza ao caller para cair no fallback
    textual -- quando o grafo tem menos de `limiar` arestas `documento_de`
    no total. Isso protege contra reconciliação enganosa enquanto o motor
    da Sprint 48 ainda não rodou em volume.

    Schema do DataFrame devolvido é idêntico ao de `carregar_boletos`:
    (data, fornecedor, valor, vencimento, status, banco_origem).

    `prazos` é aceito para compatibilidade de assinatura, mas hoje a função
    não cruza com a aba prazos -- a verdade vem do grafo. Projeções de aba
    `prazos` permanecem responsabilidade de `carregar_boletos`.
    """
    from src.graph.queries import total_arestas_por_tipo

    del prazos  # reservado para uso futuro (união com aba prazos)
    hoje = hoje or date.today()

    total_edges = total_arestas_por_tipo(db, "documento_de")
    if total_edges < limiar:
        return None

    linhas: list[dict[str, Any]] = []
    for nd in db.listar_nodes(tipo="documento"):
        meta = nd.metadata or {}
        if meta.get("tipo_documento") != "boleto_servico":
            continue
        status = _reconciliar_via_grafo(db, nd, hoje)
        valor_raw = meta.get("total")
        try:
            valor = float(valor_raw) if valor_raw is not None else None
        except (TypeError, ValueError):
            valor = None
        fornecedor = meta.get("razao_social") or nd.nome_canonico
        vencimento = meta.get("vencimento")
        data_emissao = meta.get("data_emissao")
        linhas.append(
            {
                "data": data_emissao,
                "fornecedor": fornecedor,
                "valor": valor,
                "vencimento": vencimento,
                "status": status,
                "banco_origem": meta.get("banco_origem"),
            }
        )

    colunas = ["data", "fornecedor", "valor", "vencimento", "status", "banco_origem"]
    if not linhas:
        return pd.DataFrame(columns=colunas)
    df = pd.DataFrame(linhas)
    for col in colunas:
        if col not in df.columns:
            df[col] = None
    return df[colunas].sort_values(by="vencimento", na_position="last").reset_index(drop=True)


def carregar_boletos_inteligente(
    extrato: pd.DataFrame,
    prazos: pd.DataFrame | None = None,
    hoje: date | None = None,
    db: "GrafoDB | None" = None,
    limiar: int = LIMIAR_GRAFO_PADRAO,
) -> pd.DataFrame:
    """Sprint 87.7: wrapper que prefere grafo e cai para heurística textual.

    - Se `db` é None: chama diretamente `carregar_boletos` (comportamento antigo).
    - Se `db` existe: tenta `carregar_boletos_via_grafo`. Se retorna `None`
      (cobertura abaixo do limiar), cai para `carregar_boletos`.

    Preserva retrocompatibilidade total: o dashboard pode adotar a função
    nova sem mudar testes antigos de `carregar_boletos`.
    """
    if db is None:
        return carregar_boletos(extrato, prazos, hoje)
    via_grafo = carregar_boletos_via_grafo(db, prazos, hoje, limiar=limiar)
    if via_grafo is None:
        return carregar_boletos(extrato, prazos, hoje)
    return via_grafo


# "Por forma de pagamento é como o banco pensa; precisamos pensar assim também." — Sprint 79
