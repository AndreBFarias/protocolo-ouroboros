"""Calendário mensal de pagamentos (UX-V-2.2 / UX-V-2.2.B).

Módulo extraído de ``src.dashboard.paginas.pagamentos`` para conformar
o limite canônico de 800 linhas por arquivo (padrão `(h)` do
``VALIDATOR_BRIEF.md``). As 4 funções abaixo são internas à página
Pagamentos e renderizam o calendário do mês inteiro mais a lista lateral
acionável de "próximos vencimentos".

Não há mudança comportamental nem de assinatura — apenas relocação.
"""

from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta
from urllib.parse import quote

import pandas as pd

from src.dashboard.componentes.html_utils import minificar

NOMES_MESES: tuple[str, ...] = (
    "",
    "JANEIRO",
    "FEVEREIRO",
    "MARÇO",
    "ABRIL",
    "MAIO",
    "JUNHO",
    "JULHO",
    "AGOSTO",
    "SETEMBRO",
    "OUTUBRO",
    "NOVEMBRO",
    "DEZEMBRO",
)

ABREV_MESES: tuple[str, ...] = (
    "JAN",
    "FEV",
    "MAR",
    "ABR",
    "MAI",
    "JUN",
    "JUL",
    "AGO",
    "SET",
    "OUT",
    "NOV",
    "DEZ",
)


def _gerar_calendario_mes(ano: int, mes: int) -> list[list[date | None]]:
    """Retorna matriz NxM (semanas x dias) com datas do mês.

    Células fora do mês = ``None``. Primeira semana começa Seg, última Dom.
    Garante mínimo de 5 semanas para layout estável (mockup 04-pagamentos).
    """
    primeiro_dia = date(ano, mes, 1)
    _, total_dias = monthrange(ano, mes)
    weekday_inicio = primeiro_dia.weekday()  # Seg=0, Dom=6

    dias: list[date | None] = []
    for _ in range(weekday_inicio):
        dias.append(None)
    for d in range(1, total_dias + 1):
        dias.append(date(ano, mes, d))
    while len(dias) % 7 != 0:
        dias.append(None)
    while len(dias) // 7 < 5:
        dias.extend([None] * 7)

    return [dias[i : i + 7] for i in range(0, len(dias), 7)]


def _pagamentos_por_data(
    df_prazos: pd.DataFrame, ano: int, mes: int
) -> dict[date, list[dict[str, object]]]:
    """Agrupa pagamentos do mês por data de vencimento.

    Retorna ``{date(2026, 5, 10): [{"label", "tipo", "valor"}, ...], ...}``.
    Tipos canônicos: ``fixo`` (recorrente futuro), ``em_atraso`` (data
    passada), ``cartao`` (conta com palavra "fatura"/"cartao"/"nubank"/etc),
    ``variavel`` (boleto sem regra recorrente).

    Quando ``df_prazos`` está vazio, retorna ``{}`` (fallback graceful).
    """
    if df_prazos is None or df_prazos.empty:
        return {}
    if "dia_vencimento" not in df_prazos.columns:
        return {}

    pgs: dict[date, list[dict[str, object]]] = {}
    hoje = date.today()
    palavras_cartao = ("fatura", "cartao", "cartão", "nubank", "c6 cartao")
    palavras_variavel = (
        "luz",
        "energia",
        "agua",
        "água",
        "internet",
        "telefone",
        "celular",
        "gas",
        "gás",
    )

    for _, row in df_prazos.iterrows():
        try:
            dia_raw = row.get("dia_vencimento", 0)
            if pd.isna(dia_raw):
                continue
            dia = int(dia_raw)
        except (ValueError, TypeError):
            continue
        if dia < 1 or dia > 31:
            continue
        try:
            d = date(ano, mes, dia)
        except ValueError:
            continue

        try:
            valor = float(row.get("valor", 0) or 0)
        except (ValueError, TypeError):
            valor = 0.0

        conta_raw = row.get("conta", row.get("nome", "?"))
        if pd.isna(conta_raw):
            conta_raw = "?"
        label = str(conta_raw).strip()

        label_lower = label.lower()
        if d < hoje:
            tipo = "em_atraso"
        elif any(p in label_lower for p in palavras_cartao):
            tipo = "cartao"
        elif any(p in label_lower for p in palavras_variavel):
            tipo = "variavel"
        else:
            tipo = "fixo"

        pgs.setdefault(d, []).append(
            {
                "label": label[:14],
                "tipo": tipo,
                "valor": valor,
            }
        )
    return pgs


def _mes_vizinho(ano: int, mes: int, delta: int) -> tuple[int, int]:
    """Retorna ``(ano, mes)`` deslocado por ``delta`` meses (±1 típico).

    Resolve transbordo de ano sem depender de ``dateutil``.
    """
    total = ano * 12 + (mes - 1) + delta
    return total // 12, (total % 12) + 1


def _link_navegacao_mes(ano: int, mes: int, simbolo: str, titulo: str) -> str:
    """Gera ``<a>`` que navega para outro mês preservando cluster/aba."""
    alvo = f"{ano:04d}-{mes:02d}"
    href = "?cluster=" + quote("Finanças") + "&tab=Pagamentos&mes_cal=" + alvo
    return (
        f'<a class="cal-nav-btn cal-nav-arrow" href="{href}" '
        f'target="_self" title="{titulo}">{simbolo}</a>'
    )


def _calendario_html(
    ano: int, mes: int, pagamentos_por_data: dict[date, list[dict[str, object]]]
) -> str:
    """Renderiza calendário do mês inteiro (Seg-Dom) com pílulas coloridas.

    Cabeçalho ``<mês> · <ano>`` + setas de navegação + grid 7 colunas +
    legenda no rodapé com 4 pílulas (fixo · variável · cartão · em atraso)
    e total mensal alinhado à direita.
    """
    semanas = _gerar_calendario_mes(ano, mes)
    cabecalho = ("SEG", "TER", "QUA", "QUI", "SEX", "SÁB", "DOM")
    hoje = date.today()

    head_dias = "".join(f'<div class="cal-head-dia">{d}</div>' for d in cabecalho)

    celulas: list[str] = []
    total_pgs = 0
    total_valor = 0.0
    for semana in semanas:
        for d in semana:
            if d is None:
                celulas.append('<div class="cal-celula cal-empty"></div>')
                continue
            pg_dia = pagamentos_por_data.get(d, [])
            classes = ["cal-celula"]
            if pg_dia:
                classes.append("cal-tem-pg")
                total_pgs += len(pg_dia)
                total_valor += sum(float(p.get("valor", 0) or 0) for p in pg_dia)
            if d == hoje:
                classes.append("cal-hoje")
            pills = "".join(
                f'<span class="cal-pill cal-pill-{p["tipo"]}" '
                f'title="{p["label"]}">{str(p["label"]).upper()}</span>'
                for p in pg_dia
            )
            celulas.append(
                f'<div class="{" ".join(classes)}">'
                f'<span class="cal-num">{d.day:02d}</span>'
                f"{pills}"
                f"</div>"
            )

    grid = head_dias + "".join(celulas)

    ano_prev, mes_prev = _mes_vizinho(ano, mes, -1)
    ano_next, mes_next = _mes_vizinho(ano, mes, 1)
    seta_prev = _link_navegacao_mes(ano_prev, mes_prev, "<", "mês anterior")
    seta_next = _link_navegacao_mes(ano_next, mes_next, ">", "próximo mês")

    return minificar(
        f"""
        <div class="pagamentos-calendario">
          <div class="cal-header">
            <span class="cal-titulo">{NOMES_MESES[mes].lower()} · {ano}</span>
            <div class="cal-nav">
              {seta_prev}
              <span class="cal-nav-btn">SEG-DOM</span>
              {seta_next}
            </div>
          </div>
          <div class="cal-grid">{grid}</div>
          <div class="cal-legenda">
            <span class="cal-legenda-item">
              <span class="cal-pill cal-pill-fixo"></span> fixo
            </span>
            <span class="cal-legenda-item">
              <span class="cal-pill cal-pill-variavel"></span> variável
            </span>
            <span class="cal-legenda-item">
              <span class="cal-pill cal-pill-cartao"></span> cartão
            </span>
            <span class="cal-legenda-item">
              <span class="cal-pill cal-pill-em_atraso"></span> em atraso
            </span>
            <span class="cal-legenda-total">
              {total_pgs} pagamentos no mês · R$ {total_valor:,.2f}
            </span>
          </div>
        </div>
        """
    )


def _lista_proximos_html(
    pagamentos_por_data: dict[date, list[dict[str, object]]],
    janela_dias: int = 14,
) -> str:
    """Lista lateral PRÓXIMOS N DIAS com botão "agendar" inline.

    Inclui datas em atraso (até 14 dias antes de hoje) e próximas
    (hoje + janela_dias). Cap em 10 itens.
    """
    hoje = date.today()
    inicio = hoje - timedelta(days=janela_dias)
    fim = hoje + timedelta(days=janela_dias)
    candidatos = sorted((d, pgs) for d, pgs in pagamentos_por_data.items() if inicio <= d <= fim)

    linhas: list[str] = []
    for d, pgs in candidatos:
        for p in pgs:
            classe = "linha-em-atraso" if d < hoje else ""
            label = str(p.get("label", "?"))
            tipo = str(p.get("tipo", "fixo"))
            valor = float(p.get("valor", 0) or 0)
            mes_abrev = ABREV_MESES[d.month - 1]
            linhas.append(
                f'<div class="proximo-linha {classe}">'
                f'<div class="prox-data">'
                f'<span class="prox-dia">{d.day:02d}</span>'
                f'<span class="prox-mes">{mes_abrev}</span>'
                f"</div>"
                f'<div class="prox-detalhes">'
                f'<span class="prox-label">{label}</span>'
                f'<span class="prox-meta">{tipo.replace("_", " ")}</span>'
                f"</div>"
                f'<span class="prox-valor">R$ {valor:,.2f}</span>'
                f'<button class="prox-btn">agendar</button>'
                f"</div>"
            )
            if len(linhas) >= 10:
                break
        if len(linhas) >= 10:
            break

    if not linhas:
        return minificar('<div class="proximos-vazio">Sem vencimentos no período.</div>')

    return minificar('<div class="proximos-lista">' + "".join(linhas) + "</div>")


# "O calendário é o limite onde o esquecimento se rende ao que volta." — Bachelard
