"""Página Pagamentos (UX-RD-07): calendário 14d + lista de vencimentos.

Reescrita conforme mockup `novo-mockup/mockups/04-pagamentos.html`. Estrutura:

1. ``page-header`` com título "PAGAMENTOS", subtítulo, sprint-tag e pill;
2. KPI row (4 cards): a pagar mês · em atraso · faturas cartões · fixos;
3. Coluna esquerda — calendário 7×2 dos próximos 14 dias com hoje
   destacado em ``border-purple`` e dias com vencimento marcados como
   ``dot purple`` ou pill colorido por tipo (fixo/var/cc/atraso);
4. Coluna direita — lista detalhada de "próximos eventos" com data,
   descrição, banco_pagamento, valor e chip de auto-débito;
5. Fallback: quando ``prazos`` está vazio, fallback gracioso (D7 style)
   com aviso de snapshot histórico vazio em vez de inventar dados.

A função pública ``renderizar(dados, mes_selecionado, pessoa, ctx)``
mantém a assinatura legada (com ``ctx`` opcional) usada por ``app.py``.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Iterable

import pandas as pd
import streamlit as st

from src.analysis.pagamentos import (
    STATUS_ATRASADO,
    STATUS_PAGO,
    STATUS_PENDENTE,
    alertas_vencimento,
    carregar_boletos_inteligente,
    faturas_credito,
    top_beneficiarios_pix,
)
from src.dashboard.componentes.calendario_pagamentos import (
    _calendario_html,
    _lista_proximos_html,
    _pagamentos_por_data,
)
from src.dashboard.componentes.html_utils import minificar
from src.dashboard.componentes.ui import (
    callout_html,
    carregar_css_pagina,
)
from src.dashboard.dados import (
    filtrar_por_forma_pagamento,
    filtrar_por_pessoa,
    filtro_forma_ativo,
    formatar_moeda,
)
from src.dashboard.paginas.pagamentos_valores import (
    enriquecer_prazos_com_valor,
)
from src.dashboard.tema import (
    CORES,
    FONTE_CORPO,
    rgba_cor,
)

CAL_DIAS: int = 14  # janela do calendário (próximos 14 dias)


# ---------------------------------------------------------------------------
# Funções puras (testáveis sem Streamlit)
# ---------------------------------------------------------------------------


def construir_eventos_calendario(
    prazos: pd.DataFrame,
    boletos: pd.DataFrame,
    hoje: date | None = None,
    janela_dias: int = CAL_DIAS,
) -> list[dict[str, object]]:
    """Combina prazos recorrentes + boletos pendentes em uma agenda.

    Retorna lista ordenada por data crescente, contendo:
      ``{"data": date, "conta": str, "valor": float, "tipo": str,
         "auto_debito": bool, "banco_pagamento": str, "atraso": bool}``

    Tipos seguem nomenclatura do mockup:
      - ``fix`` — recorrência identificada (prazos)
      - ``cc``  — fatura de cartão (boletos com 'fatura' na descrição)
      - ``var`` — boleto avulso pendente
      - ``late``— qualquer item com data <= hoje e ainda pendente
    """
    hoje = hoje or date.today()
    fim = hoje + timedelta(days=janela_dias)

    eventos: list[dict[str, object]] = []

    if not prazos.empty and "dia_vencimento" in prazos.columns:
        for _, row in prazos.iterrows():
            try:
                dia = int(row.get("dia_vencimento", 0))
            except (TypeError, ValueError):
                continue
            if not 1 <= dia <= 31:
                continue
            # Próxima ocorrência do dia (no mês atual ou no próximo)
            try:
                tentativa = hoje.replace(day=dia)
            except ValueError:
                continue
            if tentativa < hoje:
                # Mês seguinte
                ano = hoje.year + (1 if hoje.month == 12 else 0)
                mes = 1 if hoje.month == 12 else hoje.month + 1
                try:
                    tentativa = date(ano, mes, dia)
                except ValueError:
                    continue
            if tentativa > fim:
                continue
            auto_raw = row.get("auto_debito", False)
            auto = bool(auto_raw) if not pd.isna(auto_raw) else False
            banco_raw = row.get("banco_pagamento", "")
            banco = "" if pd.isna(banco_raw) else str(banco_raw)
            eventos.append(
                {
                    "data": tentativa,
                    "conta": str(row.get("conta", "")),
                    "valor": 0.0,
                    "tipo": "fix",
                    "auto_debito": auto,
                    "banco_pagamento": banco,
                    "atraso": False,
                }
            )

    if not boletos.empty and "vencimento" in boletos.columns:
        for _, row in boletos.iterrows():
            venc = row.get("vencimento")
            if pd.isna(venc):
                continue
            if isinstance(venc, str):
                try:
                    venc = pd.to_datetime(venc).date()
                except (ValueError, TypeError):
                    continue
            elif isinstance(venc, pd.Timestamp):
                venc = venc.date()
            elif not isinstance(venc, date):
                continue
            if venc < hoje - timedelta(days=30) or venc > fim:
                continue
            status = str(row.get("status", "")).lower()
            atrasado = status == STATUS_ATRASADO or (
                venc < hoje and status != STATUS_PAGO
            )
            descricao = str(row.get("fornecedor") or row.get("descricao") or "")
            tipo = "cc" if "fatura" in descricao.lower() else "var"
            if atrasado:
                tipo = "late"
            banco_raw = row.get("banco_origem", "")
            banco_origem = (
                "" if pd.isna(banco_raw) else str(banco_raw)
            ) if banco_raw is not None else ""
            valor_raw = row.get("valor", 0.0)
            valor_norm = (
                0.0 if pd.isna(valor_raw) else float(valor_raw or 0.0)
            )
            eventos.append(
                {
                    "data": venc,
                    "conta": descricao,
                    "valor": valor_norm,
                    "tipo": tipo,
                    "auto_debito": False,
                    "banco_pagamento": banco_origem,
                    "atraso": atrasado,
                }
            )

    eventos.sort(key=lambda e: e["data"])  # type: ignore[arg-type, return-value]
    return eventos


def calcular_kpis_pagamentos(
    eventos: list[dict[str, object]], hoje: date | None = None
) -> dict[str, float | int]:
    """KPIs para a faixa superior da página."""
    hoje = hoje or date.today()
    fim_mes = (hoje.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(
        days=1
    )

    a_pagar_mes = sum(
        float(e["valor"])  # type: ignore[arg-type]
        for e in eventos
        if isinstance(e["data"], date) and e["data"] <= fim_mes  # type: ignore[arg-type]
    )
    em_atraso = sum(
        float(e["valor"]) for e in eventos if e.get("atraso")  # type: ignore[arg-type]
    )
    faturas_cc = sum(
        float(e["valor"]) for e in eventos if e.get("tipo") == "cc"  # type: ignore[arg-type]
    )
    fixos = sum(1 for e in eventos if e.get("tipo") == "fix")

    return {
        "a_pagar_mes": a_pagar_mes,
        "em_atraso": em_atraso,
        "faturas_cc": faturas_cc,
        "fixos": fixos,
    }


def gerar_celulas_calendario(
    eventos: list[dict[str, object]],
    hoje: date | None = None,
    janela_dias: int = CAL_DIAS,
) -> list[dict[str, object]]:
    """Retorna lista com 14 dicts: ``{"data", "is_today", "eventos"}``."""
    hoje = hoje or date.today()
    por_data: dict[date, list[dict[str, object]]] = {}
    for ev in eventos:
        d = ev["data"]
        if isinstance(d, date):
            por_data.setdefault(d, []).append(ev)

    celulas: list[dict[str, object]] = []
    for offset in range(janela_dias):
        d = hoje + timedelta(days=offset)
        celulas.append(
            {
                "data": d,
                "is_today": d == hoje,
                "eventos": por_data.get(d, []),
            }
        )
    return celulas


# ---------------------------------------------------------------------------
# HTML helpers
# ---------------------------------------------------------------------------


def _page_header_html(qtd_eventos: int, em_atraso: int) -> str:
    pill_classe = "pill-d7-regredindo" if em_atraso else "pill-d7-graduado"
    pill_texto = (
        f"{em_atraso} em atraso" if em_atraso else f"{qtd_eventos} próximos 14d"
    )
    return minificar(
        f"""
        <div class="page-header">
          <div>
            <h1 class="page-title">PAGAMENTOS</h1>
            <p class="page-subtitle">
              Calendário consolidado de débitos automáticos, faturas,
              transferências e aportes para os próximos {CAL_DIAS} dias.
              Lista lateral mostra cada vencimento com banco de pagamento
              e flag de auto-débito quando registrado em prazos.yaml.
            </p>
          </div>
          <div class="page-meta">
            <span class="sprint-tag">UX-RD-07</span>
            <span class="pill {pill_classe}">{pill_texto}</span>
          </div>
        </div>
        """
    )


def _kpi_row_html(kpis: dict[str, float | int]) -> str:
    a_pagar = float(kpis["a_pagar_mes"])
    atraso = float(kpis["em_atraso"])
    faturas = float(kpis["faturas_cc"])
    fixos = int(kpis["fixos"])

    cor_atraso = CORES["negativo"] if atraso > 0 else CORES["texto_sec"]
    cor_faturas = CORES["alerta"] if faturas > 0 else CORES["texto_sec"]
    cor_fixos = CORES["destaque"] if fixos > 0 else CORES["texto_sec"]

    cards = [
        ("A pagar · mês", formatar_moeda(a_pagar), CORES["texto"], "Consolidado do mês"),
        ("Em atraso", formatar_moeda(atraso), cor_atraso, "Pagar imediatamente"),
        ("Cartões · faturas", formatar_moeda(faturas), cor_faturas, "Agendar débito"),
        ("Fixos identificados", str(fixos), cor_fixos, "Do snapshot prazos"),
    ]

    cells = []
    for label, valor, cor, sub in cards:
        cells.append(
            minificar(
                f"""
                <div class="kpi"
                     style="background:{CORES["card_fundo"]};
                            border:1px solid {rgba_cor(CORES["texto_sec"], 0.20)};
                            border-radius:8px;padding:14px 18px;">
                  <div class="kpi-label"
                       style="font-size:10px;
                              letter-spacing:0.08em;
                              text-transform:uppercase;
                              color:{CORES["texto_sec"]};">{label}</div>
                  <div class="kpi-value"
                       style="font-size:28px;
                              font-weight:500;
                              line-height:1;
                              margin-top:6px;
                              color:{cor};
                              font-variant-numeric:tabular-nums;">{valor}</div>
                  <div style="font-size:11px;
                              color:{CORES["texto_sec"]};
                              margin-top:6px;">{sub}</div>
                </div>
                """
            )
        )
    return minificar(
        f"""
        <div style="display:grid;
                    grid-template-columns:repeat(4, minmax(0,1fr));
                    gap:14px;
                    margin-bottom:18px;">
          {''.join(cells)}
        </div>
        """
    )


def _cor_tipo(tipo: str) -> str:
    return {
        "fix": CORES["destaque"],
        "var": CORES["superfluo"],
        "cc": CORES["alerta"],
        "late": CORES["negativo"],
    }.get(tipo, CORES["texto_sec"])


# ---------------------------------------------------------------------------
# Render principal
# ---------------------------------------------------------------------------


def renderizar(
    dados: dict[str, pd.DataFrame],
    mes_selecionado: str,
    pessoa: str,
    ctx: dict | None = None,
) -> None:
    """Renderiza Pagamentos (UX-V-2.2 paridade com mockup 04-pagamentos.html).

    Layout: KPIs no topo, calendário do mês inteiro à esquerda (5 semanas
    Seg-Dom com pílulas coloridas) + lista lateral PRÓXIMOS 14 DIAS com
    botão "agendar" inline. Sub-abas Boletos · Pix · Crédito preservadas.
    """
    del ctx

    from src.dashboard.componentes.topbar_actions import renderizar_grupo_acoes
    renderizar_grupo_acoes([
        {"label": "Marcar pago", "glyph": "check",
         "title": "Marcar pagamentos selecionados"},
        {"label": "Adicionar", "primary": True, "glyph": "plus",
         "title": "Novo pagamento"},
    ])

    if "extrato" not in dados:
        st.markdown(
            callout_html("warning", "Extrato não disponível."),
            unsafe_allow_html=True,
        )
        return

    # CSS dedicado da página (UX-V-2.2)
    st.markdown(
        minificar(carregar_css_pagina("pagamentos")), unsafe_allow_html=True
    )

    extrato = filtrar_por_forma_pagamento(
        filtrar_por_pessoa(dados["extrato"], pessoa),
        filtro_forma_ativo(),
    )
    prazos = dados.get("prazos", pd.DataFrame())

    db = _carregar_db_grafo()
    try:
        boletos = carregar_boletos_inteligente(extrato, prazos, db=db)
    finally:
        if db is not None:
            try:
                db.fechar()
            except Exception:  # noqa: BLE001
                pass

    eventos = construir_eventos_calendario(prazos, boletos)
    kpis = calcular_kpis_pagamentos(eventos)

    em_atraso_qtd = sum(1 for e in eventos if e.get("atraso"))

    # Mês/ano: deriva do filtro global; default = mês corrente.
    hoje = date.today()
    ano, mes = hoje.year, hoje.month
    if isinstance(mes_selecionado, str) and "-" in mes_selecionado:
        partes = mes_selecionado.split("-")
        if len(partes) >= 2:
            try:
                ano = int(partes[0])
                mes_candidato = int(partes[1])
                if 1 <= mes_candidato <= 12:
                    mes = mes_candidato
            except ValueError:
                pass

    # UX-V-2.2-FIX: setas de navegação no header do calendário escrevem
    # ``?mes_cal=YYYY-MM``. Quando presente, sobrepõe o filtro global apenas
    # para o calendário desta página (filtro global continua íntegro).
    mes_cal_qp = st.query_params.get("mes_cal")
    if isinstance(mes_cal_qp, str) and "-" in mes_cal_qp:
        partes_qp = mes_cal_qp.split("-")
        if len(partes_qp) >= 2:
            try:
                ano_qp = int(partes_qp[0])
                mes_qp = int(partes_qp[1])
                if 1 <= mes_qp <= 12:
                    ano, mes = ano_qp, mes_qp
            except ValueError:
                pass

    # UX-V-2.2.A: enriquece prazos com valor_estimado cruzando com extrato.
    # NÃO modifica o XLSX em disco; é runtime apenas.
    prazos_enriquecidos = enriquecer_prazos_com_valor(prazos, extrato)
    pgs_por_data = _pagamentos_por_data(prazos_enriquecidos, ano, mes)

    st.markdown(
        _page_header_html(len(eventos), em_atraso_qtd),
        unsafe_allow_html=True,
    )
    st.markdown(_kpi_row_html(kpis), unsafe_allow_html=True)

    col_cal, col_lista = st.columns([2, 1])
    with col_cal:
        st.markdown(
            _calendario_html(ano, mes, pgs_por_data),
            unsafe_allow_html=True,
        )
    with col_lista:
        st.markdown(
            '<h3 class="proximos-titulo">PRÓXIMOS 14 DIAS</h3>',
            unsafe_allow_html=True,
        )
        st.markdown(
            _lista_proximos_html(pgs_por_data, janela_dias=CAL_DIAS),
            unsafe_allow_html=True,
        )

    # ---------------------------------------------------------------
    # Sub-abas legadas (Boletos · Pix · Crédito) — preservadas
    # ---------------------------------------------------------------
    tab_boletos, tab_pix, tab_credito = st.tabs(["Boletos", "Pix", "Crédito"])

    with tab_boletos:
        _renderizar_boletos_tab(boletos)
    with tab_pix:
        _renderizar_pix(extrato)
    with tab_credito:
        _renderizar_credito(extrato)


def _carregar_db_grafo():  # type: ignore[no-untyped-def]
    """Sprint 87.7: abre GrafoDB quando existe; retorna None se ausente."""
    try:
        from src.graph.db import GrafoDB, caminho_padrao
    except ImportError:  # pragma: no cover -- módulo de grafo ausente
        return None
    try:
        db_path = caminho_padrao()
        if not db_path.exists():
            return None
        return GrafoDB(db_path)
    except Exception:  # noqa: BLE001 -- dashboard nunca quebra por grafo
        return None


def _renderizar_boletos_tab(boletos: pd.DataFrame) -> None:
    if boletos.empty:
        st.markdown(
            callout_html("info", "Nenhum boleto identificado no período/filtros atuais."),
            unsafe_allow_html=True,
        )
        return

    alertas = alertas_vencimento(boletos, dias_aviso=3)
    for a in alertas[:10]:
        st.markdown(callout_html("warning", a), unsafe_allow_html=True)
    if len(alertas) > 10:
        st.caption(f"+{len(alertas) - 10} alertas adicionais.")

    if "status" in boletos.columns:
        col_pago, col_pend, col_atr = st.columns(3)
        total_pagos = int((boletos["status"] == STATUS_PAGO).sum())
        total_pendentes = int((boletos["status"] == STATUS_PENDENTE).sum())
        total_atrasados = int((boletos["status"] == STATUS_ATRASADO).sum())
        col_pago.metric("Pagos", str(total_pagos))
        col_pend.metric("Pendentes", str(total_pendentes))
        col_atr.metric("Atrasados", str(total_atrasados))

    boletos_fmt = _formatar_boletos_para_exibicao(boletos)
    st.dataframe(
        boletos_fmt,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Valor": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
        },
    )


def _formatar_boletos_para_exibicao(boletos: pd.DataFrame) -> pd.DataFrame:
    """Sprint 92a item 4: prepara DataFrame de boletos para exibição.

    Preservada da versão pré-UX-RD-07.
    """
    boletos_fmt = boletos.copy()

    for coluna_datetime in ("data", "vencimento"):
        if coluna_datetime not in boletos_fmt.columns:
            continue
        serie = boletos_fmt[coluna_datetime]
        if pd.api.types.is_datetime64_any_dtype(serie):
            boletos_fmt[coluna_datetime] = serie.dt.strftime("%Y-%m-%d")
            continue
        if serie.dtype == object:
            convertido = pd.to_datetime(serie, errors="coerce")
            if convertido.notna().any():
                boletos_fmt[coluna_datetime] = convertido.dt.strftime("%Y-%m-%d").fillna(
                    serie.astype(str).where(convertido.isna(), "")
                )

    rename_map = {
        "data": "Data",
        "fornecedor": "Fornecedor",
        "valor": "Valor",
        "vencimento": "Vencimento",
        "status": "Status",
        "banco_origem": "Banco",
    }
    colunas_renomear = {k: v for k, v in rename_map.items() if k in boletos_fmt.columns}
    return boletos_fmt.rename(columns=colunas_renomear)


def _renderizar_pix(extrato: pd.DataFrame) -> None:
    top = top_beneficiarios_pix(extrato, top_n=20)
    if top.empty:
        st.markdown(
            callout_html("info", "Nenhum Pix encontrado no período/filtros atuais."),
            unsafe_allow_html=True,
        )
        return

    total = float(top["total"].sum())
    qtd = int(top.shape[0])
    col1, col2 = st.columns(2)
    col1.metric("Total Top 20", formatar_moeda(total))
    col2.metric("Beneficiários", str(qtd))

    st.markdown(
        f'<p style="font-size: {FONTE_CORPO}px; color: {CORES["texto_sec"]};">'
        f"Top 20 beneficiários:</p>",
        unsafe_allow_html=True,
    )
    st.dataframe(top, use_container_width=True, hide_index=True)


def _renderizar_credito(extrato: pd.DataFrame) -> None:
    faturas = faturas_credito(extrato)
    if not faturas:
        st.markdown(
            callout_html("info", "Nenhuma despesa em Crédito no período/filtros atuais."),
            unsafe_allow_html=True,
        )
        return

    for banco, df_banco in faturas.items():
        st.markdown(
            f'<p style="font-size: {FONTE_CORPO}px; color: {CORES["texto"]}; '
            f'font-weight: bold; margin-top:16px;">Cartão {banco}</p>',
            unsafe_allow_html=True,
        )
        total = float(df_banco["valor_total"].sum())
        st.caption(
            f"{len(df_banco)} meses — total {formatar_moeda(total)}"
        )
        st.dataframe(df_banco, use_container_width=True, hide_index=True)


# Função utilitária mantida pública para potenciais reusos por testes legados.
def _eventos_para_ui(
    eventos: Iterable[dict[str, object]],
) -> list[dict[str, object]]:
    """Identidade pass-through (placeholder para refactor futuro)."""
    return list(eventos)


# Reexporta constantes do módulo de análise para retro-compatibilidade
# de imports externos (alguns testes usam pagamentos.STATUS_PAGO).
__all__ = [
    "STATUS_ATRASADO",
    "STATUS_PAGO",
    "STATUS_PENDENTE",
    "calcular_kpis_pagamentos",
    "construir_eventos_calendario",
    "gerar_celulas_calendario",
    "renderizar",
]


# "Por forma de pagamento é como o banco pensa." — princípio Sprint 79
