"""Página Grafo Visual + Obsidian Rico -- Sprint 53.

Três seções:

1. **Subgrafo interativo** -- plotly scatter do grafo a partir de um
   fornecedor selecionado via `st.selectbox` (1-hop). Nós coloridos por
   tipo, hover com metadata. Read-only sobre `data/output/grafo.sqlite`.
2. **Obsidian Sync** -- preview renderizado do MOC do mês (Markdown) +
   `st.download_button` para baixar o `.md` real.
3. **Fluxo receita-categoria-fornecedor** -- 3 bar charts empilhados
   (substituindo Sankey por decisão do supervisor): receita por fonte,
   despesa por categoria (top 10), top 10 fornecedores por volume.

Princípios:
- Graceful degradation (ADR-10): grafo ausente mostra aviso e retorna.
- Paleta Dracula, fonte mínima 14 (tokens Sprint 20).
- Zero dependências novas: plotly nativo + Streamlit.
- NÃO usa Sankey (decisão explícita do supervisor -- 3 bar charts).
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.dashboard import dados as _dados
from src.dashboard.dados import (
    carregar_subgrafo,
    formatar_moeda,
    listar_fornecedores_com_id,
    obter_fluxo_receita_categoria_fornecedor,
)
from src.dashboard.tema import (
    CORES,
    FONTE_CORPO,
    FONTE_LABEL,
    LAYOUT_PLOTLY,
    SPACING,
    aplicar_locale_ptbr,
    hero_titulo_html,
    rgba_cor,
    rgba_cor_inline,
    subtitulo_secao_html,
)
from src.graph.queries import label_humano

CORES_TIPO: dict[str, str] = {
    "documento": CORES["destaque"],
    "fornecedor": CORES["alerta"],
    "transacao": CORES["neutro"],
    "item": CORES["positivo"],
    "categoria": CORES["superfluo"],
    "periodo": CORES["info"],
    "conta": CORES["texto_sec"],
    "tag_irpf": CORES["obrigatorio"],
    "prescricao": CORES["questionavel"],
    "garantia": CORES["info"],
    "apolice": CORES["neutro"],
    "seguradora": CORES["alerta"],
}


def renderizar(
    dados: dict[str, pd.DataFrame] | None = None,
    periodo: str | None = None,
    pessoa: str | None = None,
    ctx: dict | None = None,
) -> None:
    """Ponto de entrada da página Grafo + Obsidian."""
    _ = pessoa, ctx

    st.markdown(
        hero_titulo_html(
            "",
            "Grafo Visual + Obsidian",
            "Subgrafo interativo de um fornecedor, preview do MOC "
            "mensal sincronizado com Obsidian e fluxo "
            "receita-categoria-fornecedor em bar charts.",
        ),
        unsafe_allow_html=True,
    )

    if not _dados.CAMINHO_GRAFO.exists():
        st.warning(
            "Grafo SQLite não encontrado em `data/output/grafo.sqlite`. "
            "Popule o catálogo rodando `./run.sh --tudo` para gerar o grafo."
        )
        return

    mes_ref = _extrair_mes_ref(dados, periodo)

    # Sprint 78: nova visão full-page Obsidian-like com filtros laterais
    # e clique em nó via URL navigation. Colocada como expander para não
    # deslocar as seções existentes (subgrafo 1-hop, MOC, bar charts).
    with st.expander("Grafo Full-Page (Obsidian-like)", expanded=True):
        _renderizar_fullpage()
    st.markdown(_divisor(), unsafe_allow_html=True)

    _renderizar_subgrafo()
    st.markdown(_divisor(), unsafe_allow_html=True)
    _renderizar_obsidian(mes_ref)
    st.markdown(_divisor(), unsafe_allow_html=True)
    _renderizar_fluxo(mes_ref)


def _renderizar_fullpage() -> None:
    """Sprint 78: grafo full-page com painel de filtros + click handler JS."""
    import streamlit.components.v1 as components

    from src.dashboard.componentes.grafo_pyvis import (
        COR_POR_TIPO,
        construir_grafo_html,
    )
    from src.graph.db import GrafoDB
    from src.graph.queries import grafo_filtrado

    col_grafo, col_filtros = st.columns([7, 3], gap="medium")

    tipos_disponiveis = list(COR_POR_TIPO.keys())

    with col_filtros:
        st.caption("Filtros do grafo")
        tipos = st.multiselect(
            "Tipos de nó",
            options=tipos_disponiveis,
            default=["fornecedor", "documento", "categoria", "transacao"],
            key="grafo_tipos",
        )
        orfaos = st.toggle("Mostrar órfãos", value=False, key="grafo_orfaos")
        limite = st.slider(
            "Limite de nós", min_value=100, max_value=2000, value=500, step=100,
            key="grafo_limite",
        )
        st.divider()
        st.caption("Legenda por tipo")
        for tipo, cor in COR_POR_TIPO.items():
            st.markdown(
                f'<span style="color:{cor}; font-weight:bold;">●</span> '
                f'<span>{tipo}</span>',
                unsafe_allow_html=True,
            )

    with col_grafo:
        with st.spinner("Montando grafo..."):
            with GrafoDB(_dados.CAMINHO_GRAFO) as db:
                nodes, edges = grafo_filtrado(
                    db,
                    tipos=tipos,
                    incluir_orfaos=orfaos,
                    limite=limite,
                )
            st.caption(f"{len(nodes)} nós, {len(edges)} arestas")
            if not nodes:
                st.info(
                    "Nenhum nó para os filtros atuais. Amplie o limite, "
                    "habilite órfãos ou ajuste os tipos."
                )
                return
            html = construir_grafo_html(nodes, edges, altura_px=800)
            components.html(html, height=820, scrolling=False)


def _extrair_mes_ref(
    dados: dict[str, pd.DataFrame] | None, periodo: str | None
) -> str:
    """Determina mes_ref a usar. Fallback: mês mais recente do extrato."""
    if periodo and len(periodo) == 7 and periodo[4] == "-":
        return periodo
    if dados and "extrato" in dados and not dados["extrato"].empty:
        meses = (
            dados["extrato"]["mes_ref"].dropna().astype(str).unique().tolist()
        )
        if meses:
            return sorted(meses, reverse=True)[0]
    from datetime import date as _d

    return _d.today().strftime("%Y-%m")


def _renderizar_subgrafo() -> None:
    """Selectbox de fornecedor + plotly scatter do subgrafo 1-hop."""
    st.markdown(
        subtitulo_secao_html(
            "Subgrafo interativo (1-hop)", cor=CORES["destaque"]
        ),
        unsafe_allow_html=True,
    )

    fornecedores = listar_fornecedores_com_id()
    if not fornecedores:
        st.info("Nenhum fornecedor registrado no grafo ainda.")
        return

    rotulos = {f["id"]: label_humano(f) for f in fornecedores}
    ids_ordenados = [f["id"] for f in fornecedores]

    id_selecionado = st.selectbox(
        "Fornecedor",
        options=ids_ordenados,
        format_func=lambda i: rotulos.get(i, str(i)),
        key="grafo_obsidian_fornecedor",
    )

    if id_selecionado is None:
        return

    sub = carregar_subgrafo(int(id_selecionado), radius=1)
    nodes = sub.get("nodes", [])
    edges = sub.get("edges", [])

    if not nodes:
        st.info("Nenhum vizinho encontrado para este fornecedor.")
        return

    fig = _construir_figura_grafo(nodes, edges, int(id_selecionado))
    st.plotly_chart(fig, use_container_width=True, key="grafo_subgrafo")

    _renderizar_legenda_tipos(nodes)


def _construir_figura_grafo(
    nodes: list[dict], edges: list[dict], center_id: int
) -> go.Figure:
    """Posiciona nó central no meio; vizinhos em círculo ao redor."""
    import math

    id_para_idx: dict[int, int] = {n["id"]: idx for idx, n in enumerate(nodes)}
    n_total = len(nodes)
    posicoes_x: list[float] = [0.0] * n_total
    posicoes_y: list[float] = [0.0] * n_total

    idx_center = id_para_idx.get(center_id, 0)
    posicoes_x[idx_center] = 0.5
    posicoes_y[idx_center] = 0.5

    vizinhos = [i for i in range(n_total) if i != idx_center]
    total_viz = len(vizinhos)
    for k, idx in enumerate(vizinhos):
        angulo = (2 * math.pi * k) / max(total_viz, 1)
        raio = 0.38
        posicoes_x[idx] = 0.5 + raio * math.cos(angulo)
        posicoes_y[idx] = 0.5 + raio * math.sin(angulo)

    # arestas -- segmentos plotly com None separando
    arestas_x: list[float | None] = []
    arestas_y: list[float | None] = []
    for ar in edges:
        src = id_para_idx.get(ar["src_id"])
        dst = id_para_idx.get(ar["dst_id"])
        if src is None or dst is None:
            continue
        arestas_x += [posicoes_x[src], posicoes_x[dst], None]
        arestas_y += [posicoes_y[src], posicoes_y[dst], None]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=arestas_x,
            y=arestas_y,
            mode="lines",
            line={"width": 1.2, "color": rgba_cor(CORES["texto_sec"], 0.45)},
            hoverinfo="skip",
            showlegend=False,
            name="arestas",
        )
    )

    labels: list[str] = []
    hovers: list[str] = []
    cores_marker: list[str] = []
    tamanhos: list[int] = []
    for node in nodes:
        tipo = node.get("tipo", "outro")
        cores_marker.append(CORES_TIPO.get(tipo, CORES["texto_sec"]))
        nome_canonico = node.get("nome_canonico", "")
        rotulo_humano = label_humano(node)
        label_curto = (
            rotulo_humano if len(rotulo_humano) <= 22 else rotulo_humano[:19] + "..."
        )
        labels.append(label_curto)
        meta = node.get("metadata", {}) or {}
        partes = [f"<b>{tipo}</b>", rotulo_humano]
        if nome_canonico and nome_canonico != rotulo_humano:
            partes.append(f"id_canonico: {nome_canonico}")
        for chave in ("data", "data_emissao", "valor", "total", "cnpj"):
            if chave in meta and meta[chave]:
                partes.append(f"{chave}: {meta[chave]}")
        hovers.append("<br>".join(partes))
        tamanhos.append(40 if node["id"] == center_id else 26)

    fig.add_trace(
        go.Scatter(
            x=posicoes_x,
            y=posicoes_y,
            mode="markers+text",
            marker={
                "size": tamanhos,
                "color": cores_marker,
                "line": {"color": CORES["texto"], "width": 1.5},
            },
            text=labels,
            textposition="top center",
            textfont={"size": FONTE_LABEL, "color": CORES["texto"]},
            hovertext=hovers,
            hoverinfo="text",
            showlegend=False,
            name="nós",
        )
    )

    fig.update_layout(
        **LAYOUT_PLOTLY,
        height=520,
        xaxis={
            "visible": False,
            "range": [-0.05, 1.05],
            "showgrid": False,
        },
        yaxis={
            "visible": False,
            "range": [-0.05, 1.1],
            "showgrid": False,
        },
    )
    return fig


def _renderizar_legenda_tipos(nodes: list[dict]) -> None:
    """Mostra badges dos tipos presentes no subgrafo."""
    tipos_presentes = sorted({n.get("tipo", "outro") for n in nodes})
    if not tipos_presentes:
        return
    badges_html: list[str] = []
    for tipo in tipos_presentes:
        cor = CORES_TIPO.get(tipo, CORES["texto_sec"])
        badges_html.append(
            f'<span style="background-color: {cor};'
            f" color: {CORES['fundo']};"
            f" padding: 3px 10px;"
            f" border-radius: 4px;"
            f" font-size: {FONTE_LABEL}px;"
            f" font-weight: 700;"
            f" letter-spacing: 0.05em;"
            f" margin-right: 6px;"
            f' text-transform: uppercase;">{tipo}</span>'
        )
    st.markdown(
        f'<div style="display: flex; flex-wrap: wrap;'
        f' gap: 6px; margin-top: {SPACING["sm"]}px;">'
        + "".join(badges_html)
        + "</div>",
        unsafe_allow_html=True,
    )


def _renderizar_obsidian(mes_ref: str) -> None:
    """Preview do MOC + botão de download."""
    from src.obsidian.sync import gerar_moc_mensal

    st.markdown(
        subtitulo_secao_html(
            f"Obsidian Sync -- MOC {mes_ref}", cor=CORES["neutro"]
        ),
        unsafe_allow_html=True,
    )

    moc_md = gerar_moc_mensal(mes_ref)

    st.download_button(
        label=f"Baixar MOC {mes_ref}.md",
        data=moc_md,
        file_name=f"MOC_{mes_ref}.md",
        mime="text/markdown",
        key="download_moc_obsidian",
    )

    st.markdown(
        f'<div style="'
        f"background-color: {CORES['card_fundo']};"
        f" border-radius: 10px;"
        f" padding: {SPACING['md']}px {SPACING['md'] + 4}px;"
        f" margin-top: {SPACING['sm']}px;"
        f" max-height: 520px;"
        f" overflow-y: auto;"
        f" font-family: 'JetBrains Mono', monospace;"
        f" font-size: {FONTE_LABEL}px;"
        f" line-height: 1.6;"
        f" color: {CORES['texto']};"
        f' border: 1px solid {rgba_cor_inline(CORES["destaque"], 0.3)};">'
        f'<pre style="margin: 0; white-space: pre-wrap;'
        f' color: inherit; font-family: inherit;">{moc_md}</pre>'
        f"</div>",
        unsafe_allow_html=True,
    )


def _renderizar_fluxo(mes_ref: str) -> None:
    """Três bar charts: receita por fonte, despesa por categoria, top fornecedores.

    Decisão do supervisor: substitui o Sankey do mockup por bar charts
    empilhados (mais legíveis, sem dependência nova).
    """
    st.markdown(
        subtitulo_secao_html(
            f"Fluxo -- {mes_ref}", cor=CORES["positivo"]
        ),
        unsafe_allow_html=True,
    )

    fluxo = obter_fluxo_receita_categoria_fornecedor(mes_ref)

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        _bar_chart(
            fluxo["receita"],
            titulo="Receita por fonte",
            cor=CORES["positivo"],
            key="bar_receita",
        )
    with col_b:
        _bar_chart(
            fluxo["despesa"],
            titulo="Despesa por categoria (top 10)",
            cor=CORES["alerta"],
            key="bar_despesa",
        )
    with col_c:
        _bar_chart(
            fluxo["fornecedor"],
            titulo="Top 10 fornecedores",
            cor=CORES["destaque"],
            key="bar_fornecedor",
        )


def _bar_chart(
    itens: list[dict], *, titulo: str, cor: str, key: str
) -> None:
    """Renderiza bar chart horizontal simples."""
    st.markdown(
        f'<p style="color: {CORES["texto_sec"]};'
        f" font-size: {FONTE_LABEL}px;"
        f" font-weight: 700;"
        f" letter-spacing: 0.08em;"
        f" text-transform: uppercase;"
        f' margin: 0 0 {SPACING["xs"]}px 0;">{titulo}</p>',
        unsafe_allow_html=True,
    )

    if not itens:
        st.markdown(
            f'<p style="color: {CORES["texto_sec"]};'
            f" font-size: {FONTE_LABEL}px;"
            f' font-style: italic; margin: 0;">'
            "(sem dados neste período)</p>",
            unsafe_allow_html=True,
        )
        return

    rotulos_completos = [str(it["rotulo"]) for it in itens]
    rotulos_truncados = [
        r if len(r) <= 30 else r[:30] + "..." for r in rotulos_completos
    ]
    valores = [it["valor"] for it in itens]
    textos = [formatar_moeda(v) for v in valores]

    fig = go.Figure(
        go.Bar(
            x=valores,
            y=rotulos_truncados,
            orientation="h",
            marker={"color": cor},
            text=textos,
            textposition="outside",
            textfont={"color": CORES["texto"], "size": FONTE_LABEL},
            customdata=rotulos_completos,
            hovertemplate="%{customdata}<br>R$ %{x:.2f}<extra></extra>",
        )
    )
    layout_override = dict(LAYOUT_PLOTLY)
    layout_override["margin"] = {"l": 10, "r": 40, "t": 10, "b": 30}
    fig.update_layout(
        **layout_override,
        height=320,
        xaxis={
            "title": "",
            "gridcolor": rgba_cor_inline(CORES["texto_sec"], 0.15),
            "showgrid": True,
            "tickfont": {"size": FONTE_LABEL, "color": CORES["texto_sec"]},
        },
        yaxis={
            "title": "",
            "autorange": "reversed",
            "tickfont": {"size": FONTE_LABEL, "color": CORES["texto"]},
        },
        showlegend=False,
    )
    aplicar_locale_ptbr(fig)
    st.plotly_chart(fig, use_container_width=True, key=key)


def _divisor() -> str:
    """HTML de um divisor horizontal fino."""
    return (
        f'<hr style="'
        f"border: 0;"
        f" border-top: 1px solid {rgba_cor_inline(CORES['texto_sec'], 0.25)};"
        f" margin: {SPACING['lg']}px 0;"
        f'" />'
    )


# ancoragem evita import morto em lint
_ = FONTE_CORPO


# "Conhecer é conectar." -- Heráclito (parafraseado)
