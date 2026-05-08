"""Página de visão geral do dashboard financeiro -- redesign UX-RD-04.

Reescrita inspirada em ``novo-mockup/mockups/01-visao-geral.html`` +
``_visao-render.js``: hero com glyph Ω animado, KPI grid de 4 colunas
(Receita, Despesa, Saldo, Reserva), bloco dual (gráfico Plotly à esquerda
+ timeline à direita) e cluster cards 3-col com links para os 6 clusters
principais do shell global.

Contrato preservado (Sprint MOB-bridge-1, KAPPA-08): assinatura de
``renderizar(dados, mes_selecionado, pessoa, ctx)`` continua intocada;
``app.py`` chama essa função para o cluster Home.

Tokens consumidos via ``CORES`` (Sprint UX-RD-01) e classes utilitárias
``.kpi``, ``.pill-d7-*``, ``.card.interactive`` injetadas em UX-RD-02.
Classes específicas desta página (``.hero``, ``.cluster-grid``,
``.cluster-card``, ``.timeline``, ``.tl-item``, ``.dual``,
``.kpi.up``/``.warn``/``.bad``) são emitidas via ``<style>`` local
neste arquivo -- ``tema_css.py`` permanece intocado para evitar
regressão das outras 14 páginas.

Animação Ω: keyframes ``ob-rotate`` e ``ob-halo`` também ficam no
``<style>`` local. Nenhuma dependência externa.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.dashboard import tema
from src.dashboard.componentes.drilldown import aplicar_drilldown
from src.dashboard.dados import (
    filtrar_por_mes,
    formatar_moeda,
)
from src.dashboard.tema import (
    CORES,
    FONTE_SUBTITULO,
    LAYOUT_PLOTLY,
    aplicar_locale_ptbr,
    callout_html,
)

# Meta padrão da reserva de emergência (espelha o template
# ``mappings/metas_default.yaml`` quando o usuário não personalizou).
RESERVA_META_PADRAO = 44_019.78


def renderizar(
    dados: dict[str, pd.DataFrame],
    mes_selecionado: str,
    pessoa: str,
    ctx: dict | None = None,
) -> None:
    """Renderiza a Visão Geral canônica (UX-T-01).

    Mockup-fonte: ``novo-mockup/mockups/01-visao-geral.html``.
    Layout:
      - Topbar-actions: ``Atualizar`` + ``Ir para Validação`` (primary).
      - Hero: marca + título + subtítulo (com linha ``Sprint atual: <ID>``)
        + anel ouroboros animado.
      - KPIs agentic-first (4 cards): Arquivos catalogados / Paridade ETL ↔
        Opus / Aguardando humano / Skills regredindo.
      - Bloco dual: ``OS 5 CLUSTERS`` (6 cards) à esquerda; ``Atividade
        recente`` + ``Sprint atual`` à direita.
    """
    del mes_selecionado, pessoa, ctx  # filtros migraram para U-04 expander

    # UX-U-02: topbar-actions canônicas.
    from src.dashboard.componentes.topbar_actions import renderizar_grupo_acoes
    from src.dashboard.componentes.visao_geral_widgets import (
        calcular_kpis_agentic,
        ler_atividade_recente,
        ler_sprint_atual,
        montar_clusters_canonicos,
    )

    renderizar_grupo_acoes(
        [
            {
                "label": "Atualizar",
                "glyph": "refresh",
                "title": "Recarregar a página",
            },
            {
                "label": "Ir para Validação",
                "primary": True,
                "glyph": "validar",
                "href": "?cluster=Documentos&tab=Extra%C3%A7%C3%A3o+Tripla",
                "title": "Abrir página de Extração Tripla",
            },
        ]
    )

    from src.dashboard.componentes.atividade_recente import (
        atividade_recente_html,
        sprint_atual_html,
    )
    from src.dashboard.componentes.cards_clusters import (
        clusters_canonicos_html,
        estilos_t01_canonicos,
    )
    from src.dashboard.componentes.html_utils import minificar
    from src.dashboard.componentes.ui import carregar_css_pagina

    st.markdown(_estilos_locais(), unsafe_allow_html=True)
    st.markdown(estilos_t01_canonicos(), unsafe_allow_html=True)
    # UX-V-2.7: CSS canônico em arquivo (paridade com mockup 01-visao-geral.html).
    st.markdown(minificar(carregar_css_pagina("visao_geral")), unsafe_allow_html=True)

    sprint_meta = ler_sprint_atual()
    # VG-FIDELIDADE-FIX: usa o titulo canonico (ex.: VALIDAÇÃO-CSV-01)
    # em vez do ID interno UX-T-NN — mockup canônico mostra o titulo.
    sprint_titulo_no_hero = (sprint_meta or {}).get("titulo", "") if sprint_meta else ""
    st.markdown(_hero_html(sprint_titulo_no_hero), unsafe_allow_html=True)

    if "extrato" not in dados:
        st.markdown(
            callout_html("warning", "Nenhum dado encontrado para a visão geral."),
            unsafe_allow_html=True,
        )
        return

    kpis = calcular_kpis_agentic()
    st.markdown(_kpis_agentic_html(kpis), unsafe_allow_html=True)

    col_esq, col_dir = st.columns([1.4, 1.0])
    with col_esq:
        st.markdown(clusters_canonicos_html(montar_clusters_canonicos()), unsafe_allow_html=True)
    with col_dir:
        st.markdown(atividade_recente_html(ler_atividade_recente(n=6)), unsafe_allow_html=True)
        st.markdown(sprint_atual_html(sprint_meta), unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Helpers de cálculo
# ---------------------------------------------------------------------------


def _calcular_deltas(
    extrato_filtrado: pd.DataFrame,
    mes_atual: str,
    gran: str,
) -> tuple[float, float, float]:
    """Retorna delta percentual (período atual vs anterior) para receita,
    despesa e saldo. Quando não há período anterior comparável, retorna 0.0.
    """
    if gran != "Mês" or "mes_ref" not in extrato_filtrado.columns:
        return 0.0, 0.0, 0.0

    meses = sorted(extrato_filtrado["mes_ref"].dropna().unique().tolist())
    if mes_atual not in meses:
        return 0.0, 0.0, 0.0

    idx = meses.index(mes_atual)
    if idx == 0:
        return 0.0, 0.0, 0.0

    mes_anterior = meses[idx - 1]
    df_ant = filtrar_por_mes(extrato_filtrado, mes_anterior)
    df_atu = filtrar_por_mes(extrato_filtrado, mes_atual)

    rec_ant = float(df_ant[df_ant["tipo"] == "Receita"]["valor"].sum())
    rec_atu = float(df_atu[df_atu["tipo"] == "Receita"]["valor"].sum())
    desp_ant = float(df_ant[df_ant["tipo"].isin(["Despesa", "Imposto"])]["valor"].sum())
    desp_atu = float(df_atu[df_atu["tipo"].isin(["Despesa", "Imposto"])]["valor"].sum())
    sal_ant = rec_ant - desp_ant
    sal_atu = rec_atu - desp_atu

    def _pct(atual: float, anterior: float) -> float:
        if anterior == 0:
            return 0.0
        return (atual - anterior) / abs(anterior) * 100.0

    return _pct(rec_atu, rec_ant), _pct(desp_atu, desp_ant), _pct(sal_atu, sal_ant)


def _ultimos_eventos(extrato: pd.DataFrame, n: int = 5) -> list[dict[str, str]]:
    """Extrai últimos N eventos do extrato, ordenado por data desc."""
    if extrato.empty or "data" not in extrato.columns:
        return []

    df = extrato.copy()
    df = df.sort_values("data", ascending=False).head(n)

    eventos: list[dict[str, str]] = []
    for _, row in df.iterrows():
        data = row.get("data")
        when_str = ""
        if pd.notna(data):
            try:
                when_str = pd.to_datetime(data).strftime("%d/%m")
            except (ValueError, TypeError):
                when_str = str(data)[:10]

        tipo_t = str(row.get("tipo", ""))
        local = str(row.get("local", ""))[:32] or "---"
        valor = formatar_moeda(float(row.get("valor", 0.0)))
        categoria = str(row.get("categoria", ""))[:18] or "---"

        ic = "upload" if tipo_t == "Receita" else ("warn" if tipo_t == "Imposto" else "diff")
        what = (
            f"<strong>{local}</strong> · "
            f"<code>{categoria}</code> · {valor}"
        )

        eventos.append({"when": when_str, "ic": ic, "what": what})

    return eventos


# ---------------------------------------------------------------------------
# Helpers de HTML
# ---------------------------------------------------------------------------


def _estilos_locais() -> str:
    """Estilos específicos do redesign Visão Geral (hero, kpi modifiers,
    cluster cards, timeline, animações Ω). Isolados aqui para não tocar
    ``tema_css.py`` -- contrato preservado para as outras 14 páginas.
    """
    fundo = CORES["card_fundo"]
    inset = CORES["fundo_inset"]
    texto_pri = CORES["texto"]
    texto_sec = CORES["texto_sec"]
    texto_muted = CORES["texto_muted"]
    accent_purple = CORES["destaque"]
    accent_pink = CORES["superfluo"]
    accent_yellow = CORES["info"]
    accent_red = CORES["negativo"]
    d7_grad = CORES["d7_graduado"]
    border_subtle = "#2a2d3a"

    return f"""
    <style>
      @keyframes ob-rotate {{
        from {{ transform: rotate(0deg); }}
        to   {{ transform: rotate(360deg); }}
      }}
      @keyframes ob-halo {{
        0%, 100% {{ opacity: 0.55; transform: scale(1); }}
        50%      {{ opacity: 0.85; transform: scale(1.04); }}
      }}
      .ob-ring   {{
        transform-origin: 160px 160px;
        animation: ob-rotate 80s linear infinite;
      }}
      .ob-halo   {{
        transform-origin: 160px 160px;
        animation: ob-halo 6s ease-in-out infinite;
      }}
      .ob-dotted {{
        transform-origin: 160px 160px;
        animation: ob-rotate 200s linear infinite reverse;
        opacity: .28;
      }}

      .vg-hero {{
        background: {fundo};
        border: 1px solid {border_subtle};
        border-radius: 12px;
        padding: 32px;
        margin-bottom: 24px;
        display: grid;
        grid-template-columns: 1.6fr 1fr;
        gap: 32px;
        align-items: center;
      }}
      /* UX-T-01 followup: !important para vencer h1 global
         (font-size: FONTE_HERO !important; font-weight: 700) que
         deformava o hero para 28px/700. Mockup canônico
         01-visao-geral.html usa 32px/500. */
      .vg-hero h1 {{
        font-family: ui-monospace, 'JetBrains Mono', monospace !important;
        font-size: 32px !important;
        font-weight: 500 !important;
        letter-spacing: -0.02em !important;
        margin: 0 0 8px !important;
        color: {texto_pri} !important;
      }}
      .vg-hero p {{
        color: {texto_sec};
        font-size: 15px;
        line-height: 1.6;
        margin: 0;
        max-width: 56ch;
      }}
      .vg-hero .marca {{
        font-family: ui-monospace, 'JetBrains Mono', monospace;
        font-size: 11px;
        letter-spacing: 0.12em;
        color: {accent_purple};
        text-transform: uppercase;
        margin-bottom: 12px;
        display: block;
      }}
      .vg-hero .marca-cluster {{
        font-family: ui-monospace, 'JetBrains Mono', monospace;
        font-size: 11px;
        color: {accent_pink};
      }}
      .vg-hero .ouroboros {{
        width: 220px;
        height: 220px;
        margin-left: auto;
        display: grid;
        place-items: center;
      }}

      .vg-kpi-grid {{
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 12px;
        margin-bottom: 24px;
      }}
      .vg-kpi {{
        background: {fundo};
        border: 1px solid {border_subtle};
        border-radius: 12px;
        padding: 16px;
        display: flex;
        flex-direction: column;
        gap: 6px;
      }}
      .vg-kpi .l {{
        font-family: ui-monospace, 'JetBrains Mono', monospace;
        font-size: 11px;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: {texto_muted};
      }}
      .vg-kpi .v {{
        font-family: ui-monospace, 'JetBrains Mono', monospace;
        font-size: 32px;
        font-weight: 500;
        line-height: 1.1;
        font-variant-numeric: tabular-nums;
        color: {texto_pri};
      }}
      .vg-kpi .d {{
        font-family: ui-monospace, 'JetBrains Mono', monospace;
        font-size: 12px;
        color: {texto_muted};
      }}
      .vg-kpi.up   .v {{ color: {d7_grad}; }}
      .vg-kpi.warn .v {{ color: {accent_yellow}; }}
      .vg-kpi.bad  .v {{ color: {accent_red}; }}

      .vg-section-title {{
        font-family: ui-monospace, 'JetBrains Mono', monospace;
        font-size: 13px;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: {texto_muted};
        margin: 16px 0 12px;
      }}

      .vg-timeline {{
        background: {fundo};
        border: 1px solid {border_subtle};
        border-radius: 12px;
        padding: 16px;
      }}
      .vg-tl-item {{
        display: grid;
        grid-template-columns: 70px 1fr;
        gap: 12px;
        padding: 8px 0;
        border-bottom: 1px dashed {border_subtle};
      }}
      .vg-tl-item:last-child {{ border-bottom: none; }}
      .vg-tl-item .when {{
        font-family: ui-monospace, 'JetBrains Mono', monospace;
        font-size: 11px;
        color: {texto_muted};
        padding-top: 2px;
      }}
      .vg-tl-item .what {{
        font-size: 13px;
        color: {texto_sec};
        line-height: 1.45;
      }}
      .vg-tl-item .what strong {{
        color: {texto_pri};
        font-family: ui-monospace, 'JetBrains Mono', monospace;
      }}
      .vg-tl-item .what code {{
        color: {accent_purple};
        background: {inset};
        padding: 1px 5px;
        border-radius: 4px;
        font-size: 11px;
      }}

      .vg-cluster-grid {{
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 12px;
        margin-top: 16px;
      }}
      .vg-cluster-card {{
        background: {fundo};
        border: 1px solid {border_subtle};
        border-radius: 12px;
        padding: 16px;
        text-decoration: none;
        color: inherit;
        display: flex;
        flex-direction: column;
        gap: 8px;
        transition: border-color .15s, transform .15s;
      }}
      .vg-cluster-card:hover {{
        border-color: {accent_purple};
        transform: translateY(-2px);
      }}
      .vg-cluster-card h3 {{
        font-family: ui-monospace, 'JetBrains Mono', monospace;
        font-size: 15px;
        font-weight: 500;
        margin: 0;
        letter-spacing: -0.01em;
        color: {texto_pri};
      }}
      .vg-cluster-card .desc {{
        font-size: 13px;
        color: {texto_muted};
        line-height: 1.5;
      }}
      .vg-cluster-card .stats {{
        display: flex;
        gap: 12px;
        margin-top: auto;
        padding-top: 8px;
        border-top: 1px solid {border_subtle};
      }}
      .vg-cluster-card .stats span {{
        font-family: ui-monospace, 'JetBrains Mono', monospace;
        font-size: 11px;
        color: {texto_sec};
      }}
      .vg-cluster-card .stats strong {{
        color: {texto_pri};
        margin-right: 4px;
      }}

      @media (max-width: 1199px) {{
        .vg-kpi-grid {{ grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); }}
        .vg-cluster-grid {{ grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); }}
        .vg-hero {{ grid-template-columns: 1fr; }}
        .vg-hero .ouroboros {{ margin: 0 auto; }}
      }}
    </style>
    """


def _hero_html(sprint_atual_titulo: str = "") -> str:
    """Hero com marca, título, subtítulo (com linha Sprint atual) e Ω animado.

    UX-T-01: subtítulo passa a incluir a linha "Sprint atual: <ID>" — espelha
    o mockup canônico ``01-visao-geral.html`` que destaca a sprint vigente
    no parágrafo do hero.
    """
    svg = _ler_svg_ouroboros()
    # VG-FIDELIDADE-FIX: mockup canônico (_visao-render.js) tem
    # apenas "Sistema agentic-first" sem o "· cluster Home" extra.
    marca = '<span class="marca">Sistema agentic-first</span>'
    titulo = "<h1>Os arquivos da sua vida financeira, normalizados.</h1>"
    sprint_html = ""
    if sprint_atual_titulo:
        sprint_html = (
            " Sprint atual: <code style=\"color:var(--accent-purple);\">"
            f"{sprint_atual_titulo}</code> — medindo paridade entre as duas extrações."
        )
    subt = (
        "<p>Pipeline auto-referente. Cada arquivo é registrado pelo "
        "sha256, extraído em duas vias (ETL determinística + Opus "
        "agentic), validado por humano-no-loop, e catalogado para "
        f"análise.{sprint_html}</p>"
    )
    return (
        '<div class="vg-hero">'
        f"<div>{marca}{titulo}{subt}</div>"
        f'<div class="ouroboros">{svg}</div>'
        "</div>"
    )


def _ler_svg_ouroboros() -> str:
    """Lê ``assets/ouroboros.svg`` e retorna o conteúdo inline minificado.

    Inserir o SVG inline (em vez de ``<img src=>``) preserva a animação
    CSS controlada pelas keyframes ``ob-rotate``/``ob-halo`` definidas
    em ``_estilos_locais``.

    **Fix UX-RD-04 patch (2026-05-04):** Streamlit roteia ``st.markdown``
    pelo parser CommonMark **antes** de honrar ``unsafe_allow_html=True``.
    Linhas com 4+ espaços de indentação interna do SVG (típicas em
    ``<path d="M ...">`` multi-linha) são interpretadas como bloco de
    código e o conteúdo bruto vaza como texto na página. Solução: colapsar
    todo whitespace inter-tag para uma única linha antes de injetar.
    """
    caminho = Path(__file__).resolve().parents[3] / "assets" / "ouroboros.svg"
    if not caminho.exists():
        return ""
    bruto = caminho.read_text(encoding="utf-8")
    # Colapsa whitespace entre tags e dentro de atributos multi-linha:
    #   - "\n " entre tags vira " "
    #   - múltiplos espaços viram um só
    # Resultado: SVG numa linha única, sem indentação que o markdown
    # interprete como code block.
    sem_quebras = re.sub(r"\s+", " ", bruto)
    return sem_quebras.strip()


def _kpi_grid_html(
    *,
    receitas: float,
    despesas: float,
    saldo: float,
    reserva_atual: float,
    reserva_meta: float,
    reserva_pct: float,
    delta_receita: float,
    delta_despesa: float,
    delta_saldo: float,
) -> str:
    """Renderiza o KPI grid de 4 colunas: Receita, Despesa, Saldo, Reserva."""
    classe_receita = "up" if delta_receita >= 0 else "bad"
    classe_despesa = "warn" if delta_despesa <= 0 else "bad"
    classe_saldo = "up" if saldo >= 0 else "bad"
    classe_reserva = "up" if reserva_pct >= 100 else ("warn" if reserva_pct >= 50 else "bad")

    delta_rec_txt = _fmt_delta(delta_receita)
    delta_desp_txt = _fmt_delta(delta_despesa)
    delta_sal_txt = _fmt_delta(delta_saldo)

    return f"""
    <div class="vg-kpi-grid">
      <div class="vg-kpi {classe_receita}">
        <span class="l">Receita</span>
        <span class="v">{formatar_moeda(receitas)}</span>
        <span class="d">{delta_rec_txt} vs período anterior</span>
      </div>
      <div class="vg-kpi {classe_despesa}">
        <span class="l">Despesa</span>
        <span class="v">{formatar_moeda(despesas)}</span>
        <span class="d">{delta_desp_txt} vs período anterior</span>
      </div>
      <div class="vg-kpi {classe_saldo}">
        <span class="l">Saldo</span>
        <span class="v">{formatar_moeda(saldo)}</span>
        <span class="d">{delta_sal_txt} vs período anterior</span>
      </div>
      <div class="vg-kpi {classe_reserva}">
        <span class="l">Reserva</span>
        <span class="v">{formatar_moeda(reserva_atual)}</span>
        <span class="d">Meta {formatar_moeda(reserva_meta)} · {reserva_pct:.0f}%</span>
      </div>
    </div>
    """


def _fmt_delta(pct: float) -> str:
    """Formata delta percentual com sinal e símbolo."""
    if pct == 0.0:
        return "—"
    sinal = "+" if pct > 0 else ""
    return f"{sinal}{pct:.1f}%"


def _timeline_html(eventos: list[dict[str, str]]) -> str:
    """Timeline com até 5 últimos eventos do período ativo."""
    if not eventos:
        body = (
            '<div class="vg-tl-item"><span class="when">—</span>'
            '<span class="what">Sem eventos no período selecionado.</span></div>'
        )
    else:
        body = "".join(
            f'<div class="vg-tl-item"><span class="when">{ev["when"]}</span>'
            f'<span class="what">{ev["what"]}</span></div>'
            for ev in eventos
        )

    return f"""
    <div class="vg-section-title">Atividade recente</div>
    <div class="vg-timeline">{body}</div>
    """


def _cluster_grid_html(dados: dict[str, pd.DataFrame]) -> str:
    """Cluster cards: 6 atalhos para os subsistemas principais."""
    extrato = dados.get("extrato", pd.DataFrame())
    contas = dados.get("contas", pd.DataFrame())
    metas_df = dados.get("metas", pd.DataFrame())

    n_txns = len(extrato) if not extrato.empty else 0
    n_contas = len(contas) if not contas.empty else 0
    n_metas = len(metas_df) if not metas_df.empty else 0

    # Cluster slug coincide com o roteador do shell global (UX-RD-03).
    cards = [
        ("Inbox", "?cluster=Inbox", "Entrada de dados. Drop por sha8.",
         ("aguardando", "0"), ("na fila", "0")),
        ("Finanças", "?cluster=Finanças", "Extrato, contas, pagamentos, projeções.",
         ("contas", str(n_contas)), ("txns", _fmt_compact(n_txns))),
        ("Documentos", "?cluster=Documentos", "Busca, catálogo, completude, revisor.",
         ("arquivos", _fmt_compact(n_txns)), ("revisor", "ativo")),
        ("Análise", "?cluster=Análise", "Categorias, multi-perspectiva, IRPF.",
         ("categorias", "24"), ("IRPF", "ativo")),
        ("Metas", "?cluster=Metas", "Financeiras + operacionais (skills D7).",
         ("financeiras", str(n_metas)), ("operacionais", "—")),
        ("Sistema", "?cluster=Sistema", "Skills D7, runs, ADRs, configuração.",
         ("skills", "—"), ("ADRs", "20")),
    ]

    body = "".join(
        f'<a class="vg-cluster-card" href="{href}">'
        f'<h3>{nome}</h3>'
        f'<div class="desc">{desc}</div>'
        f'<div class="stats">'
        f'<span><strong>{s1[1]}</strong>{s1[0]}</span>'
        f'<span><strong>{s2[1]}</strong>{s2[0]}</span>'
        f'</div>'
        f'</a>'
        for nome, href, desc, s1, s2 in cards
    )

    return f"""
    <div class="vg-section-title">Os 6 clusters</div>
    <div class="vg-cluster-grid">{body}</div>
    """


def _fmt_compact(n: int) -> str:
    """Formata inteiros grandes em estilo 2.8k / 12k."""
    if n >= 1000:
        return f"{n / 1000:.1f}k".replace(".", ",")
    return str(n)


# ---------------------------------------------------------------------------
# Gráfico Receita vs Despesa (preservado da versão anterior, paleta tokens)
# ---------------------------------------------------------------------------


def _grafico_barras_historico(
    extrato: pd.DataFrame,
    mes_atual: str,
) -> None:
    """Gráfico de barras com linha de saldo: receita vs despesa últimos 6 meses."""
    if extrato.empty or "mes_ref" not in extrato.columns:
        st.markdown(
            callout_html("info", "Sem dados suficientes para o histórico mensal."),
            unsafe_allow_html=True,
        )
        return

    meses_ordenados = sorted(extrato["mes_ref"].dropna().unique().tolist())

    if mes_atual in meses_ordenados:
        idx = meses_ordenados.index(mes_atual)
        inicio = max(0, idx - 5)
        meses_sel = meses_ordenados[inicio : idx + 1]
    else:
        meses_sel = meses_ordenados[-6:]

    receitas_list: list[float] = []
    despesas_list: list[float] = []
    saldos_list: list[float] = []

    for m in meses_sel:
        ext_m = filtrar_por_mes(extrato, m)
        rec = float(ext_m[ext_m["tipo"] == "Receita"]["valor"].sum())
        desp = float(ext_m[ext_m["tipo"].isin(["Despesa", "Imposto"])]["valor"].sum())
        receitas_list.append(rec)
        despesas_list.append(desp)
        saldos_list.append(rec - desp)

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=meses_sel,
            y=receitas_list,
            name="Receita",
            marker_color=CORES["positivo"],
            customdata=meses_sel,
        )
    )
    fig.add_trace(
        go.Bar(
            x=meses_sel,
            y=despesas_list,
            name="Despesa",
            marker_color=CORES["negativo"],
            customdata=meses_sel,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=meses_sel,
            y=saldos_list,
            name="Saldo",
            mode="lines+markers",
            line=dict(color=CORES["destaque"], width=3),
            marker=dict(size=8),
            yaxis="y2",
        )
    )

    layout_barras = {**LAYOUT_PLOTLY, "margin": dict(l=50, r=20, t=70, b=80)}
    fig.update_layout(
        **layout_barras,
        title=dict(
            text="Receita vs Despesa",
            font=dict(size=FONTE_SUBTITULO),
            y=0.96,
            yanchor="top",
        ),
        barmode="group",
        yaxis_title="Valor (R$)",
        yaxis2=dict(
            title=dict(text="Saldo (R$)", font=dict(color=CORES["destaque"])),
            overlaying="y",
            side="right",
            showgrid=False,
            tickfont=dict(color=CORES["destaque"]),
        ),
    )

    tema.legenda_abaixo(fig)
    aplicar_locale_ptbr(fig, valores_eixo_x=meses_sel)
    aplicar_drilldown(
        fig,
        campo_customdata="mes_ref",
        tab_destino="Extrato",
        key_grafico="bar_receita_despesa",
    )


# ---------------------------------------------------------------------------
# UX-T-01 — KPIs agentic (CSS T-01 e cards-cluster movidos para
# ``componentes/cards_clusters.py`` em UX-V-2.7-FIX. Atividade Recente +
# Sprint Atual movidos para ``componentes/atividade_recente.py``.)
# ---------------------------------------------------------------------------


def _kpis_agentic_html(kpis: dict) -> str:
    """KPIs agentic-first canônicos do mockup."""
    from src.dashboard.componentes.html_utils import minificar

    def _card(modifier: str, href: str, label: str, valor: str, delta: str) -> str:
        return (
            f'<a class="vg-t01-kpi {modifier}" href="{href}" '
            f'style="text-decoration:none;color:inherit;">'
            f'<span class="l">{label}</span>'
            f'<span class="v">{valor}</span>'
            f'<span class="d">{delta}</span>'
            f"</a>"
        )

    return minificar(
        '<div class="vg-t01-kpis">'
        + _card("up", "?cluster=Documentos&tab=Catalogação",
                "Arquivos catalogados", kpis["arquivos_catalogados"], kpis["arquivos_delta"])
        + _card("", "?cluster=Documentos&tab=Extra%C3%A7%C3%A3o+Tripla",
                "Paridade ETL ↔ Opus", kpis["paridade_pct"], kpis["paridade_meta"])
        + _card("warn", "?cluster=Documentos&tab=Revisor",
                "Aguardando humano", kpis["aguardando_humano"], kpis["aguardando_breakdown"])
        + _card("bad", "?cluster=Sistema&tab=Skills+D7",
                "Skills regredindo", kpis["skills_regredindo"], kpis["skills_nomes"])
        + "</div>"
    )


# "Comece pelo todo, depois detalhe." -- princípio do design top-down
# "A riqueza não consiste em ter grandes posses, mas em ter poucas necessidades." -- Epicteto
