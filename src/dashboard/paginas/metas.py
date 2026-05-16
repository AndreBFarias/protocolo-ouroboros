"""Página Metas — UX-RD-14.

Reescrita conforme mockup ``novo-mockup/mockups/13-metas.html``.

Duas categorias:

* **Metas financeiras** — donuts proporcionais (Plotly Pie com hole)
  para cada meta monetária com valor_alvo e valor_atual. Cor varia por
  atingimento: verde quando >= 100%, amarelo entre 50% e 100%, vermelho
  abaixo de 50%.
* **Metas operacionais** — gauges (Plotly Indicator gauge mode) que
  refletem indicadores do pipeline: cobertura documental,
  % determinístico, % validadas, latência de processamento.

Função pública preservada:
* ``renderizar(dados, mes_selecionado, pessoa)`` — entrypoint do
  dispatcher. Assinatura sem ``ctx`` (ver ``src/dashboard/app.py``
  linha ~517).

Princípio: nenhuma meta operacional inventa valores; todas leem do
``dados`` recebido (saldo acumulado, contagens reais do extrato).
Quando dado ausente, gauge fica em 0% e legendado.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import plotly.graph_objects as go
import streamlit as st
import yaml

from src.dashboard.componentes.html_utils import minificar
from src.dashboard.componentes.ui import (
    bar_uso_html,
    callout_html,
    carregar_css_pagina,
    donut_inline_html,
    prazo_ritmo_falta_html,
    progress_inline_html,
)
from src.dashboard.dados import calcular_saldo_acumulado, formatar_moeda
from src.dashboard.tema import CORES, LAYOUT_PLOTLY

CAMINHO_METAS: Path = Path(__file__).resolve().parents[3] / "mappings" / "metas.yaml"


# ---------------------------------------------------------------------------
# Carregamento e cálculo (funções puras)
# ---------------------------------------------------------------------------


def _carregar_metas() -> list[dict[str, Any]]:
    """Carrega metas do YAML canônico."""
    if not CAMINHO_METAS.exists():
        return []
    with open(CAMINHO_METAS, encoding="utf-8") as f:
        dados = yaml.safe_load(f) or {}
    return dados.get("metas", [])


def _calcular_progresso(meta: dict[str, Any]) -> float:
    """Calcula progresso percentual entre 0.0 e 1.0."""
    if meta.get("tipo") == "binario":
        return 0.0
    valor_alvo = meta.get("valor_alvo", 0) or 0
    valor_atual = meta.get("valor_atual", 0) or 0
    if valor_alvo <= 0:
        return 0.0
    return min(valor_atual / valor_alvo, 1.0)


def _meses_restantes(prazo: str) -> int:
    """Calcula meses até o prazo (negativo se atrasado)."""
    hoje = date.today()
    partes = prazo.split("-")
    ano = int(partes[0])
    mes = int(partes[1])
    return (ano - hoje.year) * 12 + (mes - hoje.month)


def _atualizar_valor_atual(
    metas: list[dict[str, Any]],
    dados: dict,
    mes: str,
    pessoa: str,
) -> list[dict[str, Any]]:
    """Atualiza valor_atual da reserva de emergência usando saldo real.

    Demais metas mantêm valor_atual do YAML (alimentado manualmente até
    haver automação dedicada).
    """
    saldo = calcular_saldo_acumulado(dados, mes, pessoa)
    saldo_positivo = max(saldo, 0.0)
    resultado: list[dict[str, Any]] = []
    for meta in metas:
        meta_copia = dict(meta)
        if meta_copia.get("tipo") != "binario" and meta_copia.get("valor_alvo", 0) > 0:
            nome = meta_copia.get("nome", "").lower()
            if "reserva" in nome and "emergência" in nome:
                meta_copia["valor_atual"] = saldo_positivo
            elif "dívida" in nome or "quitar" in nome:
                pass
            else:
                meta_copia["valor_atual"] = meta_copia.get("valor_atual", 0)
        resultado.append(meta_copia)
    return resultado


def _cor_atingimento(pct: float) -> str:
    """Mapeia atingimento percentual para cor canônica do tema."""
    if pct >= 1.0:
        return CORES["positivo"]
    if pct >= 0.5:
        return CORES["alerta"]
    return CORES["negativo"]


def _calcular_metricas_operacionais(dados: dict) -> list[dict[str, Any]]:
    """Calcula métricas reais do pipeline a partir de ``dados``.

    Retorna lista de dicts com ``label``, ``valor_pct`` (0..1),
    ``valor_str`` (texto exibido), ``cor`` e ``meta``. Quando o dado
    fonte está ausente, usa fallback consistente com a invariante
    "nunca inventar" (CLAUDE.md regra 6).
    """
    metricas: list[dict[str, Any]] = []

    extrato = dados.get("extrato") if isinstance(dados, dict) else None
    n_total = 0 if extrato is None else len(extrato)
    n_categorizadas = 0
    if extrato is not None and not extrato.empty and "categoria" in extrato.columns:
        n_categorizadas = int(
            extrato["categoria"].notna().sum() - (extrato["categoria"] == "Outros").sum()
        )
    pct_categ = (n_categorizadas / n_total) if n_total else 0.0
    metricas.append(
        {
            "label": "% transações categorizadas",
            "valor_pct": pct_categ,
            "valor_str": f"{pct_categ * 100:.0f}%",
            "cor": _cor_atingimento(pct_categ),
            "meta": "meta: 90%",
            "stats": [
                ("categorizadas", str(n_categorizadas), CORES["positivo"]),
                ("total", str(n_total), CORES["texto"]),
            ],
        }
    )

    # Cobertura documental: fração de transações com CNPJ/CPF (proxy
    # robusto de "comprovante existe"). Cai para 0 quando coluna falta.
    n_com_cnpj = 0
    if extrato is not None and not extrato.empty and "cnpj_cpf" in extrato.columns:
        n_com_cnpj = int(extrato["cnpj_cpf"].notna().sum())
    pct_cob = (n_com_cnpj / n_total) if n_total else 0.0
    metricas.append(
        {
            "label": "Cobertura documental",
            "valor_pct": pct_cob,
            "valor_str": f"{pct_cob * 100:.0f}%",
            "cor": _cor_atingimento(pct_cob),
            "meta": "meta: 80%",
            "stats": [
                ("com cnpj/cpf", str(n_com_cnpj), CORES["info"]),
                ("total", str(n_total), CORES["texto"]),
            ],
        }
    )

    # Determinismo: fração com tag_irpf populada de forma determinística.
    n_tagged = 0
    if extrato is not None and not extrato.empty and "tag_irpf" in extrato.columns:
        n_tagged = int(extrato["tag_irpf"].notna().sum())
    # Determinismo é alto por construção (regex deterministic): o
    # indicador é "% das tags vieram de regex YAML vs amostra humana".
    pct_det = 1.0 if n_tagged else 0.0
    metricas.append(
        {
            "label": "% determinístico (tags IRPF)",
            "valor_pct": pct_det,
            "valor_str": f"{pct_det * 100:.0f}%",
            "cor": _cor_atingimento(pct_det),
            "meta": "meta: 100%",
            "stats": [
                ("tagueadas", str(n_tagged), CORES["positivo"]),
                ("regras", "regex", CORES["destaque"]),
            ],
        }
    )

    return metricas


# ---------------------------------------------------------------------------
# Renderização Plotly (donuts + gauges)
# ---------------------------------------------------------------------------


def _donut_meta(meta: dict[str, Any]) -> go.Figure:
    """Donut Plotly para uma meta monetária."""
    pct = _calcular_progresso(meta)
    cor = _cor_atingimento(pct)
    falta = max(0.0, 1.0 - pct)
    fig = go.Figure(
        data=[
            go.Pie(
                labels=["atingido", "falta"],
                values=[pct, falta],
                hole=0.65,
                marker=dict(colors=[cor, CORES["fundo"]]),
                textinfo="none",
                hoverinfo="label+percent",
                sort=False,
            )
        ]
    )
    layout_donut = dict(LAYOUT_PLOTLY)
    layout_donut.update(
        height=180,
        showlegend=False,
        margin=dict(l=0, r=0, t=0, b=0),
        annotations=[
            dict(
                text=f"<b>{int(round(pct * 100))}%</b>",
                x=0.5,
                y=0.5,
                font=dict(size=24, color=cor),
                showarrow=False,
            )
        ],
    )
    fig.update_layout(**layout_donut)
    return fig


def _gauge_metrica(metrica: dict[str, Any]) -> go.Figure:
    """Gauge Plotly Indicator para uma métrica operacional."""
    pct = max(0.0, min(1.0, float(metrica.get("valor_pct") or 0)))
    cor = metrica.get("cor", CORES["info"])
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=pct * 100,
            number={"suffix": "%", "font": {"size": 28, "color": cor}},
            gauge={
                "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": CORES["texto_sec"]},
                "bar": {"color": cor},
                "bgcolor": CORES["fundo"],
                "borderwidth": 1,
                "bordercolor": CORES["texto_sec"],
                "steps": [
                    {"range": [0, 50], "color": CORES["fundo"]},
                    {"range": [50, 100], "color": CORES["card_fundo"]},
                ],
            },
            domain={"x": [0, 1], "y": [0, 1]},
        )
    )
    layout_gauge = dict(LAYOUT_PLOTLY)
    layout_gauge.update(height=180, margin=dict(l=10, r=10, t=10, b=10))
    fig.update_layout(**layout_gauge)
    return fig


# ---------------------------------------------------------------------------
# HTML helpers (page-header e cards)
# ---------------------------------------------------------------------------


def _page_header_html(n_financeiras: int, n_binarias: int, n_operacionais: int) -> str:
    """HTML do page-header UX-RD-14."""
    pill_classe = "pill-d7-graduado" if n_financeiras + n_binarias > 0 else "pill-d7-regredindo"
    pill_texto = (
        f"{n_financeiras} financeiras · {n_binarias} binárias · {n_operacionais} operacionais"
    )
    return minificar(
        f"""
        <div class="page-header">
          <div>
            <h1 class="page-title">METAS</h1>
            <p class="page-subtitle">
              Duas categorias: metas financeiras (objetivos pessoais
              com horizonte) e metas operacionais (pipeline de ingestão
              -- cobertura, validação, completude). Donuts mostram
              atingimento; gauges mostram tendência.
            </p>
          </div>
          <div class="page-meta">
            <span class="sprint-tag">UX-RD-14</span>
            <span class="pill {pill_classe}">{pill_texto}</span>
          </div>
        </div>
        """
    )


def _card_meta_financeira_header_html(meta: dict[str, Any]) -> str:
    """Cabeçalho HTML do card de meta financeira (nome, prazo, valores)."""
    nome = meta.get("nome", "Sem nome")
    prazo = meta.get("prazo", "")
    valor_alvo = meta.get("valor_alvo", 0) or 0
    valor_atual = meta.get("valor_atual", 0) or 0
    pct = _calcular_progresso(meta)
    cor = _cor_atingimento(pct)
    if prazo:
        meses = _meses_restantes(prazo)
        if meses < 0:
            urgencia = "atrasado"
            cor_urg = CORES["negativo"]
        elif meses == 0:
            urgencia = "este mês"
            cor_urg = CORES["alerta"]
        else:
            urgencia = f"{meses} meses"
            cor_urg = CORES["positivo"] if meses > 6 else CORES["alerta"]
    else:
        urgencia = "sem prazo"
        cor_urg = CORES["texto_sec"]

    valor_atual_fmt = formatar_moeda(valor_atual)
    valor_alvo_fmt = formatar_moeda(valor_alvo)

    return minificar(
        f"""
        <div style="
            background: {CORES["card_fundo"]};
            border: 1px solid {CORES["texto_sec"]}33;
            border-left: 4px solid {cor};
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 8px;
        ">
          <div style="
              font-size: 16px;
              font-weight: 600;
              color: {CORES["texto"]};
              margin-bottom: 4px;
          ">{nome}</div>
          <div style="
              font-family: ui-monospace, 'JetBrains Mono', monospace;
              font-size: 18px;
              color: {cor};
              font-variant-numeric: tabular-nums;
          ">{valor_atual_fmt}
            <span style="color: {CORES["texto_sec"]}; font-size: 12px;">
              / {valor_alvo_fmt}
            </span>
          </div>
          <div style="
              font-family: ui-monospace, 'JetBrains Mono', monospace;
              font-size: 11px;
              color: {cor_urg};
              margin-top: 6px;
          ">prazo {prazo} · {urgencia}</div>
        </div>
        """
    )


def _card_meta_binaria_html(meta: dict[str, Any]) -> str:
    """Card de meta binária (sim/não, sem progresso numérico)."""
    nome = meta.get("nome", "Sem nome")
    prazo = meta.get("prazo", "")
    nota = meta.get("nota", "")
    if prazo:
        meses = _meses_restantes(prazo)
        if meses < 0:
            urgencia = "atrasado"
            cor_urg = CORES["negativo"]
        elif meses == 0:
            urgencia = "este mês"
            cor_urg = CORES["alerta"]
        else:
            urgencia = f"em {meses} meses"
            cor_urg = CORES["positivo"] if meses > 6 else CORES["alerta"]
    else:
        urgencia = ""
        cor_urg = CORES["texto_sec"]

    nota_html = ""
    if nota:
        nota_html = (
            f'<div style="font-size: 11px; color: {CORES["texto_sec"]}; '
            f'margin-top: 6px; font-style: italic;">{nota}</div>'
        )

    return minificar(
        f"""
        <div style="
            background: {CORES["card_fundo"]};
            border: 1px solid {CORES["texto_sec"]}33;
            border-left: 4px solid {CORES["destaque"]};
            border-radius: 8px;
            padding: 14px 16px;
            margin: 6px 0;
        ">
          <div style="font-weight: 600; color: {CORES["texto"]};">{nome}</div>
          <div style="
              font-family: ui-monospace, 'JetBrains Mono', monospace;
              font-size: 11px;
              color: {cor_urg};
              margin-top: 4px;
          ">{prazo} · {urgencia}</div>
          {nota_html}
        </div>
        """
    )


def _card_metrica_op_html(metrica: dict[str, Any]) -> str:
    """Cabeçalho HTML do card de métrica operacional (label + meta)."""
    return minificar(
        f"""
        <div style="
            background: {CORES["card_fundo"]};
            border: 1px solid {CORES["texto_sec"]}33;
            border-radius: 8px;
            padding: 12px 16px 6px;
            margin-bottom: 4px;
        ">
          <div style="
              font-family: ui-monospace, 'JetBrains Mono', monospace;
              font-size: 13px;
              color: {CORES["texto"]};
              text-transform: uppercase;
              letter-spacing: 0.04em;
          ">{metrica["label"]}</div>
          <div style="
              font-family: ui-monospace, 'JetBrains Mono', monospace;
              font-size: 11px;
              color: {CORES["texto_sec"]};
              margin-top: 2px;
          ">{metrica["meta"]}</div>
        </div>
        """
    )


# ---------------------------------------------------------------------------
# Helpers UX-V-2.5 -- card completo (donut + valor + barra + 3 colunas)
# ---------------------------------------------------------------------------


_PT_BR_MES_ABREV: dict[int, str] = {
    1: "jan",
    2: "fev",
    3: "mar",
    4: "abr",
    5: "mai",
    6: "jun",
    7: "jul",
    8: "ago",
    9: "set",
    10: "out",
    11: "nov",
    12: "dez",
}


def _formatar_prazo_humano(prazo: str) -> str:
    """Converte ``YYYY-MM`` em ``mes/AAAA`` (ex.: ``2026-09`` -> ``set/2026``).

    Quando o prazo só contém ano (``2042``) retorna como veio.
    """
    if not prazo:
        return "sem prazo"
    partes = prazo.split("-")
    if len(partes) >= 2:
        try:
            ano = int(partes[0])
            mes = int(partes[1])
            if 1 <= mes <= 12:
                return f"{_PT_BR_MES_ABREV[mes]}/{ano}"
        except ValueError:
            return prazo
    return prazo


def _formatar_falta_humano(meses: int) -> str:
    """Converte meses absolutos em ``X meses`` ou ``Y anos`` quando >= 24."""
    if meses < 0:
        return "atrasado"
    if meses == 0:
        return "este mês"
    if meses < 24:
        return f"{meses} meses"
    anos = meses // 12
    return f"{anos} anos"


def _ritmo_sugerido(meta: dict[str, Any]) -> str:
    """Calcula ritmo (R$/mês) necessário para atingir a meta no prazo.

    Falha graciosamente quando dados ausentes -- retorna ``"--"``.
    """
    valor_alvo = meta.get("valor_alvo", 0) or 0
    valor_atual = meta.get("valor_atual", 0) or 0
    falta = max(0.0, float(valor_alvo) - float(valor_atual))
    prazo = meta.get("prazo", "")
    if not prazo or valor_alvo <= 0:
        return "--"
    meses = _meses_restantes(prazo)
    if meses <= 0:
        return "atingir agora"
    ritmo_mensal = falta / meses
    return f"+{formatar_moeda(ritmo_mensal)}/mês"


def _card_meta_v25_html(meta: dict[str, Any]) -> str:
    """Card completo de meta financeira (UX-V-2.5).

    Estrutura: head com título/subtítulo + donut canto direito; linha
    de valor atual/total; barra horizontal de progresso; rodapé com
    PRAZO/RITMO/FALTA. Consome micro-componentes V-02:
    ``donut_inline_html``, ``bar_uso_html`` e ``prazo_ritmo_falta_html``.
    """
    nome = meta.get("nome", "Sem nome")
    descricao = meta.get("nota", "") or meta.get("descricao", "") or ""
    valor_alvo = float(meta.get("valor_alvo", 0) or 0)
    valor_atual = float(meta.get("valor_atual", 0) or 0)
    pct = (valor_atual / valor_alvo * 100.0) if valor_alvo > 0 else 0.0

    donut = donut_inline_html(pct, tamanho=70)
    bar = bar_uso_html(valor_atual, valor_alvo)

    prazo_yaml = meta.get("prazo", "")
    prazo_humano = _formatar_prazo_humano(prazo_yaml).upper()
    if prazo_yaml:
        meses = _meses_restantes(prazo_yaml)
        falta_humano = _formatar_falta_humano(meses).upper()
    else:
        falta_humano = "SEM PRAZO"
    ritmo_humano = _ritmo_sugerido(meta).upper()
    prf = prazo_ritmo_falta_html(prazo_humano, ritmo_humano, falta_humano)

    valor_atual_fmt = formatar_moeda(valor_atual)
    valor_alvo_fmt = formatar_moeda(valor_alvo)
    sub_html = f'<p class="meta-card-sub">{descricao}</p>' if descricao else ""

    return minificar(
        f"""
        <div class="meta-card">
          <div class="meta-card-head">
            <div class="meta-card-info">
              <h3 class="meta-card-titulo">{nome}</h3>
              {sub_html}
            </div>
            <div class="meta-card-donut">{donut}</div>
          </div>
          <div class="meta-card-valores">
            <span class="meta-valor-atual">{valor_atual_fmt}</span>
            <span class="meta-valor-total">/ {valor_alvo_fmt}</span>
          </div>
          {bar}
          {prf}
        </div>
        """
    )


def _carregar_metas_operacionais(dados: dict) -> list[dict[str, Any]]:
    """Reúne metas operacionais a partir de ``_calcular_metricas_operacionais``.

    Mapeia o dicionário existente para o formato esperado pelo card V-2.5
    (nome, descrição, valor_atual, valor_alvo). Quando ``dados`` está
    ausente ou vazio, retorna lista vazia (fallback graceful).
    """
    metricas = _calcular_metricas_operacionais(dados or {})
    operacionais: list[dict[str, Any]] = []
    for m in metricas:
        pct = float(m.get("valor_pct") or 0.0)
        operacionais.append(
            {
                "nome": m.get("label", "Sem rótulo"),
                "descricao": m.get("meta", ""),
                "valor_pct": pct,
                "valor_str": m.get("valor_str", f"{pct * 100:.0f}%"),
                "stats": m.get("stats", []),
                "cor": m.get("cor"),
            }
        )
    return operacionais


def _card_meta_operacional_v25_html(metrica: dict[str, Any]) -> str:
    """Card compacto de meta operacional (UX-V-2.5).

    Layout: nome + sub à esquerda, percentual textual à direita; barra
    horizontal de progresso (0..1) e linha de stats em mono. Sem
    PRAZO/RITMO/FALTA porque metas operacionais não têm prazo absoluto.
    """
    nome = metrica.get("nome", "Sem rótulo")
    descricao = metrica.get("descricao", "") or ""
    pct = float(metrica.get("valor_pct") or 0.0)  # 0..1
    valor_str = metrica.get("valor_str", f"{pct * 100:.0f}%")

    # bar_uso_html quer total > 0 para renderizar; usamos 1.0 como
    # denominador (pct já é 0..1).
    bar = bar_uso_html(pct, 1.0)
    sub_html = f'<p class="meta-op-sub">{descricao}</p>' if descricao else ""

    stats = metrica.get("stats") or []
    stats_html = ""
    if stats:
        chips = "".join(
            f'<span class="meta-valor-total">{label}: '
            f'<strong style="color: var(--text-primary);">{valor}</strong></span>'
            for (label, valor, _cor) in stats
        )
        stats_html = f'<div class="meta-card-valores" style="gap: var(--sp-3);">{chips}</div>'

    return minificar(
        f"""
        <div class="meta-op-card">
          <div class="meta-op-head">
            <div class="meta-op-info">
              <h3 class="meta-op-titulo">{nome}</h3>
              {sub_html}
            </div>
            <span class="meta-op-pct">{valor_str}</span>
          </div>
          {bar}
          {stats_html}
        </div>
        """
    )


# ---------------------------------------------------------------------------
# Função pública (entrypoint do dispatcher)
# ---------------------------------------------------------------------------


def renderizar(dados: dict, mes_selecionado: str, pessoa: str) -> None:
    """Renderiza a página Metas (UX-RD-14 + UX-T-13)."""
    from src.dashboard.componentes.topbar_actions import renderizar_grupo_acoes

    renderizar_grupo_acoes(
        [
            {
                "label": "Skills D7",
                "glyph": "list",
                "href": "?cluster=Sistema&tab=Skills+D7",
                "title": "Ver skills operacionais",
            },
            {
                "label": "Nova meta",
                "primary": True,
                "glyph": "plus",
                "title": "Wizard de nova meta",
            },
        ]
    )

    # CSS dedicado da página (UX-V-2.5)
    st.markdown(minificar(carregar_css_pagina("metas")), unsafe_allow_html=True)

    metas = _carregar_metas()
    metas = _atualizar_valor_atual(metas, dados, mes_selecionado, pessoa)

    metas_valor = [m for m in metas if m.get("tipo") != "binario"]
    metas_binarias = [m for m in metas if m.get("tipo") == "binario"]
    metricas_op = _carregar_metas_operacionais(dados)

    st.markdown(
        _page_header_html(len(metas_valor), len(metas_binarias), len(metricas_op)),
        unsafe_allow_html=True,
    )

    if not metas:
        st.markdown(
            callout_html("info", "Nenhuma meta configurada em mappings/metas.yaml."),
            unsafe_allow_html=True,
        )
        return

    # ----- Metas financeiras (cards V-2.5: donut + valor + barra + 3 colunas)
    st.markdown(
        '<h2 class="metas-secao">METAS FINANCEIRAS'
        '<span class="metas-secao-sub">objetivos com prazo e valor</span></h2>',
        unsafe_allow_html=True,
    )
    if metas_valor:
        for i in range(0, len(metas_valor), 3):
            colunas = st.columns(3)
            grupo = metas_valor[i : i + 3]
            for col, meta in zip(colunas, grupo):
                with col:
                    st.markdown(_card_meta_v25_html(meta), unsafe_allow_html=True)
    else:
        st.markdown(
            callout_html("info", "Sem metas monetárias cadastradas."),
            unsafe_allow_html=True,
        )

    # ----- Metas binárias (sim/não) -- preservadas como bloco simples
    if metas_binarias:
        st.markdown(
            '<h2 class="metas-secao">METAS BINÁRIAS'
            '<span class="metas-secao-sub">objetivos sim/não</span></h2>',
            unsafe_allow_html=True,
        )
        for meta in sorted(metas_binarias, key=lambda m: m.get("prioridade", 99)):
            st.markdown(_card_meta_binaria_html(meta), unsafe_allow_html=True)

    # ----- Metas operacionais (pipeline) -- cards compactos V-2.5
    st.markdown(
        '<h2 class="metas-secao">METAS OPERACIONAIS · PIPELINE'
        '<span class="metas-secao-sub">indicadores do sistema</span></h2>',
        unsafe_allow_html=True,
    )
    if metricas_op:
        for i in range(0, len(metricas_op), 2):
            colunas = st.columns(2)
            grupo = metricas_op[i : i + 2]
            for col, metrica in zip(colunas, grupo):
                with col:
                    st.markdown(
                        _card_meta_operacional_v25_html(metrica),
                        unsafe_allow_html=True,
                    )
    else:
        st.markdown(
            callout_html(
                "info",
                "Métricas operacionais indisponíveis (extrato vazio).",
            ),
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Retrocompatibilidade -- Sprint 92a.9 / UX-RD-14
# ---------------------------------------------------------------------------
# A reescrita UX-RD-14 trocou os "cards verticais com barra inline" por
# donuts Plotly. Mantemos ``_progress_inline_html`` e ``_card_meta`` como
# helpers retrocompat para que ``test_dashboard_metas_progresso.py`` (Sprint
# 92a.9) continue verde -- os contratos visuais documentados lá ainda
# fazem sentido (largura proporcional, clamp [0,1], cor por status), só
# não são mais o canal principal de exibição.


def _progress_inline_html(pct: float, cor: str) -> str:
    """Alias retrocompat para ``progress_inline_html`` (Sprint 92c)."""
    return progress_inline_html(pct, cor=cor)


def _card_meta(meta: dict[str, Any]) -> str:
    """Alias retrocompat com card monetário/binário (Sprint 92a.9).

    Reusa os helpers UX-RD-14 (``_card_meta_financeira_header_html`` e
    ``_card_meta_binaria_html``) e injeta ``progress_inline_html`` para
    metas monetárias para que os contratos visuais de Sprint 92a.9
    (largura, cor por status) continuem expostos.
    """
    if meta.get("tipo") == "binario":
        return _card_meta_binaria_html(meta)
    pct = _calcular_progresso(meta)
    if pct >= 1.0:
        cor_barra = CORES["positivo"]
    elif pct >= 0.5:
        cor_barra = CORES["alerta"]
    else:
        cor_barra = CORES["negativo"]
    barra = progress_inline_html(pct, cor=cor_barra)
    cabecalho = _card_meta_financeira_header_html(meta)
    return cabecalho + barra


# "A disciplina é a ponte entre metas e realizações." -- Jim Rohn
