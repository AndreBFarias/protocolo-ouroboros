"""Cluster Bem-estar · aba "Diário emocional" (UX-RD-18, UX-V-3.7).

Layout 3-col canônico (UX-V-3.7) espelhando ``19-diario-emocional.html``:

* **Coluna esquerda** -- 3 cards de facetas (Tipo/ParaQuem/Período) com
  counts reais derivados dos items + tags populares.
* **Coluna central** -- card NOVA ENTRADA com 4 tabs nativas
  (Trigger/Vitória/Reflexão/Observação). Cada tab tem título, pílulas
  de intensidade 1-5, "para quem", tags e corpo. Embaixo, timeline
  cronológica DESC com cards (border-left semântica por tipo).
* **Coluna direita** -- espaço reservado para futuras métricas curtas.

Lições UX-RD herdadas:

* HTML via :func:`minificar` (UX-RD-04).
* Cores via ``CORES`` -- nunca hex literal.
* Fallback graceful para vault ausente (UX-RD-15).
* Contrato uniforme ``renderizar(dados, periodo, pessoa, ctx)``.  # noqa: accent
* Identificador pessoa SEMPRE canônico (ADR-23).

Subregra retrocompatível (padrão (o)): ``_filtrar`` continua aceitando
``"trigger"|"vitoria"|"todos"`` exatamente como antes; agora também
aceita ``"reflexao"|"observacao"``. ``_card_html`` mantém border-left
vermelha (trigger) e verde (vitoria); reflexao usa purple, observacao
usa cyan.

Persistência markdown de reflexao/observacao fica como placeholder
(UX-V-3.7 não-objetivo): tabs renderizam o form, mas só trigger/vitoria
gravam via :func:`escrever_diario`.
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
from src.dashboard.componentes.ui import (
    callout_html,
    carregar_css_pagina,
    sync_indicator_html,
)
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

# Tipos do diário (UX-V-3.7). Ordem importa: corresponde às 4 tabs.
_TIPOS_ORDEM: tuple[str, ...] = ("trigger", "vitoria", "reflexao", "observacao")
_TIPOS_LABEL: dict[str, str] = {
    "trigger": "Trigger",
    "vitoria": "Vitória",
    "reflexao": "Reflexão",
    "observacao": "Observação",
}
_TIPOS_SUBTITULO: dict[str, str] = {
    "trigger": "Algo que disparou ansiedade, raiva ou tristeza.",
    "vitoria": "Algo bom -- pequeno ou grande.",
    "reflexao": "Pensamento, observação, padrão notado.",
    "observacao": "Sobre Pessoa B ou sobre o casal.",
}
# Tipos com persistência markdown atual (escrever_diario aceita).
_TIPOS_PERSISTIDOS: frozenset[str] = frozenset({"trigger", "vitoria"})

_KEY_FLASH = "be_diario_flash"


def _cor_tipo(modo: str) -> str:
    """Retorna a cor canônica por tipo (token CORES)."""
    return {
        "trigger": CORES.get("negativo", "#ff5555"),
        "vitoria": CORES.get("positivo", "#50fa7b"),
        "reflexao": CORES.get("destaque", "#bd93f9"),
        "observacao": CORES.get("neutro", "#8be9fd"),
    }.get(modo, CORES.get("texto_muted", "#6c6f7d"))


def renderizar(  # noqa: accent
    dados: dict[str, pd.DataFrame],
    periodo: str,  # noqa: accent
    pessoa: str,
    ctx: dict | None = None,
) -> None:
    """Renderiza Bem-estar / Diário emocional (UX-V-3.7)."""
    from src.dashboard.componentes.topbar_actions import renderizar_grupo_acoes

    renderizar_grupo_acoes(
        [
            {
                "label": "Heatmap",
                "glyph": "analise",
                "href": "?cluster=Bem-estar&tab=Humor",
                "title": "Ver humor 91 dias",
            },
            {
                "label": "Hoje",
                "primary": True,
                "glyph": "calendar",
                "href": "?cluster=Bem-estar&tab=Hoje",
                "title": "Registrar humor de hoje",
            },
        ]
    )

    del dados, periodo, ctx  # noqa: accent

    st.markdown(minificar(carregar_css_pagina("be_diario")), unsafe_allow_html=True)

    vault_root = descobrir_vault_root()
    items = _carregar_items(vault_root)

    flash = st.session_state.pop(_KEY_FLASH, None)
    if flash:
        st.success(flash)

    # Estado dos filtros (a coluna esquerda renderiza widgets que escrevem
    # nessas chaves; reusamos os defaults mesmo na primeira carga).
    pessoa_default = pessoa if pessoa in _PESSOAS else "todos"
    modo_atual = st.session_state.get("be_diario_modo", "todos")
    periodo_atual = st.session_state.get("be_diario_periodo", "30 dias")
    pessoa_atual = st.session_state.get("be_diario_pessoa", pessoa_default)

    # Counts derivados dos items (faceta dinâmica).
    counts = _counts_facetas(items, hoje=date.today())

    # Layout 3-col (UX-V-3.7): facetas | conteúdo | espaço lateral.
    col_facetas, col_conteudo, col_lateral = st.columns([1, 2.5, 0.5], gap="medium")

    with col_facetas:
        _renderizar_facetas(counts)

    items_filtrados = _filtrar(
        items,
        modo=st.session_state.get("be_diario_modo", modo_atual),
        periodo_dias=_PERIODOS.get(
            st.session_state.get("be_diario_periodo", periodo_atual),
            30,
        ),
        pessoa=st.session_state.get("be_diario_pessoa", pessoa_atual),
        hoje=date.today(),
    )

    with col_conteudo:
        st.markdown(
            _page_header_canonico(len(items_filtrados)),
            unsafe_allow_html=True,
        )
        # UX-V-04: indicador de observabilidade sync vault -> cache -> dashboard.
        st.markdown(
            f'<div class="sync-indicator-wrapper">{sync_indicator_html()}</div>',
            unsafe_allow_html=True,
        )

        # Card NOVA ENTRADA com 4 tabs (UX-V-3.7).
        _renderizar_card_nova_entrada(vault_root, pessoa_atual)

        # Timeline embaixo do form.
        if vault_root is None:
            msg = (
                "Vault Bem-estar não encontrado. Configure OUROBOROS_VAULT "
                "para visualizar registros do diário emocional."
            )
            st.markdown(callout_html("warning", msg), unsafe_allow_html=True)
        elif not items:
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
                "</div></div>"
                '<div style="display:flex;align-items:center;gap:10px;">'
                '<span class="skel-bloco" style="width:40px;height:40px;'
                'border-radius:50%;"></span>'
                '<div style="flex:1;display:flex;flex-direction:column;gap:6px;">'
                '<span class="skel-bloco" style="width:50%;"></span>'
                '<span class="skel-bloco" style="width:80%;height:0.9em;"></span>'
                "</div></div>"
                "</div>"
            )
            st.markdown(
                fallback_estado_inicial_html(
                    titulo="DIÁRIO EMOCIONAL · sem registros ainda",
                    descricao=(  # noqa: accent
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
            st.markdown(
                _timeline_header_html(
                    st.session_state.get("be_diario_modo", "todos"),
                    st.session_state.get("be_diario_periodo", "30 dias"),
                ),
                unsafe_allow_html=True,
            )
            for item in items_filtrados:
                st.markdown(_card_html(item), unsafe_allow_html=True)

    with col_lateral:
        # Espaço reservado (UX-V-3.7). Mockup tem coluna lateral estreita
        # para futuras métricas curtas (streak, média, etc.).
        st.markdown('<div class="diario-coluna-lateral"></div>', unsafe_allow_html=True)


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
    """Filtra items por modo, período e pessoa.

    Subregra retrocompatível (padrão (o)): ``modo`` aceita os mesmos
    valores históricos (``"todos"``, ``"trigger"``, ``"vitoria"``) e
    também os novos (``"reflexao"``, ``"observacao"``). Se o item tem
    campo ``modo`` ausente do conjunto conhecido, filtragem por modo
    específico o exclui (compatível com semântica anterior).
    """
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


def _counts_facetas(
    items: list[dict[str, Any]],
    *,
    hoje: date,
) -> dict[str, dict[str, int]]:
    """Calcula counts por faceta (tipo, pessoa, período) para a sidebar.

    Counts de tipo e pessoa consideram TODOS os items. Counts de período
    consideram itens dentro da janela respectiva.
    """
    by_tipo: Counter[str] = Counter()
    by_pessoa: Counter[str] = Counter()
    for it in items:
        by_tipo[str(it.get("modo", "")) or "sem_tipo"] += 1
        by_pessoa[str(it.get("autor", "")) or "sem_autor"] += 1

    by_periodo: dict[str, int] = {}
    for label, dias in _PERIODOS.items():
        limite = hoje - timedelta(days=dias)
        cnt = 0
        for it in items:
            try:
                d_obj = date.fromisoformat(str(it.get("data", ""))[:10])
            except ValueError:
                continue
            if limite <= d_obj <= hoje:
                cnt += 1
        by_periodo[label] = cnt

    tags_counter: Counter[str] = Counter()
    for it in items:
        for emo in it.get("emocoes") or []:
            tags_counter[str(emo).strip()] += 1
    tags_top = dict(tags_counter.most_common(8))

    return {
        "tipo": dict(by_tipo),
        "pessoa": dict(by_pessoa),
        "periodo": by_periodo,  # noqa: accent
        "total": {"todos": len(items)},
        "tags_top": tags_top,
    }


# ---------------------------------------------------------------------------
# UI: facetas (coluna esquerda)
# ---------------------------------------------------------------------------


def _renderizar_facetas(counts: dict[str, dict[str, int]]) -> None:
    """Renderiza 3 cards de facetas + tags populares com counts reais."""
    total = counts.get("total", {}).get("todos", 0)

    # Card Tipo.
    st.markdown('<div class="filtro-card"><h3>Tipo</h3>', unsafe_allow_html=True)
    opcoes_tipo = ["todos", *_TIPOS_ORDEM]

    def _label_tipo(v: str) -> str:
        if v == "todos":
            return f"todos os tipos · {total}"
        c = counts.get("tipo", {}).get(v, 0)
        return f"{_TIPOS_LABEL.get(v, v)} · {c}"

    st.radio(
        "Tipo",
        options=opcoes_tipo,
        format_func=_label_tipo,
        key="be_diario_modo",
        label_visibility="collapsed",
    )
    st.markdown("</div>", unsafe_allow_html=True)

    # Card Para quem (autor).
    st.markdown('<div class="filtro-card"><h3>Para quem</h3>', unsafe_allow_html=True)

    def _label_pessoa(v: str) -> str:
        if v == "todos":
            return f"todos · {total}"
        c = counts.get("pessoa", {}).get(v, 0)
        return f"{_PESSOAS_LABEL.get(v, v)} · {c}"

    st.radio(
        "Para quem",
        options=list(_PESSOAS),
        format_func=_label_pessoa,
        key="be_diario_pessoa",
        label_visibility="collapsed",
    )
    st.markdown("</div>", unsafe_allow_html=True)

    # Card Período.
    st.markdown('<div class="filtro-card"><h3>Período</h3>', unsafe_allow_html=True)

    def _label_periodo(v: str) -> str:
        c = counts.get("periodo", {}).get(v, 0)  # noqa: accent
        return f"{v} · {c}"

    st.radio(
        "Período",
        options=list(_PERIODOS.keys()),
        format_func=_label_periodo,
        index=1,
        key="be_diario_periodo",
        label_visibility="collapsed",
    )
    st.markdown("</div>", unsafe_allow_html=True)

    # Card Tags populares.
    tags_top = counts.get("tags_top", {})
    if tags_top:
        chips = "".join(
            f'<span class="pill">{_escape(tag)} · {qtd}</span>' for tag, qtd in tags_top.items()
        )
        st.markdown(
            minificar(
                f'<div class="filtro-card filtro-card-inset">'
                f"<h3>Tags populares</h3>"
                f'<div class="filtro-tags-top">{chips}</div>'
                f"</div>"
            ),
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# UI: card NOVA ENTRADA com 4 tabs
# ---------------------------------------------------------------------------


def _renderizar_card_nova_entrada(
    vault_root: Path | None,
    pessoa_default: str,
) -> None:
    """Renderiza o card NOVA ENTRADA com 4 tabs (UX-V-3.7).

    Cada tab tem o mesmo form: título, intensidade pílulas 1-5,
    "esse registro é para", tags, corpo. Botão de salvar muda
    label conforme tipo. Apenas trigger/vitoria persistem nesta sprint
    (placeholder para reflexao/observacao -- ver não-objetivos).
    """
    st.markdown(
        '<div class="novo-card-host"><h3 class="novo-card-titulo">Nova entrada</h3></div>',
        unsafe_allow_html=True,
    )

    abas = st.tabs([_TIPOS_LABEL[t] for t in _TIPOS_ORDEM])
    for aba, tipo in zip(abas, _TIPOS_ORDEM, strict=True):
        with aba:
            _renderizar_form_tab(vault_root, pessoa_default, tipo)


def _renderizar_form_tab(
    vault_root: Path | None,
    pessoa_default: str,
    tipo: str,
) -> None:
    """Form de uma tab. ``tipo`` é trigger/vitoria/reflexao/observacao."""
    cor = _cor_tipo(tipo)
    sub = _TIPOS_SUBTITULO.get(tipo, "")
    rotulo = _TIPOS_LABEL.get(tipo, tipo)

    # Subtítulo descritivo do tipo.
    st.markdown(
        f'<div class="novo-tab-subtitulo" style="border-left:3px solid {cor};">'
        f"{_escape(sub)}</div>",
        unsafe_allow_html=True,
    )

    if vault_root is None:
        st.markdown(
            callout_html(
                "warning",
                "Vault não encontrado. Configure OUROBOROS_VAULT para registrar.",
            ),
            unsafe_allow_html=True,
        )
        return

    persistido = tipo in _TIPOS_PERSISTIDOS
    if not persistido:
        st.markdown(
            callout_html(
                "info",
                f"Persistência de {rotulo.lower()} chega via app mobile "
                "(placeholder nesta sprint).",
            ),
            unsafe_allow_html=True,
        )

    form_key = f"be_diario_form_{tipo}"
    int_key = f"be_diario_int_{tipo}"

    # Pílulas de intensidade 1-5 fora do form (cada botão é um widget
    # interativo separado que reescreve o session_state).
    intensidade = int(st.session_state.get(int_key, 3))
    st.markdown(
        '<div class="intensidade-rotulo">Intensidade</div>',
        unsafe_allow_html=True,
    )
    cols_int = st.columns(5, gap="small")
    for v, col in enumerate(cols_int, start=1):
        ativo = v <= intensidade
        label = f"● {v}" if ativo else f"○ {v}"
        if col.button(
            label,
            key=f"{int_key}_btn_{v}",
            use_container_width=True,
        ):
            st.session_state[int_key] = v
            st.rerun()

    with st.form(form_key):
        titulo = st.text_input(
            "Título -- uma frase",
            key=f"{form_key}_titulo",
            placeholder=_placeholder_titulo(tipo),
        )
        c1, c2 = st.columns(2, gap="medium")
        with c1:
            pessoas_form = ("pessoa_a", "pessoa_b", "casal")
            autor_default = pessoa_default if pessoa_default in pessoas_form else "pessoa_a"
            autor = st.selectbox(
                "Esse registro é para",
                options=pessoas_form,
                index=pessoas_form.index(autor_default),
                format_func=lambda v: _PESSOAS_LABEL.get(v, v),
                key=f"{form_key}_autor",
            )
        with c2:
            tags_txt = st.text_input(
                "Tags (separe por vírgula)",
                key=f"{form_key}_tags",
                placeholder="trabalho, ansiedade, manhã",
            )
        corpo = st.text_area(
            "Corpo -- sem julgamento, escreva como vier",
            key=f"{form_key}_corpo",
            placeholder=sub,
            height=120,
        )
        col_a, col_b = st.columns([3, 1], gap="small")
        salvar = col_a.form_submit_button(
            f"Salvar {rotulo.lower()}",
            use_container_width=True,
            disabled=not persistido,
        )
        cancelar = col_b.form_submit_button(
            "Limpar",
            use_container_width=True,
        )

    if cancelar:
        for chave in (
            f"{form_key}_titulo",
            f"{form_key}_tags",
            f"{form_key}_corpo",
        ):
            st.session_state.pop(chave, None)
        st.session_state.pop(int_key, None)
        st.rerun()

    if salvar and persistido:
        emocoes = [t.strip() for t in (tags_txt or "").split(",") if t.strip()]
        # Heurística: tags que parecem identificador de pessoa
        # (``pessoa_*`` ou ``casal``) viram ``com_quem``. As demais
        # ficam como emocoes/tags semânticas. Mantém compat com o
        # formato gravado pelo app mobile.
        com_quem: list[str] = []
        emocoes_filtradas: list[str] = []
        for e in emocoes:
            if e.startswith("pessoa_") or e == "casal":
                com_quem.append(e)
            else:
                emocoes_filtradas.append(e)
        try:
            arquivo = escrever_diario(
                vault_root,
                date.today(),
                modo=tipo,
                emocoes=emocoes_filtradas,
                intensidade=int(st.session_state.get(int_key, 3)),
                com_quem=com_quem,
                frase=(titulo or "") + ("\n\n" + corpo if corpo else ""),
                pessoa=autor,
            )
            st.session_state[_KEY_FLASH] = f"{rotulo} gravado em {arquivo.name}."
        except (OSError, ValueError) as exc:
            st.error(f"Falha ao gravar: {exc}")
            return
        for chave in (
            f"{form_key}_titulo",
            f"{form_key}_tags",
            f"{form_key}_corpo",
        ):
            st.session_state.pop(chave, None)
        st.session_state.pop(int_key, None)
        st.rerun()


def _placeholder_titulo(tipo: str) -> str:
    return {
        "trigger": "ex.: reunião com o chefe me deixou ansioso",
        "vitoria": "ex.: consegui terminar o relatório sem travar",
        "reflexao": "ex.: percebi que ansiedade some quando ando",
        "observacao": "ex.: pessoa B parecia mais leve hoje",
    }.get(tipo, "")


# ---------------------------------------------------------------------------
# UI: timeline header
# ---------------------------------------------------------------------------


def _timeline_header_html(modo_atual: str, periodo_atual: str) -> str:
    rotulo_modo = (
        "todos os tipos"
        if modo_atual == "todos"
        else _TIPOS_LABEL.get(modo_atual, modo_atual).lower()
    )
    return minificar(
        f'<div class="timeline-head">'
        f"<h3>Timeline · {_escape(rotulo_modo)} · {_escape(periodo_atual)}</h3>"
        f"</div>"
    )


# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------


def _page_header_canonico(qtd: int) -> str:
    """Page-header canônico via UX-M-02 (substitui markup local)."""
    return renderizar_page_header(
        titulo="BEM-ESTAR · DIÁRIO",
        subtitulo=(
            "Triggers, vitórias, reflexões e observações. Cada entrada vai "
            "pro markdown do dia, indexada por tag. Filtra por tipo, "
            "para quem e período."
        ),
        sprint_tag="UX-V-3.7",
        pills=[{"texto": f"{qtd} registros", "tipo": "d7-graduado"}],
    )


def _card_html(item: dict[str, Any]) -> str:
    """Cartão único do diário com border-left semântica.

    Cores por modo (subregra retrocompatível, padrão (o)):

    * trigger -> negativo (#ff5555)
    * vitoria -> positivo (#50fa7b)
    * reflexao -> destaque (#bd93f9)
    * observacao -> neutro (#8be9fd)
    """
    modo = str(item.get("modo", ""))
    cor_borda = _cor_tipo(modo)
    classe_modo = f"diario-card-{modo}" if modo in _TIPOS_ORDEM else "diario-card-default"
    rotulo_modo = _TIPOS_LABEL.get(modo, modo or "—")

    autor = str(item.get("autor", "—"))
    data_iso = str(item.get("data", ""))
    intensidade = item.get("intensidade") or 0
    try:
        intensidade_int = int(intensidade)
    except (TypeError, ValueError):
        intensidade_int = 0
    intensidade_int = max(0, min(5, intensidade_int))

    emocoes = item.get("emocoes") or []
    chips_emo = (
        "".join(f'<span class="chip-emo">{_escape(str(e))}</span>' for e in emocoes)
        or '<span class="chip-emo chip-vazio">sem emoções tagueadas</span>'
    )

    com = item.get("com") or []
    com_html = (
        '<span class="diario-com">com ' + ", ".join(_escape(str(c)) for c in com) + "</span>"
        if com
        else ""
    )

    barra_int = "".join(
        f'<span class="dot {"on" if i < intensidade_int else "off"}"></span>' for i in range(5)
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
        texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    )


# CSS dedicado: src/dashboard/css/paginas/be_diario.css.

# "O que se nomeia, se atravessa." -- princípio terapêutico
