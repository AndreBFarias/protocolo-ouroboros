"""Cluster Bem-estar -- página "Ciclo" (UX-RD-19).

Visualização do ciclo menstrual com fases coloridas (menstrual,
folicular, ovulação, lútea) lidas do cache ``ciclo.json`` e lista
de sintomas registrados nos últimos 30 dias. Página é opt-in: respeita
a flag ``ciclo`` em ``<vault>/.ouroboros/privacidade.toml`` quando
existe, e exibe placeholder informativo quando o pessoa filtro indica
que o cluster não cobre a autora habitual.

Mockup-fonte: ``novo-mockup/mockups/25-ciclo.html``.

Lições UX-RD aplicadas:

* HTML emitido via :func:`minificar` (UX-RD-04).
* Cores via ``CORES`` em :mod:`src.dashboard.tema` -- nunca hex literal.
* Fallback graceful: cache vazio ou toggle off vira aviso, sem crash.
* Contrato uniforme ``renderizar(dados, periodo, pessoa, ctx)``.
"""

from __future__ import annotations

import json
import tomllib
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from src.dashboard.componentes.html_utils import minificar
from src.dashboard.tema import CORES
from src.mobile_cache.varrer_vault import descobrir_vault_root

CORES_FASE = {
    "menstrual": CORES["negativo"],
    "folicular": CORES["positivo"],
    "ovulacao": CORES["destaque"],
    "lutea": CORES["alerta"],
}
LABEL_FASE = {
    "menstrual": "Menstrual",
    "folicular": "Folicular",
    "ovulacao": "Ovulação",
    "lutea": "Lútea",
}


def _carregar_cache_ciclo(vault_root: Path | None) -> list[dict[str, Any]]:
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


def _calendario_mes_html(items: list[dict[str, Any]], hoje: date) -> str:
    """Calendário simples 30 dias com cor por fase quando registrado."""
    inicio = hoje - timedelta(days=29)
    mapa_data_fase: dict[str, str] = {}
    for it in items:
        ds = str(it.get("data") or "")
        fase = str(it.get("fase") or "").strip().lower()
        if ds and fase in CORES_FASE:
            mapa_data_fase[ds] = fase

    celulas: list[str] = []
    for offset in range(30):
        d = inicio + timedelta(days=offset)
        ds = d.isoformat()
        fase = mapa_data_fase.get(ds)
        if fase:
            cor = CORES_FASE[fase]
            titulo = f"{ds} · {LABEL_FASE[fase]}"
        else:
            cor = CORES["fundo_inset"]
            titulo = f"{ds} · sem registro"
        celulas.append(
            f'<div title="{titulo}" '
            f'style="height:36px;background:{cor};border-radius:3px;'
            f'border:1px solid {CORES["texto_sec"]}22;'
            f'display:flex;align-items:center;justify-content:center;'
            f'font-family:ui-monospace,monospace;font-size:10px;'
            f'color:{CORES["fundo"] if fase else CORES["texto_muted"]};">{d.day}</div>'
        )

    grid = (
        f'<div style="display:grid;grid-template-columns:repeat(10,1fr);'
        f'gap:4px;">{"".join(celulas)}</div>'
    )
    return minificar(grid)


def _legenda_html() -> str:
    chips = "".join(
        f'<span style="display:inline-flex;align-items:center;gap:6px;'
        f'margin-right:14px;font-size:12px;color:{CORES["texto_sec"]};">'
        f'<span style="width:12px;height:12px;background:{CORES_FASE[k]};'
        f'border-radius:3px;"></span>{LABEL_FASE[k]}</span>'
        for k in ("menstrual", "folicular", "ovulacao", "lutea")
    )
    return minificar(f'<div style="margin:10px 0;">{chips}</div>')


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
        sprint_tag="UX-RD-19",
        pills=pills,
    )


def renderizar(
    dados: dict[str, pd.DataFrame],
    periodo: str,
    pessoa: str,
    ctx: dict | None = None,
) -> None:
    """Renderiza Bem-estar / Ciclo (UX-T-25)."""
    from src.dashboard.componentes.topbar_actions import renderizar_grupo_acoes
    renderizar_grupo_acoes([
        {"label": "Histórico", "glyph": "list", "title": "12 ciclos anteriores"},
        {"label": "Registrar dia", "primary": True, "glyph": "plus",
         "title": "Fluxo, sintomas, humor, energia"},
    ])

    del dados, periodo, pessoa, ctx

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
        st.info(
            "Nenhum registro de ciclo encontrado. Crie arquivos em "
            "`<vault>/ciclo/<data>.md` com frontmatter `tipo: ciclo` e "
            "`fase: menstrual|folicular|ovulacao|lutea`."
        )
        return

    hoje = date.today()
    st.markdown(
        f'<h3 style="font-family:ui-monospace,monospace;font-size:11px;'
        f'letter-spacing:0.10em;text-transform:uppercase;'
        f'color:{CORES["texto_muted"]};margin:0 0 8px;">'
        f"Calendário · últimos 30 dias</h3>",
        unsafe_allow_html=True,
    )
    st.markdown(_calendario_mes_html(items, hoje), unsafe_allow_html=True)
    st.markdown(_legenda_html(), unsafe_allow_html=True)

    limite = hoje - timedelta(days=29)
    items_recentes = [
        it
        for it in items
        if (
            (d := _safe_date(str(it.get("data") or ""))) is not None
            and limite <= d <= hoje
        )
    ]
    sintomas_count: dict[str, int] = {}
    for it in items_recentes:
        for s in it.get("sintomas") or []:
            s_str = str(s).strip()
            if s_str:
                sintomas_count[s_str] = sintomas_count.get(s_str, 0) + 1

    st.markdown("###### ")
    st.markdown(
        f'<h3 style="font-family:ui-monospace,monospace;font-size:11px;'
        f'letter-spacing:0.10em;text-transform:uppercase;'
        f'color:{CORES["texto_muted"]};margin:14px 0 8px;">'
        f"Sintomas (últimos 30 dias)</h3>",
        unsafe_allow_html=True,
    )
    if not sintomas_count:
        st.info("Nenhum sintoma registrado no período.")
    else:
        ordenados = sorted(sintomas_count.items(), key=lambda kv: -kv[1])
        for sintoma, qtd in ordenados:
            st.markdown(
                minificar(
                    f'<div style="background:{CORES["fundo_inset"]};'
                    f'border:1px solid {CORES["texto_sec"]}33;'
                    f'border-radius:4px;padding:8px 12px;margin-bottom:6px;'
                    f'display:flex;justify-content:space-between;">'
                    f'<span style="color:{CORES["texto"]};font-size:13px;">{sintoma}</span>'
                    f'<span style="font-family:ui-monospace,monospace;font-size:11px;'
                    f'color:{CORES["texto_muted"]};">{qtd}x</span>'
                    f"</div>"
                ),
                unsafe_allow_html=True,
            )


def _safe_date(s: str) -> date | None:
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


# "O corpo tem suas próprias estações." -- Hipócrates
