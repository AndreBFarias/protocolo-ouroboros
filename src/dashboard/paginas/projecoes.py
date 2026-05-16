"""Página Projeções (UX-RD-08): 3 cenários 5 anos + marcos sobrepostos.

Reescrita conforme mockup ``novo-mockup/mockups/05-projecoes.html``.
Estrutura:

1. ``page-header`` com título "PROJEÇÕES", subtítulo explicando os 3
   cenários (pessimista 6%, realista 9%, otimista 13%) ao longo de 60
   meses, sprint-tag e pill "simulação";
2. KPI strip — patrimônio hoje, aporte mensal médio, projeção realista
   em 5 anos, ano de independência financeira;
3. Grid 2:1 com gráfico Plotly multi-line (3 cenários × 60 meses) e
   cards laterais com os marcos do cenário realista (reserva 100%,
   entrada apartamento, etc);
4. Trio de cards "scenarios" com badge da cor do cenário e métricas
   (aporte ano, juros, multiplicador);
5. Simulação personalizada (slider + gráfico) — preserva fluxo legado
   conectado a ``projetar_com_economia``.

A função pública ``renderizar(dados, mes_selecionado, pessoa)`` mantém a
mesma assinatura usada por ``app.py`` (sem ``ctx`` -- lição UX-RD-06).
A lógica de cálculo em ``src/projections/scenarios.py`` é preservada
intocada (regra ``forbidden`` da spec UX-RD-08).
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.dashboard import tema
from src.dashboard.componentes.html_utils import minificar
from src.dashboard.componentes.ui import (
    callout_html,
    carregar_css_pagina,
    subtitulo_secao_html,
)
from src.dashboard.dados import (
    filtrar_por_forma_pagamento,
    filtrar_por_pessoa,
    filtro_forma_ativo,
    formatar_moeda,
)
from src.dashboard.tema import (
    CORES,
    FONTE_MINIMA,
    LAYOUT_PLOTLY,
    aplicar_locale_ptbr,
    rgba_cor,
)
from src.dashboard.tema_plotly import st_plotly_chart_dracula

# ---------------------------------------------------------------------------
# Tokens de cenário — mapa cor por cenário (UX-RD-08).
# Espelha o mockup ``05-projecoes.html``: vermelho/ciano/verde com width=2.
# ---------------------------------------------------------------------------
CENARIO_PESSIMISTA: str = "negativo"
CENARIO_REALISTA: str = "neutro"
CENARIO_OTIMISTA: str = "positivo"

# Multiplicadores de retorno anual por cenário (UX-RD-08).
TAXA_PESSIMISTA: float = 0.06  # CDI / sem risco
TAXA_REALISTA: float = 0.09  # carteira balanceada
TAXA_OTIMISTA: float = 0.13  # IBOV histórico

# Horizonte canônico em meses (UX-RD-08: 5 anos).
HORIZONTE_MESES: int = 60

# Opções do seletor de horizonte (UX-V-2.0).
HORIZONTES_DISPONIVEIS: list[tuple[str, int]] = [
    ("5 anos", 60),
    ("10 anos", 120),
    ("15 anos", 180),
    ("20 anos", 240),
    ("25 anos", 300),
]

# Marcos canônicos do mockup 05-projecoes.html (UX-V-2.0).
# Cada tupla: (valor_R$, label, cor_token).
MARCOS_CANONICOS: list[tuple[float, str, str]] = [
    (100_000.0, "1ª centena · 100k", "neutro"),
    (60_000.0, "Reserva 6 meses · 60k", "positivo"),
    (120_000.0, "Entrada apto · 120k", "alerta"),
    (250_000.0, "1/4 milhão", "destaque"),
    (500_000.0, "1/2 milhão", "superfluo"),
]


# ---------------------------------------------------------------------------
# Funções puras (testáveis sem Streamlit)
# ---------------------------------------------------------------------------


def _projetar_curva(
    inicial: float, taxa_anual: float, aporte_mensal: float, meses: int = HORIZONTE_MESES
) -> list[float]:
    """Projeção de patrimônio mês a mês com juros compostos + aporte fixo.

    Retorna lista de tamanho ``meses + 1`` (inclui ponto inicial). Lógica
    canônica do mockup: ``v = v * (1 + taxa/12) + aporte``. A função
    ``src/projections/scenarios.py`` permanece a fonte para projeções de 12
    meses baseadas no extrato real; esta serve aos 3 cenários de longo
    prazo da página de projeções.
    """
    arr: list[float] = [inicial]
    valor = inicial
    taxa_mensal = taxa_anual / 12.0
    for _ in range(meses):
        valor = valor * (1.0 + taxa_mensal) + aporte_mensal
        arr.append(valor)
    return arr


def _meses_ate_meta(curva: list[float], meta: float) -> int | None:
    """Primeiro índice (mês) em que ``curva[i] >= meta``. ``None`` se nunca."""
    for i, v in enumerate(curva):
        if v >= meta:
            return i
    return None


def _formatar_meses(valor: int | None) -> str:
    """Formata quantidade de meses para exibição."""
    if valor is None:
        return "Inalcançável no ritmo atual"
    if valor == 0:
        return "Já atingido"
    return f"{valor} meses"


def _transacoes_do_extrato(
    dados: dict[str, pd.DataFrame],
    pessoa: str = "Todos",
) -> list[dict]:
    """Converte DataFrame de extrato para lista de dicts, filtrando por pessoa."""
    if "extrato" not in dados:
        return []
    df = filtrar_por_forma_pagamento(
        filtrar_por_pessoa(dados["extrato"], pessoa), filtro_forma_ativo()
    )
    return [row.to_dict() for _, row in df.iterrows()]


# ---------------------------------------------------------------------------
# Helpers preservados da Sprint 92a.10 (retrocompat — testes legados em
# tests/test_dashboard_projecoes_ritmo.py importam ``_cor_por_sinal_ritmo``
# e ``_metric_ritmo_html``). UX-RD-08 reescreve a página, mas mantém estes
# helpers puros para não quebrar contratos existentes.
# ---------------------------------------------------------------------------


def _formatar_ritmo(valor: float | None) -> str:
    """Formata um ritmo mensal para exibição. ``None`` vira texto explicativo."""
    if valor is None:
        return "Dados insuficientes"
    return formatar_moeda(valor)


def _cor_por_sinal_ritmo(valor: float | None) -> str:
    """Sprint 92a.10: cor Dracula do ritmo conforme o sinal do valor.

    Retorna hex pronto para CSS: verde quando positivo, vermelho quando
    negativo, cinza (``texto_sec``) quando ``None``. Valor exatamente zero
    é tratado como neutro (cinza) para não fingir saudável sem ritmo real.
    """
    if valor is None or valor == 0:
        return CORES["texto_sec"]
    return CORES["positivo"] if valor > 0 else CORES["negativo"]


def _metric_ritmo_html(titulo: str, valor: float | None) -> str:
    """Sprint 92a.10: renderização custom do cartão de ritmo com cor por sinal.

    Substitui ``st.metric`` para permitir coloração por sinal do valor
    (verde positivo, vermelho negativo, cinza quando ``None``). Mantém
    contraste visual Dracula e tipografia equivalente ao widget nativo.
    """
    cor = _cor_por_sinal_ritmo(valor)
    texto = _formatar_ritmo(valor)
    return (
        '<div class="ouroboros-ritmo-card">'
        '<p style="color: var(--color-texto-sec);'
        f" font-size: {FONTE_MINIMA}px;"
        f' margin: 0 0 2px 0;">{titulo}</p>'
        f'<p style="color: {cor};'
        " font-size: 28px;"
        " font-weight: 700;"
        f' margin: 0;">{texto}</p>'
        "</div>"
    )


# ---------------------------------------------------------------------------
# HTML helpers (page-header, kpi-strip, marcos, scenarios)
# ---------------------------------------------------------------------------


def _page_header_html(saldo_inicial: float) -> str:
    return minificar(
        f"""
        <div class="page-header">
          <div>
            <h1 class="page-title">PROJEÇÕES</h1>
            <p class="page-subtitle">
              Simulação de patrimônio em <strong>5 anos</strong> baseada em
              três cenários: pessimista (CDI), realista (mistura conservadora)
              e otimista (IBOV histórico). Aporte mensal e taxa derivam do
              ritmo observado no extrato — saldo inicial
              <strong>{formatar_moeda(saldo_inicial)}</strong>.
            </p>
          </div>
          <div class="page-meta">
            <span class="sprint-tag">UX-RD-08</span>
            <span class="pill pill-d7-calibracao">simulação</span>
          </div>
        </div>
        """
    )


def _kpi_strip_html(
    inicial: float,
    aporte_mensal: float,
    realista_final: float,
    independencia_label: str,
    horizonte_anos: int,
    taxa_realista: float,
) -> str:
    """Strip de 4 KPIs (UX-V-2.0). Estilos em ``css/paginas/projecoes.css``."""
    return minificar(
        f"""
        <div class="proj-kpi-row">
          <div class="proj-kpi-card">
            <div class="proj-kpi-label">Patrimônio hoje</div>
            <div class="proj-kpi-valor">{formatar_moeda(inicial)}</div>
            <div class="proj-kpi-desc">saldo médio mensal observado</div>
          </div>
          <div class="proj-kpi-card">
            <div class="proj-kpi-label">Aporte mensal médio</div>
            <div class="proj-kpi-valor proj-kpi-valor-destaque">
              {formatar_moeda(aporte_mensal)}
            </div>
            <div class="proj-kpi-desc">extraído do ritmo de saldo</div>
          </div>
          <div class="proj-kpi-card">
            <div class="proj-kpi-label">Em {horizonte_anos} anos · realista</div>
            <div class="proj-kpi-valor proj-kpi-valor-destaque">
              {formatar_moeda(realista_final)}
            </div>
            <div class="proj-kpi-desc">{taxa_realista * 100:.1f}% a.a. · projeção composta</div>
          </div>
          <div class="proj-kpi-card">
            <div class="proj-kpi-label">Independência financeira</div>
            <div class="proj-kpi-valor proj-kpi-valor-otimista">{independencia_label}</div>
            <div class="proj-kpi-desc">FIRE 25× custo · cenário realista</div>
          </div>
        </div>
        """
    )


def _card_marcos_html(marcos: list[tuple[str, str, str]]) -> str:
    """Card lateral com lista de marcos do cenário realista.

    Cada marco é tupla ``(nome, descrição, cor_token)``. Estilos em
    ``css/paginas/projecoes.css``. Mantém ``border-left:2px solid <hex>``
    inline para retrocompat com testes regressivos (UX-V-2.0).
    """

    def _li(nome: str, desc: str, cor: str) -> str:
        cor_hex = CORES.get(cor, CORES["destaque"])
        return (
            f'<li class="proj-marcos-item" style="border-left:2px solid {cor_hex};">'
            f'<strong class="proj-marcos-item-nome">{nome}</strong>'
            f'<span class="proj-marcos-item-desc">{desc}</span>'
            "</li>"
        )

    itens = "".join(_li(n, d, c) for n, d, c in marcos)
    return minificar(
        f"""
        <div class="proj-marcos-card">
          <h3 class="proj-marcos-titulo">Marcos · realista</h3>
          <ul class="proj-marcos-lista">{itens}</ul>
        </div>
        """
    )


def _card_cenario_html(
    titulo_badge: str,
    nome: str,
    valor_5a: float,
    taxa_label: str,
    aporte_ano: float,
    juros: float,
    multiplicador: float,
    cor_token: str,
    ativo: bool = False,
) -> str:
    cor = CORES.get(cor_token, CORES["destaque"])
    box_shadow = f"box-shadow:0 0 0 1px {cor};" if ativo else "box-shadow:none;"
    return minificar(
        f"""
        <div style="background:{CORES["card_fundo"]};
                    border:1px solid {rgba_cor(CORES["texto_sec"], 0.20)};
                    border-top:3px solid {cor};
                    border-radius:8px;
                    padding:18px;
                    {box_shadow}">
          <span style="font-family:monospace;
                       font-size:10px;
                       letter-spacing:0.10em;
                       text-transform:uppercase;
                       color:{cor};">{titulo_badge}</span>
          <h4 style="margin:4px 0 14px 0;
                     font-size:18px;
                     font-weight:500;
                     color:{CORES["texto"]};">{nome}</h4>
          <div style="font-family:monospace;
                      font-size:26px;
                      font-weight:500;
                      font-variant-numeric:tabular-nums;
                      line-height:1;
                      color:{CORES["texto"]};">{formatar_moeda(valor_5a)}</div>
          <div style="font-family:monospace;
                      font-size:11px;
                      color:{CORES["texto_sec"]};
                      margin-top:6px;">5 anos · {taxa_label}</div>
          <ul style="list-style:none;
                     margin:14px 0 0 0;
                     padding:14px 0 0 0;
                     border-top:1px dashed {rgba_cor(CORES["texto_sec"], 0.30)};
                     display:flex;
                     flex-direction:column;
                     gap:6px;">
            <li style="display:flex;
                       justify-content:space-between;
                       font-size:12px;
                       color:{CORES["texto_sec"]};
                       font-family:monospace;">
              <span>aporte ano</span>
              <strong style="color:{CORES["texto"]};">{formatar_moeda(aporte_ano)}</strong>
            </li>
            <li style="display:flex;
                       justify-content:space-between;
                       font-size:12px;
                       color:{CORES["texto_sec"]};
                       font-family:monospace;">
              <span>juros</span>
              <strong style="color:{cor};">{formatar_moeda(juros)}</strong>
            </li>
            <li style="display:flex;
                       justify-content:space-between;
                       font-size:12px;
                       color:{CORES["texto_sec"]};
                       font-family:monospace;">
              <span>multiplicador</span>
              <strong style="color:{CORES["texto"]};">{multiplicador:.1f}×</strong>
            </li>
          </ul>
        </div>
        """
    )


# ---------------------------------------------------------------------------
# Construção das curvas e marcos a partir das transações reais
# ---------------------------------------------------------------------------


def _saldo_inicial_estimado(transacoes: list[dict]) -> float:
    """Soma receitas menos despesas/impostos como aproximação de patrimônio.

    Mesma lógica usada em ``_calcular_projecao_5a`` — extraída como helper
    para o ``page-header`` e cabeçalhos secundários.
    """
    total = 0.0
    for t in transacoes:
        tipo = t.get("tipo")
        if tipo in ("Despesa", "Imposto"):
            total -= float(t.get("valor", 0.0) or 0.0)
        elif tipo == "Receita":
            total += float(t.get("valor", 0.0) or 0.0)
    return max(total, 0.0)


def _calcular_aporte_robusto(transacoes: list[dict]) -> tuple[float, float]:
    """Estima aporte mensal médio e despesa anual a partir do extrato real.

    Bug raiz UX-V-2.0: usar apenas ``saldo_medio`` (3 últimos meses) gerava
    R$ 0,00 quando esses meses tinham saldo negativo ou zero, mesmo havendo
    saldo positivo histórico relevante. Esta função examina três janelas
    (histórico, 12 meses, 3 meses) e devolve o **maior valor positivo**
    entre elas — fallback robusto.

    Retorna tupla ``(aporte_mensal, despesa_anual)``. ``despesa_anual`` é
    usada para o cálculo FIRE de independência financeira (25× custo).
    """
    from src.projections.scenarios import _calcular_medias, calcular_ritmos

    candidatos: list[float] = []
    ritmos = calcular_ritmos(transacoes)
    for chave in ("historico", "12_meses", "3_meses"):
        val = ritmos.get(chave)
        if val is not None and val > 0:
            candidatos.append(float(val))

    aporte = max(candidatos) if candidatos else 0.0

    medias = _calcular_medias(transacoes, n_meses=12) if transacoes else {}
    despesa_mensal = float(medias.get("despesa_media", 0.0) or 0.0)
    despesa_anual = max(0.0, despesa_mensal * 12.0)

    return aporte, despesa_anual


def _calcular_projecao_5a(
    transacoes: list[dict],
    aporte_override: float | None = None,
    taxa_override: float | None = None,
    horizonte_meses: int = HORIZONTE_MESES,
) -> dict[str, Any]:
    """Combina ``projetar_cenarios`` (lógica preservada) com extrapolação Na.

    Por padrão extrai aporte robusto via ``_calcular_aporte_robusto``
    (corrige bug R$ 0,00 — UX-V-2.0). Se ``aporte_override`` é fornecido
    (slider), substitui o cálculo derivado. Se ``taxa_override`` é dado,
    aplica-se ao cenário **realista** (pessimista/otimista mantêm deltas
    canônicos -3pp e +4pp para preservar a legenda do gráfico).
    """
    from src.projections.scenarios import projetar_cenarios

    cenarios = projetar_cenarios(transacoes)
    saldo_medio = float(cenarios.get("saldo_medio", 0.0) or 0.0)

    aporte_real, despesa_anual = _calcular_aporte_robusto(transacoes)
    if aporte_override is not None:
        aporte = max(0.0, float(aporte_override))
    else:
        aporte = aporte_real

    if taxa_override is not None:
        taxa_real = max(0.0, float(taxa_override))
        taxa_pess = max(0.0, taxa_real - 0.03)
        taxa_otim = max(0.0, taxa_real + 0.04)
    else:
        taxa_pess, taxa_real, taxa_otim = TAXA_PESSIMISTA, TAXA_REALISTA, TAXA_OTIMISTA

    inicial = _saldo_inicial_estimado(transacoes)

    pess = _projetar_curva(inicial, taxa_pess, aporte, horizonte_meses)
    real = _projetar_curva(inicial, taxa_real, aporte, horizonte_meses)
    otim = _projetar_curva(inicial, taxa_otim, aporte, horizonte_meses)

    return {
        "inicial": inicial,
        "aporte": aporte,
        "aporte_observado": aporte_real,
        "despesa_anual": despesa_anual,
        "taxa_pessimista": taxa_pess,
        "taxa_realista": taxa_real,
        "taxa_otimista": taxa_otim,
        "horizonte_meses": horizonte_meses,
        "pessimista": pess,
        "realista": real,
        "otimista": otim,
        "saldo_medio_legado": saldo_medio,
    }


def _calcular_marcos_realista(
    curva_realista: list[float],
) -> list[tuple[float, str, str]]:
    """Lista de marcos visíveis no eixo Y do gráfico (cenário realista).

    Retorna os 5 marcos canônicos (UX-V-2.0) ordenados por valor. Mantém
    todos — mesmo os ainda não alcançados; o card lateral exibe
    "Inalcançável no ritmo atual" para aqueles fora do horizonte.
    """
    return sorted(MARCOS_CANONICOS, key=lambda m: m[0])


def _label_independencia(
    curva_realista: list[float],
    despesa_anual: float = 0.0,
) -> str:
    """Estima ano em que o patrimônio atinge a meta FIRE (25× custo anual).

    Regra "4% safe withdrawal" (Trinity Study): independência financeira
    = patrimônio cobrindo 25× o custo anual. Quando ``despesa_anual`` é
    desconhecida ou zero, faz fallback para 30× aporte mensal anualizado.

    Devolve string como "2042 · 16a" (formato do mockup) ou
    "fora do horizonte" quando inalcançável dentro da curva projetada.
    """
    import datetime

    if len(curva_realista) < 2:
        return "—"

    if despesa_anual > 0:
        meta = despesa_anual * 25
    else:
        aporte_estimado = max(0.0, (curva_realista[1] - curva_realista[0]) * 12)
        if aporte_estimado <= 0:
            return "fora do horizonte"
        meta = aporte_estimado * 30

    idx = _meses_ate_meta(curva_realista, meta)
    if idx is None or idx == 0:
        return "fora do horizonte"

    anos = idx / 12.0
    ano_alvo = datetime.date.today().year + int(round(anos))
    return f"{ano_alvo} · {anos:.0f}a"


# ---------------------------------------------------------------------------
# Função pública
# ---------------------------------------------------------------------------


def renderizar(
    dados: dict[str, pd.DataFrame],
    mes_selecionado: str,
    pessoa: str,
) -> None:
    """Renderiza a página de projeções financeiras (UX-RD-08 + UX-V-2.0)."""
    from src.dashboard.componentes.topbar_actions import renderizar_grupo_acoes

    renderizar_grupo_acoes(
        [
            {"label": "Comparar cenários", "glyph": "diff", "title": "A/B/C lado a lado"},
            {
                "label": "Salvar cenário",
                "primary": True,
                "glyph": "validar",
                "title": "Persistir cenário ativo",
            },
        ]
    )

    # CSS dedicado da página (UX-V-2.0).
    st.markdown(minificar(carregar_css_pagina("projecoes")), unsafe_allow_html=True)

    if "extrato" not in dados:
        st.markdown(
            callout_html("warning", "Nenhum dado de extrato disponível para projeções."),
            unsafe_allow_html=True,
        )
        return

    transacoes = _transacoes_do_extrato(dados, pessoa)
    if not transacoes:
        st.markdown(
            callout_html("info", "Sem transações suficientes para projeções."),
            unsafe_allow_html=True,
        )
        return

    # Aporte real observado (sem override) — usado como default do slider.
    aporte_observado, despesa_anual = _calcular_aporte_robusto(transacoes)
    aporte_default = int(round(max(500.0, aporte_observado)))
    aporte_slider_max = max(15_000, int(round(aporte_default * 2.5)))

    # 1. Page header
    saldo_inicial = _saldo_inicial_estimado(transacoes)
    st.markdown(_page_header_html(saldo_inicial), unsafe_allow_html=True)

    # 2. Bloco de controles interativos (UX-V-2.0)
    titulo_ctrl = "Simulador interativo · ajuste e recalcula em tempo real"
    st.markdown(
        f'<div class="proj-controls-wrap"><p class="proj-controls-titulo">{titulo_ctrl}</p></div>',
        unsafe_allow_html=True,
    )
    col_a, col_t, col_h = st.columns([1, 1, 1])
    with col_a:
        aporte_input = st.slider(
            "Aporte mensal (R$)",
            min_value=0,
            max_value=aporte_slider_max,
            value=aporte_default,
            step=100,
            key="proj_aporte_slider",
        )
    with col_t:
        retorno_pct = st.slider(
            "Retorno a.a. (%)",
            min_value=2.0,
            max_value=20.0,
            value=9.0,
            step=0.5,
            key="proj_taxa_slider",
        )
    with col_h:
        rotulos = [r for r, _ in HORIZONTES_DISPONIVEIS]
        horizonte_label = st.selectbox(
            "Horizonte",
            rotulos,
            index=0,
            key="proj_horizonte_select",
        )
        horizonte_meses = dict(HORIZONTES_DISPONIVEIS).get(horizonte_label, HORIZONTE_MESES)

    proj = _calcular_projecao_5a(
        transacoes,
        aporte_override=float(aporte_input),
        taxa_override=float(retorno_pct) / 100.0,
        horizonte_meses=int(horizonte_meses),
    )
    inicial = float(proj["inicial"])
    aporte = float(proj["aporte"])
    pess = proj["pessimista"]
    real = proj["realista"]
    otim = proj["otimista"]
    taxa_pess = float(proj["taxa_pessimista"])
    taxa_real = float(proj["taxa_realista"])
    taxa_otim = float(proj["taxa_otimista"])
    horizonte_anos = max(1, int(round(horizonte_meses / 12)))

    realista_final = float(real[-1])
    independencia_label = _label_independencia(real, despesa_anual)

    # 3. KPI strip
    st.markdown(
        _kpi_strip_html(
            inicial,
            aporte,
            realista_final,
            independencia_label,
            horizonte_anos,
            taxa_real,
        ),
        unsafe_allow_html=True,
    )

    # 4. Grid 2:1 (gráfico + marcos)
    col_graf, col_marcos = st.columns([2, 1])
    marcos_realista = _calcular_marcos_realista(real)
    with col_graf:
        _grafico_cenarios(pess, real, otim, marcos_realista)
    with col_marcos:
        marcos_card = [
            (label, _formatar_meses(_meses_ate_meta(real, valor)), cor)
            for valor, label, cor in marcos_realista
        ]
        st.markdown(_card_marcos_html(marcos_card), unsafe_allow_html=True)

    # 5. Trio de cards de cenário
    aporte_ano = aporte * 12.0
    cards_cenarios = minificar(
        f"""
        <div style="display:grid;
                    grid-template-columns:repeat(3,1fr);
                    gap:16px;
                    margin:18px 0;">
          {
            _card_cenario_html(
                "cenário pessimista",
                "CDI · Sem risco",
                float(pess[-1]),
                f"{taxa_pess * 100:.1f}% a.a.",
                aporte_ano,
                float(pess[-1]) - inicial - aporte_ano * horizonte_anos,
                float(pess[-1]) / inicial if inicial > 0 else 0.0,
                CENARIO_PESSIMISTA,
            )
        }
          {
            _card_cenario_html(
                "cenário realista · ativo",
                "Carteira balanceada",
                realista_final,
                f"{taxa_real * 100:.1f}% a.a.",
                aporte_ano,
                realista_final - inicial - aporte_ano * horizonte_anos,
                realista_final / inicial if inicial > 0 else 0.0,
                CENARIO_REALISTA,
                ativo=True,
            )
        }
          {
            _card_cenario_html(
                "cenário otimista",
                "IBOV · Histórico",
                float(otim[-1]),
                f"{taxa_otim * 100:.1f}% a.a.",
                aporte_ano,
                float(otim[-1]) - inicial - aporte_ano * horizonte_anos,
                float(otim[-1]) / inicial if inicial > 0 else 0.0,
                CENARIO_OTIMISTA,
            )
        }
        </div>
        """
    )
    st.markdown(cards_cenarios, unsafe_allow_html=True)

    # 5. Simulação personalizada (preserva fluxo legado)
    st.markdown("---")
    # Subtítulo de seção (substitui hero_titulo_html legado — 2026-05-06).
    # Hero é exclusivo do page-header canônico no topo da página.
    st.markdown(
        subtitulo_secao_html("Simulação personalizada — slider de economia adicional (12 meses)."),
        unsafe_allow_html=True,
    )
    # UX-V-FINAL-FIX defeito 6 (2026-05-08): slider parte de R$ 100
    # (min_value/value) para não exigir interação do usuário e já mostrar
    # cenário simulado pré-pronto. Step 50 dá granularidade fina.
    economia_extra = st.slider(
        "Se eu economizar a mais por mês (R$):",
        min_value=100,
        max_value=5000,
        value=100,
        step=50,
        key="slider_economia",
    )
    if economia_extra > 0:
        from src.projections.scenarios import (
            projetar_cenarios,
            projetar_com_economia,
        )

        cenarios_legado = projetar_cenarios(transacoes)
        projecao_custom = projetar_com_economia(transacoes, float(economia_extra))
        projecao_base = cenarios_legado["cenario_atual"]["projecao_12_meses"]
        _grafico_simulacao(projecao_base, projecao_custom, economia_extra)


# ---------------------------------------------------------------------------
# Gráficos Plotly (cenários 5 anos + simulação 12 meses)
# ---------------------------------------------------------------------------


def _grafico_cenarios(
    pess: list[float],
    real: list[float],
    otim: list[float],
    marcos: list[tuple[float, str, str]],
) -> None:
    """Gráfico Plotly multi-line: 3 cenários × 60 meses + marcos verticais.

    Cores derivadas de ``CORES`` (sem hardcoded hex). Layout custom
    (paper/plot/font) garantido pela tupla canônica do mockup
    UX-RD-08: paper=fundo, plot=card_fundo, font=texto.
    """
    meses_eixo = list(range(len(real)))

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=meses_eixo,
            y=pess,
            name="Pessimista (6%)",
            mode="lines",
            line=dict(color=CORES[CENARIO_PESSIMISTA], width=2),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=meses_eixo,
            y=real,
            name="Realista (9%)",
            mode="lines",
            line=dict(color=CORES[CENARIO_REALISTA], width=2),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=meses_eixo,
            y=otim,
            name="Otimista (13%)",
            mode="lines",
            line=dict(color=CORES[CENARIO_OTIMISTA], width=2),
        )
    )

    # Marcos verticais (add_vline) — quando o cenário realista atinge
    # cada meta. Label rotacionado 90° conforme spec.
    for valor, label, cor_token in marcos:
        idx = _meses_ate_meta(real, valor)
        if idx is None or idx == 0:
            continue
        cor_marco = CORES.get(cor_token, CORES["destaque"])
        fig.add_vline(
            x=idx,
            line_dash="dash",
            line_color=cor_marco,
            annotation_text=label,
            annotation_position="top",
            annotation_textangle=-90,
            annotation_font_color=cor_marco,
            annotation_font_size=FONTE_MINIMA,
        )

    layout_custom = dict(LAYOUT_PLOTLY)
    layout_custom["paper_bgcolor"] = CORES["fundo"]
    layout_custom["plot_bgcolor"] = CORES["card_fundo"]
    fig.update_layout(
        **layout_custom,
        yaxis_title="Patrimônio Acumulado (R$)",
        xaxis_title="Meses",
        hovermode="x unified",
    )
    tema.legenda_abaixo(fig)
    aplicar_locale_ptbr(fig)
    st_plotly_chart_dracula(fig)


def _grafico_simulacao(
    projecao_base: list[dict],
    projecao_custom: list[dict],
    economia: int,
) -> None:
    """Gráfico de simulação com comparação ao cenário base (12 meses)."""
    from src.projections.scenarios import VALOR_ENTRADA_APE, VALOR_RESERVA_EMERGENCIA

    meses_labels = [p["mes"] for p in projecao_custom]
    valores_custom = [p["acumulado"] for p in projecao_custom]
    valores_base = [p["acumulado"] for p in projecao_base]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=meses_labels,
            y=valores_base,
            name="Cenário base",
            mode="lines",
            line=dict(color=CORES["texto_sec"], width=2, dash="dot"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=meses_labels,
            y=valores_custom,
            name=f"Economizando +R$ {economia}/mês",
            mode="lines+markers",
            line=dict(color=CORES["destaque"], width=3),
            marker=dict(size=6),
            fill="tonexty",
            fillcolor=rgba_cor(CORES["destaque"], 0.08),
        )
    )

    fig.add_hline(
        y=VALOR_RESERVA_EMERGENCIA,
        line_dash="dot",
        line_color=CORES["positivo"],
        annotation_text="Reserva Emergência",
        annotation_position="top left",
        annotation_font_color=CORES["positivo"],
        annotation_font_size=FONTE_MINIMA,
    )
    fig.add_hline(
        y=VALOR_ENTRADA_APE,
        line_dash="dot",
        line_color=CORES["neutro"],
        annotation_text="Entrada Apê",
        annotation_position="top left",
        annotation_font_color=CORES["neutro"],
        annotation_font_size=FONTE_MINIMA,
    )

    layout_custom = dict(LAYOUT_PLOTLY)
    layout_custom["paper_bgcolor"] = CORES["fundo"]
    layout_custom["plot_bgcolor"] = CORES["card_fundo"]
    fig.update_layout(
        **layout_custom,
        yaxis_title="Patrimônio Acumulado (R$)",
        xaxis_title="Mês",
    )
    tema.legenda_abaixo(fig)
    aplicar_locale_ptbr(fig, valores_eixo_x=meses_labels)
    st_plotly_chart_dracula(fig)


# "A preparação de hoje determina a conquista de amanhã." -- Roger Staubach
