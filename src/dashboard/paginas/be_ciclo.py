"""Cluster Bem-estar -- pagina "Ciclo" (UX-V-2.13).

Visualização do ciclo menstrual com anel SVG circular de 28 segmentos
coloridos por fase (Menstrual, Folicular, Fértil, Lútea), dia atual
destacado, sintomas registrados hoje (escala 0-3 com dots), 4 cards
canônicos de fase e cruzamento ciclo x humor. Página é opt-in: respeita
a flag ``ciclo`` em ``<vault>/.ouroboros/privacidade.toml`` quando
existe, e exibe placeholder informativo quando o cache está vazio
(fallback V-03 preservado).

Mockup-fonte: ``novo-mockup/mockups/25-ciclo.html``.

Lições UX-RD aplicadas:

* HTML emitido via :func:`minificar` (UX-RD-04).
* Cores via tokens ``--accent-*`` em :mod:`components.css` -- nunca hex literal
  no Python; o SVG usa hex apenas porque ``stroke`` inline não resolve
  ``var()`` em todos os browsers Streamlit-embedded.
* Fallback graceful: cache vazio ou toggle off vira aviso, sem crash.
* Contrato uniforme ``renderizar(dados, periodo, pessoa, ctx)``.
"""

from __future__ import annotations

import json
import math
import tomllib
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from src.dashboard.componentes.html_utils import minificar
from src.dashboard.componentes.ui import carregar_css_pagina
from src.mobile_cache.varrer_vault import descobrir_vault_root

# ---------------------------------------------------------------------------
# Constantes canônicas (alinhadas ao mockup 25-ciclo.html)
# ---------------------------------------------------------------------------

TOTAL_DIAS_CICLO = 28

# Janelas de fase no padrão do mockup: d 1-5 menstrual, d 6-13 folicular,
# d 14-16 fértil, d 17-28 lútea. Cores em hex porque viajam direto no
# atributo ``stroke`` do SVG embutido.
FASES_JANELAS: list[dict[str, Any]] = [
    {"k": "menstrual", "ini": 1, "fim": 5, "cor": "#ff5555",
     "nome": "menstrual", "janela": "d 1-5",
     "nota": "fluxo · descanso · cuidados"},
    {"k": "folicular", "ini": 6, "fim": 13, "cor": "#f1fa8c",
     "nome": "folicular", "janela": "d 6-13",
     "nota": "energia ↑ · foco ↑ · social"},
    {"k": "fertil", "ini": 14, "fim": 16, "cor": "#bd93f9",
     "nome": "fértil", "janela": "d 14-16",
     "nota": "libido pico · ovulação"},
    {"k": "lutea", "ini": 17, "fim": 28, "cor": "#ff79c6",
     "nome": "lútea", "janela": "d 17-28",
     "nota": "TPM possível · sensibilidade ↑"},
]

# Compat: mapas legados usados pela versão calendário-grid de UX-RD-19,
# preservados para não quebrar consumidores externos.
CORES_FASE = {
    "menstrual": "#ff5555",
    "folicular": "#f1fa8c",
    "ovulacao": "#bd93f9",
    "lutea": "#ff79c6",
}
LABEL_FASE = {
    "menstrual": "Menstrual",
    "folicular": "Folicular",
    "ovulacao": "Ovulação",
    "lutea": "Lútea",
}


# ---------------------------------------------------------------------------
# Helpers de dados
# ---------------------------------------------------------------------------


def _carregar_cache_ciclo(vault_root: Path | None) -> list[dict[str, Any]]:
    """Carrega ``items`` de ``<vault>/.ouroboros/cache/ciclo.json``."""
    if vault_root is None:
        return []
    arquivo = vault_root / ".ouroboros" / "cache" / "ciclo.json"
    if not arquivo.exists():
        return []
    try:
        payload = json.loads(arquivo.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    items = payload.get("items") or []
    return items if isinstance(items, list) else []


def _toggle_ativo(vault_root: Path | None) -> bool:
    """Lê ``privacidade.toml`` para checar se o módulo ciclo está ativo.

    Default: ativo (True). Toggle só é considerado se o arquivo existe e
    declara explicitamente ``ciclo = false`` no nível raiz ou na seção
    ``[modulos]``.
    """
    if vault_root is None:
        return True
    arquivo = vault_root / ".ouroboros" / "privacidade.toml"
    if not arquivo.exists():
        return True
    try:
        cfg = tomllib.loads(arquivo.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return True
    if cfg.get("ciclo") is False:
        return False
    modulos = cfg.get("modulos") or {}
    if isinstance(modulos, dict) and modulos.get("ciclo") is False:
        return False
    return True


def _safe_date(s: str) -> date | None:
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def _fase_do_dia(dia: int) -> dict[str, Any]:
    """Devolve o dicionário de fase para o dia ``d`` (1..28)."""
    for fase in FASES_JANELAS:
        if fase["ini"] <= dia <= fase["fim"]:
            return fase
    return FASES_JANELAS[-1]


def _calcular_dia_ciclo(items: list[dict[str, Any]], hoje: date) -> int:
    """Estima o dia do ciclo a partir do último registro ``menstrual``.

    Procura a entrada ``menstrual`` mais recente que NÃO seja futura. O dia
    do ciclo é ``(hoje - inicio_menstrual) + 1``, capped em 28. Quando não
    há registro menstrual, retorna 1 como degradação segura.
    """
    inicios: list[date] = []
    for it in items:
        fase = str(it.get("fase") or "").strip().lower()
        if fase != "menstrual":
            continue
        d = _safe_date(str(it.get("data") or ""))
        if d is not None and d <= hoje:
            inicios.append(d)
    if not inicios:
        return 1
    ultimo = max(inicios)
    delta = (hoje - ultimo).days + 1
    if delta < 1:
        return 1
    if delta > TOTAL_DIAS_CICLO:
        # Provavelmente já entrou em novo ciclo sem registro -- usa o resto.
        return ((delta - 1) % TOTAL_DIAS_CICLO) + 1
    return delta


def _sintomas_hoje(items: list[dict[str, Any]], hoje: date) -> list[dict[str, Any]]:
    """Retorna sintomas registrados em ``hoje`` com intensidade 0-3.

    Cache atual não traz intensidade explícita, então deriva de uma
    contagem simples: cada sintoma listado vale ``int=1`` (até cap 3).
    Quando o item lista o mesmo sintoma N vezes, soma até 3.
    """
    sintomas_hoje: dict[str, int] = {}
    iso_hoje = hoje.isoformat()
    for it in items:
        if str(it.get("data") or "") != iso_hoje:
            continue
        for s in it.get("sintomas") or []:
            nome = str(s).strip()
            if not nome:
                continue
            sintomas_hoje[nome] = min(3, sintomas_hoje.get(nome, 0) + 1)
    return [{"nome": k, "int": v} for k, v in sintomas_hoje.items()]


def _proximo_ciclo(items: list[dict[str, Any]], hoje: date) -> tuple[date | None, int | None]:
    """Estima a data prevista da próxima menstruação.

    Heurística simples: último início menstrual + 28 dias. Quando não há
    registro, retorna ``(None, None)``.
    """
    inicios = sorted(
        d for d in (
            _safe_date(str(it.get("data") or ""))
            for it in items
            if str(it.get("fase") or "").strip().lower() == "menstrual"
        )
        if d is not None
    )
    if not inicios:
        return None, None
    proxima = inicios[-1] + timedelta(days=TOTAL_DIAS_CICLO)
    return proxima, (proxima - hoje).days


# ---------------------------------------------------------------------------
# Geração do anel SVG (28 segmentos coloridos)
# ---------------------------------------------------------------------------


def _anel_ciclo_svg(dia_atual: int | None, total_dias: int = TOTAL_DIAS_CICLO) -> str:
    """SVG anel circular com ``total_dias`` segmentos coloridos por fase.

    Adapta a lógica do mockup ``25-ciclo.html`` (função ``gerarAnel``):
    cada dia vira um arco com ``stroke-width`` maior se for o dia atual,
    e há um marcador circular ciano destacando ``dia_atual``.

    Quando ``dia_atual`` é ``None`` (skeleton sem dado), todos os 28
    segmentos são renderizados em opacidade uniforme, sem largura
    aumentada nem marcador ciano. Padrão ``(o)`` retrocompatível: o
    chamador antigo ``_anel_ciclo_svg(d)`` mantém comportamento original.
    """
    cx, cy, r = 230, 230, 170
    sw = 28
    arcs: list[str] = []
    skeleton = dia_atual is None
    for d in range(1, total_dias + 1):
        a0 = ((d - 1) / total_dias) * math.pi * 2 - math.pi / 2 + 0.005
        a1 = (d / total_dias) * math.pi * 2 - math.pi / 2 - 0.005
        x0 = cx + r * math.cos(a0)
        y0 = cy + r * math.sin(a0)
        x1 = cx + r * math.cos(a1)
        y1 = cy + r * math.sin(a1)
        cor = _fase_do_dia(d)["cor"]
        is_hoje = (not skeleton) and d == dia_atual
        largura = sw + 8 if is_hoje else sw
        if skeleton:
            opacidade = 0.85
        else:
            opacidade = 1.0 if is_hoje else 0.7
        arcs.append(
            f'<path d="M {x0:.2f} {y0:.2f} A {r} {r} 0 0 1 {x1:.2f} {y1:.2f}" '
            f'stroke="{cor}" stroke-width="{largura}" fill="none" '
            f'stroke-linecap="butt" opacity="{opacidade}" />'
        )
        # Label de dia em marcos: 1, múltiplos de 7 e o dia atual.
        if d % 7 == 0 or d == 1 or is_hoje:
            al = (a0 + a1) / 2
            lx = cx + (r + sw / 2 + 16) * math.cos(al)
            ly = cy + (r + sw / 2 + 16) * math.sin(al)
            cor_label = "var(--accent-cyan)" if is_hoje else "var(--text-muted)"
            peso = "600" if is_hoje else "400"
            arcs.append(
                f'<text x="{lx:.2f}" y="{ly:.2f}" text-anchor="middle" '
                f'dominant-baseline="middle" fill="{cor_label}" '
                f'font-family="JetBrains Mono, monospace" font-size="11" '
                f'font-weight="{peso}">{d}</text>'
            )
    # Marcador "hoje" -- pequeno círculo ciano sobre o segmento atual.
    # Omitido no skeleton (sem dia destacado).
    if not skeleton:
        a_hoje = ((dia_atual - 0.5) / total_dias) * math.pi * 2 - math.pi / 2
        mx = cx + (r - sw / 2 - 6) * math.cos(a_hoje)
        my = cy + (r - sw / 2 - 6) * math.sin(a_hoje)
        arcs.append(
            f'<circle cx="{mx:.2f}" cy="{my:.2f}" r="6" '
            f'fill="var(--accent-cyan)" stroke="var(--bg-base)" stroke-width="2" />'
        )

    return (
        f'<svg class="anel-svg" viewBox="0 0 460 460" '
        f'xmlns="http://www.w3.org/2000/svg">{"".join(arcs)}</svg>'
    )


# ---------------------------------------------------------------------------
# Componentes HTML
# ---------------------------------------------------------------------------


def _anel_html(dia_atual: int, fase_atual: dict[str, Any], proxima: date | None,
               dias_para_proxima: int | None) -> str:
    """Wrapper do anel + texto central (fase, dia, total, predição)."""
    if proxima is not None and dias_para_proxima is not None:
        pred = (
            f'próxima menstruação - {proxima.strftime("%d %b").lower()} '
            f'- em {dias_para_proxima} dias'
        )
    else:
        pred = "próxima menstruação - sem registro suficiente"
    centro = (
        f'<div class="anel-centro">'
        f'<div class="fase-titulo" style="color:{fase_atual["cor"]};">'
        f'{fase_atual["nome"]}</div>'
        f'<div class="dia">d{dia_atual}</div>'
        f'<div class="total">de {TOTAL_DIAS_CICLO}</div>'
        f'<div class="pred">{pred}</div>'
        f'</div>'
    )
    return (
        f'<div class="anel-wrap">{_anel_ciclo_svg(dia_atual)}{centro}</div>'
    )


def _cards_fase_html(fase_atual_k: str) -> str:
    """4 cards canônicos com a fase atual destacada."""
    cards: list[str] = []
    for fase in FASES_JANELAS:
        ativa = " ativa" if fase["k"] == fase_atual_k else ""
        cards.append(
            f'<div class="fase-leg{ativa}" style="--cor:{fase["cor"]};">'
            f'<div class="nome">{fase["nome"]}</div>'
            f'<div class="janela">{fase["janela"]}</div>'
            f'<div class="nota">{fase["nota"]}</div>'
            f'</div>'
        )
    return f'<div class="fases-legenda">{"".join(cards)}</div>'


def _strip_mensal_html(dia_atual: int) -> str:
    """Strip linear de 28 dias com o dia atual destacado."""
    celulas: list[str] = []
    mapa_classes = {
        "menstrual": "menstr",
        "folicular": "fol",
        "fertil": "fert",
        "lutea": "lut",
    }
    for d in range(1, TOTAL_DIAS_CICLO + 1):
        fase = _fase_do_dia(d)
        classe = mapa_classes.get(fase["k"], "")
        marca = " hoje" if d == dia_atual else ""
        celulas.append(f'<div class="d {classe}{marca}">{d}</div>')
    legenda = (
        '<div class="legenda-strip">'
        '<span class="menstr">menstrual</span>'
        '<span class="fol">folicular</span>'
        '<span class="fert">fertil</span>'
        '<span class="lut">lutea</span>'
        '<span style="margin-left:auto;color:var(--accent-cyan);">hoje</span>'
        '</div>'
    )
    return (
        '<div class="ciclo-card">'
        '<h3 style="font-family:var(--ff-mono);font-size:11px;'
        'letter-spacing:0.10em;text-transform:uppercase;'
        'color:var(--text-muted);margin:0 0 var(--sp-3);">'
        'Strip do mês</h3>'
        f'<div class="mes-strip">{"".join(celulas)}</div>'
        f'{legenda}'
        '</div>'
    )


def _sintomas_card_html(sintomas: list[dict[str, Any]]) -> str:
    """Card lateral com sintomas de hoje (escala 0-3)."""
    if not sintomas:
        corpo = (
            '<div style="font-family:var(--ff-mono);font-size:11px;'
            'color:var(--text-muted);padding:8px 0;">'
            'sem sintomas registrados hoje.</div>'
        )
    else:
        linhas: list[str] = []
        for s in sintomas:
            intensidade = max(0, min(3, int(s.get("int", 0))))
            dots = "".join(
                f'<span class="{"on" if i < intensidade else ""}"></span>'
                for i in range(3)
            )
            linhas.append(
                f'<div class="sint-row">'
                f'<span class="nome">{s["nome"]}</span>'
                f'<div class="intens">{dots}</div>'
                f'</div>'
            )
        corpo = "".join(linhas)
    return (
        '<div class="sint-card">'
        '<h3>Sintomas hoje · escala 0-3</h3>'
        f'{corpo}'
        '</div>'
    )


def _cruzamento_card_html(items: list[dict[str, Any]]) -> str:
    """Cruzamento ciclo x humor.

    Quando humor não está no cache de ciclo, o card explica que requer
    cruzamento com humor-heatmap.json (futuro). Aqui mantemos placeholder
    coerente com o mockup.
    """
    return (
        '<div class="crc-card">'
        '<h3>Cruzamento · ciclo × humor</h3>'
        '<div style="font-family:var(--ff-mono);font-size:11px;'
        'color:var(--text-muted);line-height:1.5;">'
        'Cruzamento humor por fase requer histórico mínimo de 3 ciclos. '
        'Continue registrando dia a dia que aqui aparecem os agregados.'
        '</div>'
        '</div>'
    )


def _privacidade_card_html() -> str:
    return (
        '<div class="crc-card" style="background:var(--bg-inset);">'
        '<h3 style="color:var(--accent-purple);">Privacidade</h3>'
        '<div style="font-family:var(--ff-mono);font-size:11px;'
        'color:var(--text-secondary);line-height:1.6;">'
        'visível só para Pessoa B por padrão<br>'
        'Pessoa A vê apenas "fase aproximada" se autorizado<br>'
        'dados não saem do dispositivo · zero analytics<br>'
        'exportável a qualquer momento em CSV'
        '</div>'
        '</div>'
    )


SINTOMAS_SKELETON_CANONICOS: list[str] = [
    "cólica",
    "inchaço",
    "dor de cabeça",
    "sensibilidade mamária",
    "fadiga",
    "mudança de apetite",
    "mudança de humor",
    "acne",
]

CRUZAMENTO_FASES_SKELETON: list[str] = [
    "humor médio · folicular",
    "humor médio · fértil",
    "humor médio · lútea (TPM)",
    "humor médio · menstrual",
]


def _anel_skeleton_html() -> str:
    """Anel SVG canônico no skeleton: 28 segmentos coloridos sem dia destacado.

    Centro mostra ``d-- · de 28 · próxima --``. Mantém o anel completo do
    mockup mesmo quando ainda não há registros, para preservar a paridade
    visual exigida pela auditoria 2026-05-08 (página 25).
    """
    centro = (
        '<div class="anel-centro">'
        '<div class="fase-titulo" style="color:var(--text-muted);">--</div>'
        '<div class="dia">d--</div>'
        f'<div class="total">de {TOTAL_DIAS_CICLO}</div>'
        '<div class="pred">próxima menstruação · --</div>'
        '</div>'
    )
    return f'<div class="anel-wrap">{_anel_ciclo_svg(None)}{centro}</div>'


def _sintomas_skeleton_html() -> str:
    """Card SINTOMAS HOJE no skeleton: 8 linhas canônicas com escala 0-3 vazia."""
    linhas: list[str] = []
    for nome in SINTOMAS_SKELETON_CANONICOS:
        dots = "".join('<span></span>' for _ in range(3))
        linhas.append(
            '<div class="sint-row">'
            f'<span class="nome">{nome}</span>'
            f'<div class="intens">{dots}</div>'
            '</div>'
        )
    return (
        '<div class="sint-card">'
        '<h3>Sintomas hoje · escala 0-3</h3>'
        f'{"".join(linhas)}'
        '</div>'
    )


def _cruzamento_skeleton_html() -> str:
    """Card CRUZAMENTO HUMOR no skeleton: 4 fases com valor ``--``."""
    linhas: list[str] = []
    for label in CRUZAMENTO_FASES_SKELETON:
        linhas.append(
            '<div class="cruz-row">'
            f'<span>{label}</span>'
            '<span class="v">--</span>'
            '</div>'
        )
    nota = (
        '<div style="margin-top:10px;padding-top:10px;'
        'border-top:1px dashed var(--border-subtle);'
        'font-family:var(--ff-mono);font-size:11px;'
        'color:var(--text-muted);line-height:1.5;">'
        'Cruzamento humor por fase requer histórico mínimo de 3 ciclos. '
        'Continue registrando dia a dia que aqui aparecem os agregados.'
        '</div>'
    )
    return (
        '<div class="crc-card">'
        '<h3>Cruzamento · ciclo × humor (12 ciclos)</h3>'
        f'{"".join(linhas)}'
        f'{nota}'
        '</div>'
    )


def _skeleton_ciclo_completo_html() -> str:
    """Skeleton canônico V-2.13-FIX: anel + sintomas + cruzamento + fases.

    Renderiza, mesmo sem dado real, o layout esperado da página: anel SVG
    com 28 segmentos coloridos (sem dia destacado), card SINTOMAS HOJE com
    8 linhas placeholder, card CRUZAMENTO HUMOR com 4 linhas placeholder e
    os 4 cards canônicos das fases no rodapé. Substitui o skeleton pobre
    de UX-V-2.13 (silhueta cinza + 4 KPIs ``--``).
    """
    coluna_principal = (
        '<div class="ciclo-card">'
        f'{_anel_skeleton_html()}'
        f'{_cards_fase_html("")}'
        '</div>'
    )
    coluna_lateral = (
        '<div class="coluna-direita">'
        f'{_sintomas_skeleton_html()}'
        f'{_cruzamento_skeleton_html()}'
        '</div>'
    )
    return (
        '<div class="ciclo-grid">'
        f'<div>{coluna_principal}</div>'
        f'{coluna_lateral}'
        '</div>'
    )


def _page_header_html(ativo: bool) -> str:
    """UX-U-03: usa helper canônico ``componentes/page_header``."""
    from src.dashboard.componentes.page_header import renderizar_page_header

    pills = [
        {"texto": "opt-in ativo" if ativo else "desativado",
         "tipo": "d7-graduado" if ativo else "d7-regredindo"},
    ]
    return renderizar_page_header(
        titulo="CICLO MENSTRUAL",
        subtitulo="Track de fluxo, fase e sintomas. Opcional, opt-in.",
        sprint_tag="UX-V-2.13",
        pills=pills,
    )


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


def renderizar(
    dados: dict[str, pd.DataFrame],
    periodo: str,
    pessoa: str,
    ctx: dict | None = None,
) -> None:
    """Renderiza Bem-estar / Ciclo (UX-V-2.13)."""
    from src.dashboard.componentes.topbar_actions import renderizar_grupo_acoes
    renderizar_grupo_acoes([
        {"label": "Histórico", "glyph": "list", "title": "12 ciclos anteriores"},
        {"label": "Registrar dia", "primary": True, "glyph": "plus",
         "title": "Fluxo, sintomas, humor, energia"},
    ])

    del dados, periodo, pessoa, ctx

    # CSS dedicado (Onda M / V-2.13).
    st.markdown(minificar(carregar_css_pagina("be_ciclo")), unsafe_allow_html=True)

    vault_root = descobrir_vault_root()
    ativo = _toggle_ativo(vault_root)

    st.markdown(_page_header_html(ativo), unsafe_allow_html=True)

    if not ativo:
        st.info(
            "Módulo Ciclo desativado em `privacidade.toml`. "
            "Para ativar, edite `[modulos]\\nciclo = true` "
            "no arquivo de privacidade ou apague a chave."
        )
        return

    if vault_root is None:
        st.warning(
            "Vault Bem-estar não encontrado. Configure `OUROBOROS_VAULT` "
            "para visualizar o ciclo."
        )
        return

    items = _carregar_cache_ciclo(vault_root)

    if not items:
        # Fallback V-03 + UX-V-2.13-FIX: estado inicial antes do primeiro
        # registro, agora com paridade visual completa do mockup.
        from src.dashboard.componentes.ui import (
            fallback_estado_inicial_html,
            ler_sync_info,
        )
        st.markdown(
            fallback_estado_inicial_html(
                titulo="CICLO · sem registros ainda",
                descricao=(
                    "Acompanhamento do ciclo (fases menstrual, folicular, "
                    "ovulação, lútea) e sintomas associados é registrado "
                    "diariamente no app mobile. Cada arquivo "
                    "<code>vault/ciclo/&lt;data&gt;.md</code> aparece como "
                    "ponto no anel acima."
                ),
                skeleton_html=minificar(_skeleton_ciclo_completo_html()),
                cta_secao="ciclo",
                sync_info=ler_sync_info(),
            ),
            unsafe_allow_html=True,
        )
        return

    hoje = date.today()
    dia_atual = _calcular_dia_ciclo(items, hoje)
    fase_atual = _fase_do_dia(dia_atual)
    proxima, dias_para = _proximo_ciclo(items, hoje)
    sintomas = _sintomas_hoje(items, hoje)

    # Layout em grid 2 colunas (anel + sintomas/cruzamento/privacidade).
    coluna_principal = (
        '<div class="ciclo-card">'
        f'{_anel_html(dia_atual, fase_atual, proxima, dias_para)}'
        f'{_cards_fase_html(fase_atual["k"])}'
        '</div>'
        f'{_strip_mensal_html(dia_atual)}'
    )
    coluna_lateral = (
        '<div class="coluna-direita">'
        f'{_sintomas_card_html(sintomas)}'
        f'{_cruzamento_card_html(items)}'
        f'{_privacidade_card_html()}'
        '</div>'
    )
    grid = (
        '<div class="ciclo-grid">'
        f'<div>{coluna_principal}</div>'
        f'{coluna_lateral}'
        '</div>'
    )
    st.markdown(minificar(grid), unsafe_allow_html=True)


# "O corpo tem suas próprias estações." -- Hipócrates
