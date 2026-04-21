"""Página mockup -- Sprint 52 Busca Global Doc-Cêntrica.

MOCKUP wireframe para Sprint 52 -- não é código de produção.
Input único retorna fornecedores, documentos, transações, itens e timeline.
Mock estático: retorna mesmo resultado independente do input.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from mockups.tema_mockup import (
    CORES,
    LAYOUT_PLOTLY,
    badge_html,
    divisor,
    hero_titulo,
    rgba_cor,
    subtitulo_secao,
)

FORNECEDOR_DESTAQUE: dict = {
    "nome": "Neoenergia Distribuição Brasília",
    "cnpj": "00.394.460/0058-87",
    "aliases": ["NEOENERGIA DF", "CEB-DIS", "NEOENERGIA S.A.", "NEOENERGIA BRASILIA"],
    "total_documentos": 48,
    "total_gasto": 23487.12,
    "primeiro_registro": "2022-08-14",
    "ultimo_registro": "2026-04-08",
    "categoria": "Moradia / Energia",
}

DOCUMENTOS_RESULTADOS: list[dict] = [
    {
        "data": "2026-04-08",
        "tipo": "Fatura energia",
        "numero": "2026-04",
        "total": 487.23,
        "itens": 1,
    },
    {
        "data": "2026-03-08",
        "tipo": "Fatura energia",
        "numero": "2026-03",
        "total": 512.11,
        "itens": 1,
    },
    {
        "data": "2026-02-09",
        "tipo": "Fatura energia",
        "numero": "2026-02",
        "total": 498.67,
        "itens": 1,
    },
    {
        "data": "2026-01-08",
        "tipo": "Fatura energia",
        "numero": "2026-01",
        "total": 543.88,
        "itens": 1,
    },
    {
        "data": "2025-12-10",
        "tipo": "Fatura energia",
        "numero": "2025-12",
        "total": 612.42,
        "itens": 1,
    },
]

TRANSACOES_RESULTADOS: list[dict] = [
    {"data": "2026-04-09", "banco": "Itaú", "desc": "DEB AUTOMATICO NEOENERGIA", "valor": -487.23},
    {"data": "2026-03-10", "banco": "Itaú", "desc": "DEB AUTOMATICO NEOENERGIA", "valor": -512.11},
    {"data": "2026-02-10", "banco": "Itaú", "desc": "DEB AUTOMATICO NEOENERGIA", "valor": -498.67},
    {"data": "2026-01-09", "banco": "Itaú", "desc": "DEB AUTOMATICO NEOENERGIA", "valor": -543.88},
    {"data": "2025-12-11", "banco": "Itaú", "desc": "PIX NEOENERGIA", "valor": -612.42},
    {"data": "2025-11-10", "banco": "Itaú", "desc": "DEB AUTOMATICO CEB-DIS", "valor": -589.90},
    {"data": "2025-10-09", "banco": "Itaú", "desc": "DEB AUTOMATICO NEOENERGIA", "valor": -601.33},
    {"data": "2025-09-08", "banco": "Itaú", "desc": "DEB AUTOMATICO CEB-DIS", "valor": -578.14},
]

ITENS_RESULTADOS: list[dict] = [
    {"descricao": "Energia elétrica residencial (kWh)", "ocorrencias": 48, "gasto": 22891.44},
    {"descricao": "Iluminação pública (contribuição)", "ocorrencias": 48, "gasto": 595.68},
]

SUGESTOES_RAPIDAS: list[str] = [
    "neoenergia",
    "CNPJ 00.394.460/0058-87",
    "farmácia",
    "americanas",
    "2026-03",
    "R$ 487,23",
    "posto shell",
]


def _formatar_brl(valor: float) -> str:
    sinal = "-" if valor < 0 else ""
    bruto = f"{abs(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{sinal}R$ {bruto}"


def _renderizar_input_busca() -> str:
    st.markdown(
        f'<div style="'
        f"background: linear-gradient(135deg, "
        f"{rgba_cor(CORES['destaque'], 0.15)} 0%, "
        f"{rgba_cor(CORES['neutro'], 0.10)} 100%);"
        f" border-radius: 16px;"
        f" padding: 28px 32px;"
        f" margin-bottom: 20px;"
        f' border: 1px solid {rgba_cor(CORES["destaque"], 0.25)};">'
        f'<p style="color: {CORES["texto_sec"]};'
        f" font-size: 11px;"
        f" font-weight: 700;"
        f" letter-spacing: 0.12em;"
        f" text-transform: uppercase;"
        f' margin: 0 0 10px 0;">Busca global</p>'
        f"</div>",
        unsafe_allow_html=True,
    )
    query = st.text_input(
        "Busca global",
        value="neoenergia",
        placeholder="fornecedor, CNPJ, item, data (YYYY-MM), valor...",
        label_visibility="collapsed",
    )
    col_sug = st.columns(len(SUGESTOES_RAPIDAS))
    for idx, (col, sug) in enumerate(zip(col_sug, SUGESTOES_RAPIDAS)):
        with col:
            st.button(sug, key=f"sug_{idx}", use_container_width=True, disabled=True)
    return query


def _renderizar_resumo(query: str) -> None:
    total_resultados = (
        1 + len(DOCUMENTOS_RESULTADOS) + len(TRANSACOES_RESULTADOS) + len(ITENS_RESULTADOS)
    )
    st.markdown(
        f'<div style="display: flex; gap: 20px; margin: 20px 0;'
        f' align-items: center;">'
        f'<p style="color: {CORES["texto"]};'
        f" font-size: 14px;"
        f' margin: 0;">Resultados para '
        f'<strong style="color: {CORES["destaque"]};">"{query}"</strong>'
        f"</p>"
        f'<p style="color: {CORES["texto_sec"]};'
        f" font-size: 12px;"
        f' margin: 0;">{total_resultados} itens · 387 ms</p>'
        f"</div>",
        unsafe_allow_html=True,
    )


def _renderizar_card_fornecedor() -> None:
    st.markdown(
        subtitulo_secao("Fornecedor", cor=CORES["destaque"]),
        unsafe_allow_html=True,
    )
    f = FORNECEDOR_DESTAQUE
    aliases_html = " ".join(badge_html(a, CORES["texto_sec"], fonte_px=9) for a in f["aliases"])
    st.markdown(
        f'<div style="'
        f"background-color: {CORES['card_fundo']};"
        f" border-radius: 14px;"
        f" padding: 22px 26px;"
        f" border-left: 4px solid {CORES['destaque']};"
        f' box-shadow: 0 4px 12px rgba(0,0,0,0.3);">'
        f'<div style="display: flex; justify-content: space-between;'
        f' align-items: flex-start; margin-bottom: 12px;">'
        f'<div><h3 style="color: {CORES["texto"]};'
        f" font-size: 22px; font-weight: 700;"
        f' margin: 0;">{f["nome"]}</h3>'
        f'<p style="color: {CORES["neutro"]};'
        f" font-size: 13px; font-family: monospace;"
        f' margin: 6px 0 0 0;">CNPJ {f["cnpj"]}</p></div>'
        f"<div>{badge_html(f['categoria'], CORES['destaque'])}</div>"
        f"</div>"
        f'<div style="display: grid; grid-template-columns: repeat(4, 1fr);'
        f' gap: 16px; margin: 18px 0;">'
        f'<div><p style="color: {CORES["texto_sec"]};'
        f" font-size: 10px; text-transform: uppercase;"
        f' letter-spacing: 0.08em; margin: 0;">Documentos</p>'
        f'<p style="color: {CORES["texto"]};'
        f" font-size: 22px; font-weight: 700;"
        f' margin: 4px 0 0 0;">{f["total_documentos"]}</p></div>'
        f'<div><p style="color: {CORES["texto_sec"]};'
        f" font-size: 10px; text-transform: uppercase;"
        f' letter-spacing: 0.08em; margin: 0;">Total gasto</p>'
        f'<p style="color: {CORES["negativo"]};'
        f" font-size: 22px; font-weight: 700;"
        f' margin: 4px 0 0 0;">{_formatar_brl(-f["total_gasto"])}</p></div>'
        f'<div><p style="color: {CORES["texto_sec"]};'
        f" font-size: 10px; text-transform: uppercase;"
        f' letter-spacing: 0.08em; margin: 0;">Primeiro registro</p>'
        f'<p style="color: {CORES["texto"]};'
        f" font-size: 14px; font-family: monospace;"
        f' margin: 6px 0 0 0;">{f["primeiro_registro"]}</p></div>'
        f'<div><p style="color: {CORES["texto_sec"]};'
        f" font-size: 10px; text-transform: uppercase;"
        f' letter-spacing: 0.08em; margin: 0;">Último registro</p>'
        f'<p style="color: {CORES["texto"]};'
        f" font-size: 14px; font-family: monospace;"
        f' margin: 6px 0 0 0;">{f["ultimo_registro"]}</p></div>'
        f"</div>"
        f'<p style="color: {CORES["texto_sec"]};'
        f' font-size: 11px; margin: 12px 0 6px 0;">Aliases reconhecidos</p>'
        f'<div style="display: flex; gap: 6px; flex-wrap: wrap;">{aliases_html}</div>'
        f"</div>",
        unsafe_allow_html=True,
    )


def _renderizar_timeline_plotly() -> None:
    st.markdown(
        subtitulo_secao("Timeline — faturas e transações", cor=CORES["neutro"]),
        unsafe_allow_html=True,
    )
    docs_df = pd.DataFrame(DOCUMENTOS_RESULTADOS)
    tx_df = pd.DataFrame(TRANSACOES_RESULTADOS)
    docs_df["data"] = pd.to_datetime(docs_df["data"])
    tx_df["data"] = pd.to_datetime(tx_df["data"])

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=docs_df["data"],
            y=[1] * len(docs_df),
            mode="markers",
            marker={
                "size": 18,
                "color": CORES["destaque"],
                "line": {"color": CORES["texto"], "width": 2},
                "symbol": "diamond",
            },
            name="Documentos",
            text=[
                f"{r['tipo']} {r['numero']}<br>{_formatar_brl(-r['total'])}"
                for _, r in docs_df.iterrows()
            ],
            hovertemplate="%{text}<br>%{x|%Y-%m-%d}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=tx_df["data"],
            y=[0] * len(tx_df),
            mode="markers",
            marker={
                "size": 14,
                "color": CORES["neutro"],
                "line": {"color": CORES["texto"], "width": 1},
                "symbol": "circle",
            },
            name="Transações",
            text=[
                f"{r['banco']} — {r['desc']}<br>{_formatar_brl(r['valor'])}"
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
            "gridcolor": rgba_cor(CORES["texto_sec"], 0.15),
            "showgrid": True,
        },
        yaxis={
            "title": "",
            "showticklabels": False,
            "range": [-0.5, 1.5],
            "showgrid": False,
        },
    )
    st.plotly_chart(fig, use_container_width=True)


def _renderizar_documentos() -> None:
    st.markdown(
        subtitulo_secao(f"Documentos ({len(DOCUMENTOS_RESULTADOS)})"),
        unsafe_allow_html=True,
    )
    for doc in DOCUMENTOS_RESULTADOS:
        st.markdown(
            f'<div style="'
            f"background-color: {CORES['card_fundo']};"
            f" border-radius: 10px;"
            f" padding: 12px 16px;"
            f" margin-bottom: 8px;"
            f" display: flex;"
            f" justify-content: space-between;"
            f' align-items: center;">'
            f'<div><p style="color: {CORES["texto"]};'
            f" font-size: 13px; font-weight: 600;"
            f' margin: 0;">{doc["tipo"]} {doc["numero"]}</p>'
            f'<p style="color: {CORES["texto_sec"]};'
            f" font-size: 11px; font-family: monospace;"
            f' margin: 3px 0 0 0;">{doc["data"]} · {doc["itens"]} item(s)</p>'
            f"</div>"
            f'<p style="color: {CORES["negativo"]};'
            f" font-size: 15px; font-weight: 700; font-family: monospace;"
            f' margin: 0;">{_formatar_brl(-doc["total"])}</p>'
            f"</div>",
            unsafe_allow_html=True,
        )


def _renderizar_transacoes() -> None:
    st.markdown(
        subtitulo_secao(f"Transações ({len(TRANSACOES_RESULTADOS)})"),
        unsafe_allow_html=True,
    )
    for tx in TRANSACOES_RESULTADOS:
        st.markdown(
            f'<div style="'
            f"background-color: {CORES['card_fundo']};"
            f" border-radius: 8px;"
            f" padding: 10px 14px;"
            f" margin-bottom: 6px;"
            f" display: flex;"
            f" justify-content: space-between;"
            f" align-items: center;"
            f' border-left: 2px solid {CORES["neutro"]};">'
            f'<div><p style="color: {CORES["texto"]};'
            f" font-size: 12px;"
            f' margin: 0;">{tx["desc"]}</p>'
            f'<p style="color: {CORES["texto_sec"]};'
            f" font-size: 10px; font-family: monospace;"
            f' margin: 2px 0 0 0;">{tx["data"]} · {tx["banco"]}</p></div>'
            f'<p style="color: {CORES["negativo"]};'
            f" font-size: 13px; font-weight: 600; font-family: monospace;"
            f' margin: 0;">{_formatar_brl(tx["valor"])}</p>'
            f"</div>",
            unsafe_allow_html=True,
        )


def _renderizar_itens() -> None:
    st.markdown(
        subtitulo_secao(f"Itens ({len(ITENS_RESULTADOS)})"),
        unsafe_allow_html=True,
    )
    for item in ITENS_RESULTADOS:
        st.markdown(
            f'<div style="'
            f"background-color: {CORES['card_fundo']};"
            f" border-radius: 8px;"
            f" padding: 12px 14px;"
            f" margin-bottom: 6px;"
            f' border-left: 2px solid {CORES["alerta"]};">'
            f'<p style="color: {CORES["texto"]};'
            f" font-size: 13px; font-weight: 600;"
            f' margin: 0;">{item["descricao"]}</p>'
            f'<div style="display: flex; justify-content: space-between;'
            f' margin-top: 6px;">'
            f'<p style="color: {CORES["texto_sec"]};'
            f" font-size: 11px;"
            f' margin: 0;">{item["ocorrencias"]} ocorrências</p>'
            f'<p style="color: {CORES["negativo"]};'
            f" font-size: 12px; font-weight: 600; font-family: monospace;"
            f' margin: 0;">{_formatar_brl(-item["gasto"])}</p>'
            f"</div></div>",
            unsafe_allow_html=True,
        )


def renderizar() -> None:
    """Ponto de entrada da pagina mockup 52."""
    st.markdown(
        hero_titulo(
            "52",
            "Busca Global",
            "Input único: digite fornecedor, CNPJ, item, data ou valor. "
            "Retorna fornecedor agregado, documentos, transações, itens "
            "e timeline cronológica em < 500ms.",
        ),
        unsafe_allow_html=True,
    )
    query = _renderizar_input_busca()
    _renderizar_resumo(query or "(vazio)")
    _renderizar_card_fornecedor()
    _renderizar_timeline_plotly()
    st.markdown(divisor(), unsafe_allow_html=True)

    col_doc, col_tx, col_it = st.columns([1, 1, 1])
    with col_doc:
        _renderizar_documentos()
    with col_tx:
        _renderizar_transacoes()
    with col_it:
        _renderizar_itens()


# "Procura, e achareis." -- Mateus 7:7
