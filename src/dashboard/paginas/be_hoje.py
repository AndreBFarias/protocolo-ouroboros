"""Cluster Bem-estar · aba "Hoje" (UX-RD-17).

Agregador do dia: hero esquerda com captura rápida de humor (4 sliders
1..5 + chips de tags + sono + medicação + frase) e coluna direita com
3 mini-cards (diários, eventos, medidas) lendo o cache JSON gerado por
``mobile_cache.varrer_vault``.

Layout espelha ``novo-mockup/mockups/17-bem-estar-hoje.html``:

* ``page-header`` com sprint-tag UX-RD-17 + pill data atual.
* ``.hoje-layout``: 2 colunas grid (1.4fr + 1fr).
* ``hero-humor`` (esquerda) -- form Streamlit com sliders + button.
* ``.coluna-dir`` (direita) -- 3 cards filtrados pelo dia atual.

Ao clicar "Registrar humor", invoca :func:`escrever_registro` que grava
``daily/<YYYY-MM-DD>.md`` no vault e regenera o cache. A próxima
re-renderização do Streamlit já mostra o registro novo no card
"Diários do dia" (idempotente -- registros do mesmo dia/pessoa
sobrescrevem).

Lições UX-RD aplicadas:

* HTML emitido via :func:`minificar` (UX-RD-04).
* Cores via ``CORES`` em ``src.dashboard.tema`` -- nunca hex literal.
* Fallback graceful: se o vault não for encontrado, mostra aviso
  visível em vez de crash (UX-RD-15).
* Função pública ``renderizar(dados, periodo, pessoa, ctx)`` -- contrato  # noqa: accent
  uniforme do dispatcher de ``app.py``.
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
from src.dashboard.componentes.ui import (
    carregar_css_pagina,
    sync_indicator_html,
)
from src.dashboard.tema import CORES
from src.mobile_cache.escrever_humor import TAGS_CANONICAS, escrever_registro
from src.mobile_cache.varrer_vault import descobrir_vault_root

# Chaves do session_state isoladas por página.
_KEY_HUMOR = "be_hoje_humor"
_KEY_ENERGIA = "be_hoje_energia"
_KEY_ANSIEDADE = "be_hoje_ansiedade"
_KEY_FOCO = "be_hoje_foco"
_KEY_MEDICACAO = "be_hoje_medicacao"
_KEY_SONO = "be_hoje_sono"
_KEY_TAGS = "be_hoje_tags"
_KEY_FRASE = "be_hoje_frase"
_KEY_FLASH = "be_hoje_flash"
_KEY_PARA = "be_hoje_para"


def renderizar(  # noqa: accent
    dados: dict[str, pd.DataFrame],
    periodo: str,  # noqa: accent
    pessoa: str,
    ctx: dict | None = None,
) -> None:
    """Renderiza a página Bem-estar / Hoje.

    Args:
        dados: estrutura padrão de DataFrames (não consumida; a página
            opera sobre o vault Bem-estar fora do XLSX financeiro).
        periodo: período da sidebar (ignorado nesta aba).  # noqa: accent
        pessoa: pessoa selecionada na sidebar
            (``pessoa_a``/``pessoa_b``/``casal``); usado como autor
            default ao gravar humor.
        ctx: contexto extra (granularidade etc., ignorado).
    """
    from src.dashboard.componentes.topbar_actions import renderizar_grupo_acoes

    renderizar_grupo_acoes(
        [
            {
                "label": "Diário emocional",
                "glyph": "heart",
                "href": "?cluster=Bem-estar&tab=Diário",
                "title": "Ir para o diário",
            },
            {
                "label": "Salvar humor",
                "primary": True,
                "glyph": "validar",
                "title": "Persistir registro de humor de hoje",
            },
        ]
    )

    del dados, periodo, ctx  # noqa: accent

    st.markdown(minificar(carregar_css_pagina("be_hoje")), unsafe_allow_html=True)

    pessoa_default = pessoa if pessoa in {"pessoa_a", "pessoa_b", "casal"} else "pessoa_a"
    if pessoa_default == "casal":
        pessoa_default = "pessoa_a"

    hoje = date.today()
    vault_root = descobrir_vault_root()

    st.markdown(_page_header_canonico(hoje), unsafe_allow_html=True)
    # UX-V-04: indicador de observabilidade sync vault -> cache -> dashboard.
    st.markdown(
        f'<div class="sync-indicator-wrapper">{sync_indicator_html()}</div>',
        unsafe_allow_html=True,
    )

    if vault_root is None:
        _renderizar_fallback_vault()
        return

    flash = st.session_state.pop(_KEY_FLASH, None)
    if flash:
        st.success(flash)

    coluna_esq, coluna_dir = st.columns([1.4, 1])

    with coluna_esq:
        _renderizar_hero_humor(vault_root, hoje, pessoa_default)

    with coluna_dir:
        _renderizar_coluna_direita(vault_root, hoje, pessoa_default)


# ---------------------------------------------------------------------------
# Page header
# ---------------------------------------------------------------------------


def _page_header_canonico(hoje: date) -> str:
    """Page-header canônico via UX-M-02 (substitui markup local)."""
    data_pt = hoje.strftime("%d/%m/%Y")
    return renderizar_page_header(
        titulo="BEM-ESTAR · HOJE",
        subtitulo=(
            f"Captura rápida de humor (<30s) e agregado dos registros do dia. "
            f"Persiste em daily/{hoje.isoformat()}.md com autor canônico "
            f"(pessoa_a / pessoa_b / casal)."
        ),
        sprint_tag="UX-RD-17",
        pills=[{"texto": data_pt, "tipo": "d7-graduado"}],
    )


def _renderizar_fallback_vault() -> None:
    """Estado inicial atrativo (UX-V-03) quando o vault Bem-estar não é encontrado."""
    from src.dashboard.componentes.ui import (
        fallback_estado_inicial_html,
        ler_sync_info,
    )

    skeleton = (
        '<div style="display:grid;grid-template-columns:1.4fr 1fr;gap:14px;">'
        '<div style="display:flex;flex-direction:column;gap:8px;">'
        '<span class="skel-bloco" style="width:40%;height:0.8em;"></span>'
        '<div style="display:flex;gap:6px;flex-wrap:wrap;">'
        + "".join(
            '<span class="skel-bloco" style="width:38px;height:38px;border-radius:6px;"></span>'
            for _ in range(7)
        )
        + "</div>"
        '<span class="skel-bloco" style="width:80%;height:60px;"></span>'
        "</div>"
        '<div style="display:flex;flex-direction:column;gap:8px;">'
        '<div class="kpi"><span class="kpi-label">EVENTOS HOJE</span>'
        '<span class="kpi-value">--</span></div>'
        '<div class="kpi"><span class="kpi-label">DIÁRIO</span>'
        '<span class="kpi-value">--</span></div>'
        '<div class="kpi"><span class="kpi-label">STREAK</span>'
        '<span class="kpi-value">--</span></div>'
        "</div></div>"
    )
    st.markdown(
        fallback_estado_inicial_html(
            titulo="HOJE · vault Bem-estar não configurado",
            descricao=(  # noqa: accent
                "Configure a variável <code>OUROBOROS_VAULT</code> apontando "
                "para a raiz do vault Obsidian compartilhado com o app mobile, "
                "ou crie um dos diretórios candidatos canônicos. Sem o vault, "
                "a captura rápida de humor e os mini-cards do dia ficam "
                "indisponíveis."
            ),
            skeleton_html=skeleton,
            cta_secao="hoje",
            sync_info=ler_sync_info(),
        ),
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Hero humor (formulário)
# ---------------------------------------------------------------------------


def _cores_sliders() -> dict[str, str]:
    return {
        "humor": CORES["superfluo"],  # pink
        "energia": CORES["info"],  # yellow
        "ansiedade": CORES["alerta"],  # orange
        "foco": CORES["neutro"],  # cyan
    }


def _slider_humor(rotulo: str, cor: str, key: str) -> int:
    """Renderiza um slider 1..5 com label colorido em monospace.

    Helper interno: substitui 4 blocos repetidos de ~12 linhas cada por
    chamada única. Reduz acoplamento e centraliza estilo do label.
    """
    st.markdown(
        f'<span class="slider-cor-tag" style="color:{cor};">{rotulo}</span>',
        unsafe_allow_html=True,
    )
    return st.slider(
        rotulo,
        min_value=1,
        max_value=5,
        value=int(st.session_state.get(key, 3)),
        key=key,
        label_visibility="collapsed",
    )


def _renderizar_hero_humor(
    vault_root: Path,
    hoje: date,
    pessoa_default: str,
) -> None:
    cores = _cores_sliders()
    st.markdown(
        minificar(
            f"""
            <div class="hero-humor-marker">
              <div class="hero-head">
                <h2 class="hero-titulo">Como você está agora?</h2>
                <span class="hero-data">{hoje.strftime("%A · %d %b")}</span>
              </div>
              <div class="hero-legend">
                4 sliders 1..5 · multi-tag · sono · medicação · frase do dia
              </div>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )

    with st.form(key="be_hoje_form_humor", clear_on_submit=False):
        col_h, col_e = st.columns(2)
        with col_h:
            humor = _slider_humor("humor", cores["humor"], _KEY_HUMOR)
            energia = _slider_humor("energia", cores["energia"], _KEY_ENERGIA)
        with col_e:
            ansiedade = _slider_humor("ansiedade", cores["ansiedade"], _KEY_ANSIEDADE)
            foco = _slider_humor("foco", cores["foco"], _KEY_FOCO)

        col_med, col_sono = st.columns(2)
        with col_med:
            medicacao = st.checkbox(
                "Medicação tomada hoje",
                value=bool(st.session_state.get(_KEY_MEDICACAO, False)),
                key=_KEY_MEDICACAO,
            )
        with col_sono:
            sono = st.number_input(
                "Horas de sono",
                min_value=0.0,
                max_value=24.0,
                step=0.5,
                value=float(st.session_state.get(_KEY_SONO, 7.0)),
                key=_KEY_SONO,
            )

        tags_atuais: list[str] = list(st.session_state.get(_KEY_TAGS, []))
        # Pílulas multi-seleção (UX-V-3.5): substitui multiselect tradicional
        # mantendo paridade visual com mockup 17-bem-estar-hoje.html.
        tags = st.pills(
            "Tags do momento",
            options=list(TAGS_CANONICAS),
            default=tags_atuais,
            selection_mode="multi",
            key=_KEY_TAGS,
        )

        frase = st.text_area(
            "Frase do dia (opcional)",
            value=str(st.session_state.get(_KEY_FRASE, "")),
            key=_KEY_FRASE,
            height=80,
            placeholder="ex.: manhã produtiva, sono ok, tomei medicação no horário",
        )

        registrar = st.form_submit_button("Registrar humor")

    if registrar:
        # Seletor de pessoa vive na coluna direita (card "Esse registro é
        # para…") via st.pills. Lemos do session_state na hora de gravar.
        pessoa_escolhida = str(st.session_state.get(_KEY_PARA, pessoa_default))
        if pessoa_escolhida not in {"pessoa_a", "pessoa_b", "casal"}:
            pessoa_escolhida = pessoa_default
        try:
            arquivo = escrever_registro(
                vault_root,
                hoje,
                humor=humor,
                energia=energia,
                ansiedade=ansiedade,
                foco=foco,
                medicacao=medicacao,
                horas_sono=float(sono),
                tags=tags or [],
                frase=frase,
                pessoa=pessoa_escolhida,
            )
            st.session_state[_KEY_FLASH] = (
                f"Humor registrado em {arquivo.name} "
                f"(humor {humor}/5, autor={pessoa_escolhida}). "
                "O cache foi atualizado."
            )
            st.rerun()
        except (ValueError, OSError) as exc:
            st.error(f"Falha ao registrar humor: {exc}")


# ---------------------------------------------------------------------------
# Coluna direita: 3 cards canônicos (UX-V-3.5)
# 1. Esse registro é para…  (st.pills 3 opções)
# 2. Status do casal · 7 dias (humor médio Pessoa A + Pessoa B + barras)
# 3. Próximos · alarmes & tarefas (5 itens agregados)
# ---------------------------------------------------------------------------


def _carregar_cache_items(vault_root: Path, schema: str) -> list[dict[str, Any]]:
    """Lê cache ``<vault>/.ouroboros/cache/<schema>.json`` retornando ``items``.

    Padrão canônico do mobile_cache._base.varrer_schema (chave ``items``).
    Usado por ``alarmes``, ``tarefas``, ``eventos``, ``contadores``.
    """
    arquivo = vault_root / ".ouroboros" / "cache" / f"{schema}.json"
    if not arquivo.exists():
        return []
    try:
        payload = json.loads(arquivo.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    items = payload.get("items") or []
    return items if isinstance(items, list) else []


def _carregar_humor_heatmap(vault_root: Path) -> dict[str, Any]:
    """Lê ``humor-heatmap.json`` (schema próprio, chave ``celulas``)."""
    arquivo = vault_root / ".ouroboros" / "cache" / "humor-heatmap.json"
    if not arquivo.exists():
        return {}
    try:
        return json.loads(arquivo.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _renderizar_coluna_direita(
    vault_root: Path,
    hoje: date,
    pessoa_default: str,
) -> None:
    """Renderiza os 3 cards canônicos da coluna direita."""
    _card_para_quem(pessoa_default)
    _card_status_casal(vault_root, hoje)
    _card_proximos(vault_root, hoje)


def _card_para_quem(pessoa_default: str) -> None:
    """Card 1 — seletor "Esse registro é para…" via st.pills (single).

    Substitui o ``selectbox`` que estava dentro do form do hero. Estado
    persiste em ``st.session_state[_KEY_PARA]`` e é lido no submit.
    """
    st.markdown(
        minificar(
            '<div class="bloco-para-marker">'
            '<h3 class="bloco-para-titulo">Esse registro é para…</h3>'
            "</div>"
        ),
        unsafe_allow_html=True,
    )
    pessoas_validas = ["pessoa_a", "pessoa_b", "casal"]
    rotulos = {
        "pessoa_a": "para mim",
        "pessoa_b": "para Pessoa B",
        "casal": "para o casal",
    }
    atual = str(st.session_state.get(_KEY_PARA, pessoa_default))
    if atual not in pessoas_validas:
        atual = pessoa_default if pessoa_default in pessoas_validas else "pessoa_a"
    st.pills(
        "Esse registro é para",
        options=pessoas_validas,
        default=atual,
        selection_mode="single",
        format_func=lambda v: rotulos.get(v, v),
        key=_KEY_PARA,
        label_visibility="collapsed",
    )


def _card_status_casal(vault_root: Path, hoje: date) -> None:
    """Card 2 — Status do casal nos últimos 7 dias.

    Lê ``humor-heatmap.json`` (campo ``celulas``) e calcula:
      * média de humor por pessoa nos últimos 7 dias
      * número de registros
      * lista de 7 valores (um por dia, 0..5; 0=sem registro) para barras
    """
    payload = _carregar_humor_heatmap(vault_root)
    celulas = payload.get("celulas") or []

    inicio = hoje - timedelta(days=6)
    pessoas_cfg: list[tuple[str, str, str]] = [
        ("pessoa_a", "pessoa A · você", CORES.get("destaque", "#bd93f9")),
        ("pessoa_b", "pessoa B", CORES.get("superfluo", "#ff79c6")),
    ]

    cards_html: list[str] = []
    for pid, rotulo, cor in pessoas_cfg:
        valores: list[int] = [0] * 7
        soma = 0
        registros = 0
        for cel in celulas:
            if cel.get("autor") != pid:
                continue
            ds = str(cel.get("data") or "")
            try:
                d = date.fromisoformat(ds)
            except ValueError:
                continue
            if not (inicio <= d <= hoje):
                continue
            humor = cel.get("humor")
            if not isinstance(humor, int):
                continue
            idx = (d - inicio).days
            if 0 <= idx < 7:
                valores[idx] = humor
                soma += humor
                registros += 1
        media = round(soma / registros, 1) if registros else 0.0
        media_str = f"{media:.1f}" if registros else "—"
        barras = "".join(f'<span class="pmini-bar" style="--p:{v};"></span>' for v in valores)
        cards_html.append(
            f'<div class="pessoa-card" style="--cor:{cor};">'
            f'  <div class="pnome">{rotulo}</div>'
            f'  <div class="pmedia">{media_str}'
            f'<span class="pmedia-suffix">/5</span></div>'
            f'  <div class="pdetalhe">{registros} registro'
            f"{'s' if registros != 1 else ''} · 7d</div>"
            f'  <div class="pmini">{barras}</div>'
            f"</div>"
        )

    st.markdown(
        minificar(
            '<div class="bloco-status">'
            "  <h3>Status do casal · últimos 7 dias</h3>"
            f'  <div class="casal-grid">{"".join(cards_html)}</div>'
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def _card_proximos(vault_root: Path, hoje: date) -> None:
    """Card 3 — Próximos alarmes & tarefas.

    Agrega até 5 itens combinando: alarmes ativos + tarefas pendentes
    (concluida=False, prazo>=hoje) + próximos eventos + 1 contador ativo.
    Cada linha tem rótulo de tipo + horário/prazo + título + tag.
    """
    alarmes = _carregar_cache_items(vault_root, "alarmes")
    tarefas = _carregar_cache_items(vault_root, "tarefas")
    eventos = _carregar_cache_items(vault_root, "eventos")
    contadores = _carregar_cache_items(vault_root, "contadores")

    cor_alarme = CORES.get("alerta", "#ffb86c")
    cor_tarefa = CORES.get("neutro", "#8be9fd")
    cor_evento = CORES.get("superfluo", "#ff79c6")
    cor_contador = CORES.get("essencial", "#50fa7b")

    linhas: list[str] = []

    # Alarmes ativos (até 2)
    for al in alarmes:
        if not al.get("ativo", True):
            continue
        horario = str(al.get("horario") or "—")
        titulo = str(al.get("categoria") or al.get("id") or "alarme")
        tag = "diário" if al.get("recorrencia") else (al.get("autor") or "")
        linhas.append(_evt_html("alarme", cor_alarme, horario, titulo, str(tag)))
        if sum(1 for ln in linhas if "alarme" in ln) >= 2:
            break

    # Tarefas pendentes com prazo hoje ou futuro (até 2)
    iso_hoje = hoje.isoformat()
    cont_tarefa = 0
    for tr in tarefas:
        if tr.get("concluida"):
            continue
        prazo = str(tr.get("prazo") or "")
        if prazo and prazo < iso_hoje:
            continue
        titulo = str(tr.get("titulo") or "tarefa")
        hora = "hoje" if prazo == iso_hoje or not prazo else prazo
        autor = str(tr.get("autor") or "")
        rotulo_autor = {
            "pessoa_a": "mim",
            "pessoa_b": "Pessoa B",
            "casal": "casal",
        }.get(autor, autor)
        linhas.append(_evt_html("tarefa", cor_tarefa, hora, titulo, rotulo_autor))
        cont_tarefa += 1
        if cont_tarefa >= 2:
            break

    # Próximo evento futuro (1)
    for ev in sorted(eventos, key=lambda e: str(e.get("data") or "")):
        ds = str(ev.get("data") or "")
        if ds < iso_hoje:
            continue
        lugar = str(ev.get("lugar") or ev.get("categoria") or "evento")
        bairro = str(ev.get("bairro") or "")
        autor = str(ev.get("autor") or "")
        rotulo_autor = {
            "pessoa_a": "mim",
            "pessoa_b": "Pessoa B",
            "casal": "casal",
        }.get(autor, autor)
        tag = bairro or rotulo_autor
        linhas.append(_evt_html("evento", cor_evento, ds[5:] if len(ds) >= 10 else ds, lugar, tag))
        break

    # 1 contador ativo (mostra dias decorridos desde data_inicio/ultima_reset)
    for ct in contadores:
        nome = str(ct.get("nome") or "contador")
        ref = ct.get("ultima_reset") or ct.get("data_inicio") or ""
        try:
            d_ref = date.fromisoformat(str(ref))
            dias = (hoje - d_ref).days
            hora = f"{dias}d" if dias >= 0 else "—"
        except ValueError:
            hora = "—"
        categoria = str(ct.get("categoria") or "")
        linhas.append(_evt_html("contador", cor_contador, hora, nome, categoria))
        break

    if not linhas:
        linhas.append('<div class="evt-vazio">Nada pendente nos próximos dias.</div>')

    st.markdown(
        minificar(
            '<div class="bloco-proximos">'
            "  <h3>Próximos · alarmes & tarefas</h3>"
            f'  <div class="evt-lista">{"".join(linhas[:5])}</div>'
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def _evt_html(tipo: str, cor: str, hora: str, titulo: str, tag: str) -> str:
    """Linha de evento canônica do mockup 17-bem-estar-hoje."""
    return (
        f'<div class="evt">'
        f'  <span class="evt-tipo" style="--cor:{cor};">{tipo}</span>'
        f'  <span class="evt-hora">{hora}</span>'
        f'  <span class="evt-titulo">{titulo}</span>'
        f'  <span class="evt-tag">{tag}</span>'
        f"</div>"
    )


# ---------------------------------------------------------------------------
# CSS local
# ---------------------------------------------------------------------------


# CSS dedicado: src/dashboard/css/paginas/be_hoje.css (UX-M-02.D residual).
# "O dia bem registrado é o dia bem vivido." -- princípio do diarismo
