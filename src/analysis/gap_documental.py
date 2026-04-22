"""Gap Analysis documental (Sprint 75 — ADR-20).

Cruza a aba `extrato` do XLSX com as categorias declaradas em
`mappings/categorias_tracking.yaml` para identificar transações que, pela
natureza da categoria, deveriam ter comprovante mas não têm. Produz um
resumo estruturado `mês → categoria → {total, com_doc, sem_doc, orfas}` e
gera alertas textuais de recorrência.

Princípios:
  - Local First (ADR-07): só lê XLSX + YAML, nunca rede.
  - Resiliência (ADR-10): XLSX ausente ou YAML vazio não quebra — devolve
    estruturas vazias e o dashboard exibe placeholder.
  - Sem inferência mágica: se não há regra no YAML, categoria não entra
    no resumo. O usuário controla a lista de categorias obrigatórias.

API pública:

    calcular_completude(df, categorias_obrigatorias, ids_com_doc=None) -> dict
    alertas(resumo) -> list[str]
    carregar_categorias_obrigatorias() -> frozenset[str]
    orfas_para_csv(resumo) -> pd.DataFrame
"""

from __future__ import annotations

from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

_RAIZ_REPO: Path = Path(__file__).resolve().parents[2]
_CAMINHO_CATEGORIAS: Path = _RAIZ_REPO / "mappings" / "categorias_tracking.yaml"


@lru_cache(maxsize=1)
def carregar_categorias_obrigatorias() -> frozenset[str]:
    """Lê `mappings/categorias_tracking.yaml` e devolve o conjunto de categorias
    que exigem comprovante. Retorna frozenset vazio se YAML ausente/inválido."""
    if not _CAMINHO_CATEGORIAS.exists():
        return frozenset()
    try:
        dados = yaml.safe_load(_CAMINHO_CATEGORIAS.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError):
        return frozenset()
    lista = (dados or {}).get("obrigatoria_tracking", []) or []
    return frozenset(str(c) for c in lista)


def _tem_documento(tx: pd.Series, ids_com_doc: set[Any] | None) -> bool:
    """True quando a transação tem aresta `documento_de` no grafo.

    Como o grafo ainda não mapeia 1-para-1 com linhas do XLSX, usamos uma
    heurística pragmática: se o `identificador` da transação está em
    `ids_com_doc` (conjunto pré-computado pelo chamador), consideramos
    documentada. Na ausência do set, tudo é considerado "sem_doc".
    """
    if ids_com_doc is None:
        return False
    ident = tx.get("identificador")
    if ident is None or pd.isna(ident):
        return False
    return ident in ids_com_doc


def calcular_completude(
    df: pd.DataFrame,
    categorias_obrigatorias: frozenset[str] | None = None,
    ids_com_doc: set[Any] | None = None,
) -> dict[str, dict[str, dict[str, Any]]]:
    """Calcula resumo mensal de completude documental.

    Argumentos:
      - df: DataFrame da aba `extrato` com colunas `mes_ref`, `categoria`,
        `tipo`, `valor`, `local`, `data`, `identificador`.
      - categorias_obrigatorias: conjunto canônico (default = lê do YAML).
      - ids_com_doc: set com identificadores de transações que já possuem
        aresta `documento_de` no grafo (opcional; sem ele tudo é `sem_doc`).

    Retorna `{mes: {categoria: {total, com_doc, sem_doc, orfas: list[dict]}}}`,
    restrito a transações de tipo `Despesa` ou `Imposto` (receitas e TI não
    exigem comprovante). Meses sem nenhuma transação em categoria obrigatória
    não aparecem no dict.
    """
    categorias = (
        categorias_obrigatorias
        if categorias_obrigatorias is not None
        else carregar_categorias_obrigatorias()
    )
    if df.empty or not categorias:
        return {}

    subset = df[df["categoria"].isin(categorias)].copy()
    if "tipo" in subset.columns:
        subset = subset[subset["tipo"].isin(("Despesa", "Imposto"))]
    if subset.empty:
        return {}

    resumo: dict[str, dict[str, dict[str, Any]]] = defaultdict(
        lambda: defaultdict(
            lambda: {"total": 0, "com_doc": 0, "sem_doc": 0, "orfas": []}
        )
    )
    for _, tx in subset.iterrows():
        mes_ref = str(tx.get("mes_ref", "sem-mes"))
        cat = str(tx.get("categoria"))
        info = resumo[mes_ref][cat]
        info["total"] += 1
        tem_doc = _tem_documento(tx, ids_com_doc)
        if tem_doc:
            info["com_doc"] += 1
        else:
            info["sem_doc"] += 1
            info["orfas"].append(
                {
                    "data": str(tx.get("data", "")),
                    "valor": float(tx.get("valor") or 0.0),
                    "local": str(tx.get("local", "")),
                    "banco_origem": str(tx.get("banco_origem", "")),
                    "identificador": str(tx.get("identificador", "")),
                }
            )
    # Converte defaultdict aninhado em dict puro (amigável para serialização)
    return {mes: dict(cats) for mes, cats in resumo.items()}


def _percentual_cobertura(info: dict[str, Any]) -> float:
    total = info.get("total", 0)
    if total == 0:
        return 100.0
    com_doc = info.get("com_doc", 0)
    return (com_doc / total) * 100.0


def alertas(
    resumo: dict[str, dict[str, dict[str, Any]]],
    valor_alto: float = 500.0,
    min_meses_recorrencia: int = 3,
) -> list[str]:
    """Gera alertas textuais a partir do resumo.

    - Recorrência: fornecedor aparece em N meses seguidos com valor >= 100
      sem comprovante.
    - Valor alto sem doc: transação >= `valor_alto` em categoria obrigatória.
    - Zero-cobertura: categoria obrigatória com 0 comprovantes no mês.
    """
    alerta_list: list[str] = []

    # Agrupa órfãs por (fornecedor, ano) para detectar recorrência.
    por_forn: dict[tuple[str, str], set[str]] = defaultdict(set)
    for mes, cats in resumo.items():
        ano = mes[:4]
        for _cat, info in cats.items():
            for orf in info["orfas"]:
                local = orf["local"][:30]
                if abs(orf["valor"]) >= 100:
                    por_forn[(local, ano)].add(mes)

    for (local, ano), meses in por_forn.items():
        if len(meses) >= min_meses_recorrencia:
            alerta_list.append(
                f"Fornecedor '{local}' sem comprovante em {len(meses)} meses "
                f"de {ano} — é recorrência contratual? Registre o contrato."
            )

    # Valor alto sem doc.
    for mes, cats in resumo.items():
        for cat, info in cats.items():
            for orf in info["orfas"]:
                if abs(orf["valor"]) >= valor_alto:
                    alerta_list.append(
                        f"{mes} — {cat}: R$ {abs(orf['valor']):.2f} em "
                        f"'{orf['local'][:30]}' sem comprovante. Revisar."
                    )

    # Zero-cobertura por categoria/mês.
    for mes, cats in resumo.items():
        for cat, info in cats.items():
            if info["total"] > 0 and info["com_doc"] == 0 and info["total"] >= 2:
                alerta_list.append(
                    f"{mes} — {cat}: {info['total']} transações, "
                    f"0 comprovantes. IRPF pode perder dedução."
                )

    return sorted(set(alerta_list))


def orfas_para_csv(
    resumo: dict[str, dict[str, dict[str, Any]]],
) -> pd.DataFrame:
    """Achata a lista de órfãs em DataFrame para export CSV."""
    linhas: list[dict[str, Any]] = []
    for mes, cats in resumo.items():
        for cat, info in cats.items():
            for orf in info["orfas"]:
                linhas.append(
                    {
                        "mes_ref": mes,
                        "categoria": cat,
                        "data": orf["data"],
                        "valor": orf["valor"],
                        "local": orf["local"],
                        "banco_origem": orf["banco_origem"],
                        "identificador": orf["identificador"],
                    }
                )
    return pd.DataFrame(linhas)


# "O que não é medido escapa." — Peter Drucker, Sprint 75
