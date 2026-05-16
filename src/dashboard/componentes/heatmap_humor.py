"""Heatmap de humor 13 colunas × 7 linhas (UX-RD-17).

Reusado por ``paginas/be_hoje.py`` (mini-heatmap 7 dias) e
``paginas/be_humor.py`` (heatmap 91 dias completo). Renderiza HTML
estático via ``minificar`` -- nenhum JS, nenhum re-render reativo. As
células são ``<div>`` simples com cor por intensidade de humor; o
clique-para-detalhe na página be_humor é resolvido por ``st.radio``
fora deste componente (lição UX-RD-15: HTML puro para o desenho,
widget Streamlit para o estado).

Paleta canônica (Dracula + WCAG-AA):

* humor 1 → ``accent-red``    (#ff5555)
* humor 2 → ``accent-orange`` (#ffb86c)
* humor 3 → ``accent-yellow`` (#f1fa8c)
* humor 4 → ``accent-cyan``   (#8be9fd)
* humor 5 → ``accent-green``  (#50fa7b)

Sem registro → cinza muted (``texto_muted`` = #6c6f7d) com 12% opacidade.

Overlay pessoa_a / pessoa_b: quando ``pessoa == "ambos"``, cada célula
fica dividida em diagonal 50/50 via ``linear-gradient(135deg, A 50%, B
50%)`` -- ambos os humores visíveis simultaneamente. Quando há só uma
pessoa registrada no dia, a outra metade fica transparente.

Lição UX-RD-04: HTML emitido via :func:`minificar` para neutralizar o
parser CommonMark. Lição UX-RD-15: nunca emitir indentação Python
crua dentro de ``st.markdown`` -- vira ``<pre><code>``.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from src.dashboard.componentes.html_utils import minificar
from src.dashboard.tema import CORES

# Cores indexadas por humor 1..5 (índice 0 = sem registro).
_CORES_HUMOR: tuple[str, ...] = (
    "transparent",  # 0 = sem registro (overrided por classe .vazio)
    CORES["negativo"],  # 1 = #ff5555 (red)
    CORES["alerta"],  # 2 = #ffb86c (orange)
    CORES["info"],  # 3 = #f1fa8c (yellow)
    CORES["neutro"],  # 4 = #8be9fd (cyan)
    CORES["positivo"],  # 5 = #50fa7b (green)
)

_LABEL_DIAS_SEMANA: tuple[str, ...] = (
    "seg",
    "ter",
    "qua",
    "qui",
    "sex",
    "sáb",
    "dom",
)


def cor_para_humor(valor: int | None) -> str:
    """Devolve string de cor (hex ou ``transparent``) para um humor 1..5."""
    if valor is None:
        return "transparent"
    try:
        idx = int(valor)
    except (TypeError, ValueError):
        return "transparent"
    if not 1 <= idx <= 5:
        return "transparent"
    return _CORES_HUMOR[idx]


def _agrupar_por_dia(
    items: list[dict[str, Any]],
) -> dict[tuple[str, str], int]:
    """Mapeia ``(data, autor) -> humor`` (último humor do dia da pessoa).

    Quando há múltiplas células no mesmo dia/pessoa (ex.: registros
    duplicados), prevalece o último -- mas o ``humor_heatmap`` já
    deduplica antes, então essa redundância é defensiva.
    """
    mapa: dict[tuple[str, str], int] = {}
    for it in items:
        data = it.get("data")
        autor = it.get("autor")
        humor = it.get("humor")
        if not isinstance(data, str) or not isinstance(autor, str):
            continue
        if not isinstance(humor, int):
            continue
        mapa[(data, autor)] = humor
    return mapa


def _gerar_dias(periodo_dias: int, hoje: date) -> list[date]:
    """Lista os ``periodo_dias`` dias terminando em ``hoje`` (inclusivo)."""
    inicio = hoje - timedelta(days=periodo_dias - 1)
    return [inicio + timedelta(days=i) for i in range(periodo_dias)]


def _cell_html(
    cor_a: str,
    cor_b: str,
    pessoa: str,
    titulo: str,
    classe_extra: str = "",
) -> str:
    """Renderiza uma célula do heatmap (com ou sem overlay)."""
    if pessoa == "pessoa_a":
        bg = cor_a if cor_a != "transparent" else "transparent"
        if bg == "transparent":
            return f'<div class="cell vazio {classe_extra}" title="{titulo}"></div>'
        return f'<div class="cell {classe_extra}" style="background:{bg};" title="{titulo}"></div>'
    if pessoa == "pessoa_b":
        bg = cor_b if cor_b != "transparent" else "transparent"
        if bg == "transparent":
            return f'<div class="cell vazio {classe_extra}" title="{titulo}"></div>'
        return f'<div class="cell {classe_extra}" style="background:{bg};" title="{titulo}"></div>'
    # ambos -- overlay 50% via linear-gradient diagonal
    if cor_a == "transparent" and cor_b == "transparent":
        return f'<div class="cell vazio {classe_extra}" title="{titulo}"></div>'
    cor_a_render = cor_a if cor_a != "transparent" else "rgba(0,0,0,0)"
    cor_b_render = cor_b if cor_b != "transparent" else "rgba(0,0,0,0)"
    return (
        f'<div class="cell heatmap-overlay {classe_extra}" '
        f'style="background: linear-gradient(135deg, {cor_a_render} 50%, '
        f'{cor_b_render} 50%); opacity:0.5;" title="{titulo}"></div>'
    )


def gerar_heatmap_html(
    items: list[dict[str, Any]],
    *,
    pessoa: str = "ambos",
    periodo_dias: int = 91,
    hoje: date | None = None,
) -> str:
    """Gera HTML estático do heatmap 13×7 (ou n_semanas×7).

    Args:
        items: lista de células no formato emitido por
            :func:`gerar_humor_heatmap` (chaves ``data``, ``autor``,
            ``humor``).
        pessoa: ``"pessoa_a"``, ``"pessoa_b"`` ou ``"ambos"``. ``ambos``
            renderiza overlay diagonal 50%.
        periodo_dias: quantos dias renderizar (default 91 = 13 semanas).
        hoje: data de referência (default ``date.today()``). Útil para
            testes determinísticos.

    Returns:
        String HTML minificada pronta para ``st.markdown(unsafe_allow_html=True)``.
    """
    if hoje is None:
        hoje = date.today()
    if periodo_dias <= 0:
        return minificar('<div class="heatmap-vazio">período inválido</div>')

    dias = _gerar_dias(periodo_dias, hoje)
    n_semanas = (periodo_dias + 6) // 7
    mapa = _agrupar_por_dia(items)

    # Layout column-major: 13 colunas (semanas) × 7 linhas (dias da semana).
    # Cada célula é um dia. Colunas representam semanas; linhas, dias.
    # Ordem do grid CSS: row-major (linha × coluna), por isso a iteração
    # exterior é por linha (l 0..6).
    cells_html: list[str] = []
    pessoa_norm = pessoa if pessoa in {"pessoa_a", "pessoa_b", "ambos"} else "ambos"

    # Mapeia (linha, coluna) -> índice no array de dias.
    # Coluna 0 = semana mais antiga, coluna n-1 = semana atual.
    # Linha 0 = segunda-feira do mockup. Para casar, calculamos
    # weekday do primeiro dia (0=monday..6=sunday) e desenrolamos.
    for linha in range(7):
        for coluna in range(n_semanas):
            idx = coluna * 7 + linha
            if idx >= len(dias):
                cells_html.append('<div class="cell vazio"></div>')
                continue
            dia = dias[idx]
            data_iso = dia.isoformat()
            humor_a = mapa.get((data_iso, "pessoa_a"))
            humor_b = mapa.get((data_iso, "pessoa_b"))
            cor_a = cor_para_humor(humor_a)
            cor_b = cor_para_humor(humor_b)
            classe_extra = "hoje" if dia == hoje else ""
            partes_titulo = [data_iso]
            if humor_a is not None:
                partes_titulo.append(f"A: {humor_a}/5")
            if humor_b is not None:
                partes_titulo.append(f"B: {humor_b}/5")
            if humor_a is None and humor_b is None:
                partes_titulo.append("sem registro")
            titulo = " · ".join(partes_titulo)
            cells_html.append(_cell_html(cor_a, cor_b, pessoa_norm, titulo, classe_extra))

    labels_dias = "".join(
        f'<span class="heatmap-dia-label">{dia}</span>' for dia in _LABEL_DIAS_SEMANA
    )

    # Cabeçalho de meses: marca a 1ª coluna em que o mês muda.
    meses_pt = [
        "JAN",
        "FEV",
        "MAR",
        "ABR",
        "MAI",
        "JUN",
        "JUL",
        "AGO",
        "SET",
        "OUT",
        "NOV",
        "DEZ",
    ]
    cabecalho_meses: list[str] = []
    ultimo_mes = -1
    for c in range(n_semanas):
        idx_dia = c * 7
        if idx_dia >= len(dias):
            cabecalho_meses.append('<span class="mes-label"></span>')
            continue
        dia_ref = dias[idx_dia]
        if dia_ref.month != ultimo_mes:
            cabecalho_meses.append(f'<span class="mes-label">{meses_pt[dia_ref.month - 1]}</span>')
            ultimo_mes = dia_ref.month
        else:
            cabecalho_meses.append('<span class="mes-label"></span>')

    grid_template = f"repeat({n_semanas}, 1fr)"

    html = f"""
    <div class="humor-heatmap" data-pessoa="{pessoa_norm}" data-periodo="{periodo_dias}">
      <div class="heatmap-meses-host" style="grid-template-columns: {grid_template};">
        {"".join(cabecalho_meses)}
      </div>
      <div class="heatmap-corpo">
        <div class="heatmap-dias-labels-coluna">{labels_dias}</div>
        <div class="heatmap-grid"
             style="grid-template-columns: {grid_template};
                    grid-template-rows: repeat(7, minmax(20px, 1fr));">
          {"".join(cells_html)}
        </div>
      </div>
    </div>
    """
    return minificar(html)


def gerar_estilos_heatmap() -> str:
    """CSS local do heatmap. Injetar uma vez por página via ``st.markdown``."""
    bg_inset = CORES["fundo_inset"]
    border_subtle = CORES["card_elevado"]
    text_muted = CORES["texto_muted"]
    return minificar(
        f"""
        <style>
          .humor-heatmap {{
            background: {CORES["card_fundo"]};
            border: 1px solid {border_subtle};
            border-radius: 6px;
            padding: 16px;
          }}
          .humor-heatmap .heatmap-meses-host {{
            display: grid;
            gap: 4px;
            margin-left: 32px;
            margin-bottom: 6px;
            font-family: monospace;
            font-size: 10px;
            color: {text_muted};
            letter-spacing: 0.04em;
            text-transform: uppercase;
            height: 14px;
          }}
          .humor-heatmap .heatmap-corpo {{
            display: grid;
            grid-template-columns: 28px 1fr;
            gap: 6px;
            align-items: start;
          }}
          .humor-heatmap .heatmap-dias-labels-coluna {{
            display: grid;
            grid-template-rows: repeat(7, 1fr);
            gap: 4px;
            font-family: monospace;
            font-size: 10px;
            color: {text_muted};
            letter-spacing: 0.04em;
            text-transform: uppercase;
            align-items: center;
            min-height: 140px;
          }}
          .humor-heatmap .heatmap-grid {{
            display: grid;
            gap: 4px;
            min-width: 0;
          }}
          .humor-heatmap .cell {{
            border-radius: 3px;
            border: 1px solid transparent;
            min-width: 0;
            min-height: 16px;
            cursor: pointer;
            transition: transform .12s, box-shadow .12s;
          }}
          .humor-heatmap .cell:hover {{
            transform: scale(1.15);
            border-color: {CORES["texto"]};
            z-index: 5;
          }}
          .humor-heatmap .cell.vazio {{
            background: {bg_inset};
            border-color: {border_subtle};
          }}
          .humor-heatmap .cell.hoje {{
            box-shadow: 0 0 0 1px {CORES["neutro"]};
          }}
          .humor-heatmap .cell.heatmap-overlay {{
            /* opacity já fica em 0.5 via inline; classe serve de marker
               para os testes UX-RD-17. */
          }}
          .humor-heatmap .heatmap-legenda {{
            display: flex;
            align-items: center;
            gap: 12px;
            margin-top: 12px;
            padding-top: 12px;
            border-top: 1px solid {border_subtle};
            font-family: monospace;
            font-size: 11px;
            color: {text_muted};
          }}
          .humor-heatmap .legenda-escala {{
            display: flex;
            gap: 4px;
          }}
          .humor-heatmap .legenda-escala .swatch {{
            width: 18px;
            height: 18px;
            border-radius: 3px;
          }}
        </style>
        """
    )


def gerar_legenda_html() -> str:
    """Faixa "menos -> mais" abaixo do heatmap."""
    swatches = "".join(
        f'<span class="swatch" style="background:{_CORES_HUMOR[v]};"></span>' for v in range(1, 6)
    )
    return minificar(
        f"""
        <div class="heatmap-legenda">
          <span>menos</span>
          <div class="legenda-escala">{swatches}</div>
          <span>mais</span>
          <span style="margin-left:auto;">cada célula = um dia</span>
        </div>
        """
    )


# "Os dias são deuses." -- Ralph Waldo Emerson
