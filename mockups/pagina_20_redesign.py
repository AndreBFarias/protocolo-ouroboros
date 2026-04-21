"""Página mockup -- Sprint 20 Redesign Tipográfico.

MOCKUP wireframe para Sprint 20 -- não é código de produção.
Comparação lado a lado "como está hoje" vs "como deveria ficar" +
tokens de design (paleta, escala tipográfica, spacing scale).
"""

from __future__ import annotations

import streamlit as st

from mockups.tema_mockup import (
    CORES,
    DRACULA,
    divisor,
    hero_titulo,
    rgba_cor,
    subtitulo_secao,
)

ESCALA_TIPOGRAFICA: list[dict] = [
    {"nome": "Display / hero", "tamanho": "34px", "peso": "700", "uso": "título de página"},
    {"nome": "H1 — título", "tamanho": "28px", "peso": "700", "uso": "cabeçalho principal"},
    {"nome": "H2 — seção", "tamanho": "22px", "peso": "600", "uso": "abertura de bloco"},
    {"nome": "H3 — subseção", "tamanho": "13px up", "peso": "700", "uso": "rótulos de grupo"},
    {"nome": "Body", "tamanho": "15px", "peso": "400", "uso": "texto corrido"},
    {"nome": "Caption", "tamanho": "12px", "peso": "500", "uso": "metadados e legendas"},
    {"nome": "Mono", "tamanho": "12px monospace", "peso": "500", "uso": "valores, datas, CNPJ"},
]

SPACING_SCALE: list[dict] = [
    {"token": "xs", "valor": "4px", "uso": "gap entre badges"},
    {"token": "sm", "valor": "8px", "uso": "padding interno compacto"},
    {"token": "md", "valor": "16px", "uso": "gap padrão entre blocos"},
    {"token": "lg", "valor": "24px", "uso": "margem entre seções"},
    {"token": "xl", "valor": "32px", "uso": "separação de grandes áreas"},
    {"token": "2xl", "valor": "48px", "uso": "respiração do hero"},
]

PALETA: list[dict] = [
    {"nome": "background", "hex": DRACULA["background"], "papel": "fundo da página"},
    {"nome": "current_line", "hex": DRACULA["current_line"], "papel": "card / surface"},
    {"nome": "foreground", "hex": DRACULA["foreground"], "papel": "texto primário"},
    {"nome": "comment → #8892B0", "hex": "#8892B0", "papel": "texto secundário (WCAG AA)"},
    {"nome": "purple", "hex": DRACULA["purple"], "papel": "destaque / ação"},
    {"nome": "cyan", "hex": DRACULA["cyan"], "papel": "info / neutro"},
    {"nome": "green", "hex": DRACULA["green"], "papel": "positivo / obrigatório"},
    {"nome": "red", "hex": DRACULA["red"], "papel": "negativo / crítico"},
    {"nome": "orange", "hex": DRACULA["orange"], "papel": "alerta / questionável"},
    {"nome": "pink", "hex": DRACULA["pink"], "papel": "supérfluo"},
]


def _card_antes(titulo: str, descricao: str, conteudo_html: str) -> str:
    return (
        f'<div style="'
        f"background-color: {CORES['card_fundo']};"
        f" border-radius: 10px;"
        f" padding: 18px 20px;"
        f" border-left: 3px solid {CORES['negativo']};"
        f' min-height: 320px;">'
        f'<div style="display: flex; align-items: center; gap: 10px;'
        f' margin-bottom: 4px;">'
        f'<span style="background-color: {rgba_cor(CORES["negativo"], 0.2)};'
        f" color: {CORES['negativo']};"
        f" padding: 2px 10px;"
        f" border-radius: 6px;"
        f" font-size: 10px;"
        f" font-weight: 700;"
        f" letter-spacing: 0.08em;"
        f' text-transform: uppercase;">ANTES</span>'
        f'<span style="color: {CORES["texto"]};'
        f" font-size: 15px;"
        f' font-weight: 600;">{titulo}</span>'
        f"</div>"
        f'<p style="color: {CORES["texto_sec"]};'
        f" font-size: 12px;"
        f' margin: 0 0 14px 0;">{descricao}</p>'
        f"{conteudo_html}"
        f"</div>"
    )


def _card_depois(titulo: str, descricao: str, conteudo_html: str) -> str:
    return (
        f'<div style="'
        f"background-color: {CORES['card_fundo']};"
        f" border-radius: 10px;"
        f" padding: 18px 20px;"
        f" border-left: 3px solid {CORES['positivo']};"
        f' min-height: 320px;">'
        f'<div style="display: flex; align-items: center; gap: 10px;'
        f' margin-bottom: 4px;">'
        f'<span style="background-color: {rgba_cor(CORES["positivo"], 0.2)};'
        f" color: {CORES['positivo']};"
        f" padding: 2px 10px;"
        f" border-radius: 6px;"
        f" font-size: 10px;"
        f" font-weight: 700;"
        f" letter-spacing: 0.08em;"
        f' text-transform: uppercase;">DEPOIS</span>'
        f'<span style="color: {CORES["texto"]};'
        f" font-size: 15px;"
        f' font-weight: 600;">{titulo}</span>'
        f"</div>"
        f'<p style="color: {CORES["texto_sec"]};'
        f" font-size: 12px;"
        f' margin: 0 0 14px 0;">{descricao}</p>'
        f"{conteudo_html}"
        f"</div>"
    )


def _renderizar_comparativo_tipografia() -> None:
    antes_html = (
        f'<p style="color: {CORES["texto"]}; font-size: 18px; margin: 0 0 8px 0;">'
        "Visão Geral</p>"
        f'<p style="color: {CORES["texto"]}; font-size: 16px; margin: 0 0 8px 0;">'
        "Resumo Mensal</p>"
        f'<p style="color: {CORES["texto"]}; font-size: 14px; margin: 0 0 8px 0;">'
        "Receita: R$ 18.432,77</p>"
        f'<p style="color: {CORES["texto"]}; font-size: 13px; margin: 0 0 8px 0;">'
        "Despesa: R$ 12.987,43</p>"
        f'<p style="color: #6272A4; font-size: 13px; margin: 0 0 6px 0;">'
        "comment #6272A4 — contraste 3.9:1 (abaixo do WCAG AA)</p>"
        f'<p style="color: {CORES["texto_sec"]}; font-size: 11px;'
        f" font-family: monospace; margin-top: 14px;"
        f" background-color: {CORES['fundo']};"
        f' padding: 8px; border-radius: 4px;">'
        "tamanhos: 18 · 16 · 14 · 13 · 13<br>"
        "escala compactada, hierarquia visual quase nula</p>"
    )
    depois_html = (
        f'<p style="color: {CORES["texto"]}; font-size: 28px;'
        f" font-weight: 700; margin: 0 0 4px 0;"
        f' letter-spacing: -0.01em;">Visão Geral</p>'
        f'<p style="color: {CORES["neutro"]}; font-size: 13px;'
        f" font-weight: 700; letter-spacing: 0.12em;"
        f" text-transform: uppercase; margin: 14px 0 8px 0;"
        f" padding-bottom: 4px;"
        f' border-bottom: 1px solid {rgba_cor(CORES["texto_sec"], 0.3)};">'
        "Resumo Mensal</p>"
        f'<p style="color: {CORES["texto"]}; font-size: 22px;'
        f" font-weight: 700; font-family: monospace;"
        f' margin: 0 0 4px 0;">R$ 18.432,77</p>'
        f'<p style="color: {CORES["texto_sec"]}; font-size: 12px;'
        f' margin: 0 0 12px 0;">receita total</p>'
        f'<p style="color: #8892B0; font-size: 13px; margin: 0 0 6px 0;">'
        "#8892B0 — contraste 5.2:1 (WCAG AA OK)</p>"
        f'<p style="color: {CORES["texto_sec"]}; font-size: 11px;'
        f" font-family: monospace; margin-top: 14px;"
        f" background-color: {CORES['fundo']};"
        f' padding: 8px; border-radius: 4px;">'
        "hero 28 · h3 13up · body 15 · caption 12<br>"
        "escala clara com saltos reconhecíveis</p>"
    )
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(
            _card_antes(
                "Tipografia",
                "tamanhos próximos (13-18) sem saltos, contraste abaixo do WCAG",
                antes_html,
            ),
            unsafe_allow_html=True,
        )
    with col_b:
        st.markdown(
            _card_depois(
                "Tipografia",
                "escala com saltos claros, hierarquia imediata, contraste WCAG AA",
                depois_html,
            ),
            unsafe_allow_html=True,
        )


def _renderizar_comparativo_cards() -> None:
    antes_html = (
        f'<div style="display: flex; gap: 4px;">'
        f'<div style="background-color: {CORES["fundo"]};'
        f" padding: 8px; flex: 1; border: 1px solid {rgba_cor(CORES['texto_sec'], 0.2)};"
        f' border-radius: 4px;">'
        f'<p style="color: {CORES["texto_sec"]}; font-size: 11px;'
        f' margin: 0;">Receita</p>'
        f'<p style="color: {CORES["positivo"]}; font-size: 14px;'
        f' margin: 2px 0 0 0;">R$ 18.432</p></div>'
        f'<div style="background-color: {CORES["fundo"]};'
        f" padding: 10px; flex: 1;"
        f" border: 1px solid {rgba_cor(CORES['texto_sec'], 0.2)};"
        f' border-radius: 4px;">'
        f'<p style="color: {CORES["texto_sec"]}; font-size: 13px;'
        f' margin: 0;">Despesa</p>'
        f'<p style="color: {CORES["negativo"]}; font-size: 15px;'
        f' margin: 2px 0 0 0;">R$ 12.987</p></div>'
        f'<div style="background-color: {CORES["fundo"]};'
        f" padding: 6px; flex: 1;"
        f" border: 1px solid {rgba_cor(CORES['texto_sec'], 0.2)};"
        f' border-radius: 4px;">'
        f'<p style="color: {CORES["texto_sec"]}; font-size: 10px;'
        f' margin: 0;">Saldo</p>'
        f'<p style="color: {CORES["texto"]}; font-size: 13px;'
        f' margin: 2px 0 0 0;">R$ 5.445</p></div>'
        f"</div>"
        f'<p style="color: {CORES["texto_sec"]}; font-size: 11px;'
        f" font-family: monospace; margin-top: 14px;"
        f" background-color: {CORES['fundo']};"
        f' padding: 8px; border-radius: 4px;">'
        "paddings 6 · 8 · 10 inconsistentes<br>"
        "sem border-left semântico<br>"
        "tipografia diferente em cada card</p>"
    )
    depois_html = (
        f'<div style="display: flex; gap: 16px;">'
        f'<div style="background-color: {CORES["fundo"]};'
        f" padding: 20px;"
        f" flex: 1;"
        f" border-radius: 12px;"
        f" border-left: 4px solid {CORES['positivo']};"
        f' box-shadow: 0 2px 8px rgba(0,0,0,0.25);">'
        f'<p style="color: {CORES["texto_sec"]}; font-size: 11px;'
        f" font-weight: 600; letter-spacing: 0.08em;"
        f' text-transform: uppercase; margin: 0;">Receita</p>'
        f'<p style="color: {CORES["positivo"]}; font-size: 24px;'
        f" font-weight: 700; font-family: monospace;"
        f' margin: 8px 0 0 0;">R$ 18.432</p></div>'
        f'<div style="background-color: {CORES["fundo"]};'
        f" padding: 20px;"
        f" flex: 1;"
        f" border-radius: 12px;"
        f" border-left: 4px solid {CORES['negativo']};"
        f' box-shadow: 0 2px 8px rgba(0,0,0,0.25);">'
        f'<p style="color: {CORES["texto_sec"]}; font-size: 11px;'
        f" font-weight: 600; letter-spacing: 0.08em;"
        f' text-transform: uppercase; margin: 0;">Despesa</p>'
        f'<p style="color: {CORES["negativo"]}; font-size: 24px;'
        f" font-weight: 700; font-family: monospace;"
        f' margin: 8px 0 0 0;">R$ 12.987</p></div>'
        f'<div style="background-color: {CORES["fundo"]};'
        f" padding: 20px;"
        f" flex: 1;"
        f" border-radius: 12px;"
        f" border-left: 4px solid {CORES['destaque']};"
        f' box-shadow: 0 2px 8px rgba(0,0,0,0.25);">'
        f'<p style="color: {CORES["texto_sec"]}; font-size: 11px;'
        f" font-weight: 600; letter-spacing: 0.08em;"
        f' text-transform: uppercase; margin: 0;">Saldo</p>'
        f'<p style="color: {CORES["destaque"]}; font-size: 24px;'
        f" font-weight: 700; font-family: monospace;"
        f' margin: 8px 0 0 0;">R$ 5.445</p></div>'
        f"</div>"
        f'<p style="color: {CORES["texto_sec"]}; font-size: 11px;'
        f" font-family: monospace; margin-top: 14px;"
        f" background-color: {CORES['fundo']};"
        f' padding: 8px; border-radius: 4px;">'
        "padding 20 (token lg) consistente<br>"
        "border-left 4px com cor semântica<br>"
        "gap 16 (token md), shadow uniforme</p>"
    )
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(
            _card_antes(
                "Cards KPI",
                "paddings desalinhados, sem cor semântica, tipografia aleatória",
                antes_html,
            ),
            unsafe_allow_html=True,
        )
    with col_b:
        st.markdown(
            _card_depois(
                "Cards KPI",
                "grid consistente, border-left semântico, tipografia uniforme",
                depois_html,
            ),
            unsafe_allow_html=True,
        )


def _renderizar_tokens_paleta() -> None:
    st.markdown(subtitulo_secao("Paleta — tokens de cor"), unsafe_allow_html=True)
    cols = st.columns(5)
    for idx, item in enumerate(PALETA):
        col = cols[idx % 5]
        with col:
            st.markdown(
                f'<div style="'
                f"background-color: {CORES['card_fundo']};"
                f" border-radius: 10px;"
                f" padding: 14px;"
                f' margin-bottom: 12px;">'
                f'<div style="background-color: {item["hex"]};'
                f" height: 48px;"
                f" border-radius: 6px;"
                f" margin-bottom: 10px;"
                f' border: 1px solid {rgba_cor(CORES["texto_sec"], 0.2)};"></div>'
                f'<p style="color: {CORES["texto"]};'
                f" font-size: 12px; font-weight: 600;"
                f' margin: 0;">{item["nome"]}</p>'
                f'<p style="color: {CORES["texto_sec"]};'
                f" font-size: 10px; font-family: monospace;"
                f' margin: 2px 0;">{item["hex"]}</p>'
                f'<p style="color: {CORES["texto_sec"]};'
                f" font-size: 10px;"
                f' margin: 0;">{item["papel"]}</p>'
                f"</div>",
                unsafe_allow_html=True,
            )


def _renderizar_tokens_tipografia() -> None:
    st.markdown(
        subtitulo_secao("Escala tipográfica — 7 níveis"),
        unsafe_allow_html=True,
    )
    for nivel in ESCALA_TIPOGRAFICA:
        st.markdown(
            f'<div style="'
            f"background-color: {CORES['card_fundo']};"
            f" border-radius: 8px;"
            f" padding: 12px 18px;"
            f" margin-bottom: 6px;"
            f" display: grid;"
            f" grid-template-columns: 170px 140px 1fr;"
            f" gap: 16px;"
            f' align-items: center;">'
            f'<p style="color: {CORES["texto"]};'
            f" font-size: 13px; font-weight: 600;"
            f' margin: 0;">{nivel["nome"]}</p>'
            f'<p style="color: {CORES["neutro"]};'
            f" font-size: 11px; font-family: monospace;"
            f' margin: 0;">{nivel["tamanho"]} / {nivel["peso"]}</p>'
            f'<p style="color: {CORES["texto_sec"]};'
            f' font-size: 12px; margin: 0;">{nivel["uso"]}</p>'
            f"</div>",
            unsafe_allow_html=True,
        )


def _renderizar_tokens_spacing() -> None:
    st.markdown(
        subtitulo_secao("Spacing scale — 6 tokens"),
        unsafe_allow_html=True,
    )
    cols = st.columns(len(SPACING_SCALE))
    for col, token in zip(cols, SPACING_SCALE):
        px_valor = int(token["valor"].replace("px", ""))
        with col:
            st.markdown(
                f'<div style="'
                f"background-color: {CORES['card_fundo']};"
                f" border-radius: 10px;"
                f" padding: 14px;"
                f' text-align: center;">'
                f'<div style="background-color: {CORES["destaque"]};'
                f" height: 8px;"
                f" width: {min(px_valor * 2, 96)}px;"
                f" margin: 0 auto 10px auto;"
                f' border-radius: 4px;"></div>'
                f'<p style="color: {CORES["texto"]};'
                f" font-size: 14px; font-weight: 700;"
                f' margin: 0;">{token["token"]}</p>'
                f'<p style="color: {CORES["neutro"]};'
                f" font-size: 11px; font-family: monospace;"
                f' margin: 2px 0;">{token["valor"]}</p>'
                f'<p style="color: {CORES["texto_sec"]};'
                f' font-size: 10px; margin: 0;">{token["uso"]}</p>'
                f"</div>",
                unsafe_allow_html=True,
            )


def renderizar() -> None:
    """Ponto de entrada da pagina mockup 20."""
    st.markdown(
        hero_titulo(
            "20",
            "Redesign Tipográfico",
            "Comparação lado a lado do estado atual vs proposta "
            "(tipografia hierárquica, cards consistentes, contraste WCAG AA) "
            "e exposição dos tokens de design que regem o sistema.",
        ),
        unsafe_allow_html=True,
    )
    st.markdown(
        subtitulo_secao("Antes × Depois"),
        unsafe_allow_html=True,
    )
    _renderizar_comparativo_tipografia()
    st.markdown("<div style='margin: 16px 0;'></div>", unsafe_allow_html=True)
    _renderizar_comparativo_cards()
    st.markdown(divisor(), unsafe_allow_html=True)
    _renderizar_tokens_paleta()
    st.markdown(divisor(), unsafe_allow_html=True)
    _renderizar_tokens_tipografia()
    st.markdown(divisor(), unsafe_allow_html=True)
    _renderizar_tokens_spacing()


# "A simplicidade é a sofisticação suprema." -- Leonardo da Vinci
