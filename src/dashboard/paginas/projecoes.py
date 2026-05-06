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
    callout_html,
    hero_titulo_html,
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
    realista_5a: float,
    independencia_label: str,
) -> str:
    cor_destaque = CORES["destaque"]
    cor_otimista = CORES[CENARIO_OTIMISTA]
    return minificar(
        f"""
        <div style="display:grid;
                    grid-template-columns:repeat(4,1fr);
                    gap:16px;
                    margin-bottom:18px;">
          <div style="background:{CORES["card_fundo"]};
                      border:1px solid {rgba_cor(CORES["texto_sec"], 0.20)};
                      border-radius:8px;
                      padding:18px;">
            <div style="font-size:{FONTE_MINIMA}px;
                        letter-spacing:0.08em;
                        text-transform:uppercase;
                        color:{CORES["texto_sec"]};">Patrimônio hoje</div>
            <div style="font-size:26px;
                        font-weight:500;
                        line-height:1;
                        margin-top:6px;
                        font-variant-numeric:tabular-nums;
                        color:{CORES["texto"]};">{formatar_moeda(inicial)}</div>
            <div style="font-size:11px;
                        color:{CORES["texto_sec"]};
                        margin-top:6px;">saldo médio mensal observado</div>
          </div>
          <div style="background:{CORES["card_fundo"]};
                      border:1px solid {rgba_cor(CORES["texto_sec"], 0.20)};
                      border-radius:8px;
                      padding:18px;">
            <div style="font-size:{FONTE_MINIMA}px;
                        letter-spacing:0.08em;
                        text-transform:uppercase;
                        color:{CORES["texto_sec"]};">Aporte mensal médio</div>
            <div style="font-size:26px;
                        font-weight:500;
                        line-height:1;
                        margin-top:6px;
                        font-variant-numeric:tabular-nums;
                        color:{cor_destaque};">{formatar_moeda(aporte_mensal)}</div>
            <div style="font-size:11px;
                        color:{CORES["texto_sec"]};
                        margin-top:6px;">extraído do ritmo de saldo</div>
          </div>
          <div style="background:{CORES["card_fundo"]};
                      border:1px solid {rgba_cor(CORES["texto_sec"], 0.20)};
                      border-radius:8px;
                      padding:18px;">
            <div style="font-size:{FONTE_MINIMA}px;
                        letter-spacing:0.08em;
                        text-transform:uppercase;
                        color:{CORES["texto_sec"]};">Em 5 anos · realista</div>
            <div style="font-size:26px;
                        font-weight:500;
                        line-height:1;
                        margin-top:6px;
                        font-variant-numeric:tabular-nums;
                        color:{cor_destaque};">{formatar_moeda(realista_5a)}</div>
            <div style="font-size:11px;
                        color:{CORES["texto_sec"]};
                        margin-top:6px;">9% a.a. · projeção composta</div>
          </div>
          <div style="background:{CORES["card_fundo"]};
                      border:1px solid {rgba_cor(CORES["texto_sec"], 0.20)};
                      border-radius:8px;
                      padding:18px;">
            <div style="font-size:{FONTE_MINIMA}px;
                        letter-spacing:0.08em;
                        text-transform:uppercase;
                        color:{CORES["texto_sec"]};">Independência financeira</div>
            <div style="font-size:18px;
                        font-weight:500;
                        line-height:1.1;
                        margin-top:6px;
                        font-variant-numeric:tabular-nums;
                        color:{cor_otimista};">{independencia_label}</div>
            <div style="font-size:11px;
                        color:{CORES["texto_sec"]};
                        margin-top:6px;">cenário realista</div>
          </div>
        </div>
        """
    )


def _card_marcos_html(marcos: list[tuple[str, str, str]]) -> str:
    """Card lateral com lista de marcos do cenário realista.

    Cada marco é uma tupla ``(nome, descrição, cor_token)`` em que
    ``cor_token`` é uma chave de ``CORES``.
    """
    itens = "".join(
        f"""
        <li style="display:flex;
                   flex-direction:column;
                   gap:2px;
                   border-left:2px solid {CORES.get(cor, CORES["destaque"])};
                   padding-left:12px;">
          <strong style="font-size:13px;
                         font-family:monospace;
                         color:{CORES["texto"]};">{nome}</strong>
          <span style="font-family:monospace;
                       font-size:11px;
                       color:{CORES["texto_sec"]};">{desc}</span>
        </li>
        """
        for nome, desc, cor in marcos
    )
    return minificar(
        f"""
        <div style="background:{CORES["card_fundo"]};
                    border:1px solid {rgba_cor(CORES["texto_sec"], 0.20)};
                    border-radius:8px;
                    padding:18px;">
          <h3 style="font-family:monospace;
                     font-size:11px;
                     letter-spacing:0.08em;
                     text-transform:uppercase;
                     color:{CORES["texto_sec"]};
                     margin:0 0 14px 0;
                     font-weight:500;">Marcos · realista</h3>
          <ul style="list-style:none;
                     margin:0;
                     padding:0;
                     display:flex;
                     flex-direction:column;
                     gap:14px;">
            {itens}
          </ul>
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
    box_shadow = (
        f"box-shadow:0 0 0 1px {cor};" if ativo else "box-shadow:none;"
    )
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


def _calcular_projecao_5a(
    transacoes: list[dict],
) -> dict[str, Any]:
    """Combina ``projetar_cenarios`` (lógica preservada) com extrapolação 5a.

    Usa ``saldo_medio`` como aporte mensal canônico e ``saldo_pos_infobase``
    como sensibilidade. Os 3 cenários da página de projeções derivam todos
    do mesmo aporte realista, variando apenas a taxa anual de retorno.

    O patrimônio inicial vem do saldo acumulado já realizado: tomamos a
    soma de receitas menos despesas das transações reais como ponto de
    partida. Mantém-se o contrato com ``src/projections/scenarios.py``
    (que continua sendo a fonte para o gráfico de 12 meses do legado).
    """
    from src.projections.scenarios import projetar_cenarios

    cenarios = projetar_cenarios(transacoes)
    saldo_medio = float(cenarios.get("saldo_medio", 0.0) or 0.0)
    aporte = max(0.0, saldo_medio)

    inicial = 0.0
    for t in transacoes:
        tipo = t.get("tipo")
        if tipo in ("Despesa", "Imposto"):
            inicial -= float(t.get("valor", 0.0) or 0.0)
        elif tipo == "Receita":
            inicial += float(t.get("valor", 0.0) or 0.0)
    inicial = max(inicial, 0.0)

    pess = _projetar_curva(inicial, TAXA_PESSIMISTA, aporte)
    real = _projetar_curva(inicial, TAXA_REALISTA, aporte)
    otim = _projetar_curva(inicial, TAXA_OTIMISTA, aporte)

    return {
        "inicial": inicial,
        "aporte": aporte,
        "pessimista": pess,
        "realista": real,
        "otimista": otim,
        "saldo_medio_legado": saldo_medio,
    }


def _calcular_marcos_realista(
    curva_realista: list[float],
) -> list[tuple[float, str, str]]:
    """Lista de marcos visíveis no eixo Y do gráfico (cenário realista).

    Retorna tuplas ``(valor, label, cor_token)`` ordenadas crescentemente
    por valor. Ignora marcos cuja meta nunca é atingida no horizonte de 5
    anos.
    """
    from src.projections.scenarios import VALOR_ENTRADA_APE, VALOR_RESERVA_EMERGENCIA

    candidatos: list[tuple[float, str, str]] = [
        (VALOR_RESERVA_EMERGENCIA, "Reserva 100%", CENARIO_REALISTA),
        (VALOR_ENTRADA_APE, "Entrada Apartamento", "destaque"),
        (250_000.0, "1/4 milhão", "alerta"),
        (500_000.0, "1/2 milhão", "superfluo"),
    ]
    teto = max(curva_realista) if curva_realista else 0.0
    return [m for m in candidatos if m[0] <= teto]


def _label_independencia(curva_realista: list[float]) -> str:
    """Estima ano de independência financeira (multiplicador 30× aporte anual).

    Heurística simples (não autoritativa) — se a curva nunca atinge o
    múltiplo, devolve "fora do horizonte".
    """
    if len(curva_realista) < 2:
        return "—"
    aporte_anual = max(0.0, (curva_realista[1] - curva_realista[0]) * 12)
    if aporte_anual <= 0:
        return "fora do horizonte"
    meta = aporte_anual * 30
    idx = _meses_ate_meta(curva_realista, meta)
    if idx is None:
        return "fora do horizonte"
    anos = idx / 12.0
    return f"{anos:.0f}a no ritmo"


# ---------------------------------------------------------------------------
# Função pública
# ---------------------------------------------------------------------------


def renderizar(
    dados: dict[str, pd.DataFrame],
    mes_selecionado: str,
    pessoa: str,
) -> None:
    """Renderiza a página de projeções financeiras (UX-RD-08)."""
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

    proj = _calcular_projecao_5a(transacoes)
    inicial = float(proj["inicial"])
    aporte = float(proj["aporte"])
    pess = proj["pessimista"]
    real = proj["realista"]
    otim = proj["otimista"]

    realista_5a = float(real[-1])
    independencia_label = _label_independencia(real)

    # 1. Page header
    st.markdown(_page_header_html(inicial), unsafe_allow_html=True)

    # 2. KPI strip
    st.markdown(
        _kpi_strip_html(inicial, aporte, realista_5a, independencia_label),
        unsafe_allow_html=True,
    )

    # 3. Grid 2:1 (gráfico + marcos)
    col_graf, col_marcos = st.columns([2, 1])
    marcos_realista = _calcular_marcos_realista(real)
    with col_graf:
        _grafico_cenarios(pess, real, otim, marcos_realista)
    with col_marcos:
        marcos_card = [
            (label, _formatar_meses(_meses_ate_meta(real, valor)), cor)
            for valor, label, cor in marcos_realista
        ]
        if not marcos_card:
            marcos_card = [
                ("Sem marcos no horizonte", "ajuste o aporte para acelerar", "texto_sec")
            ]
        st.markdown(_card_marcos_html(marcos_card), unsafe_allow_html=True)

    # 4. Trio de cards de cenário
    aporte_ano = aporte * 12.0
    cards_cenarios = minificar(
        f"""
        <div style="display:grid;
                    grid-template-columns:repeat(3,1fr);
                    gap:16px;
                    margin:18px 0;">
          {_card_cenario_html(
            "cenário pessimista",
            "CDI · sem risco",
            float(pess[-1]),
            "6% a.a.",
            aporte_ano,
            float(pess[-1]) - inicial - aporte_ano * 5,
            float(pess[-1]) / inicial if inicial > 0 else 0.0,
            CENARIO_PESSIMISTA,
          )}
          {_card_cenario_html(
            "cenário realista · ativo",
            "Carteira balanceada",
            realista_5a,
            "9% a.a.",
            aporte_ano,
            realista_5a - inicial - aporte_ano * 5,
            realista_5a / inicial if inicial > 0 else 0.0,
            CENARIO_REALISTA,
            ativo=True,
          )}
          {_card_cenario_html(
            "cenário otimista",
            "IBOV histórico",
            float(otim[-1]),
            "13% a.a.",
            aporte_ano,
            float(otim[-1]) - inicial - aporte_ano * 5,
            float(otim[-1]) / inicial if inicial > 0 else 0.0,
            CENARIO_OTIMISTA,
          )}
        </div>
        """
    )
    st.markdown(cards_cenarios, unsafe_allow_html=True)

    # 5. Simulação personalizada (preserva fluxo legado)
    st.markdown("---")
    # Hero compacto (badge vazio) para satisfazer invariante UX-122
    # de que toda página chame hero_titulo_html, mesmo em modo redesign.
    st.markdown(
        hero_titulo_html(
            "",
            "Simulação Personalizada",
            "Slider de economia adicional aplicada ao cenário atual (12 meses).",
        ),
        unsafe_allow_html=True,
    )
    economia_extra = st.slider(
        "Se eu economizar a mais por mês (R$):",
        min_value=0,
        max_value=5000,
        value=0,
        step=100,
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
