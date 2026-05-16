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

# UX-V-2.12.A: schema estendido com fisiológicas opcionais.
# Antropométricas (6, UX-RD-16) + fisiológicas (5, UX-V-2.12.A).
CAMPOS = (
    "peso",
    "cintura",
    "quadril",
    "peito",
    "braco",
    "coxa",
    "gordura_pct",
    "pressao_sis",
    "pressao_dia",
    "freq_card",
    "sono_horas",
)
UNIDADES = {
    "peso": "kg",
    "cintura": "cm",
    "quadril": "cm",
    "peito": "cm",
    "braco": "cm",
    "coxa": "cm",
    "gordura_pct": "%",
    "pressao_sis": "mmHg",
    "pressao_dia": "mmHg",
    "freq_card": "bpm",
    "sono_horas": "h",
}
LABEL_CAMPO = {
    "peso": "peso",
    "cintura": "cintura",
    "quadril": "quadril",
    "peito": "peito",
    "braco": "braço",
    "coxa": "coxa",
    "gordura_pct": "gordura corp.",
    "pressao_sis": "pressão sis.",
    "pressao_dia": "pressão dia.",
    "freq_card": "freq. card.",
    "sono_horas": "sono médio",
}

# UX-V-2.12: paleta de cor por métrica (mockup 24-medidas.html).
# UX-V-2.12.A: estendida com fisiológicas (mantém paridade com mockup).
CORES_METRICAS = {
    "peso": "var(--accent-purple)",
    "cintura": "var(--accent-yellow)",
    "quadril": "var(--accent-cyan)",
    "peito": "var(--accent-orange)",
    "braco": "var(--accent-green)",
    "coxa": "var(--accent-pink)",
    "gordura_pct": "var(--accent-orange)",
    "pressao_sis": "var(--accent-cyan)",
    "pressao_dia": "var(--accent-cyan)",
    "freq_card": "var(--accent-green)",
    "sono_horas": "var(--accent-pink)",
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
        primeiros = [float(i[campo]) for i in ordenados if isinstance(i.get(campo), (int, float))]
        if len(primeiros) < 1:
            saida[campo] = {"primeiro": None, "ultimo": None, "delta": None}
            continue
        primeiro = primeiros[0]
        ultimo = primeiros[-1]
        delta = round(ultimo - primeiro, 2)
        saida[campo] = {"primeiro": primeiro, "ultimo": ultimo, "delta": delta}
    return saida


def _serie_30d(items: list[dict[str, Any]], campo: str) -> list[float]:
    """Retorna até 30 pontos numéricos do campo, em ordem cronológica."""
    ordenados = sorted(items, key=lambda i: str(i.get("data") or ""))
    pontos: list[float] = []
    for item in ordenados[-30:]:
        valor = item.get(campo)
        if isinstance(valor, (int, float)):
            pontos.append(float(valor))
    return pontos


def _formatar_delta(delta: float, unidade: str) -> tuple[str, str]:
    """Retorna (texto_delta, classe_css) baseado no sinal."""
    if abs(delta) < 0.05:
        return ("estável / 30d", "med-delta-flat")
    sinal = "↘" if delta < 0 else "↗"
    classe = "med-delta-up" if delta < 0 else "med-delta-down"
    sinal_num = f"{delta:+.1f}".replace("-", "−")
    return (f"{sinal} {sinal_num}{unidade} / 30d", classe)


def _card_medida_html(items: list[dict[str, Any]], campo: str) -> str:
    """UX-V-2.12: card com label + valor + delta 30d + sparkline.

    Quando ``items`` tem 0 pontos do campo, renderiza placeholder ``--``.
    Quando tem 1 ponto, renderiza valor sem sparkline (degradação graciosa).
    """
    from src.dashboard.componentes.ui import sparkline_html

    label = LABEL_CAMPO[campo].upper()
    unidade = UNIDADES[campo]
    cor = CORES_METRICAS.get(campo, "var(--accent-purple)")

    pontos = _serie_30d(items, campo)
    if not pontos:
        return minificar(
            f'<div class="med-card" style="--med-cor:{cor};">'
            f'<div class="med-head">'
            f'<span class="med-label">{label}</span>'
            f"</div>"
            f'<span class="med-vazio">--</span>'
            f"</div>"
        )

    valor = pontos[-1]
    delta = pontos[-1] - pontos[0] if len(pontos) >= 2 else 0.0
    delta_txt, delta_cls = _formatar_delta(delta, unidade)
    sparkline = sparkline_html(pontos, cor=cor, largura=240, altura=32) if len(pontos) >= 2 else ""
    spark_block = f'<div class="med-sparkline">{sparkline}</div>' if sparkline else ""
    return minificar(
        f'<div class="med-card" style="--med-cor:{cor};">'
        f'<div class="med-head">'
        f'<span class="med-label">{label}</span>'
        f"</div>"
        f'<div class="med-valor">{valor:.1f}'
        f'<span class="med-unid">{unidade}</span></div>'
        f'<div class="med-delta {delta_cls}">{delta_txt}</div>'
        f"{spark_block}"
        f"</div>"
    )


def _toggle_pessoa_html(pessoa_atual: str) -> str:
    """UX-V-2.12: toggle Pessoa A/B linkando para query string."""
    cor_a = "var(--accent-purple)"
    cor_b = "var(--accent-pink)"
    classe_a = "med-tab ativo" if pessoa_atual == "pessoa_a" else "med-tab"
    classe_b = "med-tab ativo" if pessoa_atual == "pessoa_b" else "med-tab"
    cor_atual = cor_a if pessoa_atual == "pessoa_a" else cor_b
    return minificar(
        f'<div class="med-pessoa-tabs" style="--med-cor-pessoa:{cor_atual};">'
        f'<a class="{classe_a}" '
        f'href="?cluster=Bem-estar&tab=Medidas&pessoa=pessoa_a" '
        f'style="text-decoration:none;">PESSOA A</a>'
        f'<a class="{classe_b}" '
        f'href="?cluster=Bem-estar&tab=Medidas&pessoa=pessoa_b" '
        f'style="text-decoration:none;">PESSOA B</a>'
        f"</div>"
    )


def _agrupar_semanas(items: list[dict[str, Any]], n: int = 6) -> list[dict[str, Any]]:
    """Retorna até ``n`` itens mais recentes (1 por semana ISO), DESC."""
    if not items:
        return []
    ordenados = sorted(items, key=lambda i: str(i.get("data") or ""), reverse=True)
    vistos: dict[str, dict[str, Any]] = {}
    for item in ordenados:
        data_str = str(item.get("data") or "")
        if not data_str:
            continue
        try:
            ts = pd.Timestamp(data_str)
        except (ValueError, TypeError):
            continue
        chave = f"{ts.isocalendar().year}-W{ts.isocalendar().week:02d}"
        if chave not in vistos:
            vistos[chave] = item
        if len(vistos) >= n:
            break
    return list(vistos.values())


def _formatar_data_pt(data_str: str) -> str:
    """Converte ``2026-04-01`` em ``01 abr 26`` (PT-BR)."""
    meses = {
        1: "jan",
        2: "fev",
        3: "mar",
        4: "abr",
        5: "mai",
        6: "jun",
        7: "jul",
        8: "ago",
        9: "set",
        10: "out",
        11: "nov",
        12: "dez",
    }
    try:
        ts = pd.Timestamp(data_str)
    except (ValueError, TypeError):
        return data_str
    return f"{ts.day:02d} {meses[ts.month]} {ts.year % 100:02d}"


def _coluna_tem_dado(items: list[dict[str, Any]], campo: str) -> bool:
    """UX-V-2.12.A: True se ao menos 1 item tem valor numérico no campo."""
    return any(isinstance(i.get(campo), (int, float)) for i in items)


def _tabela_historico_html(items: list[dict[str, Any]], pessoa: str) -> str:
    """UX-V-2.12: tabela das 6 semanas mais recentes.

    UX-V-2.12.A: colunas fisiológicas (gordura_pct, pressao, freq_card,
    sono_horas) aparecem somente quando ao menos 1 dos itens semanais
    expostos tem dado numérico no campo (padrão (o) -- retrocompatível).
    """
    semanas = _agrupar_semanas(items, n=6)
    if not semanas:
        return ""
    pessoa_label = (
        "Pessoa A" if pessoa == "pessoa_a" else ("Pessoa B" if pessoa == "pessoa_b" else "Casal")
    )

    def _cel(v: Any, unidade: str = "") -> str:
        if not isinstance(v, (int, float)):
            return "<td>--</td>"
        sufixo = f" {unidade}" if unidade else ""
        return f'<td><span class="v">{v:.1f}</span>{sufixo}</td>'

    # Colunas-base sempre visíveis.
    colunas_base: list[tuple[str, str, str]] = [
        ("peso", "peso", "kg"),
        ("cintura", "cintura", "cm"),
        ("quadril", "quadril", "cm"),
        ("peito", "peito", "cm"),
    ]
    # Colunas fisiológicas, adicionadas só se houver dado.
    colunas_extras: list[tuple[str, str, str]] = []
    for campo, header, unidade in (
        ("gordura_pct", "bf%", "%"),
        ("pressao_sis", "press. sis.", "mmHg"),
        ("pressao_dia", "press. dia.", "mmHg"),
        ("freq_card", "freq. card.", "bpm"),
        ("sono_horas", "sono", "h"),
    ):
        if _coluna_tem_dado(semanas, campo):
            colunas_extras.append((campo, header, unidade))
    colunas = colunas_base + colunas_extras

    linhas: list[str] = []
    for item in semanas:
        data_pt = _formatar_data_pt(str(item.get("data") or ""))
        celulas = "".join(_cel(item.get(campo), unidade) for campo, _, unidade in colunas)
        linhas.append(f"<tr><td>{data_pt}</td>{celulas}</tr>")
    cabecalho = "".join(f"<th>{header}</th>" for _, header, _ in colunas)
    return minificar(
        f'<div class="med-hist-card">'
        f"<h3>Histórico semanal · últimas 6 semanas · "
        f"{pessoa_label}</h3>"
        f'<table class="med-tbl">'
        f"<thead><tr><th>data</th>{cabecalho}</tr></thead>"
        f"<tbody>{''.join(linhas)}</tbody>"
        f"</table>"
        f"</div>"
    )


def _comparativo_card_html(campo: str, dados: dict[str, float | None]) -> str:
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
        f"border:1px solid {CORES['texto_sec']}33;border-radius:6px;"
        f'padding:14px;">'
        f'  <div style="font-family:ui-monospace,monospace;font-size:10px;'
        f"                letter-spacing:0.10em;text-transform:uppercase;"
        f'                color:{CORES["texto_muted"]};margin-bottom:8px;">{label}</div>'
        f'  <div style="font-size:20px;font-weight:500;color:{CORES["texto"]};'
        f'                font-variant-numeric:tabular-nums;">{valor_str}</div>'
        f'  <div style="font-family:ui-monospace,monospace;font-size:11px;'
        f'                color:{cor_delta};margin-top:6px;">{delta_str}</div>'
        f"</div>"
    )


def _skeleton_mockup_html() -> str:
    """UX-V-2.12-FIX: skeleton canônico do mockup `24-medidas.html`.

    Renderiza 6 cards corporais (peso / gordura corp. / cintura / pressão /
    frequência rep. / sono médio) com valor `--`, unidade, delta placeholder e
    sparkline-skeleton (linha cinza pontilhada). Em seguida tabela "Histórico
    semanal · últimas 6 semanas" com 6 linhas placeholder. Usado dentro do
    bloco :func:`fallback_estado_inicial_html` quando vault está vazio.

    A escolha das 6 métricas e cores espelha exatamente o mockup -- nenhuma
    invenção numérica, apenas placeholders `--` (padrão (a) edit cirúrgico).
    """
    cards_meta: list[tuple[str, str, str]] = [
        ("peso", "kg", "var(--accent-purple)"),
        ("gordura corp.", "%", "var(--accent-orange)"),
        ("cintura", "cm", "var(--accent-yellow)"),
        ("pressão", "mmHg", "var(--accent-cyan)"),
        ("frequência rep.", "bpm", "var(--accent-green)"),
        ("sono médio", "/noite", "var(--accent-pink)"),
    ]

    cards: list[str] = []
    for nome, unidade, cor in cards_meta:
        cards.append(
            f'<div class="med-card med-card-skeleton" style="--med-cor:{cor};">'
            f'<div class="med-head">'
            f'<span class="med-label">{nome}</span>'
            f'<span class="med-data">--</span>'
            f"</div>"
            f'<div class="med-valor">--<span class="med-unid">{unidade}'
            f"</span></div>"
            f'<div class="med-delta med-delta-flat">delta vs 30d</div>'
            f'<div class="med-sparkline med-sparkline-skeleton">'
            f'<svg viewBox="0 0 240 32" preserveAspectRatio="none">'
            f'<line x1="2" y1="16" x2="238" y2="16" '
            f'stroke="var(--text-muted, #6b6f80)" stroke-width="1" '
            f'stroke-dasharray="3 4" />'
            f"</svg>"
            f"</div>"
            f"</div>"
        )

    grid_cards = f'<div class="med-grid med-grid-skeleton">{"".join(cards)}</div>'

    colunas = ("data", "peso", "bf%", "cintura", "pressão", "sono médio")
    cabecalho = "".join(f"<th>{c}</th>" for c in colunas)
    linhas: list[str] = []
    for _ in range(6):
        celulas = "".join('<td><span class="v">--</span></td>' for _ in colunas)
        linhas.append(f"<tr>{celulas}</tr>")
    tabela = (
        '<div class="med-hist-card med-hist-card-skeleton">'
        "<h3>Histórico semanal · últimas 6 semanas</h3>"
        '<table class="med-tbl">'
        f"<thead><tr>{cabecalho}</tr></thead>"
        f"<tbody>{''.join(linhas)}</tbody>"
        "</table>"
        "</div>"
    )

    return minificar(grid_cards + tabela)


def _page_header_html(qtd: int) -> str:
    """UX-U-03: usa helper canônico ``componentes/page_header``."""
    from src.dashboard.componentes.page_header import renderizar_page_header

    return renderizar_page_header(
        titulo="MEDIDAS · CORPO",
        subtitulo=("Métricas físicas registradas no vault. Comparativo última vs primeira."),
        sprint_tag="UX-RD-19",
        pills=[{"texto": f"{qtd} registros", "tipo": "generica"}],
    )


def renderizar(
    dados: dict[str, pd.DataFrame],
    periodo: str,
    pessoa: str,
    ctx: dict | None = None,
) -> None:
    """Renderiza Bem-estar / Medidas (UX-T-24 + UX-V-2.12)."""
    from src.dashboard.componentes.topbar_actions import renderizar_grupo_acoes
    from src.dashboard.componentes.ui import carregar_css_pagina

    renderizar_grupo_acoes(
        [
            {"label": "Importar Mi Fit", "glyph": "upload", "title": "Balança Xiaomi"},
            {"label": "Registrar", "primary": True, "glyph": "plus", "title": "Peso, BF%, cintura"},
        ]
    )

    del dados, periodo, ctx

    # UX-V-2.12: CSS dedicado da página (tokens via components.css).
    st.markdown(minificar(carregar_css_pagina("be_medidas")), unsafe_allow_html=True)

    vault_root = descobrir_vault_root()
    items = _carregar_medidas(vault_root)

    if pessoa in {"pessoa_a", "pessoa_b"}:
        items_filtrados = [i for i in items if i.get("autor") == pessoa]
    else:
        items_filtrados = list(items)

    st.markdown(_page_header_html(len(items_filtrados)), unsafe_allow_html=True)

    if vault_root is None:
        st.warning(
            "Vault Bem-estar não encontrado. Configure `OUROBOROS_VAULT` para visualizar medidas."
        )
        return

    if not items_filtrados:
        from src.dashboard.componentes.ui import (
            fallback_estado_inicial_html,
            ler_sync_info,
        )

        # UX-V-2.12-FIX: toggle Pessoa A/B sempre presente, mesmo no fallback.
        st.markdown(_toggle_pessoa_html(pessoa), unsafe_allow_html=True)
        st.markdown(
            fallback_estado_inicial_html(
                titulo="MEDIDAS · sem registros ainda",
                descricao=(
                    "Métricas físicas (peso, gordura corp., cintura, pressão, "
                    "frequência cardíaca, sono médio) são capturadas no app "
                    "mobile via integração Mi Fit/Garmin ou entrada manual. "
                    "Cada medida vira um arquivo <code>.md</code> em "
                    "<code>vault/medidas/&lt;pessoa&gt;/</code>."
                ),
                skeleton_html=_skeleton_mockup_html(),
                cta_secao="medidas",
                sync_info=ler_sync_info(),
            ),
            unsafe_allow_html=True,
        )
        return

    # UX-V-2.12: toggle Pessoa A/B.
    st.markdown(_toggle_pessoa_html(pessoa), unsafe_allow_html=True)

    # UX-V-2.12: grid de 6 cards (peso/cintura/quadril/peito/braço/coxa)
    # com sparkline 30d + variação. ``_comparativo`` antigo é mantido
    # para retrocompatibilidade dos testes em test_be_resto.py.
    cards_html = "".join(_card_medida_html(items_filtrados, campo) for campo in CAMPOS)
    st.markdown(
        f'<div class="med-grid">{cards_html}</div>',
        unsafe_allow_html=True,
    )

    # UX-V-2.12: tabela histórico das 6 semanas mais recentes.
    tabela_html = _tabela_historico_html(items_filtrados, pessoa)
    if tabela_html:
        st.markdown(tabela_html, unsafe_allow_html=True)

    # Histórico legado de peso (line_chart Streamlit) preservado abaixo
    # do bloco novo para continuidade visual de dashboards já adotados.
    st.markdown("###### ")
    df = pd.DataFrame(items_filtrados)
    if "data" in df.columns and "peso" in df.columns:
        df_peso = df[["data", "peso"]].dropna()
        if not df_peso.empty:
            df_peso = df_peso.sort_values("data").set_index("data")
            st.markdown(
                f'<h3 style="font-family:ui-monospace,monospace;font-size:11px;'
                f"letter-spacing:0.10em;text-transform:uppercase;"
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
            f"letter-spacing:0.10em;text-transform:uppercase;"
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
                        f"border:1px solid {CORES['texto_sec']}33;"
                        f"color:{CORES['texto_muted']};"
                        f"font-family:ui-monospace,monospace;font-size:10px;"
                        f'text-align:center;padding:6px;">{p}</div>'
                    ),
                    unsafe_allow_html=True,
                )


# "O corpo é o templo do espírito." -- adágio antigo, citado por Cícero
