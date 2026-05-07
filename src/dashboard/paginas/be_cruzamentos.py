"""Cluster Bem-estar -- página "Cruzamentos" (UX-RD-19).

Três correlações read-only sobre os caches do vault:

* **Humor × Eventos** -- humor médio em dias com evento positivo vs
  negativo vs neutro.
* **Humor × Medidas** -- série temporal de peso ao lado de humor médio
  por mês.
* **Treinos × Humor** -- humor médio em dias com treino vs sem treino.

Mockup-fonte: ``novo-mockup/mockups/26-cruzamentos.html``.

Lições UX-RD aplicadas:

* HTML emitido via :func:`minificar` (UX-RD-04).
* Cores via ``CORES`` em :mod:`src.dashboard.tema` -- nunca hex literal.
* Fallback graceful: cache vazio vira aviso por correlação, sem crash.
* Contrato uniforme ``renderizar(dados, periodo, pessoa, ctx)``.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

import pandas as pd
import streamlit as st

from src.mobile_cache.varrer_vault import descobrir_vault_root


def _carregar_cache(vault_root: Path | None, nome: str) -> list[dict[str, Any]]:
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


def _humor_por_dia(vault_root: Path | None) -> dict[str, float]:
    """Mapa data -> humor médio do dia (todas as pessoas)."""
    if vault_root is None:
        return {}
    arquivo = vault_root / ".ouroboros" / "cache" / "humor-heatmap.json"
    if not arquivo.exists():
        return {}
    try:
        payload = json.loads(arquivo.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    celulas = payload.get("celulas") or []
    if not isinstance(celulas, list):
        return {}
    por_dia: dict[str, list[float]] = defaultdict(list)
    for c in celulas:
        ds = str(c.get("data") or "")
        v = c.get("humor")
        if ds and isinstance(v, (int, float)):
            por_dia[ds].append(float(v))
    return {ds: mean(vs) for ds, vs in por_dia.items() if vs}


def _correlacao_humor_eventos(
    humor_dia: dict[str, float], eventos: list[dict[str, Any]]
) -> pd.DataFrame:
    """Humor médio agrupado por modo do evento no mesmo dia."""
    grupos: dict[str, list[float]] = {"positivo": [], "negativo": [], "sem evento": []}
    datas_com_evento_pos = {
        str(e.get("data") or "")
        for e in eventos
        if str(e.get("modo") or "").lower() == "positivo"
    }
    datas_com_evento_neg = {
        str(e.get("data") or "")
        for e in eventos
        if str(e.get("modo") or "").lower() == "negativo"
    }
    for ds, h in humor_dia.items():
        if ds in datas_com_evento_pos:
            grupos["positivo"].append(h)
        elif ds in datas_com_evento_neg:
            grupos["negativo"].append(h)
        else:
            grupos["sem evento"].append(h)
    linhas = [
        {"grupo": k, "humor_medio": round(mean(v), 2), "n_dias": len(v)}
        for k, v in grupos.items()
        if v
    ]
    return pd.DataFrame(linhas)


def _correlacao_humor_medidas(
    humor_dia: dict[str, float], medidas: list[dict[str, Any]]
) -> pd.DataFrame:
    """Série mensal de peso médio + humor médio no mês."""
    pesos_mes: dict[str, list[float]] = defaultdict(list)
    for m in medidas:
        ds = str(m.get("data") or "")
        peso = m.get("peso")
        if ds and isinstance(peso, (int, float)):
            pesos_mes[ds[:7]].append(float(peso))

    humor_mes: dict[str, list[float]] = defaultdict(list)
    for ds, h in humor_dia.items():
        humor_mes[ds[:7]].append(h)

    meses = sorted(set(pesos_mes.keys()) | set(humor_mes.keys()))
    linhas: list[dict[str, Any]] = []
    for m in meses:
        peso_avg = round(mean(pesos_mes[m]), 2) if pesos_mes.get(m) else None
        humor_avg = round(mean(humor_mes[m]), 2) if humor_mes.get(m) else None
        linhas.append({"mes": m, "peso": peso_avg, "humor": humor_avg})
    return pd.DataFrame(linhas)


def _correlacao_treinos_humor(
    humor_dia: dict[str, float], treinos: list[dict[str, Any]]
) -> pd.DataFrame:
    """Humor médio em dias com treino vs sem treino."""
    datas_com_treino = {str(t.get("data") or "") for t in treinos}
    com: list[float] = []
    sem: list[float] = []
    for ds, h in humor_dia.items():
        (com if ds in datas_com_treino else sem).append(h)
    linhas = []
    if com:
        linhas.append(
            {"grupo": "com treino", "humor_medio": round(mean(com), 2), "n_dias": len(com)}
        )
    if sem:
        linhas.append(
            {"grupo": "sem treino", "humor_medio": round(mean(sem), 2), "n_dias": len(sem)}
        )
    return pd.DataFrame(linhas)


def _page_header_html() -> str:
    """UX-U-03: usa helper canônico ``componentes/page_header``."""
    from src.dashboard.componentes.page_header import renderizar_page_header

    return renderizar_page_header(
        titulo="CRUZAMENTOS",
        subtitulo=(
            "Correlações determinísticas entre humor, eventos, medidas e "
            "treinos. Roda local sobre os JSONs em .ouroboros/cache/."
        ),
        sprint_tag="UX-RD-19",
    )


def renderizar(
    dados: dict[str, pd.DataFrame],
    periodo: str,
    pessoa: str,
    ctx: dict | None = None,
) -> None:
    """Renderiza Bem-estar / Cruzamentos (UX-T-26)."""
    from src.dashboard.componentes.topbar_actions import renderizar_grupo_acoes
    renderizar_grupo_acoes([
        {"label": "Salvar como bloco do Recap",
         "title": "Padrão vai aparecer no Recap mensal"},
        {"label": "Voltar ao Recap", "primary": True,
         "href": "?cluster=Bem-estar&tab=Recap"},
    ])

    del dados, periodo, pessoa, ctx

    st.markdown(_page_header_html(), unsafe_allow_html=True)

    vault_root = descobrir_vault_root()
    if vault_root is None:
        from src.dashboard.componentes.ui import (
            fallback_estado_inicial_html,
            ler_sync_info,
        )
        skeleton = (
            '<div style="display:flex;flex-direction:column;gap:10px;">'
            '<div style="display:flex;gap:10px;">'
            '<span class="skel-bloco" style="width:30%;height:36px;"></span>'
            '<span class="skel-bloco" style="width:30%;height:36px;"></span>'
            '<span class="skel-bloco" style="width:30%;height:36px;"></span>'
            '</div>'
            '<span class="skel-bloco" style="width:100%;height:160px;"></span>'
            '</div>'
        )
        st.markdown(
            fallback_estado_inicial_html(
                titulo="CRUZAMENTOS · sem dados para correlacionar",
                descricao=(
                    "Correlações entre humor × eventos × medidas × treinos "
                    "exigem caches populados no vault. Configure "
                    "<code>OUROBOROS_VAULT</code> e registre pelo app mobile "
                    "ao longo de algumas semanas para que padrões emerjam."
                ),
                skeleton_html=skeleton,
                cta_secao="cruzamentos",
                sync_info=ler_sync_info(),
            ),
            unsafe_allow_html=True,
        )
        return

    humor_dia = _humor_por_dia(vault_root)
    eventos = _carregar_cache(vault_root, "eventos")
    medidas = _carregar_cache(vault_root, "medidas")
    treinos = _carregar_cache(vault_root, "treinos")

    with st.expander("Humor × Eventos (mesmo dia)", expanded=True):
        df = _correlacao_humor_eventos(humor_dia, eventos)
        if df.empty:
            st.info("Sem dados suficientes (cache de humor ou eventos vazio).")
        else:
            st.bar_chart(df.set_index("grupo")["humor_medio"], height=220)
            st.dataframe(df, hide_index=True, use_container_width=True)

    with st.expander("Humor × Medidas (peso, mensal)", expanded=False):
        df = _correlacao_humor_medidas(humor_dia, medidas)
        if df.empty:
            st.info("Sem dados suficientes (cache de humor ou medidas vazio).")
        else:
            st.line_chart(df.set_index("mes"), height=240)
            st.dataframe(df, hide_index=True, use_container_width=True)

    with st.expander("Treinos × Humor (mesmo dia)", expanded=False):
        df = _correlacao_treinos_humor(humor_dia, treinos)
        if df.empty:
            st.info("Sem dados suficientes (cache de humor ou treinos vazio).")
        else:
            st.bar_chart(df.set_index("grupo")["humor_medio"], height=220)
            st.dataframe(df, hide_index=True, use_container_width=True)


# "Tudo está em todas as coisas." -- Anaxágoras
