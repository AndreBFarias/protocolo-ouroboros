"""Cluster Bem-estar · aba "Eventos" (UX-RD-18).

Timeline cronológica DESC dos eventos registrados. Cada evento vira um
cartão com border-left semântica (verde para ``positivo``, vermelha
para ``negativo``), data, modo pill, lugar+bairro, slider visual da
intensidade (1..5), thumbs das fotos anexadas, categoria pill e "com".
Coluna lateral direita mostra os 10 bairros mais frequentes (agregação
do cache, NUNCA hardcoded).

Layout espelha ``novo-mockup/mockups/22-eventos.html``:

* ``page-header`` com sprint-tag UX-RD-18 + pill da contagem visível.
* Coluna esquerda (filtros + lista) e direita (Bairros frequentes).
* ``.evento-card`` com border-left 4px (verde/vermelha).
* Botão "Registrar evento" abre ``st.dialog`` (com fallback para
  ``st.expander``) que invoca :func:`escrever_evento`.

Lições UX-RD herdadas:

* HTML via :func:`minificar` (UX-RD-04).
* Cores via ``CORES`` -- nunca hex literal.
* Fallback graceful para vault ausente (UX-RD-15).
* Bairros agregados em runtime, sem hardcode (forbidden da spec).
* Contrato uniforme ``renderizar(dados, periodo, pessoa, ctx)``.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from src.dashboard.componentes.html_utils import minificar
from src.dashboard.componentes.page_header import renderizar_page_header
from src.dashboard.componentes.ui import callout_html
from src.dashboard.tema import CORES
from src.mobile_cache.escrever_evento import escrever_evento
from src.mobile_cache.eventos import gerar_cache as gerar_cache_eventos
from src.mobile_cache.varrer_vault import descobrir_vault_root

_PERIODOS: dict[str, int] = {
    "7 dias": 7,
    "30 dias": 30,
    "90 dias": 90,
    "1 ano": 365,
}

_PESSOAS = ("todos", "pessoa_a", "pessoa_b", "casal")
_PESSOAS_LABEL = {
    "todos": "Todos",
    "pessoa_a": "Pessoa A",
    "pessoa_b": "Pessoa B",
    "casal": "Casal",
}

_KEY_FLASH = "be_eventos_flash"


def renderizar(
    dados: dict[str, pd.DataFrame],
    periodo: str,
    pessoa: str,
    ctx: dict | None = None,
) -> None:
    """Renderiza Bem-estar / Eventos (UX-T-22)."""
    from src.dashboard.componentes.topbar_actions import renderizar_grupo_acoes
    renderizar_grupo_acoes([
        {"label": "Calendário", "title": "Vista mensal"},
        {"label": "Novo evento", "primary": True,
         "title": "Wizard de evento"},
    ])

    del dados, periodo, ctx

    st.markdown(_estilos_locais(), unsafe_allow_html=True)

    vault_root = descobrir_vault_root()
    items = _carregar_items(vault_root)

    flash = st.session_state.pop(_KEY_FLASH, None)
    if flash:
        st.success(flash)

    col_filtros, col_lista, col_lateral = st.columns([1, 2.4, 1], gap="large")

    with col_filtros:
        modo_label = st.radio(
            "Modo",
            options=["todos", "positivo", "negativo"],
            format_func=lambda v: {
                "todos": "Todos",
                "positivo": "Positivo",
                "negativo": "Negativo",
            }[v],
            key="be_eventos_modo",
        )
        periodo_label = st.selectbox(
            "Período",
            options=list(_PERIODOS.keys()),
            index=2,
            key="be_eventos_periodo",
        )
        categorias_disponiveis = ["todas"] + sorted(
            {str(it.get("categoria") or "").strip() for it in items if it.get("categoria")}
        )
        categoria_label = st.selectbox(
            "Categoria",
            options=categorias_disponiveis,
            index=0,
            key="be_eventos_categoria",
        )
        pessoa_default = pessoa if pessoa in _PESSOAS else "todos"
        pessoa_label = st.selectbox(
            "Pessoa",
            options=list(_PESSOAS),
            index=list(_PESSOAS).index(pessoa_default),
            format_func=lambda v: _PESSOAS_LABEL[v],
            key="be_eventos_pessoa",
        )

        st.markdown("---")
        if st.button("Registrar evento", use_container_width=True, key="be_eventos_btn_abrir"):
            st.session_state["be_eventos_form_aberto"] = True

    items_filtrados = _filtrar(
        items,
        modo=modo_label,
        periodo_dias=_PERIODOS[periodo_label],
        categoria=categoria_label,
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
                "para visualizar a timeline de eventos."
            )
            st.markdown(callout_html("warning", msg), unsafe_allow_html=True)
        elif not items:
            msg = (
                "Nenhum evento registrado no vault. "
                "Use o botão à esquerda para criar o primeiro."
            )
            st.markdown(callout_html("info", msg), unsafe_allow_html=True)
        elif not items_filtrados:
            st.markdown(
                callout_html("info", "Nenhum evento casa com os filtros atuais."),
                unsafe_allow_html=True,
            )
        else:
            for item in items_filtrados:
                st.markdown(_card_html(item), unsafe_allow_html=True)

    with col_lateral:
        st.markdown(
            _bairros_html(_top_bairros(items, top_n=10)),
            unsafe_allow_html=True,
        )

    if st.session_state.get("be_eventos_form_aberto"):
        _renderizar_form(vault_root, pessoa_label)


# ---------------------------------------------------------------------------
# Cache loader + filtros
# ---------------------------------------------------------------------------


def _carregar_items(vault_root: Path | None) -> list[dict[str, Any]]:
    if vault_root is None:
        return []
    arquivo = vault_root / ".ouroboros" / "cache" / "eventos.json"
    if not arquivo.exists():
        try:
            gerar_cache_eventos(vault_root)
        except OSError:
            return []
    if not arquivo.exists():
        return []
    try:
        payload = json.loads(arquivo.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    items = payload.get("items", []) or []
    items.sort(key=lambda i: (str(i.get("data", "")), str(i.get("autor", ""))), reverse=True)
    return items


def _filtrar(
    items: list[dict[str, Any]],
    *,
    modo: str,
    periodo_dias: int,
    categoria: str,
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
        if categoria != "todas" and str(it.get("categoria")) != categoria:
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


def _top_bairros(items: list[dict[str, Any]], *, top_n: int = 10) -> list[tuple[str, int]]:
    """Agrega bairros do cache (NUNCA hardcoded -- requisito spec)."""
    contador: Counter[str] = Counter()
    for it in items:
        bairro = str(it.get("bairro") or "").strip()
        if bairro:
            contador[bairro] += 1
    # Ordenação determinística: count DESC, depois nome ASC.
    sorted_items = sorted(contador.items(), key=lambda kv: (-kv[1], kv[0]))
    return sorted_items[:top_n]


# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------


def _page_header_canonico(qtd: int) -> str:
    """Page-header canônico via UX-M-02 (substitui markup local)."""
    return renderizar_page_header(
        titulo="BEM-ESTAR · EVENTOS",
        subtitulo=(
            "Timeline cronológica de eventos positivo ou negativo "
            "com lugar, bairro e fotos anexadas."
        ),
        sprint_tag="UX-RD-18",
        pills=[{"texto": f"{qtd} eventos", "tipo": "d7-graduado"}],
    )


def _card_html(item: dict[str, Any]) -> str:
    modo = str(item.get("modo", ""))
    cor_borda = (
        CORES.get("positivo", "#27ae60") if modo == "positivo"
        else CORES.get("negativo", "#c0392b") if modo == "negativo"
        else CORES.get("texto_muted", "#888")
    )
    rotulo_modo = {"positivo": "Positivo", "negativo": "Negativo"}.get(modo, modo or "—")

    autor = str(item.get("autor", "—"))
    data_iso = str(item.get("data", ""))
    lugar = _escape(str(item.get("lugar") or ""))
    bairro = _escape(str(item.get("bairro") or ""))
    categoria = _escape(str(item.get("categoria") or ""))

    intensidade = item.get("intensidade") or 0
    try:
        intensidade_int = int(intensidade)
    except (TypeError, ValueError):
        intensidade_int = 0
    intensidade_int = max(0, min(5, intensidade_int))
    barra_int = "".join(
        f'<span class="dot {"on" if i < intensidade_int else "off"}"></span>'
        for i in range(5)
    )

    fotos = item.get("fotos") or []
    thumbs_html = ""
    if fotos:
        thumbs_html = '<div class="evento-thumbs">' + "".join(
            f'<span class="thumb-mini" title="{_escape(str(f))}">{_escape(str(f)[:14])}</span>'
            for f in fotos
        ) + "</div>"

    com = item.get("com") or []
    com_html = (
        '<span class="evento-com">com '
        + ", ".join(_escape(str(c)) for c in com)
        + "</span>"
        if com else ""
    )

    categoria_html = (
        f'<span class="evento-cat-pill">{categoria}</span>' if categoria else ""
    )

    return minificar(
        f"""
        <div class="evento-card" style="border-left:4px solid {cor_borda};">
          <div class="evento-card-head">
            <span class="evento-data">{_escape(data_iso[:10])}</span>
            <span class="evento-modo-pill" style="color:{cor_borda};
              border:1px solid {cor_borda};">{rotulo_modo}</span>
            {categoria_html}
            <span class="evento-autor">{_escape(autor)}</span>
          </div>
          <div class="evento-lugar">
            <strong>{lugar or '—'}</strong>
            {f'<span class="evento-bairro">· {bairro}</span>' if bairro else ''}
          </div>
          <div class="evento-intens">
            <span class="evento-intens-label">intensidade</span>
            {barra_int}
            <span class="evento-intens-num">{intensidade_int}/5</span>
          </div>
          {thumbs_html}
          {com_html}
        </div>
        """
    )


def _bairros_html(top_bairros: list[tuple[str, int]]) -> str:
    if not top_bairros:
        linhas = '<div class="bairro-vazio">Sem bairros catalogados.</div>'
    else:
        linhas = "".join(
            f'<div class="bairro-linha"><span class="bairro-nome">{_escape(nome)}</span>'
            f'<span class="bairro-count">{count}</span></div>'
            for nome, count in top_bairros
        )
    return minificar(
        f"""
        <div class="bairros-card">
          <div class="bairros-titulo">Bairros frequentes</div>
          <div class="bairros-lista">{linhas}</div>
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


def _estilos_locais() -> str:
    return minificar(
        f"""
        <style>
          .evento-card {{
            background: {CORES['card_fundo']};
            border: 1px solid {CORES['card_elevado']};
            border-radius: 6px;
            padding: 12px 14px;
            margin-bottom: 10px;
          }}
          .evento-card-head {{
            display: flex;
            gap: 12px;
            align-items: center;
            margin-bottom: 8px;
            flex-wrap: wrap;
          }}
          .evento-data {{
            font-family: monospace;
            font-size: 13px;
            color: {CORES['texto']};
          }}
          .evento-modo-pill {{
            font-family: monospace;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            padding: 2px 8px;
            border-radius: 12px;
          }}
          .evento-cat-pill {{
            font-family: monospace;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            padding: 2px 8px;
            border-radius: 4px;
            background: {CORES['fundo_inset']};
            color: {CORES['texto_sec']};
          }}
          .evento-autor {{
            font-family: monospace;
            font-size: 11px;
            color: {CORES['texto_muted']};
            margin-left: auto;
          }}
          .evento-lugar {{
            font-size: 14px;
            color: {CORES['texto']};
            margin-bottom: 6px;
          }}
          .evento-bairro {{
            font-size: 12px;
            color: {CORES['texto_muted']};
            margin-left: 4px;
          }}
          .evento-intens {{
            display: flex;
            align-items: center;
            gap: 6px;
            margin-bottom: 6px;
          }}
          .evento-intens-label {{
            font-family: monospace;
            font-size: 10px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: {CORES['texto_muted']};
          }}
          .evento-intens .dot {{
            width: 10px;
            height: 10px;
            border-radius: 50%;
            display: inline-block;
          }}
          .evento-intens .dot.on {{
            background: {CORES['destaque']};
          }}
          .evento-intens .dot.off {{
            background: {CORES['card_elevado']};
          }}
          .evento-intens-num {{
            font-family: monospace;
            font-size: 11px;
            color: {CORES['texto_muted']};
            margin-left: 4px;
          }}
          .evento-thumbs {{
            display: flex;
            gap: 6px;
            flex-wrap: wrap;
            margin-bottom: 6px;
          }}
          .thumb-mini {{
            font-family: monospace;
            font-size: 10px;
            background: {CORES['fundo_inset']};
            color: {CORES['texto_sec']};
            padding: 4px 8px;
            border-radius: 4px;
            border: 1px dashed {CORES['card_elevado']};
          }}
          .evento-com {{
            display: inline-block;
            margin-top: 4px;
            font-family: monospace;
            font-size: 11px;
            color: {CORES['texto_muted']};
          }}
          .bairros-card {{
            background: {CORES['card_fundo']};
            border: 1px solid {CORES['card_elevado']};
            border-radius: 6px;
            padding: 14px;
            position: sticky;
            top: 20px;
          }}
          .bairros-titulo {{
            font-family: monospace;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.10em;
            color: {CORES['texto_muted']};
            margin-bottom: 10px;
          }}
          .bairro-linha {{
            display: flex;
            justify-content: space-between;
            align-items: baseline;
            padding: 4px 0;
            border-bottom: 1px solid {CORES['card_elevado']};
          }}
          .bairro-linha:last-child {{
            border-bottom: none;
          }}
          .bairro-nome {{
            font-size: 12px;
            color: {CORES['texto']};
          }}
          .bairro-count {{
            font-family: monospace;
            font-size: 11px;
            color: {CORES['destaque']};
          }}
          .bairro-vazio {{
            font-family: monospace;
            font-size: 11px;
            color: {CORES['texto_muted']};
            font-style: italic;
          }}
        </style>
        """
    )


# ---------------------------------------------------------------------------
# Form modal
# ---------------------------------------------------------------------------


def _renderizar_form(vault_root: Path | None, pessoa_default: str) -> None:
    titulo = "Registrar evento"
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
        if st.button("Fechar", key="be_eventos_form_fechar"):
            st.session_state.pop("be_eventos_form_aberto", None)
            st.rerun()
        return

    with st.form("be_eventos_form"):
        modo = st.radio(
            "Modo",
            options=["positivo", "negativo"],
            format_func=lambda v: "Positivo" if v == "positivo" else "Negativo",
            key="be_eventos_form_modo",
        )
        lugar = st.text_input(
            "Lugar",
            key="be_eventos_form_lugar",
            placeholder="padaria do bairro",
        )
        bairro = st.text_input(
            "Bairro",
            key="be_eventos_form_bairro",
        )
        categoria = st.text_input(
            "Categoria",
            key="be_eventos_form_categoria",
            placeholder="rolezinho",
        )
        intensidade = st.slider(
            "Intensidade",
            min_value=1,
            max_value=5,
            value=3,
            key="be_eventos_form_intensidade",
        )
        com_txt = st.text_input(
            "Com quem (separado por vírgula)",
            key="be_eventos_form_com",
        )
        fotos_txt = st.text_input(
            "Fotos (paths, separados por vírgula)",
            key="be_eventos_form_fotos",
        )
        pessoas_form = ("pessoa_a", "pessoa_b", "casal")
        autor_default = pessoa_default if pessoa_default in pessoas_form else "pessoa_a"
        autor = st.selectbox(
            "Autor",
            options=pessoas_form,
            index=pessoas_form.index(autor_default),
            format_func=lambda v: _PESSOAS_LABEL.get(v, v),
            key="be_eventos_form_autor",
        )
        texto = st.text_area(
            "Memória do evento",
            key="be_eventos_form_texto",
        )
        col_a, col_b = st.columns(2)
        salvar = col_a.form_submit_button("Salvar")
        cancelar = col_b.form_submit_button("Cancelar")

    if cancelar:
        st.session_state.pop("be_eventos_form_aberto", None)
        st.rerun()

    if salvar:
        com_quem = [c.strip() for c in (com_txt or "").split(",") if c.strip()]
        fotos = [f.strip() for f in (fotos_txt or "").split(",") if f.strip()]
        try:
            arquivo = escrever_evento(
                vault_root,
                date.today(),
                modo=modo,
                lugar=lugar or "",
                bairro=bairro or "",
                com_quem=com_quem,
                categoria=categoria or "",
                fotos=fotos,
                intensidade=intensidade,
                pessoa=autor,
                texto=texto or "",
            )
            st.session_state[_KEY_FLASH] = (
                f"Evento gravado em {arquivo.name}."
            )
        except (OSError, ValueError) as exc:
            st.error(f"Falha ao gravar: {exc}")
            return
        st.session_state.pop("be_eventos_form_aberto", None)
        st.rerun()


# "O lugar é onde o tempo se atravessa em memória." -- Gaston Bachelard
