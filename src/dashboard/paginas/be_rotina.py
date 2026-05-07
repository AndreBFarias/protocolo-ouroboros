"""Cluster Bem-estar -- página "Rotina" (UX-RD-19).

Visualização de alarmes, tarefas e contadores recorrentes a partir de
``<vault>/.ouroboros/rotina.toml`` (ou ``~/.ouroboros/rotina.toml`` no
fallback). Lê o arquivo, parseia via :mod:`tomllib` e renderiza três
seções como cartões agrupados por horário/categoria.

Esta página é o lado visual do par ``Editor TOML`` (UX-RD-19): aquele
edita o arquivo, esta materializa em UI o que o arquivo declara. Se
``rotina.toml`` ainda não existe, a página exibe um aviso explicando
que o usuário deve criar via Editor TOML antes.

Mockup-fonte: ``novo-mockup/mockups/20-rotina.html``.

Lições UX-RD aplicadas:

* HTML emitido via :func:`minificar` (UX-RD-04).
* Cores via ``CORES`` em :mod:`src.dashboard.tema` -- nunca hex literal.
* Fallback graceful: rotina.toml ausente vira mensagem clara.
* Contrato uniforme ``renderizar(dados, periodo, pessoa, ctx)``.
"""

from __future__ import annotations

import tomllib
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from src.dashboard.componentes.html_utils import minificar
from src.dashboard.tema import CORES
from src.mobile_cache.varrer_vault import descobrir_vault_root

_DIAS_LABEL = {
    "seg": "S",
    "ter": "T",
    "qua": "Q",
    "qui": "Q",
    "sex": "S",
    "sab": "S",
    "dom": "D",
}
_ORDEM_DIAS = ("seg", "ter", "qua", "qui", "sex", "sab", "dom")


def _resolver_caminho_rotina() -> Path:
    vault_root = descobrir_vault_root()
    base = vault_root if vault_root is not None else Path.home()
    return base / ".ouroboros" / "rotina.toml"


def _ler_rotina(caminho: Path) -> dict[str, Any] | None:
    if not caminho.exists():
        return None
    try:
        return tomllib.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return None


def _carregar_rotinas_toml(vault_root: Path | None) -> dict[str, list[dict[str, Any]]]:
    """Lê todos os ``*.toml`` em ``<vault>/.ouroboros/rotina/`` e agrega.

    Retorna ``{"alarmes": [...], "tarefas": [...], "contadores": [...]}``.
    Quando o diretório não existe ou está vazio, retorna estrutura vazia.

    Padrão ``(o)`` (subregra retrocompatível): este formato (diretório com
    múltiplos arquivos) coexiste com ``rotina.toml`` único legado, sem
    invalidar nenhum dos dois.
    """
    if vault_root is None:
        return {"alarmes": [], "tarefas": [], "contadores": []}
    pasta = vault_root / ".ouroboros" / "rotina"
    if not pasta.exists() or not pasta.is_dir():
        return {"alarmes": [], "tarefas": [], "contadores": []}
    alarmes: list[dict[str, Any]] = []
    tarefas: list[dict[str, Any]] = []
    contadores: list[dict[str, Any]] = []
    for arq in sorted(pasta.glob("*.toml")):
        try:
            d = tomllib.loads(arq.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError):
            continue
        if isinstance(d.get("alarme"), list):
            alarmes.extend(x for x in d["alarme"] if isinstance(x, dict))
        if isinstance(d.get("tarefa"), list):
            tarefas.extend(x for x in d["tarefa"] if isinstance(x, dict))
        if isinstance(d.get("contador"), list):
            contadores.extend(x for x in d["contador"] if isinstance(x, dict))
    return {"alarmes": alarmes, "tarefas": tarefas, "contadores": contadores}


def _proximo_alarme(alarmes: list[dict[str, Any]]) -> str:
    """Retorna a próxima hora futura (HH:MM) ou ``--`` se nada agendado."""
    agora = datetime.now().strftime("%H:%M")
    horas_validas = [
        str(a.get("hora", "")).strip()
        for a in alarmes
        if isinstance(a, dict) and a.get("hora")
    ]
    futuros = [h for h in horas_validas if h > agora]
    if futuros:
        return min(futuros)
    if horas_validas:
        return min(horas_validas)
    return "--"


def _kpis_rotina_html(dados: dict[str, list[dict[str, Any]]]) -> str:
    """Renderiza grade de 4 KPIs (tarefas hoje, próximo alarme, streak, ativos)."""
    tarefas = dados.get("tarefas", [])
    alarmes = dados.get("alarmes", [])
    contadores = dados.get("contadores", [])
    n_tarefas = len(tarefas)
    n_concluidas = sum(1 for t in tarefas if t.get("concluida"))
    n_a_fazer = max(n_tarefas - n_concluidas, 0)
    proximo = _proximo_alarme(alarmes)
    streak = max(
        (int(c.get("streak_dias", 0)) for c in contadores if isinstance(c, dict)),
        default=0,
    )
    n_alarmes = len(alarmes)
    return minificar(
        f"""
        <div class="kpi-grid" style="grid-template-columns:repeat(4,1fr);
             gap:10px;margin-bottom:14px;">
          <div class="kpi">
            <span class="kpi-label">TAREFAS HOJE</span>
            <span class="kpi-value">{n_concluidas}/{n_tarefas}</span>
            <span class="kpi-sub">{n_a_fazer} a fazer</span>
          </div>
          <div class="kpi">
            <span class="kpi-label">PRÓXIMO ALARME</span>
            <span class="kpi-value" style="color:var(--accent-orange);">{proximo}</span>
            <span class="kpi-sub">próximas horas</span>
          </div>
          <div class="kpi">
            <span class="kpi-label">STREAK ATIVO</span>
            <span class="kpi-value" style="color:var(--accent-green);">{streak} dias</span>
            <span class="kpi-sub">contador top</span>
          </div>
          <div class="kpi">
            <span class="kpi-label">ALARMES ATIVOS</span>
            <span class="kpi-value">{n_alarmes}</span>
            <span class="kpi-sub">configurados</span>
          </div>
        </div>
        """
    )


def _alarme_row_html(a: dict[str, Any]) -> str:
    """Linha de alarme estilo mockup (hora, titulo, meta, toggle visual)."""
    hora = str(a.get("hora", "--:--")).strip()
    titulo = str(a.get("nome") or a.get("titulo") or a.get("id") or "alarme").strip()
    dias = a.get("dias") or []
    if not isinstance(dias, list):
        dias = []
    meta_dias = " · ".join(str(d) for d in dias) if dias else "diário"
    obs = str(a.get("obs") or "").strip()
    meta = meta_dias + (f" · {obs}" if obs else "")
    ativo = bool(a.get("ativo", True))
    toggle_estado = "on" if ativo else ""
    bg_toggle = CORES["destaque"] if ativo else CORES["fundo_inset"]
    return (
        f'<div style="display:grid;grid-template-columns:auto 1fr auto;gap:10px;'
        f'align-items:center;padding:10px;background:{CORES["fundo_inset"]};'
        f'border:1px solid {CORES["texto_sec"]}33;border-left:3px solid '
        f'{CORES["destaque"]};border-radius:4px;margin-bottom:6px;">'
        f'  <div style="font-family:ui-monospace,monospace;font-size:20px;'
        f'              font-weight:500;color:{CORES["texto"]};line-height:1;">{hora}</div>'
        f'  <div style="display:flex;flex-direction:column;gap:2px;min-width:0;">'
        f'    <span style="font-size:13px;color:{CORES["texto"]};'
        f'font-weight:500;overflow:hidden;text-overflow:ellipsis;'
        f'white-space:nowrap;">{titulo}</span>'
        f'    <span style="font-family:ui-monospace,monospace;font-size:10px;'
        f'                  color:{CORES["texto_muted"]};">{meta}</span>'
        f"  </div>"
        f'  <div class="alarme-toggle {toggle_estado}" style="position:relative;'
        f'width:36px;height:20px;background:{bg_toggle};border-radius:999px;'
        f'border:1px solid {CORES["texto_sec"]}33;"></div>'
        f"</div>"
    )


def _tarefa_row_html(t: dict[str, Any]) -> str:
    """Linha de tarefa estilo mockup (checkbox, titulo, meta de prioridade)."""
    titulo = str(t.get("nome") or t.get("titulo") or t.get("id") or "tarefa").strip()
    prio = str(t.get("prioridade") or t.get("prio") or "media").strip().lower()
    cor_prio = {
        "alta": "var(--accent-red)",
        "media": "var(--accent-yellow)",
        "média": "var(--accent-yellow)",
        "baixa": CORES["texto_muted"],
    }.get(prio, CORES["texto_muted"])
    rotulo_prio = {
        "alta": "alta",
        "media": "média",
        "média": "média",
        "baixa": "baixa",
    }.get(prio, prio)
    contexto = str(t.get("contexto") or t.get("tipo") or "").strip()
    duracao = t.get("duracao_min")
    duracao_str = f"~{duracao}min" if isinstance(duracao, (int, float)) else ""
    extras = " · ".join(m for m in (contexto, duracao_str) if m)
    concluida = bool(t.get("concluida"))
    classe_check = "on" if concluida else ""
    estilo_titulo = (
        f"text-decoration:line-through;color:{CORES['texto_muted']};"
        if concluida
        else f"color:{CORES['texto']};"
    )
    fundo_check = CORES["destaque"] if concluida else "transparent"
    return (
        f'<div style="display:grid;grid-template-columns:auto 1fr;gap:10px;'
        f'align-items:center;padding:10px;background:{CORES["fundo_inset"]};'
        f'border:1px solid {CORES["texto_sec"]}33;border-radius:4px;margin-bottom:6px;'
        f'{"opacity:0.55;" if concluida else ""}">'
        f'  <div class="checkbox {classe_check}" style="width:18px;height:18px;'
        f'border:1.5px solid {cor_prio};border-radius:3px;flex-shrink:0;'
        f'background:{fundo_check};"></div>'
        f'  <div style="display:flex;flex-direction:column;gap:2px;min-width:0;">'
        f'    <span style="font-size:13px;{estilo_titulo}">{titulo}</span>'
        f'    <span style="font-family:ui-monospace,monospace;font-size:10px;'
        f'                  color:{CORES["texto_muted"]};">'
        f'      <span style="color:{cor_prio};">{rotulo_prio}</span>'
        f'      {(" · " + extras) if extras else ""}'
        f"    </span>"
        f"  </div>"
        f"</div>"
    )


def _contador_row_html(c: dict[str, Any]) -> str:
    """Linha de contador estilo mockup (titulo, valor, barra, meta)."""
    titulo = str(c.get("nome") or c.get("titulo") or c.get("id") or "contador").strip()
    tipo = str(c.get("tipo") or "streak").strip()
    streak = int(c.get("streak_dias", 0))
    meta_valor = c.get("meta")
    unidade = str(c.get("unidade") or "dias").strip()
    if isinstance(meta_valor, (int, float)) and meta_valor > 0:
        progresso = min(100, int((streak / meta_valor) * 100))
        valor_str = f"{streak}/{int(meta_valor)}"
        meta_legenda = f"meta · {meta_valor} {unidade}"
    else:
        progresso = min(100, streak)
        valor_str = str(streak)
        meta_legenda = "sem meta"
    reset = str(c.get("reset") or "diário").strip()
    return (
        f'<div style="padding:14px;background:{CORES["fundo_inset"]};'
        f'border:1px solid {CORES["texto_sec"]}33;border-left:3px solid '
        f'{CORES["destaque"]};border-radius:4px;display:flex;flex-direction:column;'
        f'gap:8px;margin-bottom:8px;">'
        f'  <div style="display:flex;align-items:baseline;justify-content:space-between;">'
        f'    <span style="font-size:13px;color:{CORES["texto"]};font-weight:500;">{titulo}</span>'
        f'    <span style="font-family:ui-monospace,monospace;font-size:10px;'
        f'                  color:{CORES["destaque"]};letter-spacing:0.10em;'
        f'                  text-transform:uppercase;">{tipo}</span>'
        f"  </div>"
        f'  <div style="font-family:ui-monospace,monospace;font-size:28px;'
        f'              font-weight:500;color:{CORES["destaque"]};line-height:1;">'
        f'    {valor_str}'
        f'    <small style="font-size:13px;color:{CORES["texto_muted"]};'
        f'                   font-weight:400;"> {unidade}</small>'
        f"  </div>"
        f'  <div style="height:6px;background:{CORES["fundo"]};border-radius:999px;'
        f'overflow:hidden;position:relative;">'
        f'    <span style="position:absolute;left:0;top:0;bottom:0;width:{progresso}%;'
        f'background:{CORES["destaque"]};border-radius:999px;display:block;"></span>'
        f"  </div>"
        f'  <div style="display:flex;justify-content:space-between;'
        f'              font-family:ui-monospace,monospace;font-size:10px;'
        f'              color:{CORES["texto_muted"]};">'
        f'    <span>{meta_legenda}</span><span>reset {reset}</span>'
        f"  </div>"
        f"</div>"
    )


def _coluna_html(titulo: str, contagem: int, conteudo_rows: str) -> str:
    """Encapsula uma coluna em card com header (titulo + contagem)."""
    return (
        f'<div style="background:{CORES["card_fundo"]};border:1px solid '
        f'{CORES["texto_sec"]}33;border-radius:6px;padding:14px;display:flex;'
        f'flex-direction:column;">'
        f'  <div style="display:flex;align-items:center;justify-content:space-between;'
        f'              margin-bottom:12px;padding-bottom:8px;'
        f'              border-bottom:1px solid {CORES["texto_sec"]}33;">'
        f'    <span style="font-family:ui-monospace,monospace;font-size:12px;'
        f'                  letter-spacing:0.10em;text-transform:uppercase;'
        f'                  color:{CORES["destaque"]};font-weight:600;">'
        f'      {titulo} · {contagem}</span>'
        f"  </div>"
        f'  <div style="display:flex;flex-direction:column;gap:6px;">{conteudo_rows}</div>'
        f"</div>"
    )


def _page_header_html(qtd_alarmes: int, qtd_tarefas: int, qtd_contadores: int) -> str:
    """UX-U-03: usa helper canônico ``componentes/page_header``."""
    from src.dashboard.componentes.page_header import renderizar_page_header

    return renderizar_page_header(
        titulo="ROTINA",
        subtitulo=(
            "Alarmes recorrentes, tarefas e contadores diários. "
            "Persiste em .ouroboros/rotina.toml."
        ),
        sprint_tag="UX-RD-19",
        pills=[{
            "texto": (
                f"{qtd_alarmes} alarmes · {qtd_tarefas} tarefas · "
                f"{qtd_contadores} contadores"
            ),
            "tipo": "generica",
        }],
    )


def _alarme_card_html(alarme: dict[str, Any]) -> str:
    nome = str(alarme.get("nome") or alarme.get("id") or "alarme").strip()
    hora = str(alarme.get("hora") or "--:--").strip()
    dias = alarme.get("dias") or []
    if not isinstance(dias, list):
        dias = []
    chips_dias = "".join(
        f'<span style="display:inline-block;width:18px;height:18px;'
        f"line-height:18px;text-align:center;font-family:ui-monospace,monospace;"
        f"font-size:10px;border-radius:3px;margin-right:2px;"
        f'background:{CORES["destaque"] if d in dias else CORES["fundo_inset"]};'
        f'color:{CORES["fundo"] if d in dias else CORES["texto_muted"]};">'
        f"{_DIAS_LABEL.get(d, d[:1].upper())}</span>"
        for d in _ORDEM_DIAS
    )
    tags = alarme.get("tags") or []
    if not isinstance(tags, list):
        tags = []
    chips_tags = "".join(
        f'<span style="display:inline-block;background:{CORES["fundo_inset"]};'
        f'color:{CORES["texto_sec"]};font-family:ui-monospace,monospace;'
        f"font-size:10px;padding:2px 8px;border-radius:10px;margin-right:4px;"
        f'border:1px solid {CORES["texto_sec"]}33;">'
        f"{tag}</span>"
        for tag in tags
    )
    return (
        f'<div style="background:{CORES["card_fundo"]};'
        f'border:1px solid {CORES["texto_sec"]}33;border-radius:6px;'
        f'padding:14px;margin-bottom:10px;">'
        f'  <div style="display:flex;justify-content:space-between;'
        f'              align-items:center;margin-bottom:8px;">'
        f'    <strong style="color:{CORES["texto"]};font-size:14px;">{nome}</strong>'
        f'    <span style="font-family:ui-monospace,monospace;font-size:18px;'
        f'                  color:{CORES["destaque"]};">{hora}</span>'
        f"  </div>"
        f'  <div style="margin-bottom:6px;">{chips_dias}</div>'
        f"  <div>{chips_tags}</div>"
        f"</div>"
    )


def _tarefa_card_html(tarefa: dict[str, Any]) -> str:
    nome = str(tarefa.get("nome") or tarefa.get("id") or "tarefa").strip()
    duracao = tarefa.get("duracao_min")
    duracao_str = f"~{duracao}min" if isinstance(duracao, (int, float)) else "--"
    tipo = str(tarefa.get("tipo") or "geral").strip()
    return (
        f'<div style="background:{CORES["card_fundo"]};'
        f'border:1px solid {CORES["texto_sec"]}33;border-radius:6px;'
        f'padding:12px 14px;margin-bottom:8px;'
        f'display:flex;align-items:center;gap:10px;">'
        f'  <div style="width:14px;height:14px;'
        f'              border:1.5px solid {CORES["destaque"]};'
        f'              border-radius:3px;flex-shrink:0;"></div>'
        f'  <div style="flex:1;color:{CORES["texto"]};font-size:13px;">{nome}'
        f'    <span style="font-family:ui-monospace,monospace;font-size:10px;'
        f'                  color:{CORES["texto_muted"]};margin-left:8px;">{duracao_str}</span>'
        f"  </div>"
        f'  <span style="font-family:ui-monospace,monospace;font-size:10px;'
        f'                color:{CORES["texto_muted"]};">tipo: {tipo}</span>'
        f"</div>"
    )


def _contador_card_html(contador: dict[str, Any]) -> str:
    nome = str(contador.get("nome") or contador.get("id") or "contador").strip()
    meta = contador.get("meta")
    meta_str = str(meta) if meta is not None else "--"
    reset = str(contador.get("reset") or "diario").strip()
    return (
        f'<div style="background:{CORES["card_fundo"]};'
        f'border:1px solid {CORES["texto_sec"]}33;border-radius:6px;'
        f'padding:12px 14px;margin-bottom:8px;">'
        f'  <div style="color:{CORES["texto"]};font-size:14px;">{nome}</div>'
        f'  <div style="font-family:ui-monospace,monospace;font-size:11px;'
        f'                color:{CORES["texto_muted"]};margin-top:4px;">'
        f"meta: {meta_str} · reset {reset}"
        f"  </div>"
        f"</div>"
    )


def renderizar(
    dados: dict[str, pd.DataFrame],
    periodo: str,
    pessoa: str,
    ctx: dict | None = None,
) -> None:
    """Renderiza Bem-estar / Rotina (UX-T-20)."""
    from src.dashboard.componentes.topbar_actions import renderizar_grupo_acoes
    renderizar_grupo_acoes([
        {"label": "Hoje", "glyph": "calendar",
         "href": "?cluster=Bem-estar&tab=Hoje"},
        {"label": "Novo", "primary": True, "glyph": "plus",
         "title": "Wizard alarme/tarefa/contador"},
    ])

    del dados, periodo, pessoa, ctx

    # Caminho 1 (UX-V-2.10): diretório <vault>/.ouroboros/rotina/*.toml.
    # Caminho 2 (legado UX-RD-19): arquivo único <vault>/.ouroboros/rotina.toml.
    # Subregra retrocompatível -- padrão (o).
    vault_root = descobrir_vault_root()
    rotinas_dir = _carregar_rotinas_toml(vault_root)
    caminho = _resolver_caminho_rotina()
    cfg = _ler_rotina(caminho)

    alarmes_legado = cfg.get("alarme", []) if cfg else []
    tarefas_legado = cfg.get("tarefa", []) if cfg else []
    contadores_legado = cfg.get("contador", []) if cfg else []

    if not isinstance(alarmes_legado, list):
        alarmes_legado = []
    if not isinstance(tarefas_legado, list):
        tarefas_legado = []
    if not isinstance(contadores_legado, list):
        contadores_legado = []

    # União: formato novo precede legado (mais recente vence visualmente).
    alarmes = list(rotinas_dir["alarmes"]) + [
        a for a in alarmes_legado if isinstance(a, dict)
    ]
    tarefas = list(rotinas_dir["tarefas"]) + [
        t for t in tarefas_legado if isinstance(t, dict)
    ]
    contadores = list(rotinas_dir["contadores"]) + [
        c for c in contadores_legado if isinstance(c, dict)
    ]

    tem_dados_novos = bool(
        rotinas_dir["alarmes"] or rotinas_dir["tarefas"] or rotinas_dir["contadores"]
    )

    st.markdown(
        _page_header_html(len(alarmes), len(tarefas), len(contadores)),
        unsafe_allow_html=True,
    )

    # KPIs renderizam quando há qualquer dado (novo ou legado).
    if alarmes or tarefas or contadores:
        st.markdown(
            _kpis_rotina_html(
                {"alarmes": alarmes, "tarefas": tarefas, "contadores": contadores}
            ),
            unsafe_allow_html=True,
        )

    # Quando o diretório novo existe, renderizar 3 colunas estilo mockup.
    if tem_dados_novos:
        col_alarmes, col_tarefas, col_contadores = st.columns(
            [1, 1, 1], gap="medium"
        )
        with col_alarmes:
            rows_a = "".join(_alarme_row_html(a) for a in alarmes) or (
                f'<div style="color:{CORES["texto_muted"]};font-size:12px;">'
                "Nenhum alarme.</div>"
            )
            st.markdown(
                minificar(_coluna_html("Alarmes", len(alarmes), rows_a)),
                unsafe_allow_html=True,
            )
        with col_tarefas:
            rows_t = "".join(_tarefa_row_html(t) for t in tarefas) or (
                f'<div style="color:{CORES["texto_muted"]};font-size:12px;">'
                "Nenhuma tarefa.</div>"
            )
            st.markdown(
                minificar(_coluna_html("Tarefas Hoje", len(tarefas), rows_t)),
                unsafe_allow_html=True,
            )
        with col_contadores:
            rows_c = "".join(_contador_row_html(c) for c in contadores) or (
                f'<div style="color:{CORES["texto_muted"]};font-size:12px;">'
                "Nenhum contador.</div>"
            )
            st.markdown(
                minificar(_coluna_html("Contadores", len(contadores), rows_c)),
                unsafe_allow_html=True,
            )
        return

    if cfg is None:
        from src.dashboard.componentes.ui import (
            fallback_estado_inicial_html,
            ler_sync_info,
        )
        skeleton = (
            '<div style="display:grid;grid-template-columns:repeat(4,1fr);'
            'gap:10px;margin-bottom:14px;">'
            '<div class="kpi"><span class="kpi-label">ALARMES</span>'
            '<span class="kpi-value">--</span></div>'
            '<div class="kpi"><span class="kpi-label">TAREFAS</span>'
            '<span class="kpi-value">--</span></div>'
            '<div class="kpi"><span class="kpi-label">CONTADORES</span>'
            '<span class="kpi-value">--</span></div>'
            '<div class="kpi"><span class="kpi-label">STREAK</span>'
            '<span class="kpi-value">--</span></div>'
            '</div>'
            '<div style="display:grid;grid-template-columns:1.2fr 1fr 0.8fr;'
            'gap:14px;">'
            '<div><span class="skel-bloco" style="width:40%;height:0.8em;'
            'margin-bottom:8px;"></span>'
            '<div style="display:flex;flex-direction:column;gap:6px;">'
            '<span class="skel-bloco" style="width:90%;"></span>'
            '<span class="skel-bloco" style="width:70%;"></span>'
            '</div></div>'
            '<div><span class="skel-bloco" style="width:40%;height:0.8em;'
            'margin-bottom:8px;"></span>'
            '<div style="display:flex;flex-direction:column;gap:6px;">'
            '<span class="skel-bloco" style="width:85%;"></span>'
            '<span class="skel-bloco" style="width:75%;"></span>'
            '</div></div>'
            '<div><span class="skel-bloco" style="width:50%;height:0.8em;'
            'margin-bottom:8px;"></span>'
            '<div style="display:flex;flex-direction:column;gap:6px;">'
            '<span class="skel-bloco" style="width:80%;"></span>'
            '<span class="skel-bloco" style="width:60%;"></span>'
            '</div></div>'
            '</div>'
        )
        st.markdown(
            fallback_estado_inicial_html(
                titulo="ROTINA · sem configuração ainda",
                descricao=(
                    "Alarmes, tarefas recorrentes e contadores diários são "
                    "definidos em <code>privacidade/rotina.toml</code>. Use a "
                    "aba <code>Editor TOML</code> ao lado para criar a "
                    "configuração inicial -- ou edite o arquivo direto no "
                    "app mobile, que sincroniza com o vault."
                ),
                skeleton_html=skeleton,
                cta_label="Configure pelo Editor TOML ou pelo app mobile",
                cta_secao="rotina",
                sync_info=ler_sync_info(),
            ),
            unsafe_allow_html=True,
        )
        return

    col_alarmes, col_tarefas, col_contadores = st.columns([1.2, 1, 0.8], gap="large")

    with col_alarmes:
        st.markdown(
            f'<h3 style="font-family:ui-monospace,monospace;font-size:11px;'
            f'letter-spacing:0.10em;text-transform:uppercase;'
            f'color:{CORES["texto_muted"]};margin:0 0 12px;">Alarmes</h3>',
            unsafe_allow_html=True,
        )
        if not alarmes:
            st.info("Nenhum alarme configurado.")
        else:
            html = "".join(_alarme_card_html(a) for a in alarmes if isinstance(a, dict))
            st.markdown(minificar(html), unsafe_allow_html=True)

    with col_tarefas:
        st.markdown(
            f'<h3 style="font-family:ui-monospace,monospace;font-size:11px;'
            f'letter-spacing:0.10em;text-transform:uppercase;'
            f'color:{CORES["texto_muted"]};margin:0 0 12px;">Tarefas</h3>',
            unsafe_allow_html=True,
        )
        if not tarefas:
            st.info("Nenhuma tarefa configurada.")
        else:
            html = "".join(_tarefa_card_html(t) for t in tarefas if isinstance(t, dict))
            st.markdown(minificar(html), unsafe_allow_html=True)

    with col_contadores:
        st.markdown(
            f'<h3 style="font-family:ui-monospace,monospace;font-size:11px;'
            f'letter-spacing:0.10em;text-transform:uppercase;'
            f'color:{CORES["texto_muted"]};margin:0 0 12px;">Contadores</h3>',
            unsafe_allow_html=True,
        )
        if not contadores:
            st.info("Nenhum contador configurado.")
        else:
            html = "".join(_contador_card_html(c) for c in contadores if isinstance(c, dict))
            st.markdown(minificar(html), unsafe_allow_html=True)


# "A rotina é a coluna vertebral da liberdade." -- Friedrich Nietzsche
