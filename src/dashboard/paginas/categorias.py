"""Página Categorias — UX-RD-12.

Reescrita conforme mockup ``novo-mockup/mockups/11-categorias.html``.

Layout em grid 1.5fr / 1fr:

* **Esquerda** — árvore navegável de categorias (família por classificação
  canônica do schema -- `Obrigatório`, `Questionável`, `Supérfluo`, `N/A`),
  expandindo as `categoria` com count, valor e barra de proporção.
* **Direita (topo)** — treemap Plotly com paleta accent WCAG-AA validada
  contra ``#0e0f15`` (todos ≥ 4.5:1). Click em folha filtra Extrato via
  ``aplicar_drilldown`` (ADR-19, Sprint 73).
* **Direita (base)** — painel com regras YAML aplicadas, lidas de
  ``mappings/categorias.yaml`` e agrupadas pela categoria selecionada (ou
  globais quando não há seleção). Mostra regex, categoria-alvo e contagem
  de hits (quantas transações da categoria casariam aquela regra).

Funções públicas:

* ``renderizar(dados, mes_selecionado, pessoa, ctx)`` — entrypoint chamado
  pelo dispatcher do app. Assinatura preservada.

Funções puras testáveis (UX-RD-12 #3 da seção `tests`):

* ``calcular_arvore_categorias(df)`` — agrega despesas por classificação +
  categoria.
* ``calcular_kpis_categoria(df)`` — métricas dos 4 cards do topo.
* ``carregar_regras_yaml(path)`` — leitura idempotente de
  ``mappings/categorias.yaml`` com cache simples por path.
* ``agregar_regras_aplicadas(df, regras, categoria_filtro)`` — calcula
  ``hits`` por regra dentro do recorte filtrado.

WCAG-AA: paleta validada por
``_validar_contraste_paleta`` no momento da carga (assertiva quebra teste
caso alguém altere ``CORES`` para um tom abaixo de 4.5:1 no fundo dark).
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st
import yaml

from src.dashboard.componentes.drilldown import aplicar_drilldown
from src.dashboard.componentes.html_utils import minificar
from src.dashboard.dados import (
    filtrar_por_forma_pagamento,
    filtrar_por_periodo,
    filtrar_por_pessoa,
    filtro_forma_ativo,
    formatar_moeda,
)
from src.dashboard.tema import (
    CORES,
    LAYOUT_PLOTLY,
    MAPA_CLASSIFICACAO,
    aplicar_locale_ptbr,
    callout_html,
)

# Retrocompat com testes da Sprint 92a (test_dashboard_categorias.py): expõe o
# mapa classificação -> cor canônico, agora consolidado em ``tema.py``. A v2
# UX-RD-12 colore o treemap por categoria (não por classificação) com
# ``PALETA_WCAG_AA``; este alias permanece para uso externo eventual.
MAPA_CLASSIFICACAO_COR: dict[str, str] = MAPA_CLASSIFICACAO


# ---------------------------------------------------------------------------
# Paleta WCAG-AA validada contra fundo ``#0e0f15``
# ---------------------------------------------------------------------------
# Cada par (token CORES -> contraste mínimo medido):
#   positivo #50fa7b -> 13.94:1
#   negativo #ff5555 ->  6.09:1
#   neutro   #8be9fd -> 13.82:1
#   alerta   #ffb86c -> 11.23:1
#   destaque #bd93f9 ->  7.93:1
#   superfluo #ff79c6 ->  8.02:1
#   info     #f1fa8c -> 17.12:1
#   d7_graduado #6b8e7f -> 5.28:1
# Todas ≥ 4.5:1 (WCAG-AA texto normal). Seleção rotativa para colorir até 8
# folhas no treemap. Quando há mais de 8 categorias o ciclo se repete; isso
# é aceitável porque a área e o rótulo da folha continuam diferenciando.
PALETA_WCAG_AA: tuple[str, ...] = (
    CORES["destaque"],   # roxo
    CORES["superfluo"],  # rosa
    CORES["neutro"],     # ciano
    CORES["positivo"],   # verde
    CORES["alerta"],     # laranja
    CORES["info"],       # amarelo
    CORES["d7_graduado"],  # verde-musgo
    CORES["negativo"],   # vermelho
)


def _linearizar(canal: float) -> float:
    """Linearização sRGB (WCAG 2.1)."""
    return canal / 12.92 if canal <= 0.03928 else ((canal + 0.055) / 1.055) ** 2.4


def _luminância(hex_cor: str | None) -> float:
    """Luminância relativa de uma cor ``#RRGGBB``.

    Fallback: input inválido (None, string vazia, formato errado) devolve
    0.0 -- equivale a fundo preto, e callers escolhem branco por contraste.
    """
    if not hex_cor or not isinstance(hex_cor, str):
        return 0.0
    h = hex_cor.lstrip("#").strip()
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        return 0.0
    try:
        r = int(h[0:2], 16) / 255.0
        g = int(h[2:4], 16) / 255.0
        b = int(h[4:6], 16) / 255.0
    except ValueError:
        return 0.0
    return 0.2126 * _linearizar(r) + 0.7152 * _linearizar(g) + 0.0722 * _linearizar(b)


def calcular_contraste(cor_a: str, cor_b: str) -> float:
    """Razão de contraste WCAG entre duas cores ``#RRGGBB``."""
    la, lb = _luminância(cor_a), _luminância(cor_b)
    if la < lb:
        la, lb = lb, la
    return (la + 0.05) / (lb + 0.05)


def _validar_contraste_paleta(bg: str = None) -> dict[str, float]:
    """Devolve mapa cor->contraste contra ``bg``.

    Usado em testes para garantir que a paleta permanece WCAG-AA mesmo se
    alguém alterar ``CORES`` no futuro. Default ``bg`` = fundo dark canônico.
    """
    fundo = bg or CORES["fundo"]
    return {cor: calcular_contraste(fundo, cor) for cor in PALETA_WCAG_AA}


def _cor_texto_por_fundo(fundo_hex: str) -> str:
    """Preto sobre fundos claros (luminância > 0.6), branco caso contrário."""
    return "#000" if _luminância(fundo_hex) > 0.6 else "#fff"


# ---------------------------------------------------------------------------
# Carga de regras YAML
# ---------------------------------------------------------------------------
PATH_CATEGORIAS_YAML = Path("mappings/categorias.yaml")


@lru_cache(maxsize=8)
def carregar_regras_yaml(path: str | None = None) -> list[dict[str, Any]]:
    """Lê ``mappings/categorias.yaml`` e devolve lista de regras normalizada.

    Cada item: ``{"nome": str, "regex": str, "categoria": str, "tipo": str|None,
    "classificacao": str|None}``. Cache LRU evita re-leitura repetida durante
    a sessão. Idempotente quando o arquivo não muda.
    """
    p = Path(path) if path else PATH_CATEGORIAS_YAML
    if not p.exists():
        return []
    bruto = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    regras_dict = bruto.get("regras", {}) or {}
    saida: list[dict[str, Any]] = []
    for nome, regra in regras_dict.items():
        if not isinstance(regra, dict):
            continue
        saida.append(
            {
                "nome": str(nome),
                "regex": str(regra.get("regex", "")),
                "categoria": str(regra.get("categoria", "")),
                "tipo": regra.get("tipo"),
                "classificacao": regra.get("classificacao"),
            }
        )
    return saida


def agregar_regras_aplicadas(
    df: pd.DataFrame,
    regras: list[dict[str, Any]],
    categoria_filtro: str | None = None,
) -> list[dict[str, Any]]:
    """Conta hits de cada regra dentro do recorte ``df``.

    Quando ``categoria_filtro`` é fornecido, devolve só regras cuja
    ``categoria`` casa com esse valor (ordenadas por hits desc). Quando é
    None, devolve todas as regras com hits > 0 (top 8 por hits).
    """
    if df.empty or not regras:
        return []
    # `local` é o campo bruto disponível para todas as transações; quando
    # disponível, usamos `_descricao_original` como em irpf_tagger.
    coluna = "_descricao_original" if "_descricao_original" in df.columns else "local"
    if coluna not in df.columns:
        return []
    series = df[coluna].fillna("").astype(str)

    resultado: list[dict[str, Any]] = []
    for regra in regras:
        if categoria_filtro and regra["categoria"] != categoria_filtro:
            continue
        regex = regra["regex"]
        if not regex:
            continue
        try:
            hits = int(series.str.contains(regex, regex=True, case=False, na=False).sum())
        except re.error:
            hits = 0
        if categoria_filtro is None and hits == 0:
            continue
        resultado.append({**regra, "hits": hits})

    resultado.sort(key=lambda r: r["hits"], reverse=True)
    if categoria_filtro is None:
        resultado = resultado[:8]
    return resultado


# ---------------------------------------------------------------------------
# Agregações de domínio
# ---------------------------------------------------------------------------
def calcular_arvore_categorias(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Devolve árvore ``família -> [categoria, valor, count]``.

    A "família" (nó pai) é a coluna de classificação do extrato (com valores
    canônicos `Obrigatório`, `Questionável`, `Supérfluo`, `N/A`). A folha é
    `categoria`. Ordenado por valor descendente em cada nível.
    """
    if df.empty:
        return []
    base = (
        df.groupby(["classificacao", "categoria"])
        .agg(valor=("valor", lambda s: float(s.abs().sum())), count=("valor", "size"))
        .reset_index()
    )
    if base.empty:
        return []
    arvore: list[dict[str, Any]] = []
    for clas, grupo in base.groupby("classificacao"):
        sub = (
            grupo[["categoria", "valor", "count"]]
            .sort_values("valor", ascending=False)
            .to_dict("records")
        )
        total_clas = float(grupo["valor"].sum())
        count_clas = int(grupo["count"].sum())
        arvore.append(
            {
                "classificacao": str(clas),
                "valor": total_clas,
                "count": count_clas,
                "subcategorias": sub,
            }
        )
    arvore.sort(key=lambda n: n["valor"], reverse=True)
    return arvore


def calcular_kpis_categoria(df: pd.DataFrame) -> dict[str, Any]:
    """Métricas para os 4 cards do topo."""
    if df.empty:
        return {
            "saida_total": 0.0,
            "transacoes": 0,
            "cobertura_pct": 0.0,
            "categorias_ativas": 0,
            "maior_familia": ("—", 0.0, 0.0),
            "nao_classificadas": 0,
            "valor_nao_classif": 0.0,
        }
    valor_abs = df["valor"].abs()
    total = float(valor_abs.sum())
    transacoes = int(len(df))

    # cobertura: 1 - fração com categoria == "Outros" (fallback do categorizer)
    nao_classif_mask = df["categoria"].fillna("Outros").eq("Outros")
    nao_classif = int(nao_classif_mask.sum())
    valor_nao_classif = float(valor_abs[nao_classif_mask].sum())
    cobertura = 100.0 * (1.0 - nao_classif / transacoes) if transacoes else 0.0

    categorias_ativas = int(df["categoria"].fillna("Outros").nunique())

    soma_por_cat = df.assign(valor_abs=valor_abs).groupby("categoria")["valor_abs"].sum()
    if not soma_por_cat.empty:
        cat_top = str(soma_por_cat.idxmax())
        valor_top = float(soma_por_cat.max())
        pct_top = 100.0 * valor_top / total if total else 0.0
    else:
        cat_top, valor_top, pct_top = "—", 0.0, 0.0

    return {
        "saida_total": total,
        "transacoes": transacoes,
        "cobertura_pct": round(cobertura, 1),
        "categorias_ativas": categorias_ativas,
        "maior_familia": (cat_top, valor_top, round(pct_top, 1)),
        "nao_classificadas": nao_classif,
        "valor_nao_classif": valor_nao_classif,
    }


# ---------------------------------------------------------------------------
# CSS local (página-específico) — não toca tema_css.py
# ---------------------------------------------------------------------------
_CSS_PAGINA = minificar(
    """
    <style>
    .ux-rd-12-kpi-row {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: var(--sp-3, 12px);
        margin-bottom: var(--sp-4, 16px);
    }
    .ux-rd-12-kpi {
        background: var(--bg-surface, #1a1d28);
        border: 1px solid var(--border-subtle, #313445);
        border-radius: var(--r-md, 6px);
        padding: var(--sp-4, 16px);
    }
    .ux-rd-12-kpi .l {
        font-family: var(--ff-mono, monospace);
        font-size: 10px;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--text-muted, #6c6f7d);
    }
    .ux-rd-12-kpi .v {
        font-family: var(--ff-mono, monospace);
        font-size: 26px;
        font-weight: 500;
        line-height: 1;
        margin-top: 6px;
        font-variant-numeric: tabular-nums;
    }
    .ux-rd-12-kpi .d {
        font-family: var(--ff-mono, monospace);
        font-size: 11px;
        color: var(--text-muted, #6c6f7d);
        margin-top: 6px;
    }
    .ux-rd-12-grid {
        display: grid;
        grid-template-columns: 1.5fr 1fr;
        gap: var(--sp-3, 12px);
    }
    .ux-rd-12-card {
        background: var(--bg-surface, #1a1d28);
        border: 1px solid var(--border-subtle, #313445);
        border-radius: var(--r-md, 6px);
        margin-bottom: var(--sp-3, 12px);
    }
    .ux-rd-12-card .head {
        padding: var(--sp-3, 12px) var(--sp-4, 16px);
        border-bottom: 1px solid var(--border-subtle, #313445);
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .ux-rd-12-card .head h3 {
        font-family: var(--ff-mono, monospace);
        font-size: 11px;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--text-secondary, #a8a9b8);
        margin: 0;
    }
    .ux-rd-12-tree {
        padding: var(--sp-3, 12px);
    }
    .ux-rd-12-cat-row {
        display: grid;
        grid-template-columns: 1fr 80px 100px;
        gap: var(--sp-3, 12px);
        align-items: center;
        padding: 8px var(--sp-3, 12px);
        border-radius: var(--r-sm, 4px);
    }
    .ux-rd-12-cat-row.l1 {
        font-weight: 500;
    }
    .ux-rd-12-cat-row.l2 {
        padding-left: var(--sp-5, 20px);
        font-size: 12px;
    }
    .ux-rd-12-cat-row.l2 .name {
        color: var(--text-secondary, #a8a9b8);
    }
    .ux-rd-12-cat-row .name {
        font-family: var(--ff-mono, monospace);
        font-size: 13px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .ux-rd-12-cat-row .name .dot {
        width: 10px;
        height: 10px;
        border-radius: 2px;
        flex-shrink: 0;
    }
    .ux-rd-12-cat-row .pct {
        font-family: var(--ff-mono, monospace);
        font-size: 11px;
        color: var(--text-muted, #6c6f7d);
        text-align: right;
        font-variant-numeric: tabular-nums;
    }
    .ux-rd-12-cat-row .v {
        font-family: var(--ff-mono, monospace);
        font-size: 13px;
        text-align: right;
        font-variant-numeric: tabular-nums;
    }
    .ux-rd-12-cat-row .bar {
        grid-column: 1/-1;
        height: 3px;
        background: var(--bg-inset, #0a0b10);
        border-radius: var(--r-full, 999px);
        overflow: hidden;
        margin-top: 4px;
    }
    .ux-rd-12-cat-row .bar > span {
        display: block;
        height: 100%;
    }
    details.ux-rd-12-fam {
        border: none;
        margin-bottom: 4px;
    }
    details.ux-rd-12-fam > summary {
        list-style: none;
        cursor: pointer;
    }
    details.ux-rd-12-fam > summary::-webkit-details-marker {
        display: none;
    }
    .ux-rd-12-fam .arrow {
        display: inline-block;
        width: 12px;
        color: var(--text-muted, #6c6f7d);
        transition: transform 0.15s;
    }
    details[open].ux-rd-12-fam .arrow {
        transform: rotate(90deg);
    }
    .ux-rd-12-rules {
        padding: var(--sp-4, 16px);
    }
    .ux-rd-12-rules h3 {
        font-family: var(--ff-mono, monospace);
        font-size: 11px;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--text-secondary, #a8a9b8);
        margin: 0 0 var(--sp-3, 12px);
    }
    .ux-rd-12-rule {
        display: grid;
        grid-template-columns: 1fr auto;
        gap: var(--sp-2, 8px);
        padding: var(--sp-2, 8px) 0;
        border-bottom: 1px dashed var(--border-subtle, #313445);
        font-size: 12px;
    }
    .ux-rd-12-rule:last-child {
        border-bottom: none;
    }
    .ux-rd-12-rule .regex {
        font-family: var(--ff-mono, monospace);
        color: var(--accent-purple, #bd93f9);
        font-size: 11px;
        word-break: break-all;
    }
    .ux-rd-12-rule .desc {
        font-family: var(--ff-mono, monospace);
        color: var(--text-secondary, #a8a9b8);
        margin-top: 2px;
    }
    .ux-rd-12-rule .ct {
        font-family: var(--ff-mono, monospace);
        font-size: 11px;
        color: var(--text-muted, #6c6f7d);
        white-space: nowrap;
    }
    .ux-rd-12-empty {
        font-family: var(--ff-mono, monospace);
        color: var(--text-muted, #6c6f7d);
        font-size: 12px;
        padding: var(--sp-3, 12px);
        text-align: center;
    }
    </style>
    """
)


# ---------------------------------------------------------------------------
# Renderização HTML (puras)
# ---------------------------------------------------------------------------
def _kpis_html(kpis: dict[str, Any]) -> str:
    cat_top, valor_top, pct_top = kpis["maior_familia"]
    cobertura = kpis["cobertura_pct"]
    cor_cob = (
        CORES["positivo"]
        if cobertura >= 90
        else CORES["alerta"]
        if cobertura >= 70
        else CORES["negativo"]
    )
    return minificar(
        f"""
        <div class="ux-rd-12-kpi-row">
            <div class="ux-rd-12-kpi">
                <div class="l">Saída · período</div>
                <div class="v">{formatar_moeda(kpis["saida_total"])}</div>
                <div class="d">{kpis["transacoes"]} transações</div>
            </div>
            <div class="ux-rd-12-kpi">
                <div class="l">Cobertura auto</div>
                <div class="v" style="color:{cor_cob};">{cobertura:.0f}%</div>
                <div class="d">{kpis["categorias_ativas"]} categorias ativas</div>
            </div>
            <div class="ux-rd-12-kpi">
                <div class="l">Maior família</div>
                <div class="v" style="color:{CORES["superfluo"]};">{pct_top:.0f}%</div>
                <div class="d">{cat_top} · {formatar_moeda(valor_top)}</div>
            </div>
            <div class="ux-rd-12-kpi">
                <div class="l">Não-classificadas</div>
                <div class="v" style="color:{CORES["info"]};">{kpis["nao_classificadas"]}</div>
                <div class="d">{formatar_moeda(kpis["valor_nao_classif"])} · revisar</div>
            </div>
        </div>
        """
    )


def _arvore_html(arvore: list[dict[str, Any]], total: float) -> str:
    """Renderiza árvore expansível (HTML <details>) por família."""
    if not arvore or total <= 0:
        return '<div class="ux-rd-12-empty">Sem dados para o período.</div>'

    blocos: list[str] = []
    for i, fam in enumerate(arvore):
        cor_fam = PALETA_WCAG_AA[i % len(PALETA_WCAG_AA)]
        pct_fam = 100.0 * fam["valor"] / total if total else 0.0
        sub_html_parts: list[str] = []
        for j, sub in enumerate(fam["subcategorias"]):
            cor_sub = PALETA_WCAG_AA[(i + j) % len(PALETA_WCAG_AA)]
            pct_sub = 100.0 * sub["valor"] / total if total else 0.0
            sub_html_parts.append(
                f"""
                <div class="ux-rd-12-cat-row l2" data-categoria="{sub["categoria"]}">
                    <div class="name">
                        <span class="dot" style="background:{cor_sub};"></span>
                        {sub["categoria"]}
                    </div>
                    <div class="pct">{pct_sub:.1f}%</div>
                    <div class="v">{formatar_moeda(sub["valor"])}</div>
                    <div class="bar">
                        <span style="width:{pct_sub}%;background:{cor_sub};"></span>
                    </div>
                </div>
                """
            )
        sub_html = "".join(sub_html_parts)

        # Primeira família já vem aberta (mockup espelhado).
        aberto = " open" if i == 0 else ""
        blocos.append(
            f"""
            <details class="ux-rd-12-fam"{aberto}>
                <summary>
                    <div class="ux-rd-12-cat-row l1">
                        <div class="name">
                            <span class="arrow">›</span>
                            <span class="dot" style="background:{cor_fam};"></span>
                            {fam["classificacao"]}
                        </div>
                        <div class="pct">{pct_fam:.1f}%</div>
                        <div class="v">{formatar_moeda(fam["valor"])}</div>
                        <div class="bar">
                            <span style="width:{pct_fam}%;background:{cor_fam};"></span>
                        </div>
                    </div>
                </summary>
                {sub_html}
            </details>
            """
        )
    return minificar(
        '<div class="ux-rd-12-card"><div class="head"><h3>Árvore · período</h3></div>'
        f'<div class="ux-rd-12-tree">{"".join(blocos)}</div></div>'
    )


def _regras_yaml_html(
    regras: list[dict[str, Any]],
    categoria_filtro: str | None = None,
) -> str:
    titulo = (
        f"Regras YAML — {categoria_filtro}"
        if categoria_filtro
        else "Regras YAML — top hits"
    )
    if not regras:
        corpo = (
            '<div class="ux-rd-12-empty">'
            f'Sem regras com hits para {"esta categoria" if categoria_filtro else "o período"}.'
            "</div>"
        )
    else:
        partes: list[str] = []
        for regra in regras:
            classif = regra.get("classificacao") or regra.get("tipo") or ""
            sufixo = f" ({classif})" if classif else ""
            partes.append(
                f"""
                <div class="ux-rd-12-rule" data-categoria="{regra["categoria"]}">
                    <div>
                        <div class="regex">desc ~ /{regra["regex"]}/i</div>
                        <div class="desc">→ <strong>{regra["categoria"]}</strong>{sufixo}</div>
                    </div>
                    <div class="ct">{regra["hits"]} hits</div>
                </div>
                """
            )
        corpo = "".join(partes)
    return minificar(
        f"""
        <div class="ux-rd-12-card ux-rd-12-rules">
            <h3>{titulo}</h3>
            {corpo}
        </div>
        """
    )


# ---------------------------------------------------------------------------
# Treemap Plotly (paleta WCAG-AA + drilldown)
# ---------------------------------------------------------------------------
def _treemap_categorias(df: pd.DataFrame) -> None:
    """Treemap com paleta WCAG-AA e drill-down para Extrato."""
    agrupado = (
        df.assign(valor_abs=df["valor"].abs())
        .groupby(["classificacao", "categoria"])["valor_abs"]
        .sum()
        .reset_index()
        .sort_values("valor_abs", ascending=False)
    )
    if agrupado.empty:
        return

    # Paleta accent rotativa, ancorada no índice da categoria. Garante que
    # cada folha tenha cor com contraste WCAG-AA contra `#0e0f15`.
    cores_categoria = {
        cat: PALETA_WCAG_AA[i % len(PALETA_WCAG_AA)]
        for i, cat in enumerate(agrupado["categoria"].unique())
    }

    fig = px.treemap(
        agrupado,
        path=["classificacao", "categoria"],
        values="valor_abs",
        color="categoria",
        color_discrete_map=cores_categoria,
    )

    fig.update_layout(
        **{**LAYOUT_PLOTLY, "margin": dict(l=0, r=0, t=10, b=0)},
        uniformtext=dict(minsize=12, mode="hide"),
    )

    cores_texto_leaf = [
        _cor_texto_por_fundo(cores_categoria.get(c, CORES["fundo"]))
        for c in agrupado["categoria"]
    ]
    fig.update_traces(
        textinfo="label+value",
        texttemplate="<b>%{label}</b><br>R$ %{value:,.2f}",
        textfont=dict(size=13, family="monospace", color=cores_texto_leaf),
        marker=dict(line=dict(color=CORES["fundo"], width=2)),
        textposition="middle center",
        tiling=dict(pad=4),
        customdata=agrupado["categoria"],
    )

    aplicar_locale_ptbr(fig)
    aplicar_drilldown(
        fig,
        campo_customdata="categoria",
        tab_destino="Extrato",
        key_grafico="treemap_categorias_ux_rd_12",
    )


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
def renderizar(
    dados: dict[str, pd.DataFrame],
    mes_selecionado: str,
    pessoa: str,
    ctx: dict | None = None,
) -> None:
    """Renderiza a página Categorias (UX-RD-12)."""
    st.markdown(_CSS_PAGINA, unsafe_allow_html=True)

    if "extrato" not in dados:
        st.markdown(
            callout_html("warning", "Nenhum dado encontrado para análise de categorias."),
            unsafe_allow_html=True,
        )
        return

    gran = ctx.get("granularidade", "Mês") if ctx else "Mês"
    periodo = ctx.get("periodo", mes_selecionado) if ctx else mes_selecionado

    extrato = dados["extrato"]
    df_filtrado = filtrar_por_forma_pagamento(
        filtrar_por_pessoa(extrato, pessoa), filtro_forma_ativo()
    )
    df = filtrar_por_periodo(df_filtrado, gran, periodo)
    df = df[df["tipo"].isin(["Despesa", "Imposto"])].copy()

    if df.empty:
        st.markdown(
            callout_html("info", "Sem despesas para o período selecionado."),
            unsafe_allow_html=True,
        )
        return

    # Header + KPIs
    kpis = calcular_kpis_categoria(df)
    header_html = minificar(
        f"""
        <div class="page-header">
            <div>
                <h1 class="page-title">CATEGORIAS</h1>
                <p class="page-subtitle">
                    Hierarquia de categorias com regras de auto-classificação.
                    Cobertura:
                    <strong style="color:{CORES["positivo"]};">
                        {kpis["cobertura_pct"]:.0f}%
                    </strong>.
                    <strong style="color:{CORES["info"]};">
                        {kpis["nao_classificadas"]}
                    </strong>
                    transações não-classificadas.
                </p>
            </div>
            <div class="page-meta">
                <span class="sprint-tag">UX-RD-12</span>
                <span class="pill pill-d7-graduado">
                    {kpis["categorias_ativas"]} categorias
                    · {kpis["transacoes"]} txns
                </span>
            </div>
        </div>
        """
    )
    st.markdown(header_html, unsafe_allow_html=True)
    st.markdown(_kpis_html(kpis), unsafe_allow_html=True)

    # Layout 1.5fr / 1fr: árvore | (treemap + regras)
    col_arvore, col_dir = st.columns([1.5, 1])

    arvore = calcular_arvore_categorias(df)
    total = sum(n["valor"] for n in arvore)

    with col_arvore:
        st.markdown(_arvore_html(arvore, total), unsafe_allow_html=True)

    with col_dir:
        st.markdown(
            minificar(
                '<div class="ux-rd-12-card">'
                '<div class="head"><h3>Treemap · proporção</h3>'
                '<span style="font-family:var(--ff-mono);font-size:11px;'
                'color:var(--text-muted);">área = valor</span></div>'
                "</div>"
            ),
            unsafe_allow_html=True,
        )
        _treemap_categorias(df)

        # Painel regras YAML — categoria selecionada via session_state ou
        # query_params. Quando não há filtro, mostra top hits global.
        categoria_filtro = (
            st.session_state.get("filtro_categoria")
            or st.query_params.get("categoria")
        )
        regras = carregar_regras_yaml()
        regras_aplicadas = agregar_regras_aplicadas(df, regras, categoria_filtro)
        st.markdown(
            _regras_yaml_html(regras_aplicadas, categoria_filtro),
            unsafe_allow_html=True,
        )


# "Categorizar é compreender." -- princípio da taxonomia
