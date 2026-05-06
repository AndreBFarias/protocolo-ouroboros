"""Cluster Bem-estar -- página "Medidas" (UX-RD-19).

Comparativo entre primeira e última medida registrada por pessoa
(peso, cintura, quadril, peito, braço, coxa) lido do cache
``medidas.json``. Inclui galeria simples de fotos comparativas
quando o frontmatter referencia paths.

Mockup-fonte: ``novo-mockup/mockups/24-medidas.html``.

Lições UX-RD aplicadas:

* HTML emitido via :func:`minificar` (UX-RD-04).
* Cores via ``CORES`` em :mod:`src.dashboard.tema` -- nunca hex literal.
* Fallback graceful: cache vazio vira aviso explicativo, sem crash.
* Contrato uniforme ``renderizar(dados, periodo, pessoa, ctx)``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from src.dashboard.componentes.html_utils import minificar
from src.dashboard.tema import CORES
from src.mobile_cache.varrer_vault import descobrir_vault_root

CAMPOS = ("peso", "cintura", "quadril", "peito", "braco", "coxa")
UNIDADES = {
    "peso": "kg",
    "cintura": "cm",
    "quadril": "cm",
    "peito": "cm",
    "braco": "cm",
    "coxa": "cm",
}
LABEL_CAMPO = {
    "peso": "peso",
    "cintura": "cintura",
    "quadril": "quadril",
    "peito": "peito",
    "braco": "braço",
    "coxa": "coxa",
}


def _carregar_medidas(vault_root: Path | None) -> list[dict[str, Any]]:
    if vault_root is None:
        return []
    arquivo = vault_root / ".ouroboros" / "cache" / "medidas.json"
    if not arquivo.exists():
        return []
    try:
        payload = json.loads(arquivo.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    items = payload.get("items") or []
    return items if isinstance(items, list) else []


def _comparativo(items: list[dict[str, Any]]) -> dict[str, dict[str, float | None]]:
    """Para cada campo, retorna ``{primeiro, ultimo, delta}``."""
    if not items:
        return {}
    ordenados = sorted(items, key=lambda i: str(i.get("data") or ""))
    saida: dict[str, dict[str, float | None]] = {}
    for campo in CAMPOS:
        primeiros = [
            float(i[campo])
            for i in ordenados
            if isinstance(i.get(campo), (int, float))
        ]
        if len(primeiros) < 1:
            saida[campo] = {"primeiro": None, "ultimo": None, "delta": None}
            continue
        primeiro = primeiros[0]
        ultimo = primeiros[-1]
        delta = round(ultimo - primeiro, 2)
        saida[campo] = {"primeiro": primeiro, "ultimo": ultimo, "delta": delta}
    return saida


def _comparativo_card_html(
    campo: str, dados: dict[str, float | None]
) -> str:
    label = LABEL_CAMPO[campo]
    unidade = UNIDADES[campo]
    primeiro = dados["primeiro"]
    ultimo = dados["ultimo"]
    delta = dados["delta"]
    if primeiro is None or ultimo is None:
        valor_str = "--"
        delta_str = "sem registros"
        cor_delta = CORES["texto_muted"]
    else:
        valor_str = f"{ultimo:.1f} {unidade}"
        if delta is None or abs(delta) < 0.01:
            delta_str = f"= mesmo ({primeiro:.1f})"
            cor_delta = CORES["texto_muted"]
        elif delta > 0:
            delta_str = f"↗ +{delta:.1f} {unidade}"
            cor_delta = CORES["alerta"] if campo == "peso" else CORES["positivo"]
        else:
            delta_str = f"↘ {delta:.1f} {unidade}"
            cor_delta = CORES["positivo"] if campo == "peso" else CORES["alerta"]
    return (
        f'<div style="background:{CORES["card_fundo"]};'
        f'border:1px solid {CORES["texto_sec"]}33;border-radius:6px;'
        f'padding:14px;">'
        f'  <div style="font-family:ui-monospace,monospace;font-size:10px;'
        f'                letter-spacing:0.10em;text-transform:uppercase;'
        f'                color:{CORES["texto_muted"]};margin-bottom:8px;">{label}</div>'
        f'  <div style="font-size:20px;font-weight:500;color:{CORES["texto"]};'
        f'                font-variant-numeric:tabular-nums;">{valor_str}</div>'
        f'  <div style="font-family:ui-monospace,monospace;font-size:11px;'
        f'                color:{cor_delta};margin-top:6px;">{delta_str}</div>'
        f"</div>"
    )


def _page_header_html(qtd: int) -> str:
    """UX-U-03: usa helper canônico ``componentes/page_header``."""
    from src.dashboard.componentes.page_header import renderizar_page_header

    return renderizar_page_header(
        titulo="MEDIDAS · CORPO",
        subtitulo=(
            "Métricas físicas registradas no vault. "
            "Comparativo última vs primeira."
        ),
        sprint_tag="UX-RD-19",
        pills=[{"texto": f"{qtd} registros", "tipo": "generica"}],
    )


def renderizar(
    dados: dict[str, pd.DataFrame],
    periodo: str,
    pessoa: str,
    ctx: dict | None = None,
) -> None:
    """Renderiza Bem-estar / Medidas (UX-T-24)."""
    from src.dashboard.componentes.topbar_actions import renderizar_grupo_acoes
    renderizar_grupo_acoes([
        {"label": "Importar Mi Fit", "title": "Balança Xiaomi"},
        {"label": "Registrar", "primary": True, "title": "Peso, BF%, cintura"},
    ])

    del dados, periodo, ctx

    vault_root = descobrir_vault_root()
    items = _carregar_medidas(vault_root)

    if pessoa in {"pessoa_a", "pessoa_b"}:
        items_filtrados = [i for i in items if i.get("autor") == pessoa]
    else:
        items_filtrados = list(items)

    st.markdown(_page_header_html(len(items_filtrados)), unsafe_allow_html=True)

    if vault_root is None:
        st.warning(
            "Vault Bem-estar não encontrado. Configure `OUROBOROS_VAULT` "
            "para visualizar medidas."
        )
        return

    if not items_filtrados:
        st.info(
            "Nenhuma medida registrada ainda. Crie arquivos em "
            "`<vault>/medidas/<pessoa>/<data>.md` com frontmatter "
            "`tipo: medidas`, `peso`, `cintura`, etc."
        )
        return

    comp = _comparativo(items_filtrados)

    cols = st.columns(3)
    for idx, campo in enumerate(CAMPOS):
        with cols[idx % 3]:
            st.markdown(
                _comparativo_card_html(campo, comp[campo]),
                unsafe_allow_html=True,
            )

    st.markdown("###### ")
    df = pd.DataFrame(items_filtrados)
    if "data" in df.columns and "peso" in df.columns:
        df_peso = df[["data", "peso"]].dropna()
        if not df_peso.empty:
            df_peso = df_peso.sort_values("data").set_index("data")
            st.markdown(
                f'<h3 style="font-family:ui-monospace,monospace;font-size:11px;'
                f'letter-spacing:0.10em;text-transform:uppercase;'
                f'color:{CORES["texto_muted"]};margin:0 0 8px;">'
                f"Histórico de peso</h3>",
                unsafe_allow_html=True,
            )
            st.line_chart(df_peso, height=240)

    fotos_paths: list[str] = []
    for it in items_filtrados:
        paths = it.get("fotos") or []
        if isinstance(paths, list):
            for p in paths:
                p_str = str(p).strip()
                if p_str:
                    fotos_paths.append(p_str)

    if fotos_paths:
        st.markdown(
            f'<h3 style="font-family:ui-monospace,monospace;font-size:11px;'
            f'letter-spacing:0.10em;text-transform:uppercase;'
            f'color:{CORES["texto_muted"]};margin:18px 0 8px;">'
            f"Fotos comparativas</h3>",
            unsafe_allow_html=True,
        )
        cols_fotos = st.columns(min(4, len(fotos_paths)))
        for idx, p in enumerate(fotos_paths):
            with cols_fotos[idx % len(cols_fotos)]:
                st.markdown(
                    minificar(
                        f'<div style="background:{CORES["fundo_inset"]};'
                        f"height:160px;display:flex;align-items:center;"
                        f"justify-content:center;border-radius:4px;"
                        f'border:1px solid {CORES["texto_sec"]}33;'
                        f'color:{CORES["texto_muted"]};'
                        f"font-family:ui-monospace,monospace;font-size:10px;"
                        f'text-align:center;padding:6px;">{p}</div>'
                    ),
                    unsafe_allow_html=True,
                )


# "O corpo é o templo do espírito." -- adágio antigo, citado por Cícero
