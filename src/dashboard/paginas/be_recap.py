"""Cluster Bem-estar -- página "Recap" (UX-RD-19).

Resumo agregado dos últimos 7/30/90 dias com métricas determinísticas
calculadas sobre os caches Bem-estar (humor, eventos, treinos, medidas).
Sem LLM: ADR-13 proíbe API programática neste projeto, então a
"narrativa" do mockup vira um conjunto de KPIs + mini-charts honestos
sobre os dados reais do vault.

Mockup-fonte: ``novo-mockup/mockups/21-recap.html``.

Lições UX-RD aplicadas:

* HTML emitido via :func:`minificar` (UX-RD-04).
* Cores via ``CORES`` em :mod:`src.dashboard.tema` -- nunca hex literal.
* Fallback graceful: vault ausente vira aviso, sem crash.
* Contrato uniforme ``renderizar(dados, periodo, pessoa, ctx)``.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import date, timedelta
from pathlib import Path
from statistics import mean
from typing import Any

import pandas as pd
import streamlit as st

from src.dashboard.componentes.html_utils import minificar
from src.dashboard.tema import CORES
from src.mobile_cache.varrer_vault import descobrir_vault_root

_PERIODOS_LABEL = {"7 dias": 7, "30 dias": 30, "90 dias": 90}


def _carregar_cache(vault_root: Path | None, nome: str) -> list[dict[str, Any]]:
    """Lê ``<vault>/.ouroboros/cache/<nome>.json`` retornando ``items``."""
    if vault_root is None:
        return []
    arquivo = vault_root / ".ouroboros" / "cache" / f"{nome}.json"
    if not arquivo.exists():
        return []
    try:
        payload = json.loads(arquivo.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    items = payload.get("items") or []
    return items if isinstance(items, list) else []


def _filtrar_periodo(
    items: list[dict[str, Any]], dias: int, hoje: date
) -> list[dict[str, Any]]:
    limite = hoje - timedelta(days=dias - 1)
    saida: list[dict[str, Any]] = []
    for it in items:
        ds = str(it.get("data") or "")
        try:
            d = date.fromisoformat(ds)
        except ValueError:
            continue
        if limite <= d <= hoje:
            saida.append(it)
    return saida


def _agregados_humor(vault_root: Path | None, dias: int, hoje: date) -> dict[str, Any]:
    """Lê humor-heatmap.json e calcula média/qtd/melhor/pior do período."""
    if vault_root is None:
        return {"media": None, "qtd": 0, "melhor": None, "pior": None}
    arquivo = vault_root / ".ouroboros" / "cache" / "humor-heatmap.json"
    if not arquivo.exists():
        return {"media": None, "qtd": 0, "melhor": None, "pior": None}
    try:
        payload = json.loads(arquivo.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"media": None, "qtd": 0, "melhor": None, "pior": None}
    celulas = payload.get("celulas") or []
    if not isinstance(celulas, list):
        return {"media": None, "qtd": 0, "melhor": None, "pior": None}
    limite = hoje - timedelta(days=dias - 1)
    valores: list[float] = []
    for c in celulas:
        ds = str(c.get("data") or "")
        try:
            d = date.fromisoformat(ds)
        except ValueError:
            continue
        if not (limite <= d <= hoje):
            continue
        v = c.get("humor")
        if isinstance(v, (int, float)):
            valores.append(float(v))
    if not valores:
        return {"media": None, "qtd": 0, "melhor": None, "pior": None}
    return {
        "media": round(mean(valores), 2),
        "qtd": len(valores),
        "melhor": max(valores),
        "pior": min(valores),
    }


def _agregados_eventos(items: list[dict[str, Any]]) -> dict[str, Any]:
    pos = sum(1 for it in items if str(it.get("modo") or "").lower() == "positivo")
    neg = sum(1 for it in items if str(it.get("modo") or "").lower() == "negativo")
    bairros = Counter(
        str(it.get("bairro") or "").strip()
        for it in items
        if str(it.get("bairro") or "").strip()
    )
    return {
        "qtd": len(items),
        "positivos": pos,
        "negativos": neg,
        "top_bairros": bairros.most_common(3),
    }


def _agregados_treinos(items: list[dict[str, Any]]) -> dict[str, Any]:
    rotinas = Counter(
        str(it.get("rotina") or "").strip()
        for it in items
        if str(it.get("rotina") or "").strip()
    )
    duracoes = [
        float(it["duracao_min"])
        for it in items
        if isinstance(it.get("duracao_min"), (int, float))
    ]
    return {
        "qtd": len(items),
        "rotina_dominante": rotinas.most_common(1)[0][0] if rotinas else "--",
        "duracao_media": round(mean(duracoes), 1) if duracoes else None,
    }


def _agregados_medidas(items: list[dict[str, Any]]) -> dict[str, Any]:
    pesos = [
        (it.get("data"), float(it["peso"]))
        for it in items
        if isinstance(it.get("peso"), (int, float))
    ]
    pesos.sort(key=lambda p: str(p[0] or ""))
    if len(pesos) < 2:
        return {"qtd": len(pesos), "delta_peso": None, "primeiro": None, "ultimo": None}
    primeiro = pesos[0][1]
    ultimo = pesos[-1][1]
    return {
        "qtd": len(pesos),
        "delta_peso": round(ultimo - primeiro, 2),
        "primeiro": primeiro,
        "ultimo": ultimo,
    }


def _kpi_card_html(titulo: str, valor: str, subtitulo: str) -> str:
    return (
        f'<div style="background:{CORES["card_fundo"]};'
        f'border:1px solid {CORES["texto_sec"]}33;border-radius:6px;'
        f'padding:16px;">'
        f'  <div style="font-family:ui-monospace,monospace;font-size:10px;'
        f'                letter-spacing:0.10em;text-transform:uppercase;'
        f'                color:{CORES["texto_muted"]};margin-bottom:8px;">'
        f"{titulo}</div>"
        f'  <div style="font-size:24px;font-weight:500;color:{CORES["texto"]};'
        f'                font-variant-numeric:tabular-nums;">{valor}</div>'
        f'  <div style="font-size:11px;color:{CORES["texto_sec"]};'
        f'                margin-top:4px;">{subtitulo}</div>'
        f"</div>"
    )


def _page_header_html(periodo_label: str) -> str:
    return minificar(
        f"""
        <div style="display:flex;justify-content:space-between;align-items:flex-end;
                    margin-bottom:18px;border-bottom:1px solid {CORES['texto_sec']}33;
                    padding-bottom:14px;">
            <div>
                <h1 style="margin:0;font-size:24px;letter-spacing:0.04em;
                            color:{CORES['texto']};">RECAP · {periodo_label.upper()}</h1>
                <p style="margin:4px 0 0;color:{CORES['texto_sec']};font-size:13px;">
                    Resumo agregado determinístico sobre os caches do vault.
                    Sem narrativa LLM (ADR-13).
                </p>
            </div>
            <div style="font-family:ui-monospace,monospace;font-size:11px;
                        color:{CORES['texto_muted']};letter-spacing:0.04em;">
                <span style="background:{CORES['fundo_inset']};padding:3px 8px;
                              border:1px solid {CORES['texto_sec']}33;
                              border-radius:4px;">UX-RD-19</span>
            </div>
        </div>
        """
    )


def renderizar(
    dados: dict[str, pd.DataFrame],
    periodo: str,
    pessoa: str,
    ctx: dict | None = None,
) -> None:
    """Renderiza a página Bem-estar / Recap."""
    del dados, periodo, pessoa, ctx

    periodo_label = st.radio(
        "Período",
        options=list(_PERIODOS_LABEL.keys()),
        index=1,
        horizontal=True,
        key="be_recap_periodo",
    )
    dias = _PERIODOS_LABEL[periodo_label]

    st.markdown(_page_header_html(periodo_label), unsafe_allow_html=True)

    vault_root = descobrir_vault_root()
    hoje = date.today()

    if vault_root is None:
        st.warning(
            "Vault Bem-estar não encontrado. Configure `OUROBOROS_VAULT` "
            "para visualizar o recap."
        )
        return

    eventos = _filtrar_periodo(_carregar_cache(vault_root, "eventos"), dias, hoje)
    treinos = _filtrar_periodo(_carregar_cache(vault_root, "treinos"), dias, hoje)
    medidas = _filtrar_periodo(_carregar_cache(vault_root, "medidas"), dias, hoje)

    h = _agregados_humor(vault_root, dias, hoje)
    e = _agregados_eventos(eventos)
    t = _agregados_treinos(treinos)
    m = _agregados_medidas(medidas)

    col1, col2, col3, col4 = st.columns(4)
    media_humor_str = f"{h['media']:.2f}" if h["media"] is not None else "--"
    delta_peso_str = (
        f"{m['delta_peso']:+.1f} kg" if m["delta_peso"] is not None else "--"
    )

    with col1:
        st.markdown(
            _kpi_card_html(
                "humor médio",
                media_humor_str,
                f"{h['qtd']} registros no período",
            ),
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            _kpi_card_html(
                "eventos",
                str(e["qtd"]),
                f"{e['positivos']} positivos · {e['negativos']} negativos",
            ),
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            _kpi_card_html(
                "treinos",
                str(t["qtd"]),
                f"rotina dominante: {t['rotina_dominante']}",
            ),
            unsafe_allow_html=True,
        )
    with col4:
        st.markdown(
            _kpi_card_html(
                "peso · variação",
                delta_peso_str,
                f"{m['qtd']} medidas registradas",
            ),
            unsafe_allow_html=True,
        )

    st.markdown("###### ")
    col_humor, col_bairros = st.columns([1.4, 1], gap="large")

    with col_humor:
        st.markdown(
            f'<h3 style="font-family:ui-monospace,monospace;font-size:11px;'
            f'letter-spacing:0.10em;text-transform:uppercase;'
            f'color:{CORES["texto_muted"]};margin:0 0 8px;">'
            f"Comparativo de humor</h3>",
            unsafe_allow_html=True,
        )
        if h["media"] is None:
            st.info("Sem registros de humor no período.")
        else:
            df_humor = pd.DataFrame(
                {
                    "métrica": ["média", "melhor", "pior"],
                    "valor": [h["media"], h["melhor"], h["pior"]],
                }
            )
            st.bar_chart(df_humor.set_index("métrica"), height=240)

    with col_bairros:
        st.markdown(
            f'<h3 style="font-family:ui-monospace,monospace;font-size:11px;'
            f'letter-spacing:0.10em;text-transform:uppercase;'
            f'color:{CORES["texto_muted"]};margin:0 0 8px;">'
            f"Bairros mais frequentes</h3>",
            unsafe_allow_html=True,
        )
        if not e["top_bairros"]:
            st.info("Sem bairros tagueados.")
        else:
            for bairro, qtd in e["top_bairros"]:
                st.markdown(
                    minificar(
                        f'<div style="background:{CORES["fundo_inset"]};'
                        f'border:1px solid {CORES["texto_sec"]}33;'
                        f'border-radius:4px;padding:8px 12px;margin-bottom:6px;'
                        f'display:flex;justify-content:space-between;">'
                        f'<span style="color:{CORES["texto"]};font-size:13px;">{bairro}</span>'
                        f'<span style="font-family:ui-monospace,monospace;font-size:11px;'
                        f'color:{CORES["texto_muted"]};">{qtd}x</span>'
                        f"</div>"
                    ),
                    unsafe_allow_html=True,
                )


# "Lembrar é a única forma de continuar." -- adágio popular brasileiro
