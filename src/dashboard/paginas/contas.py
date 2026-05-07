"""Página Contas (UX-RD-07): cards de bancos e cartões com utilização D7.

Reescrita conforme mockup `novo-mockup/mockups/03-contas.html`. Estrutura:

1. ``page-header`` com título "CONTAS", subtítulo, sprint-tag e pill resumo;
2. Faixa de "patrimônio líquido" + "fatura aberta" + última sincronização
   (calculada do XLSX);
3. Grid de cards de bancos correntes/investimento (saldo + variação 30d);
4. Grid de cards de cartões com progress bar de utilização cuja cor segue
   tokens D7 (graduado <60%, calibracao 60-80%, regredindo 80-100%, alerta
   >=100%);
5. Aviso de snapshot histórico com data dinâmica do mtime do XLSX, em vez
   do hardcoded "Dados congelados desde 2023" da versão pré-UX-RD-07;
6. Seções legadas (Dívidas Ativas, Inventário, Prazos) preservadas como
   tabelas densas abaixo do redesign — D7 ainda não substituiu esses
   snapshots e o XLSX continua sendo a fonte autoritativa.

A função pública ``renderizar(dados, mes_selecionado, pessoa)`` mantém a
mesma assinatura usada por ``app.py`` (sem ``ctx`` -- lição UX-RD-06).
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from src.dashboard.componentes.html_utils import minificar
from src.dashboard.componentes.ui import (
    callout_html,
    card_html,
    subtitulo_secao_html,
)
from src.dashboard.dados import (
    CAMINHO_XLSX,
    filtrar_por_forma_pagamento,
    filtrar_por_mes,
    filtrar_por_pessoa,
    filtro_forma_ativo,
    formatar_moeda,
    renderizar_dataframe,
)
from src.dashboard.tema import (
    CORES,
    FONTE_CORPO,
    FONTE_MINIMA,
    rgba_cor,
)

# Limites de utilização de cartão de crédito (escala D7).
# Não hardcodar — alterar tokens D7 calibracao/regredindo move a cor sozinha.
LIMITE_CALIBRACAO: float = 0.60  # abaixo disso = graduado (verde sóbrio)
LIMITE_REGREDINDO: float = 0.80  # 60-80% = calibracao, 80-100% = regredindo
LIMITE_ALERTA: float = 1.00  # >=100% = accent-red

# Bancos detectados em ``extrato.banco_origem`` que rendem cards na grade
# principal de contas. A ordem aqui controla a ordem de exibição.
BANCOS_CONTAS: tuple[tuple[str, str, str, str], ...] = (
    # (banco_origem, sigla, cor_token, tipo)
    ("Itaú", "IT", "destaque", "Corrente · CC"),
    ("Santander", "SA", "superfluo", "Cartão · Crédito"),
    ("Nubank", "NU", "destaque", "Conta + Cartão"),
    ("C6", "C6", "alerta", "Cartão · Crédito"),
    ("Bradesco", "BD", "superfluo", "Corrente · CC"),
    ("Inter", "IN", "alerta", "Investimento"),
)


# ---------------------------------------------------------------------------
# Funções puras (testáveis sem Streamlit)
# ---------------------------------------------------------------------------


def calcular_data_snapshot(caminho_xlsx: Path = CAMINHO_XLSX) -> str:
    """Retorna data formatada DD/MM/YYYY do mtime do XLSX consolidado.

    Substitui o aviso hardcoded "snapshot 2023" (UX-RD-07). Se o arquivo
    não existir, devolve string vazia (caller usa fallback gracioso).
    """
    try:
        if not caminho_xlsx.exists():
            return ""
        mtime = datetime.fromtimestamp(caminho_xlsx.stat().st_mtime)
        return mtime.strftime("%d/%m/%Y")
    except OSError:
        return ""


def aviso_snapshot_html(caminho_xlsx: Path = CAMINHO_XLSX) -> str:
    """Aviso textual de snapshot com data dinâmica."""
    data_str = calcular_data_snapshot(caminho_xlsx)
    if not data_str:
        return (
            "Snapshot histórico vazio. Atualização manual via XLSX legado em "
            "data/output/ouroboros_2026.xlsx (abas dividas_ativas, inventario, "
            "prazos)."
        )
    return (
        f"Snapshot de {data_str} — atualização manual nas abas dividas_ativas, "
        f"inventario e prazos do XLSX consolidado."
    )


def classe_utilizacao_d7(percentual: float) -> str:
    """Mapeia percentual de utilização de cartão para classe CSS D7.

    Tabela do spec UX-RD-07:
      - <60%       => ``d7-graduado`` (verde sóbrio)
      - 60% a 80%  => ``d7-calibracao`` (amarelo)
      - 80% a 100% => ``d7-regredindo`` (laranja)
      - >=100%     => ``accent-red`` (alerta vermelho)
    """
    if percentual >= LIMITE_ALERTA:
        return "accent-red"
    if percentual >= LIMITE_REGREDINDO:
        return "d7-regredindo"
    if percentual >= LIMITE_CALIBRACAO:
        return "d7-calibracao"
    return "d7-graduado"


def cor_utilizacao_d7(percentual: float) -> str:
    """Hex correspondente à classe D7 para uso em ``style="color:..."``."""
    classe = classe_utilizacao_d7(percentual)
    mapa = {
        "d7-graduado": CORES["d7_graduado"],
        "d7-calibracao": CORES["d7_calibracao"],
        "d7-regredindo": CORES["d7_regredindo"],
        "accent-red": CORES["negativo"],
    }
    return mapa[classe]


def calcular_saldo_por_banco(
    extrato: pd.DataFrame, bancos: Iterable[str]
) -> dict[str, dict[str, float]]:
    """Soma cumulativa por banco e variação dos últimos 30 dias.

    Retorna dict ``{banco: {"saldo": x, "delta_30d": y, "txns_30d": n}}``.
    Inferência simples: ``saldo = sum(valor)`` por ``banco_origem``,
    delta_30d filtra ``data > hoje - 30d``.
    """
    resultado: dict[str, dict[str, float]] = {}
    if extrato.empty or "banco_origem" not in extrato.columns:
        return resultado

    df = extrato.copy()
    df["data"] = pd.to_datetime(df["data"], errors="coerce")
    hoje = pd.Timestamp.today().normalize()
    janela = hoje - pd.Timedelta(days=30)

    for banco in bancos:
        df_b = df[df["banco_origem"] == banco]
        if df_b.empty:
            continue
        df_30 = df_b[df_b["data"] >= janela]
        resultado[banco] = {
            "saldo": float(df_b["valor"].sum()),
            "delta_30d": float(df_30["valor"].sum()),
            "txns_30d": int(len(df_30)),
        }
    return resultado


def calcular_utilizacao_cartoes(
    extrato: pd.DataFrame,
    limites: dict[str, float] | None = None,
) -> list[dict[str, object]]:
    """Calcula uso (R$) e percentual por cartão de crédito.

    ``limites`` é dict opcional ``{banco: limite_total}``. Se ausente,
    usa heurística: limite = max(uso_mensal observado) * 1.5 (estimativa
    conservadora). Retorna lista ordenada decrescentemente por uso.
    """
    if extrato.empty or "forma_pagamento" not in extrato.columns:
        return []

    creditos = extrato[extrato["forma_pagamento"] == "Crédito"].copy()
    if creditos.empty:
        return []

    creditos["data"] = pd.to_datetime(creditos["data"], errors="coerce")
    hoje = pd.Timestamp.today().normalize()
    inicio_mes = hoje.replace(day=1)
    ciclo = creditos[creditos["data"] >= inicio_mes]

    cartoes: list[dict[str, object]] = []
    for banco in ciclo["banco_origem"].dropna().unique():
        df_banco = ciclo[ciclo["banco_origem"] == banco]
        # valores de cartão são negativos no extrato — usamos abs
        usado = float(df_banco["valor"].abs().sum())
        if limites and banco in limites:
            limite = float(limites[banco])
        else:
            # heurística: limite ~ 1.5x maior fatura histórica do banco
            todo_credito_banco = creditos[creditos["banco_origem"] == banco]
            por_mes = todo_credito_banco.groupby(
                todo_credito_banco["data"].dt.to_period("M")
            )["valor"].apply(lambda s: s.abs().sum())
            base = float(por_mes.max()) if not por_mes.empty else usado
            limite = max(base * 1.5, usado, 1000.0)
        percentual = usado / limite if limite > 0 else 0.0
        cartoes.append(
            {
                "banco": str(banco),
                "limite": limite,
                "usado": usado,
                "disponivel": max(limite - usado, 0.0),
                "percentual": percentual,
                "classe_d7": classe_utilizacao_d7(percentual),
            }
        )
    cartoes.sort(key=lambda c: float(c["usado"]), reverse=True)  # type: ignore[arg-type]
    return cartoes


# ---------------------------------------------------------------------------
# HTML helpers
# ---------------------------------------------------------------------------


def _page_header_html(num_contas: int, num_cartoes: int) -> str:
    return minificar(
        f"""
        <div class="page-header">
          <div>
            <h1 class="page-title">CONTAS</h1>
            <p class="page-subtitle">
              Saldos consolidados por banco e cartão. Cores de utilização
              seguem a escala D7 — abaixo de 60% graduado, entre 60% e 80%
              calibracao, entre 80% e 100% regredindo, 100% ou mais em
              alerta vermelho.
            </p>
          </div>
          <div class="page-meta">
            <span class="sprint-tag">UX-RD-07</span>
            <span class="pill pill-d7-graduado">{num_contas} contas · {num_cartoes} cartões</span>
          </div>
        </div>
        """
    )


def _patrimonio_strip_html(
    saldo_total: float, fatura_aberta: float, ultima_sync: str
) -> str:
    fatura_cor = CORES["alerta"] if fatura_aberta > 0 else CORES["texto_sec"]
    return minificar(
        f"""
        <div style="background:{CORES["card_fundo"]};
                    border:1px solid {rgba_cor(CORES["texto_sec"], 0.20)};
                    border-radius:8px;
                    padding:18px 24px;
                    margin-bottom:18px;
                    display:flex;
                    align-items:center;
                    gap:32px;">
          <div>
            <div style="font-size:{FONTE_MINIMA}px;
                        letter-spacing:0.08em;
                        text-transform:uppercase;
                        color:{CORES["texto_sec"]};">Patrimônio líquido</div>
            <div style="font-size:32px;
                        font-weight:500;
                        line-height:1;
                        font-variant-numeric:tabular-nums;
                        margin-top:4px;
                        color:{CORES["texto"]};">{formatar_moeda(saldo_total)}</div>
          </div>
          <div style="height:48px;width:1px;
                      background:{rgba_cor(CORES["texto_sec"], 0.30)};"></div>
          <div>
            <div style="font-size:{FONTE_MINIMA}px;
                        letter-spacing:0.08em;
                        text-transform:uppercase;
                        color:{CORES["texto_sec"]};">Cartões · fatura aberta</div>
            <div style="font-size:24px;
                        color:{fatura_cor};
                        font-variant-numeric:tabular-nums;
                        margin-top:4px;">{formatar_moeda(fatura_aberta)}</div>
          </div>
          <div style="margin-left:auto;
                      font-size:{FONTE_MINIMA}px;
                      color:{CORES["texto_sec"]};
                      text-align:right;">
            <div>última sincronização</div>
            <div style="color:{CORES["texto"]};font-size:13px;">{ultima_sync}</div>
          </div>
        </div>
        """
    )


def _section_bar_html(titulo: str, contagem: str) -> str:
    return minificar(
        f"""
        <div style="display:flex;
                    align-items:baseline;
                    gap:12px;
                    margin:24px 0 12px 0;">
          <h2 style="font-size:{FONTE_MINIMA}px;
                     letter-spacing:0.08em;
                     text-transform:uppercase;
                     color:{CORES["texto_sec"]};
                     margin:0;
                     font-weight:500;">{titulo}</h2>
          <span style="margin-left:auto;
                       font-size:{FONTE_MINIMA}px;
                       color:{CORES["texto_sec"]};">{contagem}</span>
        </div>
        """
    )


def _card_banco_html(
    banco: str, sigla: str, cor_token: str, tipo: str, info: dict[str, float]
) -> str:
    cor_acento = CORES.get(cor_token, CORES["destaque"])
    saldo = float(info["saldo"])
    delta = float(info["delta_30d"])
    txns = int(info["txns_30d"])
    delta_cor = (
        CORES["d7_graduado"]
        if delta >= 0
        else CORES["negativo"]
    )
    delta_sinal = "+" if delta >= 0 else "−"
    delta_str = f"{delta_sinal} {formatar_moeda(abs(delta))} · 30d"
    return minificar(
        f"""
        <div class="acc"
             style="background:{CORES["card_fundo"]};
                    border:1px solid {rgba_cor(CORES["texto_sec"], 0.20)};
                    border-top:3px solid {cor_acento};
                    border-radius:8px;
                    padding:16px 18px;">
          <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;">
            <div style="width:40px;height:40px;
                        border-radius:6px;
                        background:{cor_acento};
                        color:{CORES["fundo"]};
                        display:flex;
                        align-items:center;
                        justify-content:center;
                        font-weight:700;
                        font-size:14px;">{sigla}</div>
            <div>
              <div style="font-size:15px;color:{CORES["texto"]};">{banco}</div>
              <div style="font-size:10px;
                          letter-spacing:0.08em;
                          text-transform:uppercase;
                          color:{CORES["texto_sec"]};">{tipo}</div>
            </div>
          </div>
          <div style="font-size:28px;
                      font-weight:500;
                      line-height:1;
                      font-variant-numeric:tabular-nums;
                      color:{CORES["texto"]};
                      margin-bottom:4px;">{formatar_moeda(saldo)}</div>
          <div style="font-size:11px;color:{delta_cor};">{delta_str}</div>
          <div style="display:grid;
                      grid-template-columns:repeat(2,1fr);
                      gap:8px;
                      margin-top:14px;
                      padding-top:12px;
                      border-top:1px solid {rgba_cor(CORES["texto_sec"], 0.20)};">
            <div style="font-size:11px;color:{CORES["texto_sec"]};">
              transações 30d
              <strong style="display:block;
                             font-size:13px;
                             color:{CORES["texto"]};
                             margin-top:2px;">{txns}</strong>
            </div>
            <div style="font-size:11px;color:{CORES["texto_sec"]};">
              banco_origem
              <strong style="display:block;
                             font-size:13px;
                             color:{cor_acento};
                             margin-top:2px;">{banco}</strong>
            </div>
          </div>
        </div>
        """
    )


def _card_cartao_html(cartao: dict[str, object]) -> str:
    banco = str(cartao["banco"])
    limite = float(cartao["limite"])  # type: ignore[arg-type]
    usado = float(cartao["usado"])  # type: ignore[arg-type]
    disponivel = float(cartao["disponivel"])  # type: ignore[arg-type]
    percentual = float(cartao["percentual"])  # type: ignore[arg-type]
    classe_d7 = str(cartao["classe_d7"])
    cor = cor_utilizacao_d7(percentual)
    pct_int = int(round(percentual * 100))

    return minificar(
        f"""
        <div class="cc-card pill-{classe_d7}"
             data-utilizacao="{classe_d7}"
             style="background:{CORES["card_fundo"]};
                    border:1px solid {rgba_cor(CORES["texto_sec"], 0.20)};
                    border-left:3px solid {cor};
                    border-radius:8px;
                    padding:16px 18px;">
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
            <div style="font-size:14px;color:{CORES["texto"]};">{banco}</div>
            <span style="margin-left:auto;
                         font-size:11px;
                         color:{CORES["texto_sec"]};
                         letter-spacing:0.06em;">cartão crédito</span>
          </div>
          <div style="display:grid;
                      grid-template-columns:1fr 1fr 1fr;
                      gap:12px;
                      margin-top:8px;">
            <div>
              <div style="font-size:10px;
                          letter-spacing:0.06em;
                          text-transform:uppercase;
                          color:{CORES["texto_sec"]};">limite</div>
              <div style="font-size:18px;
                          font-weight:500;
                          font-variant-numeric:tabular-nums;
                          color:{CORES["texto"]};">{formatar_moeda(limite)}</div>
            </div>
            <div>
              <div style="font-size:10px;
                          letter-spacing:0.06em;
                          text-transform:uppercase;
                          color:{CORES["texto_sec"]};">usado</div>
              <div style="font-size:18px;
                          font-weight:500;
                          font-variant-numeric:tabular-nums;
                          color:{cor};">{formatar_moeda(usado)}</div>
            </div>
            <div>
              <div style="font-size:10px;
                          letter-spacing:0.06em;
                          text-transform:uppercase;
                          color:{CORES["texto_sec"]};">disponível</div>
              <div style="font-size:18px;
                          font-weight:500;
                          font-variant-numeric:tabular-nums;
                          color:{CORES["d7_graduado"]};">{formatar_moeda(disponivel)}</div>
            </div>
          </div>
          <div style="height:6px;
                      background:{rgba_cor(CORES["texto_sec"], 0.15)};
                      border-radius:999px;
                      overflow:hidden;
                      margin-top:14px;">
            <span style="display:block;
                         height:100%;
                         width:{min(percentual * 100, 100):.1f}%;
                         background:{cor};"></span>
          </div>
          <div style="display:flex;
                      justify-content:space-between;
                      font-size:11px;
                      color:{CORES["texto_sec"]};
                      margin-top:6px;">
            <span>{pct_int}% usado · classe {classe_d7}</span>
            <span>limite estimado (1.5× pico histórico)</span>
          </div>
        </div>
        """
    )


# ---------------------------------------------------------------------------
# Render principal
# ---------------------------------------------------------------------------


def renderizar(dados: dict[str, pd.DataFrame], mes_selecionado: str, pessoa: str) -> None:
    """Renderiza a página de contas (UX-RD-07 + UX-T-03).

    UX-T-03: topbar-actions canônicas adicionadas (Adicionar conta +
    Sincronizar OFX).
    """
    from src.dashboard.componentes.topbar_actions import renderizar_grupo_acoes
    renderizar_grupo_acoes([
        {"label": "Adicionar conta", "glyph": "plus",
         "title": "Cadastrar nova conta bancária"},
        {"label": "Sincronizar OFX", "primary": True, "glyph": "refresh",
         "title": "Reprocessar OFX e atualizar saldos"},
    ])

    extrato = dados.get("extrato", pd.DataFrame())
    extrato_pessoa = (
        filtrar_por_pessoa(extrato, pessoa) if not extrato.empty else extrato
    )

    contas_info = calcular_saldo_por_banco(
        extrato_pessoa, [b[0] for b in BANCOS_CONTAS]
    )
    cartoes = calcular_utilizacao_cartoes(extrato_pessoa)

    saldo_total = sum(float(info["saldo"]) for info in contas_info.values())
    fatura_aberta = sum(float(c["usado"]) for c in cartoes)  # type: ignore[arg-type]
    ultima_sync = (
        calcular_data_snapshot(CAMINHO_XLSX) or "indisponível"
    )

    st.markdown(
        _page_header_html(len(contas_info), len(cartoes)),
        unsafe_allow_html=True,
    )
    st.markdown(
        _patrimonio_strip_html(saldo_total, fatura_aberta, ultima_sync),
        unsafe_allow_html=True,
    )

    if contas_info:
        st.markdown(
            _section_bar_html(
                "Contas correntes & investimento", f"{len(contas_info)} bancos detectados"
            ),
            unsafe_allow_html=True,
        )
        cards = [
            _card_banco_html(banco, sigla, cor, tipo, contas_info[banco])
            for banco, sigla, cor, tipo in BANCOS_CONTAS
            if banco in contas_info
        ]
        grid_html = minificar(
            f"""
            <div style="display:grid;
                        grid-template-columns:repeat(3, minmax(0,1fr));
                        gap:14px;
                        margin-bottom:18px;">
              {''.join(cards)}
            </div>
            """
        )
        st.markdown(grid_html, unsafe_allow_html=True)
    else:
        st.markdown(
            callout_html("info", "Nenhum banco com transações detectadas."),
            unsafe_allow_html=True,
        )

    if cartoes:
        pct_geral = (
            sum(float(c["percentual"]) for c in cartoes) / len(cartoes)  # type: ignore[arg-type]
            if cartoes
            else 0.0
        )
        st.markdown(
            _section_bar_html(
                "Cartões de crédito",
                f"{len(cartoes)} cartões · utilização média {int(round(pct_geral * 100))}%",
            ),
            unsafe_allow_html=True,
        )
        cards_cc = [_card_cartao_html(c) for c in cartoes]
        grid_cc_html = minificar(
            f"""
            <div style="display:grid;
                        grid-template-columns:repeat(2, minmax(0,1fr));
                        gap:14px;
                        margin-bottom:18px;">
              {''.join(cards_cc)}
            </div>
            """
        )
        st.markdown(grid_cc_html, unsafe_allow_html=True)

    # ---------------------------------------------------------------
    # Seções legadas (snapshots históricos do XLSX)
    # ---------------------------------------------------------------
    tem_dividas = "dividas_ativas" in dados
    tem_inventario = "inventario" in dados
    tem_prazos = "prazos" in dados

    if not (tem_dividas or tem_inventario or tem_prazos):
        return

    st.markdown(
        _section_bar_html(
            "Snapshot histórico (XLSX legado)", "atualização manual"
        ),
        unsafe_allow_html=True,
    )
    # Subtítulo de seção (substitui hero_titulo_html legado — 2026-05-06).
    # Hero é exclusivo do page-header canônico no topo da página.
    st.markdown(
        subtitulo_secao_html("Dívidas ativas, inventário e prazos do XLSX legado."),
        unsafe_allow_html=True,
    )
    st.markdown(
        callout_html("warning", aviso_snapshot_html(CAMINHO_XLSX)),
        unsafe_allow_html=True,
    )

    if tem_dividas:
        _secao_dividas(dados["dividas_ativas"], mes_selecionado, pessoa)
    if tem_inventario:
        _secao_inventario(dados["inventario"])
    if tem_prazos:
        _secao_prazos(dados["prazos"])


# ---------------------------------------------------------------------------
# Seções legadas (preservadas conforme regra inviolável 7)
# ---------------------------------------------------------------------------


def _secao_dividas(df: pd.DataFrame, mes: str, pessoa: str) -> None:
    """Exibe tabela de dívidas ativas com indicadores visuais."""
    st.subheader("Dívidas Ativas")

    df_mes = filtrar_por_mes(df, mes)
    if "recorrente" in df.columns:
        df_recorrentes = df[
            (df["recorrente"] == True) & (df["status"] != "Pago")  # noqa: E712
        ]
        df_mes = pd.concat([df_mes, df_recorrentes]).drop_duplicates()
    df_mes = filtrar_por_forma_pagamento(
        filtrar_por_pessoa(df_mes, pessoa), filtro_forma_ativo()
    )

    if df_mes.empty:
        st.markdown(
            callout_html("info", "Sem dívidas registradas para este período."),
            unsafe_allow_html=True,
        )
        return

    _resumo_pagamentos(df_mes)

    df_mes = renderizar_dataframe(df_mes)

    linhas_html: list[str] = []
    for _, row in df_mes.iterrows():
        status = row.get("status", "")
        cor_borda = CORES["positivo"] if status == "Pago" else CORES["negativo"]
        cor_fundo = (
            rgba_cor(CORES["positivo"], 0.08)
            if status == "Pago"
            else rgba_cor(CORES["negativo"], 0.08)
        )
        status_texto = "Pago" if status == "Pago" else "Pendente"
        obs_raw = row.get("obs", "")
        obs = obs_raw if obs_raw not in ("", "—", None) else "—"

        linhas_html.append(
            f'<tr style="background-color: {cor_fundo};'
            f' border-left: 3px solid {cor_borda};">'
            f'<td style="padding: 12px 10px; color: {CORES["texto"]};'
            f' font-size: {FONTE_CORPO}px;">{row.get("custo", "")}</td>'
            f'<td style="padding: 12px 10px; color: {CORES["texto"]};'
            f' font-size: {FONTE_CORPO}px; text-align: right;">'
            f"{formatar_moeda(row.get('valor', 0))}</td>"
            f'<td style="padding: 12px 10px; color: {cor_borda};'
            f' font-weight: bold; font-size: {FONTE_CORPO}px;">'
            f"{status_texto}</td>"
            f'<td style="padding: 12px 10px; color: {CORES["texto_sec"]};'
            f' font-size: {FONTE_MINIMA}px;">{obs}</td></tr>'
        )

    html = minificar(
        f"""
        <table style="width: 100%; border-collapse: collapse; margin: 10px 0 20px 0;">
          <thead>
            <tr style="background-color: {CORES["card_fundo"]};">
              <th style="padding: 10px; text-align: left;
                         color: {CORES["texto_sec"]}; font-size: {FONTE_MINIMA}px;">Custo</th>
              <th style="padding: 10px; text-align: right;
                         color: {CORES["texto_sec"]}; font-size: {FONTE_MINIMA}px;">Valor</th>
              <th style="padding: 10px; text-align: left;
                         color: {CORES["texto_sec"]}; font-size: {FONTE_MINIMA}px;">Status</th>
              <th style="padding: 10px; text-align: left;
                         color: {CORES["texto_sec"]}; font-size: {FONTE_MINIMA}px;">Obs</th>
            </tr>
          </thead>
          <tbody>{''.join(linhas_html)}</tbody>
        </table>
        """
    )

    st.markdown(html, unsafe_allow_html=True)


def _resumo_pagamentos(df: pd.DataFrame) -> None:
    """Exibe resumo de pagamentos: total pago vs pendente."""
    total_pago = df[df["status"] == "Pago"]["valor"].sum()
    total_pendente = df[df["status"] == "Não Pago"]["valor"].sum()
    total_geral = total_pago + total_pendente

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            card_html("Total Pago", formatar_moeda(total_pago), CORES["positivo"]),
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            card_html("Total Pendente", formatar_moeda(total_pendente), CORES["negativo"]),
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            card_html("Total Geral", formatar_moeda(total_geral), CORES["neutro"]),
            unsafe_allow_html=True,
        )


def _secao_inventario(df: pd.DataFrame) -> None:
    """Exibe inventário de bens com depreciação."""
    st.subheader("Inventário")

    if df.empty:
        st.markdown(
            callout_html("info", "Sem bens cadastrados no inventário."),
            unsafe_allow_html=True,
        )
        return

    df = renderizar_dataframe(df)
    st.dataframe(df, width="stretch", hide_index=True)


def _secao_prazos(df: pd.DataFrame) -> None:
    """Exibe prazos de vencimento com indicador de urgência."""
    st.subheader("Prazos de Vencimento")

    if df.empty:
        st.markdown(
            callout_html("info", "Sem prazos cadastrados."),
            unsafe_allow_html=True,
        )
        return

    hoje = date.today()
    dia_atual = hoje.day

    linhas_html: list[str] = []
    for _, row in df.sort_values("dia_vencimento").iterrows():
        conta = row.get("conta", "")
        dia = int(row.get("dia_vencimento", 0))
        dias_ate = dia - dia_atual

        if dias_ate < 0:
            urgencia = "Vencido"
            cor = CORES["negativo"]
        elif dias_ate <= 3:
            urgencia = f"Em {dias_ate} dias"
            cor = CORES["alerta"]
        elif dias_ate <= 7:
            urgencia = f"Em {dias_ate} dias"
            cor = CORES["info"]
        else:
            urgencia = f"Em {dias_ate} dias"
            cor = CORES["texto_sec"]

        linhas_html.append(
            f'<tr style="border-bottom: 1px solid {CORES["card_fundo"]};">'
            f'<td style="padding: 10px; color: {CORES["texto"]};'
            f' font-size: {FONTE_CORPO}px;">{conta}</td>'
            f'<td style="padding: 10px; color: {CORES["texto"]};'
            f' font-size: {FONTE_CORPO}px; text-align: center;">Dia {dia}</td>'
            f'<td style="padding: 10px; color: {cor};'
            f' font-size: {FONTE_CORPO}px; font-weight: bold;">'
            f"{urgencia}</td></tr>"
        )

    html = minificar(
        f"""
        <table style="width: 100%; border-collapse: collapse;">
          <thead>
            <tr style="background-color: {CORES["card_fundo"]};">
              <th style="padding: 10px; text-align: left;
                         color: {CORES["texto_sec"]}; font-size: {FONTE_MINIMA}px;">Conta</th>
              <th style="padding: 10px; text-align: center;
                         color: {CORES["texto_sec"]}; font-size: {FONTE_MINIMA}px;">Vencimento</th>
              <th style="padding: 10px; text-align: left;
                         color: {CORES["texto_sec"]}; font-size: {FONTE_MINIMA}px;">Urgência</th>
            </tr>
          </thead>
          <tbody>{''.join(linhas_html)}</tbody>
        </table>
        """
    )

    st.markdown(html, unsafe_allow_html=True)


# Mantemos a constante histórica disponível para retro-compatibilidade
# de imports externos (testes antigos podem importar). UX-RD-07 deixou
# de usá-la — o aviso real é construído por ``aviso_snapshot_html``.
AVISO_SNAPSHOT: str = (
    "Snapshot histórico — atualização manual nas abas dividas_ativas, "
    "inventario e prazos do XLSX consolidado."
)


# "O preço de qualquer coisa é a quantidade de vida que você troca por ela."
# -- Henry David Thoreau
