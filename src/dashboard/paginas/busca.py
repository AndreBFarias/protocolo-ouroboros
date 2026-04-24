"""Página Busca Global -- Sprint 52.

Input de busca permanente no topo que consulta o grafo SQLite (read-only)
e retorna resultados agrupados em quatro seções: fornecedores, documentos,
transações e itens. Timeline plotly renderizada quando há resultados
temporais.

Princípios:
- Read-only sobre `data/output/grafo.sqlite` (abre em `mode=ro`).
- Graceful degradation (ADR-10): grafo ausente mostra aviso e retorna.
- Paleta Dracula e tokens tipográficos vindos de `src.dashboard.tema`
  (Sprint 20).
- Input único permanente (decisão do supervisor pós-mockup): sem modal
  Ctrl+K, sem estado escondido.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.dashboard import dados as _dados
from src.dashboard.dados import (
    buscar_global,
    formatar_moeda,
)
from src.dashboard.tema import (
    CORES,
    FONTE_CORPO,
    FONTE_LABEL,
    LAYOUT_PLOTLY,
    SPACING,
    callout_html,
    card_html,
    hero_titulo_html,
    icon_html,
    rgba_cor_inline,
    subtitulo_secao_html,
)

SUGESTOES_RAPIDAS: list[str] = [
    "neoenergia",
    "farmácia",
    "americanas",
    "posto",
    "2026-03",
    "uber",
]


def renderizar(
    dados: dict[str, pd.DataFrame] | None = None,
    periodo: str | None = None,
    pessoa: str | None = None,
    ctx: dict | None = None,
) -> None:
    """Ponto de entrada da página Busca Global.

    A assinatura casa com as outras páginas para manter contrato uniforme
    no dashboard, mas a fonte de verdade é o grafo -- XLSX não é usado.
    """
    _ = dados, periodo, pessoa, ctx  # não utilizados -- contrato da página

    st.markdown(
        hero_titulo_html(
            "",
            "Busca Global",
            "Input único permanente: digite fornecedor, CNPJ, item, data "
            "(YYYY-MM) ou valor. Retorna fornecedores agregados, documentos, "
            "transações e itens casados, com timeline cronológica.",
        ),
        unsafe_allow_html=True,
    )

    termo = _renderizar_input_permanente()

    if not _dados.CAMINHO_GRAFO.exists():
        st.markdown(
            callout_html(
                "warning",
                "Grafo SQLite não encontrado. Popule o catálogo rodando "
                "`./run.sh --tudo` (ou `make process`) para gerar "
                "`data/output/grafo.sqlite`.",
            ),
            unsafe_allow_html=True,
        )
        return

    if not termo:
        st.markdown(
            callout_html(
                "info",
                "Digite um termo acima ou use uma das sugestões para iniciar "
                "a busca. Os resultados aparecem aqui agrupados por tipo.",
            ),
            unsafe_allow_html=True,
        )
        return

    resultados = buscar_global(termo)
    _renderizar_resumo(termo, resultados)

    total = sum(len(v) for v in resultados.values())
    if total == 0:
        st.markdown(
            callout_html("info", f"Nenhum resultado encontrado para '{termo}'."),
            unsafe_allow_html=True,
        )
        return

    _renderizar_fornecedores(resultados["fornecedores"])
    _renderizar_timeline(resultados)
    st.markdown(_divisor(), unsafe_allow_html=True)
    _renderizar_documentos(resultados["documentos"])
    _renderizar_transacoes(resultados["transacoes"])
    _renderizar_itens(resultados["itens"])


def _aplicar_chip_sugestao(valor: str) -> None:
    """Callback do chip: injeta o termo no input da busca.

    Ao ser usado como `on_click` do `st.button`, este callback roda ANTES
    do próximo ciclo de render -- por isso o `st.text_input` com
    `key="busca_termo_input"` abaixo já renderiza com o valor atualizado,
    sem precisar de `st.rerun()` explícito (padrão canônico Streamlit e
    contorno da armadilha A59-1: `st.rerun` em callback inline gera loop).
    """
    st.session_state["busca_termo_input"] = valor


def _renderizar_input_permanente() -> str:
    """Input único permanente no topo + chips de sugestão clicáveis.

    Sprint 92c: o ícone Feather ``search`` precede o label do input, dando
    affordance visual à caixa de busca. Streamlit não expõe ``prefix`` em
    ``st.text_input``, então renderizamos o par ícone+label como HTML acima
    do input, com label nativo colapsado (``label_visibility="collapsed"``).
    """
    svg_busca = icon_html("search", tamanho=18, cor=CORES["destaque"])
    # Sprint 92c: classe utilitaria .ouroboros-label-icon (em css_global)
    # consolida display:flex + gap + cor destaque + margin.
    st.markdown(
        f'<div class="ouroboros-label-icon">{svg_busca}<span>Busca global</span></div>',
        unsafe_allow_html=True,
    )
    termo = st.text_input(
        "Busca global",
        placeholder="fornecedor, CNPJ, item, data (YYYY-MM), valor...",
        label_visibility="collapsed",
        key="busca_termo_input",
    )

    cols = st.columns(len(SUGESTOES_RAPIDAS))
    for idx, (col, sug) in enumerate(zip(cols, SUGESTOES_RAPIDAS)):
        with col:
            st.button(
                sug,
                key=f"busca_sug_{idx}",
                use_container_width=True,
                on_click=_aplicar_chip_sugestao,
                args=(sug,),
            )

    return (termo or "").strip()


def _renderizar_resumo(termo: str, resultados: dict[str, list[dict]]) -> None:
    """Linha de resumo mostrando contagem total.

    Sprint 92c: classe utilitaria ``ouroboros-row-flex`` consolida o layout
    inline anterior; inner <p> usa var CSS para cor e fonte.
    """
    total = sum(len(v) for v in resultados.values())
    st.markdown(
        '<div class="ouroboros-row-flex ouroboros-row-resumo-busca">'
        '<p style="color: var(--color-texto); font-size: var(--font-corpo);'
        ' margin: 0;">Resultados para '
        f'<strong style="color: var(--color-destaque);">"{termo}"</strong></p>'
        '<p style="color: var(--color-texto-sec); font-size: var(--font-label);'
        f' margin: 0;">{total} itens encontrados</p>'
        '</div>',
        unsafe_allow_html=True,
    )


def _renderizar_fornecedores(fornecedores: list[dict]) -> None:
    """Seção de fornecedores como cards coloridos com aliases e agregados."""
    if not fornecedores:
        return

    st.markdown(
        subtitulo_secao_html(
            f"Fornecedores encontrados ({len(fornecedores)})",
            cor=CORES["destaque"],
        ),
        unsafe_allow_html=True,
    )

    for forn in fornecedores[:10]:
        nome = (forn.get("nome_canonico") or "").strip() or "--"
        cnpj = forn.get("cnpj") or "--"
        aliases = forn.get("aliases") or []
        ndocs = int(forn.get("total_documentos") or 0)
        total = float(forn.get("total_gasto") or 0.0)
        categoria = forn.get("categoria") or ""

        aliases_html = _aliases_html(aliases)
        categoria_html = ""
        if categoria:
            categoria_html = (
                f'<span style="background-color: {CORES["destaque"]};'
                f" color: {CORES['fundo']};"
                f" border-radius: 4px;"
                f" padding: 2px 8px;"
                f" font-size: {FONTE_LABEL - 2}px;"
                f" font-weight: 700;"
                f' text-transform: uppercase;">{categoria}</span>'
            )

        # Sprint 92c: classes .ouroboros-card-hero-busca e .ouroboros-row-between
        # substituem o antigo encadeamento de <div style=> inline. O inner
        # "flex: 1" (unico) permanece por ser aplicado a um elemento especifico
        # que compete com o irmao de categoria.
        total_str = formatar_moeda(total)
        st.markdown(
            '<div class="ouroboros-card-hero-busca">'
            '<div class="ouroboros-row-between">'
            '<div style="flex: 1;">'
            '<p style="color: var(--color-texto); '
            f"font-size: {FONTE_CORPO + 1}px; "
            "font-weight: 700; "
            f'margin: 0;">{nome}</p>'
            '<p style="color: var(--color-neutro); '
            "font-size: var(--font-label); "
            "font-family: monospace; "
            f'margin: 4px 0 0 0;">CNPJ {cnpj}</p>'
            "</div>"
            f"<div>{categoria_html}</div>"
            "</div>"
            '<div class="ouroboros-row-flex" '
            f'style="gap: {SPACING["lg"]}px; margin: {SPACING["md"]}px 0 {SPACING["sm"]}px 0;">'
            "<div>"
            '<p style="color: var(--color-texto-sec); '
            f"font-size: {FONTE_LABEL - 2}px; "
            "text-transform: uppercase; "
            'letter-spacing: 0.08em; margin: 0;">Documentos</p>'
            '<p style="color: var(--color-texto); '
            f"font-size: {FONTE_CORPO + 4}px; "
            "font-weight: 700; "
            f'margin: 2px 0 0 0;">{ndocs}</p>'
            "</div>"
            "<div>"
            '<p style="color: var(--color-texto-sec); '
            f"font-size: {FONTE_LABEL - 2}px; "
            "text-transform: uppercase; "
            'letter-spacing: 0.08em; margin: 0;">Total transações</p>'
            '<p style="color: var(--color-negativo); '
            f"font-size: {FONTE_CORPO + 4}px; "
            "font-weight: 700; "
            f'margin: 2px 0 0 0;">{total_str}</p>'
            "</div>"
            "</div>"
            f"{aliases_html}"
            "</div>",
            unsafe_allow_html=True,
        )


def _aliases_html(aliases: list[str]) -> str:
    """Renderiza aliases como badges horizontais; vazio se não houver.

    Sprint 92c: ``.ouroboros-aliases-line`` (CSS global) substitui o
    ``display: flex`` inline anterior; cores migram para ``var(--color-*)``.
    """
    if not aliases:
        return ""
    badges = []
    for alias in aliases[:6]:
        badges.append(
            '<span style="background-color: '
            f"{rgba_cor_inline(CORES['texto_sec'], 0.25)};"
            " color: var(--color-texto);"
            " border-radius: 4px;"
            " padding: 2px 6px;"
            f" font-size: {FONTE_LABEL - 2}px;"
            f' margin-right: 4px;">{alias}</span>'
        )
    return (
        '<p style="color: var(--color-texto-sec);'
        f" font-size: {FONTE_LABEL - 1}px;"
        ' margin: 0 0 4px 0;">Aliases</p>'
        '<div class="ouroboros-aliases-line">'
        f"{''.join(badges)}"
        "</div>"
    )


def _renderizar_timeline(resultados: dict[str, list[dict]]) -> None:
    """Timeline plotly: diamond = documento, círculo = transação."""
    docs = [d for d in resultados.get("documentos", []) if d.get("data")]
    txs = [t for t in resultados.get("transacoes", []) if t.get("data")]

    if not docs and not txs:
        return

    st.markdown(
        subtitulo_secao_html(
            "Timeline — documentos e transações",
            cor=CORES["neutro"],
        ),
        unsafe_allow_html=True,
    )

    fig = go.Figure()

    if docs:
        docs_df = pd.DataFrame(docs)
        docs_df["_data_dt"] = pd.to_datetime(docs_df["data"], errors="coerce")
        docs_df = docs_df.dropna(subset=["_data_dt"])
        if not docs_df.empty:
            fig.add_trace(
                go.Scatter(
                    x=docs_df["_data_dt"],
                    y=[1] * len(docs_df),
                    mode="markers",
                    marker={
                        "size": 16,
                        "color": CORES["destaque"],
                        "line": {"color": CORES["texto"], "width": 2},
                        "symbol": "diamond",
                    },
                    name="Documentos",
                    text=[
                        f"{r.get('tipo_documento', '--')}<br>"
                        f"{formatar_moeda(float(r.get('total', 0.0) or 0.0))}"
                        for _, r in docs_df.iterrows()
                    ],
                    hovertemplate="%{text}<br>%{x|%Y-%m-%d}<extra></extra>",
                )
            )

    if txs:
        tx_df = pd.DataFrame(txs)
        tx_df["_data_dt"] = pd.to_datetime(tx_df["data"], errors="coerce")
        tx_df = tx_df.dropna(subset=["_data_dt"])
        if not tx_df.empty:
            fig.add_trace(
                go.Scatter(
                    x=tx_df["_data_dt"],
                    y=[0] * len(tx_df),
                    mode="markers",
                    marker={
                        "size": 12,
                        "color": CORES["neutro"],
                        "line": {"color": CORES["texto"], "width": 1},
                        "symbol": "circle",
                    },
                    name="Transações",
                    text=[
                        f"{r.get('local', '--')}<br>"
                        f"{formatar_moeda(float(r.get('valor', 0.0) or 0.0))}"
                        for _, r in tx_df.iterrows()
                    ],
                    hovertemplate="%{text}<br>%{x|%Y-%m-%d}<extra></extra>",
                )
            )

    fig.update_layout(
        **LAYOUT_PLOTLY,
        height=260,
        showlegend=True,
        legend={"orientation": "h", "y": -0.35, "x": 0},
        xaxis={
            "title": "",
            "gridcolor": rgba_cor_inline(CORES["texto_sec"], 0.15),
            "showgrid": True,
        },
        yaxis={
            "title": "",
            "showticklabels": False,
            "range": [-0.5, 1.5],
            "showgrid": False,
        },
    )
    st.plotly_chart(fig, use_container_width=True, key="busca_timeline")


def _renderizar_documentos(docs: list[dict]) -> None:
    """Seção de documentos em DataFrame compacto."""
    st.markdown(
        subtitulo_secao_html(f"Documentos ({len(docs)})"),
        unsafe_allow_html=True,
    )

    if not docs:
        st.markdown(
            callout_html("info", "Nenhum documento casou com a busca."),
            unsafe_allow_html=True,
        )
        return

    df = pd.DataFrame(
        [
            {
                "Data": d.get("data", "--") or "--",
                "Tipo": d.get("tipo_documento", "--"),
                "Fornecedor": (d.get("razao_social") or "--").strip() or "--",
                "Total": formatar_moeda(float(d.get("total", 0.0) or 0.0)),
            }
            for d in docs
        ]
    )
    st.dataframe(
        df.sort_values("Data", ascending=False),
        width="stretch",
        hide_index=True,
    )


def _renderizar_transacoes(txs: list[dict]) -> None:
    """Seção de transações em DataFrame compacto."""
    st.markdown(
        subtitulo_secao_html(f"Transações ({len(txs)})"),
        unsafe_allow_html=True,
    )

    if not txs:
        st.markdown(
            callout_html("info", "Nenhuma transação casou com a busca."),
            unsafe_allow_html=True,
        )
        return

    df = pd.DataFrame(
        [
            {
                "Data": t.get("data", "--") or "--",
                "Local": t.get("local", "--") or "--",
                "Banco": t.get("banco", "--") or "--",
                "Tipo": t.get("tipo_transacao", "--") or "--",
                "Valor": formatar_moeda(float(t.get("valor", 0.0) or 0.0)),
            }
            for t in txs
        ]
    )
    st.dataframe(df, width="stretch", hide_index=True)


def _renderizar_itens(itens: list[dict]) -> None:
    """Seção de itens em DataFrame compacto."""
    st.markdown(
        subtitulo_secao_html(f"Itens ({len(itens)})"),
        unsafe_allow_html=True,
    )

    if not itens:
        st.markdown(
            callout_html("info", "Nenhum item casou com a busca."),
            unsafe_allow_html=True,
        )
        return

    agrupados: dict[str, dict] = {}
    for it in itens:
        chave = (it.get("descricao") or "").strip().lower() or "(sem descrição)"
        slot = agrupados.setdefault(
            chave,
            {
                "descricao": it.get("descricao", "--"),
                "ocorrencias": 0,
                "valor": 0.0,
            },
        )
        slot["ocorrencias"] += 1
        slot["valor"] += float(it.get("valor", 0.0) or 0.0)

    df = pd.DataFrame(
        [
            {
                "Descrição": linha["descricao"],
                "Ocorrências": linha["ocorrencias"],
                "Valor somado": formatar_moeda(linha["valor"]),
            }
            for linha in agrupados.values()
        ]
    )
    df = df.sort_values("Ocorrências", ascending=False)
    st.dataframe(df, width="stretch", hide_index=True)

    # mantém referência ao helper de card para evitar import morto em lint
    _ = card_html


def _divisor() -> str:
    """HTML de um divisor horizontal fino reutilizável."""
    return (
        f'<hr style="'
        f"border: 0;"
        f" border-top: 1px solid {rgba_cor_inline(CORES['texto_sec'], 0.25)};"
        f" margin: {SPACING['lg']}px 0;"
        f'" />'
    )


# "Buscar é perguntar com precisão." -- Sócrates (parafraseado)
