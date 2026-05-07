"""Página Análise -- UX-RD-13.

Reescrita conforme mockup ``novo-mockup/mockups/12-analise.html``.

Três sub-abas internas:

* **Fluxo de caixa** -- diagrama Sankey de três níveis
  (categoria -> classificação -> pessoa), com KPIs do topo (entradas,
  saídas, investido, saldo). Resolve UX-03 do plano ativo (labels visíveis
  em viewport >=1200px) via margem direita ampla e ``textfont`` explícito
  no layout.
* **Comparativo mensal** -- linhas multi-metric ao longo dos meses:
  Receita, Despesa, Saldo, % Poupança. Hover tooltip por linha. KPIs do
  mês corrente vs média móvel 6 meses.
* **Padrões temporais** -- heatmap calendário (52 semanas ISO x 7 dias da
  semana) com cor D7 ``destaque`` (#bd93f9) graduada por intensidade. A
  escala começa em ``texto_muted`` (não em ``fundo``) para que cells de
  valor baixo permaneçam visíveis -- invariante UX-RD-12 / WCAG-AA. Click
  em cell dispara drill-down para Extrato filtrado pelo mes_ref.

Funções puras testáveis (UX-RD-13 #2 da seção `tests`):

* ``calcular_kpis_fluxo(df)`` -- agrega receita/despesa/investido/saldo.
* ``preparar_dados_sankey(df)`` -- 3 níveis (categoria, classificação,
  pessoa) com source/target/value.
* ``preparar_dados_comparativo(df)`` -- pivot por mes_ref com 4 métricas.
* ``preparar_dados_heatmap(df)`` -- pivot 7 x 52 com mes_ref de cada cell
  (usado para drill-down).

Funções de renderização (privadas):

* ``_renderizar_aba_fluxo(...)``
* ``_renderizar_aba_comparativo(...)``
* ``_renderizar_aba_padroes(...)``

Função pública:

* ``renderizar(dados, periodo, pessoa, ctx)`` -- entrypoint do dispatcher.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.dashboard import tema
from src.dashboard.componentes.drilldown import aplicar_drilldown
from src.dashboard.componentes.html_utils import minificar
from src.dashboard.componentes.ui import callout_html
from src.dashboard.dados import (
    filtrar_por_forma_pagamento,
    filtrar_por_periodo,
    filtrar_por_pessoa,
    filtro_forma_ativo,
)
from src.dashboard.tema import (
    CORES,
    FONTE_MINIMA,
    FONTE_SUBTITULO,
    LAYOUT_PLOTLY,
    rgba_cor,
)
from src.dashboard.tema_plotly import st_plotly_chart_dracula

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

CORES_CICLO: list[str] = [
    CORES["positivo"],
    CORES["negativo"],
    CORES["neutro"],
    CORES["alerta"],
    CORES["destaque"],
]

MAPA_CLASSIFICACAO_COR: dict[str, str] = {
    "Obrigatório": CORES["obrigatorio"],
    "Questionável": CORES["questionavel"],
    "Supérfluo": CORES["superfluo"],
    "N/A": CORES["texto_sec"],
}

DIAS_SEMANA_PT: list[str] = [
    "Seg",
    "Ter",
    "Qua",
    "Qui",
    "Sex",
    "Sáb",
    "Dom",
]

# Métricas canônicas exibidas no comparativo mensal. Ordem importa para o
# layout (4 linhas, 4 cores estáveis).
METRICAS_COMPARATIVO: list[str] = [
    "Receita",
    "Despesa",
    "Saldo",
    "% Poupança",
]


# ---------------------------------------------------------------------------
# Funções puras testáveis
# ---------------------------------------------------------------------------


def calcular_kpis_fluxo(df: pd.DataFrame) -> dict[str, float]:
    """Agrega KPIs do topo da aba Fluxo.

    Retorna dict com:
      * ``entradas``: soma de Receita
      * ``saidas``: soma de Despesa + Imposto (positivo, valor absoluto)
      * ``investido``: soma de despesas categorizadas como Investimento
      * ``saldo``: entradas - saidas
      * ``taxa_poupanca``: investido / entradas (0 se entradas == 0)
    """
    if df.empty:
        return {
            "entradas": 0.0,
            "saidas": 0.0,
            "investido": 0.0,
            "saldo": 0.0,
            "taxa_poupanca": 0.0,
        }

    receitas = df[df["tipo"] == "Receita"]["valor"].sum()
    despesas = df[df["tipo"].isin(["Despesa", "Imposto"])]["valor"].sum()
    saidas = abs(float(despesas))
    entradas = float(receitas)

    if "categoria" in df.columns:
        cat_series = df["categoria"].astype(str)
        eh_investimento = cat_series.str.contains("Investimento", case=False, na=False)
        eh_despesa = df["tipo"] == "Despesa"
        investido = abs(float(df[eh_despesa & eh_investimento]["valor"].sum()))
    else:
        investido = 0.0

    saldo = entradas - saidas
    taxa_poupanca = (investido / entradas) if entradas > 0 else 0.0

    return {
        "entradas": entradas,
        "saidas": saidas,
        "investido": investido,
        "saldo": saldo,
        "taxa_poupanca": taxa_poupanca,
    }


def preparar_dados_sankey(df: pd.DataFrame, top_n: int = 8) -> dict:
    """Prepara dados Sankey de 3 níveis: categoria -> classificação -> pessoa.

    Filtra apenas despesas e impostos. Top ``top_n`` categorias por valor
    absoluto. Retorna dict com chaves:

      * ``labels``: nomes dos nós (categorias + classificações + pessoas)
      * ``colors``: cor de cada nó
      * ``source``, ``target``, ``value``: arestas
      * ``link_colors``: cor de cada link (rgba 0.3 do nó alvo)
    """
    df_gastos = df[df["tipo"].isin(["Despesa", "Imposto"])].copy()
    if df_gastos.empty:
        return {}

    df_gastos["valor_abs"] = df_gastos["valor"].abs()

    # Top categorias
    por_categoria = (
        df_gastos.groupby("categoria")["valor_abs"]
        .sum()
        .sort_values(ascending=False)
        .head(top_n)
    )
    if por_categoria.empty:
        return {}

    categorias_top = por_categoria.index.tolist()
    df_top = df_gastos[df_gastos["categoria"].isin(categorias_top)]

    classificacoes = sorted(df_top["classificacao"].dropna().unique().tolist())
    pessoas = sorted(df_top["quem"].dropna().unique().tolist()) if "quem" in df_top.columns else []

    labels: list[str] = []
    cores_nos: list[str] = []

    # Bloco 1: categorias
    for cat in categorias_top:
        labels.append(str(cat))
        cores_nos.append(CORES["destaque"])
    idx_cat: dict[str, int] = {cat: i for i, cat in enumerate(categorias_top)}

    # Bloco 2: classificações
    base_class = len(labels)
    for cls in classificacoes:
        labels.append(str(cls))
        cores_nos.append(MAPA_CLASSIFICACAO_COR.get(str(cls), CORES["texto_sec"]))
    idx_class: dict[str, int] = {cls: base_class + i for i, cls in enumerate(classificacoes)}

    # Bloco 3: pessoas
    base_pessoa = len(labels)
    for p in pessoas:
        labels.append(str(p))
        cores_nos.append(CORES["neutro"])
    idx_pessoa: dict[str, int] = {p: base_pessoa + i for i, p in enumerate(pessoas)}

    source: list[int] = []
    target: list[int] = []
    value: list[float] = []
    cores_links: list[str] = []

    # Aresta 1: categoria -> classificação
    cat_class = df_top.groupby(["categoria", "classificacao"])["valor_abs"].sum().reset_index()
    for _, row in cat_class.iterrows():
        cat = row["categoria"]
        cls = row["classificacao"]
        if cat not in idx_cat or cls not in idx_class:
            continue
        source.append(idx_cat[cat])
        target.append(idx_class[cls])
        value.append(float(row["valor_abs"]))
        cores_links.append(
            rgba_cor(MAPA_CLASSIFICACAO_COR.get(str(cls), CORES["texto_sec"]), 0.3)
        )

    # Aresta 2: classificação -> pessoa
    if pessoas:
        class_pessoa = (
            df_top.groupby(["classificacao", "quem"])["valor_abs"].sum().reset_index()
        )
        for _, row in class_pessoa.iterrows():
            cls = row["classificacao"]
            p = row["quem"]
            if cls not in idx_class or p not in idx_pessoa:
                continue
            source.append(idx_class[cls])
            target.append(idx_pessoa[p])
            value.append(float(row["valor_abs"]))
            cores_links.append(rgba_cor(CORES["neutro"], 0.3))

    return {
        "labels": labels,
        "colors": cores_nos,
        "source": source,
        "target": target,
        "value": value,
        "link_colors": cores_links,
        "n_categorias": len(categorias_top),
        "n_classificacoes": len(classificacoes),
        "n_pessoas": len(pessoas),
    }


def preparar_dados_comparativo(df: pd.DataFrame) -> pd.DataFrame:
    """Prepara DataFrame com 4 métricas por mes_ref.

    Colunas retornadas: ``mes_ref``, ``Receita``, ``Despesa``, ``Saldo``,
    ``% Poupança``. Ordenado por mes_ref ascendente. ``Despesa`` é positivo
    (valor absoluto). ``% Poupança`` = saldo/receita * 100, 0 quando receita
    é zero.
    """
    if df.empty or "mes_ref" not in df.columns:
        return pd.DataFrame(columns=["mes_ref", *METRICAS_COMPARATIVO])

    df_validos = df[df["mes_ref"].notna()].copy()
    if df_validos.empty:
        return pd.DataFrame(columns=["mes_ref", *METRICAS_COMPARATIVO])

    receita_por_mes = (
        df_validos[df_validos["tipo"] == "Receita"].groupby("mes_ref")["valor"].sum()
    )
    despesa_por_mes = (
        df_validos[df_validos["tipo"].isin(["Despesa", "Imposto"])]
        .groupby("mes_ref")["valor"]
        .sum()
        .abs()
    )

    meses = sorted(set(receita_por_mes.index) | set(despesa_por_mes.index))
    if not meses:
        return pd.DataFrame(columns=["mes_ref", *METRICAS_COMPARATIVO])

    linhas: list[dict] = []
    for mes in meses:
        rec = float(receita_por_mes.get(mes, 0.0))
        desp = float(despesa_por_mes.get(mes, 0.0))
        saldo = rec - desp
        pct = (saldo / rec * 100.0) if rec > 0 else 0.0
        linhas.append(
            {
                "mes_ref": mes,
                "Receita": rec,
                "Despesa": desp,
                "Saldo": saldo,
                "% Poupança": pct,
            }
        )

    return pd.DataFrame(linhas)


def preparar_dados_heatmap(df: pd.DataFrame) -> dict:
    """Prepara matriz heatmap 7 x 52 (dia da semana x semana ISO).

    Retorna dict com:
      * ``z``: matriz 7x52 (linha = dia da semana, coluna = semana)
      * ``x``: labels das semanas (str da semana ISO)
      * ``y``: labels dos dias da semana em PT-BR
      * ``customdata``: matriz 7x52 com mes_ref de cada cell (string YYYY-MM
        canônica do dia mais frequente naquela cell). Vazio quando cell tem
        valor zero.

    Decisão de design: ``z`` armazena valor absoluto de despesa (zero quando
    sem dado), permitindo colorscale começar acima do fundo no token mínimo
    para cells visíveis -- invariante UX-RD-12 contra "fundo Dracula que
    faz cell desaparecer".
    """
    df_gastos = df[df["tipo"].isin(["Despesa", "Imposto"])].copy()
    if df_gastos.empty or "data" not in df_gastos.columns:
        return {}

    df_gastos["data_dt"] = pd.to_datetime(df_gastos["data"], errors="coerce")
    df_gastos = df_gastos.dropna(subset=["data_dt"])
    if df_gastos.empty:
        return {}

    df_gastos["valor_abs"] = df_gastos["valor"].abs()
    df_gastos["dia_semana"] = df_gastos["data_dt"].dt.dayofweek
    df_gastos["semana_iso"] = df_gastos["data_dt"].dt.isocalendar().week.astype(int)
    df_gastos["mes_ref_calc"] = df_gastos["data_dt"].dt.strftime("%Y-%m")

    pivot = (
        df_gastos.groupby(["dia_semana", "semana_iso"])["valor_abs"]
        .sum()
        .reset_index()
        .pivot(index="dia_semana", columns="semana_iso", values="valor_abs")
        .reindex(range(7))
        .fillna(0.0)
    )
    pivot = pivot.reindex(sorted(pivot.columns), axis=1)

    # mes_ref por cell: usa o mes_ref mais frequente dentre as transações
    # daquele (dia_semana, semana_iso). Se vazio -> string vazia.
    mes_pivot = (
        df_gastos.groupby(["dia_semana", "semana_iso"])["mes_ref_calc"]
        .agg(lambda s: s.mode().iat[0] if not s.mode().empty else "")
        .reset_index()
        .pivot(index="dia_semana", columns="semana_iso", values="mes_ref_calc")
        .reindex(range(7))
        .fillna("")
    )
    mes_pivot = mes_pivot.reindex(sorted(mes_pivot.columns), axis=1)

    semanas_labels = [str(s) for s in pivot.columns.tolist()]

    return {
        "z": pivot.values.tolist(),
        "x": semanas_labels,
        "y": DIAS_SEMANA_PT,
        "customdata": mes_pivot.values.tolist(),
    }


# ---------------------------------------------------------------------------
# Render helpers privados (HTML/Plotly)
# ---------------------------------------------------------------------------


def _kpi_card_html(label: str, valor: str, delta: str, cor_valor: str) -> str:
    """HTML do card KPI no estilo do mockup 12-analise.

    Lição UX-RD-04 canonizada via ``minificar``: indentação Python >=4
    espaços vira ``<pre><code>`` no parser CommonMark do Streamlit.
    """
    return minificar(
        f"""
        <div style='background:{CORES["card_fundo"]};
                    border:1px solid {rgba_cor(CORES["texto_sec"], 0.2)};
                    border-radius:8px;padding:16px;'>
          <div style='font-family:monospace;font-size:10px;letter-spacing:0.08em;
                      text-transform:uppercase;color:{CORES["texto_muted"]};'>
            {label}
          </div>
          <div style='font-family:monospace;font-size:24px;font-weight:500;
                      color:{cor_valor};margin-top:6px;line-height:1;
                      font-variant-numeric:tabular-nums;'>
            {valor}
          </div>
          <div style='font-family:monospace;font-size:11px;
                      color:{CORES["texto_muted"]};margin-top:6px;'>
            {delta}
          </div>
        </div>
        """
    )


def _renderizar_aba_fluxo(df: pd.DataFrame) -> None:
    """Renderiza KPIs + Sankey de 3 níveis."""
    kpis = calcular_kpis_fluxo(df)

    col1, col2, col3, col4 = st.columns(4)
    cols = [col1, col2, col3, col4]

    def fmt(v: float) -> str:
        return f"R$ {v:,.0f}".replace(",", ".")

    cor_saldo = CORES["d7_graduado"] if kpis["saldo"] >= 0 else CORES["negativo"]
    pct_poupanca = f"{kpis['taxa_poupanca'] * 100:.1f}% taxa de poupança"
    cards = [
        ("Entradas", fmt(kpis["entradas"]), "Receita do recorte", CORES["positivo"]),
        ("Saídas", fmt(kpis["saidas"]), "Despesas + impostos", CORES["negativo"]),
        ("Investido", fmt(kpis["investido"]), pct_poupanca, CORES["destaque"]),
        ("Saldo", fmt(kpis["saldo"]), "Entradas - saídas", cor_saldo),
    ]
    for col, (label, valor, delta, cor) in zip(cols, cards, strict=True):
        with col:
            st.markdown(_kpi_card_html(label, valor, delta, cor), unsafe_allow_html=True)

    st.markdown("---")

    dados_sankey = preparar_dados_sankey(df)
    if not dados_sankey:
        st.markdown(
            callout_html("info", "Dados insuficientes para o diagrama Sankey."),
            unsafe_allow_html=True,
        )
        return

    fig = go.Figure(
        data=[
            go.Sankey(
                node=dict(
                    pad=24,
                    thickness=22,
                    line=dict(color=CORES["card_fundo"], width=1),
                    label=dados_sankey["labels"],
                    color=dados_sankey["colors"],
                ),
                link=dict(
                    source=dados_sankey["source"],
                    target=dados_sankey["target"],
                    value=dados_sankey["value"],
                    color=dados_sankey["link_colors"],
                    hovertemplate=(
                        "%{source.label} -> %{target.label}<br>"
                        "R$ %{value:,.2f}<extra></extra>"
                    ),
                ),
                # UX-RD-13 / UX-03: textfont explícito garante labels visíveis
                # em viewport >=1200px sem truncamento.
                textfont=dict(
                    color=CORES["texto"],
                    size=FONTE_MINIMA,
                    family="JetBrains Mono, monospace",
                ),
            )
        ]
    )

    fig.update_layout(
        **LAYOUT_PLOTLY,
        title=dict(
            text="Fluxo: categoria -> classificação -> pessoa",
            font=dict(size=FONTE_SUBTITULO),
        ),
    )
    tema.legenda_abaixo(fig)
    # Margens generosas (l=40, r=160) para evitar corte de label longo.
    fig.update_layout(margin=dict(l=40, r=160, t=fig.layout.margin.t, b=fig.layout.margin.b))
    st_plotly_chart_dracula(fig)


def _renderizar_aba_comparativo(df: pd.DataFrame) -> None:
    """Renderiza linhas multi-metric ao longo dos meses."""
    df_comp = preparar_dados_comparativo(df)
    if df_comp.empty:
        st.markdown(
            callout_html("info", "Dados insuficientes para o comparativo mensal."),
            unsafe_allow_html=True,
        )
        return

    fig = go.Figure()
    cores_metricas = {
        "Receita": CORES["positivo"],
        "Despesa": CORES["negativo"],
        "Saldo": CORES["destaque"],
        "% Poupança": CORES["alerta"],
    }

    # Receita / Despesa / Saldo no eixo Y principal (R$); % Poupança no Y2.
    for metrica in ["Receita", "Despesa", "Saldo"]:
        fig.add_trace(
            go.Scatter(
                x=df_comp["mes_ref"],
                y=df_comp[metrica],
                name=metrica,
                mode="lines+markers",
                line=dict(color=cores_metricas[metrica], width=2),
                marker=dict(size=7),
                hovertemplate=(
                    f"{metrica}<br>Mês: %{{x}}<br>R$ %{{y:,.2f}}<extra></extra>"
                ),
            )
        )

    fig.add_trace(
        go.Scatter(
            x=df_comp["mes_ref"],
            y=df_comp["% Poupança"],
            name="% Poupança",
            mode="lines+markers",
            line=dict(color=cores_metricas["% Poupança"], width=2, dash="dot"),
            marker=dict(size=6, symbol="diamond"),
            yaxis="y2",
            hovertemplate=(
                "% Poupança<br>Mês: %{x}<br>%{y:.1f}%<extra></extra>"
            ),
        )
    )

    layout_base = {k: v for k, v in LAYOUT_PLOTLY.items() if k != "margin"}
    fig.update_layout(
        **layout_base,
        title=dict(
            text="Comparativo mensal -- 4 métricas",
            font=dict(size=FONTE_SUBTITULO),
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.25,
            xanchor="center",
            x=0.5,
            font=dict(size=FONTE_MINIMA),
        ),
        xaxis_title="Mês",
        yaxis=dict(
            title="Valor (R$)",
            side="left",
        ),
        yaxis2=dict(
            title="% Poupança",
            overlaying="y",
            side="right",
            showgrid=False,
            ticksuffix="%",
        ),
        margin=dict(l=60, r=60, t=60, b=80),
        hovermode="x unified",
    )

    st_plotly_chart_dracula(fig)


def _renderizar_aba_padroes(df: pd.DataFrame) -> None:
    """Renderiza heatmap calendário 7 x 52 com drill-down por mes_ref."""
    dados_heatmap = preparar_dados_heatmap(df)
    if not dados_heatmap:
        st.markdown(
            callout_html("info", "Dados insuficientes para o heatmap calendário."),
            unsafe_allow_html=True,
        )
        return

    # UX-RD-12 invariante WCAG-AA: começar a colorscale em ``texto_muted``
    # (não ``fundo``) garante que cells de valor zero/baixo permaneçam
    # visíveis no fundo Dracula. Token D7 ``destaque`` (#bd93f9) gradua até
    # o pico.
    escala_cores = [
        [0.0, CORES["texto_muted"]],
        [0.25, rgba_cor(CORES["destaque"], 0.4)],
        [0.5, rgba_cor(CORES["destaque"], 0.65)],
        [0.75, rgba_cor(CORES["destaque"], 0.85)],
        [1.0, CORES["destaque"]],
    ]

    fig = go.Figure(
        data=go.Heatmap(
            z=dados_heatmap["z"],
            x=dados_heatmap["x"],
            y=dados_heatmap["y"],
            customdata=dados_heatmap["customdata"],
            colorscale=escala_cores,
            zmin=0,
            hovertemplate=(
                "Semana %{x}<br>%{y}<br>"
                "R$ %{z:,.2f}<br>"
                "Mês: %{customdata}<extra></extra>"
            ),
            colorbar=dict(
                title=dict(text="R$", font=dict(size=FONTE_MINIMA)),
                tickfont=dict(size=FONTE_MINIMA),
            ),
            xgap=2,
            ygap=2,
        )
    )

    fig.update_layout(
        **LAYOUT_PLOTLY,
        title=dict(
            text="Calendário de gastos -- 52 semanas x 7 dias",
            font=dict(size=FONTE_SUBTITULO),
        ),
        xaxis_title="Semana ISO",
        yaxis_title="Dia da semana",
        yaxis=dict(autorange="reversed"),
    )
    tema.legenda_abaixo(fig)

    # Drill-down: click em cell aplica filtro mes_ref e navega para Extrato.
    aplicar_drilldown(
        fig,
        campo_customdata="mes_ref",
        tab_destino="Extrato",
        key_grafico="heatmap_analise_padroes",
    )


# ---------------------------------------------------------------------------
# Entrypoint público
# ---------------------------------------------------------------------------


def renderizar(
    dados: dict[str, pd.DataFrame],
    periodo: str,
    pessoa: str,
    ctx: dict | None = None,
) -> None:
    """Renderiza página Análise (UX-RD-12 + UX-T-12)."""
    from src.dashboard.componentes.topbar_actions import renderizar_grupo_acoes
    renderizar_grupo_acoes([
        {"label": "Categorias", "href": "?cluster=Análise&tab=Categorias",
         "title": "Ir para regras de categorias"},
        {"label": "Exportar relatório", "primary": True,
         "title": "Gerar PDF do relatório"},
    ])

    # UX-U-03: page-header canônico via helper.
    from src.dashboard.componentes.page_header import renderizar_page_header
    st.markdown(
        renderizar_page_header(
            titulo="ANÁLISE",
            subtitulo=(
                "Três perspectivas sobre o mesmo dataset normalizado: para "
                "onde vai o dinheiro (fluxo), o que mudou ao longo do tempo "
                "(comparativo) e quando acontece (padrões)."
            ),
            sprint_tag="UX-RD-12",
        ),
        unsafe_allow_html=True,
    )

    if "extrato" not in dados:
        st.markdown(
            callout_html("warning", "Nenhum dado encontrado para análise."),
            unsafe_allow_html=True,
        )
        return

    gran = ctx.get("granularidade", "Mês") if ctx else "Mês"
    periodo_filtro = ctx.get("periodo", periodo) if ctx else periodo

    extrato = dados["extrato"]
    extrato_pessoa = filtrar_por_forma_pagamento(
        filtrar_por_pessoa(extrato, pessoa), filtro_forma_ativo()
    )
    extrato_periodo = filtrar_por_periodo(extrato_pessoa, gran, periodo_filtro)

    aba_fluxo, aba_comparativo, aba_padroes = st.tabs(
        ["Fluxo de caixa", "Comparativo mensal", "Padrões temporais"]
    )

    with aba_fluxo:
        _renderizar_aba_fluxo(extrato_periodo)

    with aba_comparativo:
        # Comparativo usa série histórica completa (não recortada por período)
        # para revelar tendência ao longo dos meses, espelhando o card "12 meses"
        # do mockup.
        _renderizar_aba_comparativo(extrato_pessoa)

    with aba_padroes:
        _renderizar_aba_padroes(extrato_pessoa)


# "Aqueles que não conseguem lembrar o passado estão condenados a repeti-lo." -- George Santayana
