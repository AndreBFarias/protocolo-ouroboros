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
from calendar import monthrange
from collections import Counter
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from src.dashboard.componentes.html_utils import minificar
from src.dashboard.componentes.page_header import renderizar_page_header
from src.dashboard.componentes.ui import callout_html, carregar_css_pagina
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

    renderizar_grupo_acoes(
        [
            {"label": "Calendário", "glyph": "calendar", "title": "Vista mensal"},
            {"label": "Novo evento", "primary": True, "glyph": "plus", "title": "Wizard de evento"},
        ]
    )

    del dados, periodo, ctx

    st.markdown(minificar(carregar_css_pagina("be_eventos")), unsafe_allow_html=True)

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
            from src.dashboard.componentes.ui import (
                fallback_estado_inicial_html,
                ler_sync_info,
            )

            skeleton = (
                '<div style="display:flex;flex-direction:column;gap:14px;">'
                '<div style="display:flex;gap:10px;align-items:flex-start;">'
                '<span class="skel-bloco" style="width:60px;height:0.9em;"></span>'
                '<div style="flex:1;display:flex;flex-direction:column;gap:6px;">'
                '<span class="skel-bloco" style="width:55%;"></span>'
                '<span class="skel-bloco" style="width:75%;height:0.85em;"></span>'
                "</div></div>"
                '<div style="display:flex;gap:10px;align-items:flex-start;">'
                '<span class="skel-bloco" style="width:60px;height:0.9em;"></span>'
                '<div style="flex:1;display:flex;flex-direction:column;gap:6px;">'
                '<span class="skel-bloco" style="width:45%;"></span>'
                '<span class="skel-bloco" style="width:65%;height:0.85em;"></span>'
                "</div></div>"
                '<div style="display:flex;gap:10px;align-items:flex-start;">'
                '<span class="skel-bloco" style="width:60px;height:0.9em;"></span>'
                '<div style="flex:1;display:flex;flex-direction:column;gap:6px;">'
                '<span class="skel-bloco" style="width:60%;"></span>'
                '<span class="skel-bloco" style="width:80%;height:0.85em;"></span>'
                "</div></div>"
                "</div>"
            )
            st.markdown(
                fallback_estado_inicial_html(
                    titulo="EVENTOS · sem registros ainda",
                    descricao=(
                        "Marcadores cronológicos (encontros, exames, viagens, "
                        "datas-chave) são registrados rapidamente no app mobile "
                        "e formam a timeline acima. Use a aba "
                        "<code>+ Evento</code> do app para criar o primeiro."
                    ),
                    skeleton_html=skeleton,
                    cta_secao="eventos",
                    sync_info=ler_sync_info(),
                ),
                unsafe_allow_html=True,
            )
        elif not items_filtrados:
            st.markdown(
                callout_html("info", "Nenhum evento casa com os filtros atuais."),
                unsafe_allow_html=True,
            )
        else:
            for item in items_filtrados:
                st.markdown(_card_html(item), unsafe_allow_html=True)

    with col_lateral:
        if items:
            hoje = date.today()
            st.markdown(
                _visao_mes_html(items, ano=hoje.year, mes=hoje.month),
                unsafe_allow_html=True,
            )
            st.markdown(
                _distribuicao_html(items),
                unsafe_allow_html=True,
            )
            st.markdown(
                _cruzamento_humor_html(),
                unsafe_allow_html=True,
            )
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
        CORES.get("positivo", "#27ae60")
        if modo == "positivo"
        else CORES.get("negativo", "#c0392b")
        if modo == "negativo"
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
        f'<span class="dot {"on" if i < intensidade_int else "off"}"></span>' for i in range(5)
    )

    fotos = item.get("fotos") or []
    thumbs_html = ""
    if fotos:
        thumbs_html = (
            '<div class="evento-thumbs">'
            + "".join(
                f'<span class="thumb-mini" title="{_escape(str(f))}">{_escape(str(f)[:14])}</span>'
                for f in fotos
            )
            + "</div>"
        )

    com = item.get("com") or []
    com_html = (
        '<span class="evento-com">com ' + ", ".join(_escape(str(c)) for c in com) + "</span>"
        if com
        else ""
    )

    categoria_html = f'<span class="evento-cat-pill">{categoria}</span>' if categoria else ""

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
            <strong>{lugar or "—"}</strong>
            {f'<span class="evento-bairro">· {bairro}</span>' if bairro else ""}
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


_MESES_PT = (
    "janeiro",
    "fevereiro",
    "março",
    "abril",
    "maio",
    "junho",
    "julho",
    "agosto",
    "setembro",
    "outubro",
    "novembro",
    "dezembro",
)


def _calendario_visual_html(
    eventos: list[dict[str, Any]],
    ano: int,
    mes: int,
) -> str:
    """Calendário 5x7 com pontos coloridos em datas com eventos.

    Layout espelha ``.cal-mini`` do mockup ``22-eventos.html`` (linha
    de cabeçalho D/S/T/Q/Q/S/S + grid de células com classes
    ``tem-evento`` e ``hoje``).
    """
    weekday_inicio = (date(ano, mes, 1).weekday() + 1) % 7
    _, total_dias = monthrange(ano, mes)
    dias: list[date | None] = [None] * weekday_inicio
    dias.extend(date(ano, mes, d) for d in range(1, total_dias + 1))
    while len(dias) % 7 != 0:
        dias.append(None)

    dias_evento: set[int] = set()
    for ev in eventos:
        try:
            d = date.fromisoformat(str(ev.get("data", ""))[:10])
        except ValueError:
            continue
        if d.year == ano and d.month == mes:
            dias_evento.add(d.day)

    hoje = date.today()
    celulas: list[str] = []
    for d in dias:
        if d is None:
            celulas.append('<div class="ddia fora"></div>')
            continue
        classes = ["ddia"]
        if d.day in dias_evento:
            classes.append("tem-evento")
        if d == hoje:
            classes.append("hoje")
        celulas.append(f'<div class="{" ".join(classes)}">{d.day}</div>')

    cabec = "".join(f'<span class="dlabel">{d}</span>' for d in ("D", "S", "T", "Q", "Q", "S", "S"))
    return minificar(
        f'<div class="calendario-visual">'
        f'<div class="cal-mini">{cabec}{"".join(celulas)}</div>'
        f"</div>"
    )


def _visao_mes_html(
    eventos: list[dict[str, Any]],
    ano: int,
    mes: int,
) -> str:
    """Card com KPIs do mês corrente + calendário 5x7 embutido."""
    eventos_no_mes = []
    com_pessoa_b = 0
    for ev in eventos:
        try:
            d = date.fromisoformat(str(ev.get("data", ""))[:10])
        except ValueError:
            continue
        if d.year == ano and d.month == mes:
            eventos_no_mes.append(ev)
            com = ev.get("com") or []
            autor = str(ev.get("autor", ""))
            if autor == "pessoa_b" or "pessoa_b" in com:
                com_pessoa_b += 1

    nome_mes = _MESES_PT[mes - 1]
    cal_html = _calendario_visual_html(eventos, ano, mes)
    return minificar(
        f"""
        <div class="ev-stat">
          <div class="l">{nome_mes} · visão</div>
          <div class="ev-stat-numeros">
            <div class="ev-stat-bloco">
              <div class="v" style="color:var(--accent-purple, #bd93f9);">
                {len(eventos_no_mes)}
              </div>
              <div class="sub">eventos</div>
            </div>
            <div class="ev-stat-bloco">
              <div class="v" style="color:var(--accent-pink, #ff79c6);">
                {com_pessoa_b}
              </div>
              <div class="sub">com pessoa B</div>
            </div>
          </div>
          {cal_html}
        </div>
        """
    )


_CAT_CORES = {
    "trabalho": "var(--accent-cyan, #8be9fd)",
    "saude": "var(--accent-orange, #ffb86c)",
    "saúde": "var(--accent-orange, #ffb86c)",
    "casal": "var(--accent-pink, #ff79c6)",
    "viagem": "var(--accent-purple, #bd93f9)",
    "familia": "var(--accent-yellow, #f1fa8c)",
    "família": "var(--accent-yellow, #f1fa8c)",
    "social": "var(--accent-green, #50fa7b)",
}


def _distribuicao_html(eventos: list[dict[str, Any]]) -> str:
    """Bar chart simples por categoria, ordenado DESC por contagem."""
    cats: Counter[str] = Counter(
        str(e.get("categoria") or "").strip().lower()
        for e in eventos
        if str(e.get("categoria") or "").strip()
    )
    if not cats:
        return ""
    max_v = max(cats.values())
    linhas: list[str] = []
    for cat, n in cats.most_common():
        pct = (n / max_v) * 100 if max_v else 0
        cor = _CAT_CORES.get(cat, "var(--accent-purple, #bd93f9)")
        linhas.append(
            f"""
            <div class="tb-row">
              <span class="nome">{_escape(cat)}</span>
              <div class="barra">
                <span style="width:{pct:.1f}%;background:{cor};"></span>
              </div>
              <span class="qtd">{n}</span>
            </div>
            """
        )
    return minificar(
        f"""
        <div class="ev-stat">
          <div class="l">distribuição por tipo</div>
          <div class="tipos-bars">{"".join(linhas)}</div>
        </div>
        """
    )


def _cruzamento_humor_html() -> str:
    """Placeholder do cruzamento eventos x humor (escopo V-2.14)."""
    return minificar(
        """
        <div class="ev-stat">
          <div class="l">cruzamento com humor</div>
          <div class="cruzamento-texto">
            Em produção: o backend cruza eventos x humor para responder
            perguntas como
            <ul class="cruzamento-perguntas">
              <li>"viagens elevam meu humor?"</li>
              <li>"reuniões aumentam ansiedade?"</li>
              <li>"rolezinhos ajudam o casal?"</li>
            </ul>
          </div>
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
        texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    )


# CSS dedicado: src/dashboard/css/paginas/be_eventos.css (UX-M-02.D residual).
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
        st.warning("Vault não encontrado. Configure `OUROBOROS_VAULT` antes de registrar.")
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
            st.session_state[_KEY_FLASH] = f"Evento gravado em {arquivo.name}."
        except (OSError, ValueError) as exc:
            st.error(f"Falha ao gravar: {exc}")
            return
        st.session_state.pop("be_eventos_form_aberto", None)
        st.rerun()


# "O lugar é onde o tempo se atravessa em memória." -- Gaston Bachelard
