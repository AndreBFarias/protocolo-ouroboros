"""Cluster Bem-estar · aba "Diário emocional" (UX-RD-18).

Lista cronológica DESC dos registros de diário emocional. Cada registro
vira um cartão com border-left semântica (vermelha para ``trigger``,
verde para ``vitoria``), chips das emoções tagueadas, slider visual da
intensidade (1..5) e a frase capturada. Filtros laterais permitem
restringir por modo (trigger/vitória/todos), período (7/30/90/365 dias)
e pessoa.

Layout espelha ``novo-mockup/mockups/19-diario-emocional.html``:

* ``page-header`` com sprint-tag UX-RD-18 + pill com a contagem de
  registros visíveis após filtros.
* ``.diario-layout`` -- duas colunas (sidebar esquerda + lista).
* ``.diario-card`` -- border-left 4px (red para trigger, green para
  vitória), data, modo pill, chips emoção, slider visual, frase, "com".
* Botão "Registrar diário" abre ``st.dialog`` (com fallback para
  ``st.expander`` em versões antigas) com formulário compacto que
  invoca :func:`escrever_diario`.

Lições UX-RD herdadas:

* HTML via :func:`minificar` (UX-RD-04).
* Cores via ``CORES`` -- nunca hex literal.
* Fallback graceful para vault ausente (UX-RD-15).
* Contrato uniforme ``renderizar(dados, periodo, pessoa, ctx)``.
* Identificador pessoa SEMPRE canônico (ADR-23).
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from src.dashboard.componentes.html_utils import minificar
from src.dashboard.componentes.page_header import renderizar_page_header
from src.dashboard.componentes.ui import callout_html, carregar_css_pagina
from src.dashboard.tema import CORES
from src.mobile_cache.diario_emocional import gerar_cache as gerar_cache_diario
from src.mobile_cache.escrever_diario import escrever_diario
from src.mobile_cache.varrer_vault import descobrir_vault_root

# Mapa período em dias.
_PERIODOS: dict[str, int] = {
    "7 dias": 7,
    "30 dias": 30,
    "90 dias": 90,
    "1 ano": 365,
}

# Pessoas selecionáveis -- inclui ``todos`` para colapsar A/B/casal.
_PESSOAS = ("todos", "pessoa_a", "pessoa_b", "casal")
_PESSOAS_LABEL = {
    "todos": "Todos",
    "pessoa_a": "Pessoa A",
    "pessoa_b": "Pessoa B",
    "casal": "Casal",
}

_KEY_FLASH = "be_diario_flash"


def renderizar(
    dados: dict[str, pd.DataFrame],
    periodo: str,
    pessoa: str,
    ctx: dict | None = None,
) -> None:
    """Renderiza Bem-estar / Diário emocional (UX-T-19)."""
    from src.dashboard.componentes.topbar_actions import renderizar_grupo_acoes
    renderizar_grupo_acoes([
        {"label": "Heatmap", "href": "?cluster=Bem-estar&tab=Humor",
         "title": "Ver humor 91 dias"},
        {"label": "Hoje", "primary": True,
         "href": "?cluster=Bem-estar&tab=Hoje",
         "title": "Registrar humor de hoje"},
    ])

    del dados, periodo, ctx

    st.markdown(minificar(carregar_css_pagina("be_diario")), unsafe_allow_html=True)

    vault_root = descobrir_vault_root()
    items = _carregar_items(vault_root)

    flash = st.session_state.pop(_KEY_FLASH, None)
    if flash:
        st.success(flash)

    # Filtros laterais. Usamos st.columns ao invés de st.sidebar
    # para manter os filtros no contexto do conteúdo (sidebar global
    # já é dos filtros transversais).
    col_filtros, col_lista = st.columns([1, 3], gap="large")

    with col_filtros:
        modo_label = st.radio(
            "Modo",
            options=["todos", "trigger", "vitoria"],
            format_func=lambda v: {
                "todos": "Todos",
                "trigger": "Trigger",
                "vitoria": "Vitória",
            }[v],
            key="be_diario_modo",
        )
        periodo_label = st.selectbox(
            "Período",
            options=list(_PERIODOS.keys()),
            index=1,
            key="be_diario_periodo",
        )
        pessoa_default = pessoa if pessoa in _PESSOAS else "todos"
        pessoa_label = st.selectbox(
            "Pessoa",
            options=list(_PESSOAS),
            index=list(_PESSOAS).index(pessoa_default),
            format_func=lambda v: _PESSOAS_LABEL[v],
            key="be_diario_pessoa",
        )

        st.markdown("---")
        if st.button("Registrar diário", use_container_width=True, key="be_diario_btn_abrir"):
            st.session_state["be_diario_form_aberto"] = True

    items_filtrados = _filtrar(
        items,
        modo=modo_label,
        periodo_dias=_PERIODOS[periodo_label],
        pessoa=pessoa_label,
        hoje=date.today(),
    )

    with col_lista:
        st.markdown(
            _page_header_canonico(len(items_filtrados)),
            unsafe_allow_html=True,
        )

        if vault_root is None:
            msg = (
                "Vault Bem-estar não encontrado. Configure OUROBOROS_VAULT "
                "para visualizar registros do diário emocional."
            )
            st.markdown(callout_html("warning", msg), unsafe_allow_html=True)
            return

        if not items:
            from src.dashboard.componentes.ui import (
                fallback_estado_inicial_html,
                ler_sync_info,
            )
            skeleton = (
                '<div style="display:flex;flex-direction:column;gap:10px;">'
                '<div style="display:flex;align-items:center;gap:10px;">'
                '<span class="skel-bloco" style="width:40px;height:40px;'
                'border-radius:50%;"></span>'
                '<div style="flex:1;display:flex;flex-direction:column;gap:6px;">'
                '<span class="skel-bloco" style="width:60%;"></span>'
                '<span class="skel-bloco" style="width:90%;height:0.9em;"></span>'
                '</div></div>'
                '<div style="display:flex;align-items:center;gap:10px;">'
                '<span class="skel-bloco" style="width:40px;height:40px;'
                'border-radius:50%;"></span>'
                '<div style="flex:1;display:flex;flex-direction:column;gap:6px;">'
                '<span class="skel-bloco" style="width:50%;"></span>'
                '<span class="skel-bloco" style="width:80%;height:0.9em;"></span>'
                '</div></div>'
                '</div>'
            )
            st.markdown(
                fallback_estado_inicial_html(
                    titulo="DIÁRIO EMOCIONAL · sem registros ainda",
                    descricao=(
                        "Entradas longas de diário (ânimo, contexto, gatilhos) "
                        "são escritas no app mobile e viram cards emocionais "
                        "aqui. Cada arquivo <code>.md</code> em "
                        "<code>vault/diario/&lt;data&gt;.md</code> aparece como "
                        "card individual após o sync."
                    ),
                    skeleton_html=skeleton,
                    cta_secao="diario",
                    sync_info=ler_sync_info(),
                ),
                unsafe_allow_html=True,
            )
        elif not items_filtrados:
            st.markdown(
                callout_html("info", "Nenhum registro casa com os filtros atuais."),
                unsafe_allow_html=True,
            )
        else:
            for item in items_filtrados:
                st.markdown(_card_html(item), unsafe_allow_html=True)

    if st.session_state.get("be_diario_form_aberto"):
        _renderizar_form(vault_root, pessoa_label)


# ---------------------------------------------------------------------------
# Cache loader + filtros
# ---------------------------------------------------------------------------


def _carregar_items(vault_root: Path | None) -> list[dict[str, Any]]:
    """Lê ``<vault>/.ouroboros/cache/diario-emocional.json``.

    Se o cache não existir mas o vault existir, gera on-the-fly antes
    de desistir. Retorna lista de items ordenada DESC por data.
    """
    if vault_root is None:
        return []
    arquivo = vault_root / ".ouroboros" / "cache" / "diario-emocional.json"
    if not arquivo.exists():
        try:
            gerar_cache_diario(vault_root)
        except OSError:
            return []
    if not arquivo.exists():
        return []
    try:
        payload = json.loads(arquivo.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    items = payload.get("items", []) or []
    # Ordenação DESC por data (parser sorta ASC; queremos cronológico inverso).
    items.sort(key=lambda i: (str(i.get("data", "")), str(i.get("autor", ""))), reverse=True)
    return items


def _filtrar(
    items: list[dict[str, Any]],
    *,
    modo: str,
    periodo_dias: int,
    pessoa: str,
    hoje: date,
) -> list[dict[str, Any]]:
    limite = hoje - timedelta(days=periodo_dias)
    out: list[dict[str, Any]] = []
    for it in items:
        if modo != "todos" and str(it.get("modo")) != modo:
            continue
        if pessoa != "todos" and str(it.get("autor")) != pessoa:
            continue
        data_iso = str(it.get("data", ""))
        try:
            d_obj = date.fromisoformat(data_iso[:10])
        except ValueError:
            continue
        if not (limite <= d_obj <= hoje):
            continue
        out.append(it)
    return out


# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------


def _page_header_canonico(qtd: int) -> str:
    """Page-header canônico via UX-M-02 (substitui markup local)."""
    return renderizar_page_header(
        titulo="BEM-ESTAR · DIÁRIO",
        subtitulo=(
            "Lista cronológica de registros do tipo trigger ou vitória. "
            "Cache lido de .ouroboros/cache/diario-emocional.json."
        ),
        sprint_tag="UX-RD-18",
        pills=[{"texto": f"{qtd} registros", "tipo": "d7-graduado"}],
    )


def _card_html(item: dict[str, Any]) -> str:
    """Cartão único do diário com border-left vermelha (trigger) ou verde (vitória)."""
    modo = str(item.get("modo", ""))
    cor_borda = (
        CORES.get("negativo", "#c0392b") if modo == "trigger"
        else CORES.get("positivo", "#27ae60")
    )
    classe_modo = (
        f"diario-card-{modo}" if modo in {"trigger", "vitoria"}
        else "diario-card-default"
    )
    rotulo_modo = {"trigger": "Trigger", "vitoria": "Vitória"}.get(modo, modo or "—")

    autor = str(item.get("autor", "—"))
    data_iso = str(item.get("data", ""))
    intensidade = item.get("intensidade") or 0
    try:
        intensidade_int = int(intensidade)
    except (TypeError, ValueError):
        intensidade_int = 0
    intensidade_int = max(0, min(5, intensidade_int))

    emocoes = item.get("emocoes") or []
    chips_emo = "".join(
        f'<span class="chip-emo">{_escape(str(e))}</span>'
        for e in emocoes
    ) or '<span class="chip-emo chip-vazio">sem emoções tagueadas</span>'

    com = item.get("com") or []
    com_html = (
        "<span class=\"diario-com\">com "
        + ", ".join(_escape(str(c)) for c in com)
        + "</span>"
        if com else ""
    )

    barra_int = "".join(
        f'<span class="dot {"on" if i < intensidade_int else "off"}"></span>'
        for i in range(5)
    )

    texto = _escape(str(item.get("texto") or "")) or "<em>(sem frase)</em>"

    return minificar(
        f"""
        <div class="diario-card {classe_modo}" style="border-left:4px solid {cor_borda};">
          <div class="diario-card-head">
            <span class="diario-data">{_escape(data_iso[:10])}</span>
            <span class="diario-modo-pill" style="color:{cor_borda};
              border:1px solid {cor_borda};">{rotulo_modo}</span>
            <span class="diario-autor">{_escape(autor)}</span>
          </div>
          <div class="diario-emocoes">{chips_emo}</div>
          <div class="diario-intens">
            <span class="diario-intens-label">intensidade</span>
            {barra_int}
            <span class="diario-intens-num">{intensidade_int}/5</span>
          </div>
          <div class="diario-frase">{texto}</div>
          {com_html}
        </div>
        """
    )


def _escape(texto: str) -> str:
    return (
        texto.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


# CSS dedicado: src/dashboard/css/paginas/be_diario.css (UX-M-02.D residual).
# ---------------------------------------------------------------------------
# Form modal
# ---------------------------------------------------------------------------


def _renderizar_form(vault_root: Path | None, pessoa_default: str) -> None:
    """Form de captura. Usa st.dialog quando disponível, senão st.expander."""
    titulo = "Registrar diário emocional"

    # API st.dialog é da 1.31+; como guard, caímos em expander se ausente.
    dialog = getattr(st, "dialog", None)
    if dialog is not None:
        @dialog(titulo)
        def _modal():
            _form_corpo(vault_root, pessoa_default)
        _modal()
    else:
        with st.expander(titulo, expanded=True):
            _form_corpo(vault_root, pessoa_default)


def _form_corpo(vault_root: Path | None, pessoa_default: str) -> None:
    if vault_root is None:
        st.warning(
            "Vault não encontrado. Configure `OUROBOROS_VAULT` antes de registrar."
        )
        if st.button("Fechar", key="be_diario_form_fechar"):
            st.session_state.pop("be_diario_form_aberto", None)
            st.rerun()
        return

    with st.form("be_diario_form"):
        modo = st.radio(
            "Modo",
            options=["trigger", "vitoria"],
            format_func=lambda v: "Trigger" if v == "trigger" else "Vitória",
            key="be_diario_form_modo",
        )
        emocoes_txt = st.text_input(
            "Emoções (separadas por vírgula)",
            key="be_diario_form_emocoes",
            placeholder="ansiedade, cansaço",
        )
        intensidade = st.slider(
            "Intensidade",
            min_value=1,
            max_value=5,
            value=3,
            key="be_diario_form_intensidade",
        )
        com_txt = st.text_input(
            "Com quem (separado por vírgula)",
            key="be_diario_form_com",
            placeholder="pessoa_b",
        )
        pessoas_form = ("pessoa_a", "pessoa_b", "casal")
        autor_default = pessoa_default if pessoa_default in pessoas_form else "pessoa_a"
        autor = st.selectbox(
            "Autor",
            options=pessoas_form,
            index=pessoas_form.index(autor_default),
            format_func=lambda v: _PESSOAS_LABEL.get(v, v),
            key="be_diario_form_autor",
        )
        frase = st.text_area(
            "Frase",
            key="be_diario_form_frase",
            placeholder="reuniao chata logo cedo.",
        )
        col_a, col_b = st.columns(2)
        salvar = col_a.form_submit_button("Salvar")
        cancelar = col_b.form_submit_button("Cancelar")

    if cancelar:
        st.session_state.pop("be_diario_form_aberto", None)
        st.rerun()

    if salvar:
        emocoes = [e.strip() for e in (emocoes_txt or "").split(",") if e.strip()]
        com_quem = [c.strip() for c in (com_txt or "").split(",") if c.strip()]
        try:
            arquivo = escrever_diario(
                vault_root,
                date.today(),
                modo=modo,
                emocoes=emocoes,
                intensidade=intensidade,
                com_quem=com_quem,
                frase=frase or "",
                pessoa=autor,
            )
            st.session_state[_KEY_FLASH] = (
                f"Registro gravado em {arquivo.name}."
            )
        except (OSError, ValueError) as exc:
            st.error(f"Falha ao gravar: {exc}")
            return
        st.session_state.pop("be_diario_form_aberto", None)
        st.rerun()


# "O que se nomeia, se atravessa." -- princípio terapêutico
