"""Página mockup -- Sprint 51 Dashboard de Catalogação.

MOCKUP wireframe para Sprint 51 -- não é código de produção.
Dados fictícios determinísticos. Não consulta grafo SQLite real.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
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

TIPOS_DOCUMENTO: list[dict] = [
    {"tipo": "DANFE (NFe-55)", "contagem": 128, "mes": 42, "cor": CORES["destaque"]},
    {"tipo": "NFC-e (modelo 65)", "contagem": 87, "mes": 31, "cor": CORES["neutro"]},
    {"tipo": "Cupom térmico (foto)", "contagem": 64, "mes": 18, "cor": CORES["alerta"]},
    {"tipo": "Recibo / boleto", "contagem": 42, "mes": 12, "cor": CORES["info"]},
    {"tipo": "Receita médica", "contagem": 19, "mes": 3, "cor": CORES["superfluo"]},
    {"tipo": "Termo de garantia", "contagem": 11, "mes": 2, "cor": CORES["positivo"]},
    {"tipo": "Apólice de seguro", "contagem": 6, "mes": 0, "cor": CORES["obrigatorio"]},
]

DOCUMENTOS_RECENTES: list[dict] = [
    {
        "data": "2026-04-19",
        "tipo": "DANFE",
        "fornecedor": "Americanas S.A.",
        "total": 287.40,
        "status": "linked",
        "itens": 7,
    },
    {
        "data": "2026-04-18",
        "tipo": "NFC-e",
        "fornecedor": "Supermercado Super Maia",
        "total": 412.89,
        "status": "linked",
        "itens": 23,
    },
    {
        "data": "2026-04-17",
        "tipo": "Cupom térmico",
        "fornecedor": "Farmácia Pague Menos",
        "total": 68.50,
        "status": "unlinked",
        "itens": 3,
    },
    {
        "data": "2026-04-16",
        "tipo": "DANFE",
        "fornecedor": "Magazine Luiza",
        "total": 1289.00,
        "status": "conflito",
        "itens": 1,
    },
    {
        "data": "2026-04-15",
        "tipo": "Receita médica",
        "fornecedor": "Dra. Aline Ribeiro (CRM-DF 22314)",
        "total": 0.00,
        "status": "linked",
        "itens": 2,
    },
    {
        "data": "2026-04-14",
        "tipo": "NFC-e",
        "fornecedor": "Padaria Ki-Sabor",
        "total": 47.30,
        "status": "linked",
        "itens": 5,
    },
    {
        "data": "2026-04-13",
        "tipo": "Cupom térmico",
        "fornecedor": "Posto Shell SCLN 208",
        "total": 189.72,
        "status": "unlinked",
        "itens": 1,
    },
    {
        "data": "2026-04-12",
        "tipo": "DANFE",
        "fornecedor": "Neoenergia Distribuição",
        "total": 487.23,
        "status": "linked",
        "itens": 1,
    },
]

CONFLITOS: list[dict] = [
    {
        "doc": "DANFE Magazine Luiza 2026-04-16",
        "descricao": "Candidatos múltiplos: 2 débitos de R$ 1.289,00 em 2026-04-17",
        "arquivo": "docs/propostas/linking/2026-04-20_magalu_duplo.md",
        "prioridade": "alta",
    },
    {
        "doc": "Cupom térmico Farmácia Pague Menos 2026-04-17",
        "descricao": "OCR retornou R$ 68,50 mas banco mostra R$ 85,60 próximo",
        "arquivo": "docs/propostas/linking/2026-04-19_farmacia_ocr.md",
        "prioridade": "media",
    },
    {
        "doc": "Cupom térmico Posto Shell 2026-04-13",
        "descricao": "Sem transação correspondente em +/- 3 dias",
        "arquivo": "docs/propostas/linking/2026-04-18_shell_orfao.md",
        "prioridade": "baixa",
    },
]

GAPS: list[dict] = [
    {"mes": "2025-11", "docs": 2, "esperado": "10+"},
    {"mes": "2025-09", "docs": 4, "esperado": "10+"},
    {"mes": "2024-12", "docs": 3, "esperado": "10+"},
]

CORES_STATUS: dict[str, str] = {
    "linked": CORES["positivo"],
    "unlinked": CORES["alerta"],
    "conflito": CORES["negativo"],
}

ROTULO_STATUS: dict[str, str] = {
    "linked": "Vinculado",
    "unlinked": "Sem transação",
    "conflito": "Conflito",
}


def _renderizar_kpis() -> None:
    total_docs = sum(t["contagem"] for t in TIPOS_DOCUMENTO)
    docs_mes = sum(t["mes"] for t in TIPOS_DOCUMENTO)
    propostas = len(CONFLITOS)
    pct_linked = 0.82
    col1, col2, col3, col4 = st.columns(4)
    kpis = [
        (col1, "Documentos catalogados", str(total_docs), CORES["destaque"]),
        (col2, "Chegaram este mês", str(docs_mes), CORES["neutro"]),
        (col3, "Vinculados a transação", f"{pct_linked:.0%}", CORES["positivo"]),
        (col4, "Propostas abertas", str(propostas), CORES["alerta"]),
    ]
    for col, label, valor, cor in kpis:
        with col:
            st.markdown(
                f'<div style="'
                f"background-color: {CORES['card_fundo']};"
                f" border-radius: 12px;"
                f" padding: 20px;"
                f" border-left: 4px solid {cor};"
                f' box-shadow: 0 2px 8px rgba(0,0,0,0.25);">'
                f'<p style="color: {CORES["texto_sec"]};'
                f" font-size: 11px;"
                f" font-weight: 600;"
                f" letter-spacing: 0.08em;"
                f" text-transform: uppercase;"
                f' margin: 0;">{label}</p>'
                f'<p style="color: {cor};'
                f" font-size: 32px;"
                f" font-weight: 700;"
                f' margin: 8px 0 0 0;">{valor}</p>'
                f"</div>",
                unsafe_allow_html=True,
            )


def _renderizar_cards_tipos() -> None:
    st.markdown(subtitulo_secao("Documentos por tipo"), unsafe_allow_html=True)
    cols = st.columns(len(TIPOS_DOCUMENTO))
    for col, tipo in zip(cols, TIPOS_DOCUMENTO):
        with col:
            st.markdown(
                f'<div style="'
                f"background-color: {CORES['card_fundo']};"
                f" border-radius: 10px;"
                f" padding: 16px 12px;"
                f" border-top: 3px solid {tipo['cor']};"
                f" text-align: center;"
                f' min-height: 130px;">'
                f'<p style="color: {CORES["texto_sec"]};'
                f" font-size: 11px;"
                f" font-weight: 600;"
                f" line-height: 1.3;"
                f' margin: 0 0 10px 0;">{tipo["tipo"]}</p>'
                f'<p style="color: {tipo["cor"]};'
                f" font-size: 28px;"
                f" font-weight: 700;"
                f" line-height: 1;"
                f' margin: 0;">{tipo["contagem"]}</p>'
                f'<p style="color: {CORES["texto_sec"]};'
                f" font-size: 10px;"
                f' margin: 8px 0 0 0;">+ {tipo["mes"]} este mês</p>'
                f"</div>",
                unsafe_allow_html=True,
            )


def _renderizar_timeline_barras() -> None:
    st.markdown(
        subtitulo_secao("Volume mensal por tipo (últimos 12 meses)"),
        unsafe_allow_html=True,
    )
    meses = [
        "2025-05",
        "2025-06",
        "2025-07",
        "2025-08",
        "2025-09",
        "2025-10",
        "2025-11",
        "2025-12",
        "2026-01",
        "2026-02",
        "2026-03",
        "2026-04",
    ]
    dados = []
    for idx, mes in enumerate(meses):
        dados.append({"mes": mes, "tipo": "DANFE", "quantidade": 8 + idx + (idx % 3)})
        dados.append({"mes": mes, "tipo": "NFC-e", "quantidade": 5 + (idx % 5) * 2})
        dados.append({"mes": mes, "tipo": "Cupom térmico", "quantidade": 3 + (idx % 4)})
        dados.append({"mes": mes, "tipo": "Outros", "quantidade": 2 + (idx % 3)})
    df = pd.DataFrame(dados)
    fig = px.bar(
        df,
        x="mes",
        y="quantidade",
        color="tipo",
        color_discrete_map={
            "DANFE": CORES["destaque"],
            "NFC-e": CORES["neutro"],
            "Cupom térmico": CORES["alerta"],
            "Outros": CORES["texto_sec"],
        },
    )
    fig.update_layout(
        **LAYOUT_PLOTLY,
        height=320,
        showlegend=True,
        legend={"orientation": "h", "y": -0.25, "x": 0},
        xaxis={"title": "", "gridcolor": rgba_cor(CORES["texto_sec"], 0.15)},
        yaxis={"title": "documentos", "gridcolor": rgba_cor(CORES["texto_sec"], 0.15)},
    )
    st.plotly_chart(fig, use_container_width=True)


def _renderizar_tabela_documentos() -> None:
    st.markdown(subtitulo_secao("Documentos recentes"), unsafe_allow_html=True)
    linhas_html = []
    for doc in DOCUMENTOS_RECENTES:
        cor_status = CORES_STATUS[doc["status"]]
        rotulo = ROTULO_STATUS[doc["status"]]
        valor = (
            "R$ --"
            if doc["total"] == 0
            else f"R$ {doc['total']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )
        linhas_html.append(
            f"<tr>"
            f'<td style="padding: 10px 12px; color: {CORES["texto_sec"]};'
            f' font-family: monospace; font-size: 12px;">{doc["data"]}</td>'
            f'<td style="padding: 10px 12px; color: {CORES["texto"]};'
            f' font-size: 13px;">{doc["tipo"]}</td>'
            f'<td style="padding: 10px 12px; color: {CORES["texto"]};'
            f' font-size: 13px;">{doc["fornecedor"]}</td>'
            f'<td style="padding: 10px 12px; color: {CORES["texto"]};'
            f" font-size: 13px; text-align: right; font-family: monospace;"
            f' font-weight: 600;">{valor}</td>'
            f'<td style="padding: 10px 12px; text-align: center;'
            f' font-size: 12px;">{doc["itens"]}</td>'
            f'<td style="padding: 10px 12px;">'
            f"{badge_html(rotulo, cor_status)}</td>"
            f"</tr>"
        )
    tabela_html = (
        f'<div style="background-color: {CORES["card_fundo"]};'
        f" border-radius: 12px;"
        f" overflow: hidden;"
        f' box-shadow: 0 2px 8px rgba(0,0,0,0.25);">'
        f'<table style="width: 100%; border-collapse: collapse;">'
        f'<thead><tr style="background-color: {rgba_cor(CORES["destaque"], 0.15)};">'
        f'<th style="padding: 12px; text-align: left; color: {CORES["texto_sec"]};'
        f' font-size: 11px; letter-spacing: 0.08em; text-transform: uppercase;">Data</th>'
        f'<th style="padding: 12px; text-align: left; color: {CORES["texto_sec"]};'
        f' font-size: 11px; letter-spacing: 0.08em; text-transform: uppercase;">Tipo</th>'
        f'<th style="padding: 12px; text-align: left; color: {CORES["texto_sec"]};'
        f' font-size: 11px; letter-spacing: 0.08em; text-transform: uppercase;">Fornecedor</th>'
        f'<th style="padding: 12px; text-align: right; color: {CORES["texto_sec"]};'
        f' font-size: 11px; letter-spacing: 0.08em; text-transform: uppercase;">Total</th>'
        f'<th style="padding: 12px; text-align: center; color: {CORES["texto_sec"]};'
        f' font-size: 11px; letter-spacing: 0.08em; text-transform: uppercase;">Itens</th>'
        f'<th style="padding: 12px; text-align: left; color: {CORES["texto_sec"]};'
        f' font-size: 11px; letter-spacing: 0.08em; text-transform: uppercase;">Status</th>'
        f"</tr></thead>"
        f"<tbody>{''.join(linhas_html)}</tbody>"
        f"</table>"
        f"</div>"
    )
    st.markdown(tabela_html, unsafe_allow_html=True)


def _renderizar_painel_conflitos() -> None:
    st.markdown(subtitulo_secao("Conflitos pendentes", cor=CORES["alerta"]), unsafe_allow_html=True)
    cores_prioridade = {
        "alta": CORES["negativo"],
        "media": CORES["alerta"],
        "baixa": CORES["texto_sec"],
    }
    for conflito in CONFLITOS:
        cor = cores_prioridade[conflito["prioridade"]]
        st.markdown(
            f'<div style="'
            f"background-color: {CORES['card_fundo']};"
            f" border-radius: 10px;"
            f" padding: 14px 16px;"
            f" margin-bottom: 10px;"
            f' border-left: 3px solid {cor};">'
            f'<div style="display: flex; justify-content: space-between;'
            f' align-items: center; margin-bottom: 6px;">'
            f'<p style="color: {CORES["texto"]};'
            f" font-size: 13px; font-weight: 600;"
            f' margin: 0;">{conflito["doc"]}</p>'
            f"{badge_html(conflito['prioridade'], cor, fonte_px=9)}"
            f"</div>"
            f'<p style="color: {CORES["texto_sec"]};'
            f" font-size: 12px;"
            f' margin: 4px 0 8px 0;">{conflito["descricao"]}</p>'
            f'<p style="color: {CORES["neutro"]};'
            f" font-size: 10px;"
            f" font-family: monospace;"
            f' margin: 0;">{conflito["arquivo"]}</p>'
            f"</div>",
            unsafe_allow_html=True,
        )
    col_a, col_b = st.columns(2)
    with col_a:
        st.button("Revisar todas", use_container_width=True, disabled=True)
    with col_b:
        st.button("Abrir em /conferencia", use_container_width=True, disabled=True)


def _renderizar_gaps() -> None:
    st.markdown(subtitulo_secao("Gaps de cobertura", cor=CORES["negativo"]), unsafe_allow_html=True)
    for gap in GAPS:
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
            f" font-size: 14px; font-weight: 600;"
            f' margin: 0;">{gap["mes"]}</p>'
            f'<p style="color: {CORES["texto_sec"]};'
            f" font-size: 11px;"
            f' margin: 2px 0 0 0;">esperado: {gap["esperado"]}</p></div>'
            f'<div style="text-align: right;">'
            f'<p style="color: {CORES["negativo"]};'
            f" font-size: 24px; font-weight: 700;"
            f' margin: 0; line-height: 1;">{gap["docs"]}</p>'
            f'<p style="color: {CORES["texto_sec"]};'
            f" font-size: 10px;"
            f' margin: 2px 0 0 0;">docs</p></div>'
            f"</div>",
            unsafe_allow_html=True,
        )


def renderizar() -> None:
    """Ponto de entrada da pagina mockup 51."""
    st.markdown(
        hero_titulo(
            "51",
            "Catalogação de Documentos",
            "Visão consolidada do catálogo: tipos de documento, volume mensal, "
            "conflitos de linking aguardando revisão e meses com baixa cobertura.",
        ),
        unsafe_allow_html=True,
    )
    _renderizar_kpis()
    st.markdown(divisor(), unsafe_allow_html=True)
    _renderizar_cards_tipos()
    st.markdown(divisor(), unsafe_allow_html=True)

    col_principal, col_lateral = st.columns([2, 1])
    with col_principal:
        _renderizar_timeline_barras()
        _renderizar_tabela_documentos()
    with col_lateral:
        _renderizar_painel_conflitos()
        _renderizar_gaps()


# "Catalogar é o primeiro ato da inteligência." -- Carl Linnaeus (parafraseado)
