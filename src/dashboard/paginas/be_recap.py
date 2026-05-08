"""Cluster Bem-estar -- página "Recap" (UX-RD-19, UX-V-2.17-FIX).

Resumo agregado dos últimos 7/30/90 dias com métricas determinísticas
calculadas sobre os caches Bem-estar (humor, eventos, treinos, medidas,
tarefas). Sem LLM: ADR-13 proíbe API programática neste projeto, então
a "narrativa" do mockup vira:

1. KPIs determinísticos no topo (humor médio, eventos, treinos, peso).
2. Bloco NARRATIVA DO MÊS lendo ``docs/recaps/<YYYY-MM>.md`` ou CTA
   para a skill ``/gerar-recap`` (Opus interativo via Claude Code).
3. Cards DESTAQUES DO MÊS gerados deterministicamente do cache.
4. Tabela COMPARATIVO vs 30D ANTERIORES com 9 métricas e deltas
   coloridos (substitui o antigo gráfico de barras "Comparativo de
   humor", UX-V-2.17-FIX).

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
    inicio = hoje - timedelta(days=dias - 1)
    base = _humor_intervalo(vault_root, inicio, hoje, _retornar_brutos=True)
    valores = base.pop("_brutos", [])
    if not valores:
        return {**base, "melhor": None, "pior": None}
    return {**base, "melhor": max(valores), "pior": min(valores)}


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


def _periodo_anterior(dias: int, hoje: date) -> tuple[date, date]:
    """Retorna ``(início, fim)`` da janela de ``dias`` imediatamente anterior.

    Exemplo: para ``dias=30`` e ``hoje=2026-05-07`` o periodo atual e
    ``[2026-04-08, 2026-05-07]``; o anterior e ``[2026-03-09, 2026-04-07]``.
    """
    fim_atual = hoje
    inicio_atual = fim_atual - timedelta(days=dias - 1)
    fim_ant = inicio_atual - timedelta(days=1)
    inicio_ant = fim_ant - timedelta(days=dias - 1)
    return inicio_ant, fim_ant


def _filtrar_intervalo(
    items: list[dict[str, Any]], inicio: date, fim: date
) -> list[dict[str, Any]]:
    """Filtra items por ``data`` ISO no intervalo fechado ``[início, fim]``."""
    saida: list[dict[str, Any]] = []
    for it in items:
        ds = str(it.get("data") or "")
        try:
            d = date.fromisoformat(ds)
        except ValueError:
            continue
        if inicio <= d <= fim:
            saida.append(it)
    return saida


def _humor_intervalo(
    vault_root: Path | None,
    inicio: date,
    fim: date,
    *,
    _retornar_brutos: bool = False,
) -> dict[str, Any]:
    """Variante de :func:`_agregados_humor` para janela ``[início, fim]``.

    Devolve médias de humor, ansiedade, foco e energia. Chaves cuja média
    não pode ser calculada ficam como ``None`` para sinalizar ausência
    de dado (nunca zero -- evita mentir comparativo). Quando
    ``_retornar_brutos=True`` inclui ``_brutos`` com a lista de humores
    para auxiliar :func:`_agregados_humor` (min/max).
    """
    vazio: dict[str, Any] = {
        "media": None, "qtd": 0,
        "ansiedade_media": None, "foco_media": None, "energia_media": None,
    }
    if _retornar_brutos:
        vazio["_brutos"] = []
    if vault_root is None:
        return dict(vazio)
    arquivo = vault_root / ".ouroboros" / "cache" / "humor-heatmap.json"
    if not arquivo.exists():
        return dict(vazio)
    try:
        payload = json.loads(arquivo.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return dict(vazio)
    celulas = payload.get("celulas") or []
    if not isinstance(celulas, list):
        return dict(vazio)
    acc: dict[str, list[float]] = {
        "humor": [], "ansiedade": [], "foco": [], "energia": []
    }
    for c in celulas:
        try:
            d = date.fromisoformat(str(c.get("data") or ""))
        except ValueError:
            continue
        if not (inicio <= d <= fim):
            continue
        for chave in acc:
            v = c.get(chave)
            if isinstance(v, (int, float)):
                acc[chave].append(float(v))
    if not acc["humor"]:
        return dict(vazio)

    def _med(lst: list[float]) -> float | None:
        return round(mean(lst), 2) if lst else None

    out: dict[str, Any] = {
        "media": _med(acc["humor"]),
        "qtd": len(acc["humor"]),
        "ansiedade_media": _med(acc["ansiedade"]),
        "foco_media": _med(acc["foco"]),
        "energia_media": _med(acc["energia"]),
    }
    if _retornar_brutos:
        out["_brutos"] = acc["humor"]
    return out


def _tarefas_concluidas_pct(
    vault_root: Path | None, inicio: date, fim: date
) -> tuple[float | None, int]:
    """Calcula porcentagem de tarefas concluídas na janela ``[início, fim]``.

    Tarefa entra na janela se ``prazo`` está em ``[início, fim]`` (proxy
    para "tarefas do período"). Retorna ``(pct_0_a_100, total)`` ou
    ``(None, 0)`` se janela vazia.
    """
    if vault_root is None:
        return (None, 0)
    items = _carregar_cache(vault_root, "tarefas")
    if not items:
        return (None, 0)
    total = 0
    concluidas = 0
    for it in items:
        prazo = str(it.get("prazo") or "")
        try:
            d = date.fromisoformat(prazo)
        except ValueError:
            continue
        if not (inicio <= d <= fim):
            continue
        total += 1
        if bool(it.get("concluida")):
            concluidas += 1
    if total == 0:
        return (None, 0)
    return (round(100.0 * concluidas / total, 1), total)


def _metricas_janela(
    vault_root: Path | None,
    inicio: date,
    fim: date,
) -> dict[str, float]:
    """Calcula métricas comparáveis para a janela ``[início, fim]``.

    Devolve apenas chaves que tem dado real (``None`` filtrado em
    :func:`_comparativo_html`). Conformidade ADR-13: tudo deterministico
    sobre caches do vault, zero LLM.
    """
    eventos_full = _carregar_cache(vault_root, "eventos")
    treinos_full = _carregar_cache(vault_root, "treinos")
    medidas_full = _carregar_cache(vault_root, "medidas")

    eventos = _filtrar_intervalo(eventos_full, inicio, fim)
    treinos = _filtrar_intervalo(treinos_full, inicio, fim)
    medidas = _filtrar_intervalo(medidas_full, inicio, fim)

    h = _humor_intervalo(vault_root, inicio, fim)
    e = _agregados_eventos(eventos)
    t = _agregados_treinos(treinos)
    m = _agregados_medidas(medidas)
    pct_tarefas, total_tarefas = _tarefas_concluidas_pct(vault_root, inicio, fim)

    out: dict[str, float] = {
        "registros": float(h["qtd"]),
        "eventos": float(e["qtd"]),
        "eventos_negativos": float(e["negativos"]),
        "treinos": float(t["qtd"]),
    }
    opcionais = {
        "humor_medio": h["media"],
        "ansiedade_media": h.get("ansiedade_media"),
        "foco_medio": h.get("foco_media"),
        "energia_media": h.get("energia_media"),
        "peso_var": m["delta_peso"],
        "tarefas_concluidas": pct_tarefas if total_tarefas > 0 else None,
    }
    out.update({k: float(v) for k, v in opcionais.items() if v is not None})
    return out


_COMPARATIVO_CONFIG: tuple[tuple[str, str, str, bool], ...] = (
    # (chave, label, formato, menor_eh_melhor)
    # formato: "f" -> 2 casas; "i" -> inteiro; "pp" -> porcento (delta em pp);
    #          "kg" -> sufixo kg; "fmt" -> sinal +/- ja embutido (peso_var).
    ("humor_medio", "humor médio", "f", False),
    ("ansiedade_media", "ansiedade média", "f", True),
    ("foco_medio", "foco médio", "f", False),
    ("energia_media", "energia média", "f", False),
    ("eventos", "eventos", "i", False),
    ("eventos_negativos", "eventos negativos", "i", True),
    ("treinos", "treinos", "i", False),
    ("tarefas_concluidas", "tarefas concluídas", "pp", False),
    ("peso_var", "peso (variação kg)", "kg", False),
)


def _formatar_valor(valor: float, formato: str) -> str:
    if formato == "i":
        return f"{int(round(valor))}"
    if formato == "pp":
        return f"{valor:.0f}%"
    if formato == "kg":
        return f"{valor:+.1f} kg"
    return f"{valor:.2f}"


def _formatar_delta(delta: float, formato: str) -> str:
    if formato == "i":
        return f"{int(round(delta)):+d}"
    if formato == "pp":
        return f"{delta:+.0f}pp"
    if formato == "kg":
        return f"{delta:+.1f}kg"
    return f"{delta:+.2f}"


def _comparativo_html(
    metricas_atual: dict[str, float], metricas_ant: dict[str, float]
) -> str:
    """Tabela `vs 30D anteriores` com 9 métricas e delta colorido por sinal.

    Métricas em que "menor é melhor" (ansiedade, eventos negativos)
    usam ↘ verde quando descem. Métricas sem dado em ambas as janelas
    são omitidas (jamais mostrar zero falso). UX-V-2.17-FIX.
    """
    linhas: list[str] = []
    for chave, label, formato, menor_eh_melhor in _COMPARATIVO_CONFIG:
        atual = metricas_atual.get(chave)
        ant = metricas_ant.get(chave)
        if atual is None or ant is None:
            continue
        delta = atual - ant
        delta_str = _formatar_delta(delta, formato)
        if abs(delta) < 0.01:
            sinal = '<span class="delta-zero">= mesmo</span>'
        else:
            subiu = delta > 0
            seta = "↗" if subiu else "↘"
            classe = (
                "delta-pos" if (subiu != menor_eh_melhor) else "delta-neg"
            )
            sinal = f'<span class="{classe}">{seta} {delta_str}</span>'
        valor_str = _formatar_valor(atual, formato)
        linhas.append(
            '<div class="comparativo-linha">'
            f'<span class="comp-label">{label}</span>'
            f'<span class="comp-valor">{valor_str}</span>'
            f'{sinal}'
            "</div>"
        )
    if not linhas:
        return minificar(
            '<div class="comparativo-bloco">'
            '<h3 class="comp-titulo">COMPARATIVO · vs 30D ANTERIORES</h3>'
            '<p class="destaques-vazio">Sem dado suficiente para comparar.</p>'
            '</div>'
        )
    return minificar(
        '<div class="comparativo-bloco">'
        '<h3 class="comp-titulo">COMPARATIVO · vs 30D ANTERIORES</h3>'
        + "".join(linhas)
        + '</div>'
    )


def _maior_streak_humor_alto(
    vault_root: Path | None, inicio: date, fim: date, limiar: float = 4.0
) -> int:
    """Maior sequência de dias com humor médio diário >= ``limiar``.

    Lacunas quebram a sequência. Retorna 0 se sem dados.
    """
    if vault_root is None:
        return 0
    arquivo = vault_root / ".ouroboros" / "cache" / "humor-heatmap.json"
    if not arquivo.exists():
        return 0
    try:
        celulas = json.loads(arquivo.read_text(encoding="utf-8")).get("celulas") or []
    except (OSError, json.JSONDecodeError):
        return 0
    if not isinstance(celulas, list):
        return 0
    por_dia: dict[date, list[float]] = {}
    for c in celulas:
        try:
            d = date.fromisoformat(str(c.get("data") or ""))
        except ValueError:
            continue
        if inicio <= d <= fim and isinstance(c.get("humor"), (int, float)):
            por_dia.setdefault(d, []).append(float(c["humor"]))
    melhor = atual = 0
    cursor = inicio
    while cursor <= fim:
        regs = por_dia.get(cursor)
        if regs and sum(regs) / len(regs) >= limiar:
            atual += 1
            melhor = max(melhor, atual)
        else:
            atual = 0
        cursor += timedelta(days=1)
    return melhor


def _gerar_destaques(
    vault_root: Path | None, inicio: date, fim: date
) -> list[dict[str, str]]:
    """Gera até 5 destaques determinísticos da janela ``[início, fim]``.

    Heurísticas (todas sobre caches reais, ADR-13 compliant):
    - viagem: evento com categoria "viagem"
    - vitória: rotina de treino dominante (>=3 ocorrências)
    - conquista: melhora de humor >=0.5 vs janela anterior
    - vitória: streak de >=5 dias com humor médio >=4
    - vitória: perda de peso saudável (-2.0kg a -0.1kg)
    - social: bairro top com >=3 eventos
    - risco: >=2 eventos negativos no período
    """
    if vault_root is None:
        return []

    destaques: list[dict[str, str]] = []
    eventos = _filtrar_intervalo(_carregar_cache(vault_root, "eventos"), inicio, fim)
    treinos = _filtrar_intervalo(_carregar_cache(vault_root, "treinos"), inicio, fim)
    medidas = _filtrar_intervalo(_carregar_cache(vault_root, "medidas"), inicio, fim)

    # Viagens
    viagens = [
        e for e in eventos
        if "viagem" in str(e.get("categoria") or "").lower()
    ]
    if viagens:
        primeiro = viagens[0]
        lugar = (
            primeiro.get("lugar")
            or primeiro.get("bairro")
            or primeiro.get("titulo")
            or "destino"
        )
        destaques.append({
            "tipo": "social",
            "rotulo": f"Viagem · {lugar}",
            "data": str(primeiro.get("data") or ""),
        })

    # Streak de humor alto (>=5 dias seguidos com humor >=4)
    streak = _maior_streak_humor_alto(vault_root, inicio, fim)
    if streak >= 5:
        destaques.append({
            "tipo": "vitoria",
            "rotulo": f"Streak de {streak} dias seguidos com humor ≥ 4",
            "data": "",
        })

    # Rotina dominante
    agg_treinos = _agregados_treinos(treinos)
    if agg_treinos["qtd"] >= 3 and agg_treinos["rotina_dominante"] != "--":
        destaques.append({
            "tipo": "vitoria",
            "rotulo": (
                f"{agg_treinos['rotina_dominante']} · "
                f"{agg_treinos['qtd']} treinos"
            ),
            "data": "",
        })

    # Melhora de humor entre janela anterior e atual
    dias = (fim - inicio).days + 1
    inicio_ant, fim_ant = _periodo_anterior(dias, fim)
    h_atual = _humor_intervalo(vault_root, inicio, fim)
    h_ant = _humor_intervalo(vault_root, inicio_ant, fim_ant)
    if (
        h_atual["media"] is not None
        and h_ant["media"] is not None
        and h_atual["media"] - h_ant["media"] >= 0.5
    ):
        destaques.append({
            "tipo": "conquista",
            "rotulo": (
                f"humor melhorou +{h_atual['media'] - h_ant['media']:.1f} "
                "vs janela anterior"
            ),
            "data": "",
        })

    # Perda de peso saudavel
    agg_medidas = _agregados_medidas(medidas)
    delta_peso = agg_medidas.get("delta_peso")
    if delta_peso is not None and -2.0 <= delta_peso <= -0.1:
        destaques.append({
            "tipo": "vitoria",
            "rotulo": f"peso · {delta_peso:+.1f} kg na janela",
            "data": "",
        })

    # Top bairro
    agg_eventos = _agregados_eventos(eventos)
    if agg_eventos["top_bairros"]:
        bairro, qtd = agg_eventos["top_bairros"][0]
        if qtd >= 3:
            destaques.append({
                "tipo": "social",
                "rotulo": f"{bairro} · {qtd} eventos",
                "data": "",
            })

    # Risco: eventos negativos
    if agg_eventos["negativos"] >= 2:
        destaques.append({
            "tipo": "risco",
            "rotulo": (
                f"{agg_eventos['negativos']} eventos negativos no período"
            ),
            "data": "",
        })

    return destaques[:5]


def _destaques_html(destaques: list[dict[str, str]]) -> str:
    """Renderiza grid de destaques. Fallback claro quando vazio."""
    if not destaques:
        return minificar(
            '<div class="destaques-bloco">'
            '<h3 class="destaques-titulo">DESTAQUES DO MÊS</h3>'
            '<p class="destaques-vazio">Sem destaques no período.</p>'
            '</div>'
        )

    cards: list[str] = []
    for d in destaques:
        tipo = d.get("tipo") or "vitoria"
        rotulo = d.get("rotulo") or "(sem rótulo)"
        data_str = d.get("data") or ""
        cards.append(
            f'<div class="destaque-card destaque-{tipo}">'
            f'<span class="destaque-rotulo">{rotulo}</span>'
            f'<span class="destaque-data">{data_str}</span>'
            "</div>"
        )
    return minificar(
        '<div class="destaques-bloco">'
        f'<h3 class="destaques-titulo">DESTAQUES DO MÊS · {len(destaques)}</h3>'
        '<div class="destaques-grid">'
        + "".join(cards)
        + '</div>'
        '</div>'
    )


def _narrativa_manual_html(periodo: str) -> str:
    """Le ``docs/recaps/<periodo>.md`` se existir; senao renderiza CTA.

    Conformidade ADR-13: nenhum LLM via API. Conteúdo gerado por humano
    (Opus interativo via skill ``/gerar-recap``) e gravado a mao no
    arquivo Markdown. Aqui apenas exibimos.
    """
    raiz = Path(__file__).resolve().parents[3]
    recap_path = raiz / "docs" / "recaps" / f"{periodo}.md"

    if recap_path.exists():
        try:
            md = recap_path.read_text(encoding="utf-8")
        except OSError:
            md = ""
        if md.strip():
            return minificar(
                '<div class="narrativa-bloco">'
                f'<h3 class="narrativa-titulo">NARRATIVA · {periodo}</h3>'
                f'<div class="narrativa-corpo">{md}</div>'
                '</div>'
            )

    return minificar(
        '<div class="narrativa-bloco narrativa-vazia">'
        f'<h3 class="narrativa-titulo">NARRATIVA · {periodo}</h3>'
        '<p>Nenhuma narrativa gerada para este período. Use a skill canônica '
        f'<code>/gerar-recap {periodo}</code> no Claude Code interativo '
        '(Opus principal) para registrar a narrativa do mês em '
        f'<code>docs/recaps/{periodo}.md</code>. ADR-13: nenhum LLM via '
        'API é chamado pelo dashboard.</p>'
        '</div>'
    )


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
    """UX-U-03: usa helper canônico ``componentes/page_header``."""
    from src.dashboard.componentes.page_header import renderizar_page_header

    return renderizar_page_header(
        titulo=f"RECAP · {periodo_label.upper()}",
        subtitulo=(
            "Resumo agregado determinístico sobre os caches do vault. "
            "Sem narrativa LLM (ADR-13)."
        ),
        sprint_tag="UX-RD-19",
    )


def renderizar(
    dados: dict[str, pd.DataFrame],
    periodo: str,
    pessoa: str,
    ctx: dict | None = None,
) -> None:
    """Renderiza Bem-estar / Recap (UX-T-21)."""
    from src.dashboard.componentes.topbar_actions import renderizar_grupo_acoes
    renderizar_grupo_acoes([
        {"label": "Re-gerar agora", "glyph": "refresh",
         "title": "Gerar Recap do período"},
        {"label": "Compartilhar com Pessoa B", "primary": True,
         "title": "Vista resumida sem trechos íntimos"},
    ])

    del dados, periodo, pessoa, ctx

    periodo_label = st.radio(
        "Período",
        options=list(_PERIODOS_LABEL.keys()),
        index=1,
        horizontal=True,
        key="be_recap_periodo",
    )
    dias = _PERIODOS_LABEL[periodo_label]

    # CSS dedicado dos blocos UX-V-2.17 (comparativo/destaques/narrativa).
    from src.dashboard.componentes.ui import carregar_css_pagina
    css_recap = carregar_css_pagina("be_recap")
    if css_recap:
        st.markdown(minificar(css_recap), unsafe_allow_html=True)

    st.markdown(_page_header_html(periodo_label), unsafe_allow_html=True)

    vault_root = descobrir_vault_root()
    hoje = date.today()

    if vault_root is None:
        from src.dashboard.componentes.ui import (
            fallback_estado_inicial_html,
            ler_sync_info,
        )
        skeleton = (
            '<div style="display:grid;grid-template-columns:repeat(4,1fr);'
            'gap:10px;margin-bottom:12px;">'
            '<div class="kpi"><span class="kpi-label">HUMOR MÉDIO</span>'
            '<span class="kpi-value">--</span></div>'
            '<div class="kpi"><span class="kpi-label">EVENTOS</span>'
            '<span class="kpi-value">--</span></div>'
            '<div class="kpi"><span class="kpi-label">TREINOS</span>'
            '<span class="kpi-value">--</span></div>'
            '<div class="kpi"><span class="kpi-label">MEDIDAS</span>'
            '<span class="kpi-value">--</span></div>'
            '</div>'
            '<div style="display:flex;flex-direction:column;gap:6px;">'
            '<span class="skel-bloco" style="width:80%;"></span>'
            '<span class="skel-bloco" style="width:65%;"></span>'
            '<span class="skel-bloco" style="width:90%;height:0.9em;"></span>'
            '</div>'
        )
        st.markdown(
            fallback_estado_inicial_html(
                titulo="RECAP · sem dados no período",
                descricao=(
                    "O recap agrega humor, eventos, treinos e medidas dos "
                    "últimos N dias. Configure <code>OUROBOROS_VAULT</code> "
                    "apontando para o vault Obsidian compartilhado com o app "
                    "mobile para popular este painel."
                ),
                skeleton_html=skeleton,
                cta_secao="recap",
                sync_info=ler_sync_info(),
            ),
            unsafe_allow_html=True,
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

    # ------------------------------------------------------------------
    # UX-V-2.17-FIX -- Comparativo (tabela 9 métricas) substitui o
    # gráfico de barras antigo "Comparativo de humor". Layout pareia
    # narrativa + destaques (esquerda) com tabela comparativo (direita)
    # conforme mockup 21-recap.html. ADR-13 mantido (zero LLM API).
    # ------------------------------------------------------------------
    inicio_atual = hoje - timedelta(days=dias - 1)
    inicio_ant, fim_ant = _periodo_anterior(dias, hoje)
    metricas_atual = _metricas_janela(vault_root, inicio_atual, hoje)
    metricas_ant = _metricas_janela(vault_root, inicio_ant, fim_ant)
    destaques = _gerar_destaques(vault_root, inicio_atual, hoje)
    periodo_recap = hoje.strftime("%Y-%m")

    st.markdown("###### ")
    col_narr, col_comp = st.columns([1.4, 1], gap="large")
    with col_narr:
        st.markdown(_narrativa_manual_html(periodo_recap), unsafe_allow_html=True)
        st.markdown(_destaques_html(destaques), unsafe_allow_html=True)
    with col_comp:
        st.markdown(
            _comparativo_html(metricas_atual, metricas_ant),
            unsafe_allow_html=True,
        )

    # Bairros mais frequentes (preservado, abaixo do bloco principal).
    st.markdown("###### ")
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
