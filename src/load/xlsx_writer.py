"""Geração do XLSX consolidado com 8 abas."""

from datetime import date, datetime
from pathlib import Path
from typing import Optional

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from src.utils.logger import configurar_logger

logger = configurar_logger("xlsx_writer")

COLUNAS_EXTRATO = [
    "data",
    "valor",
    "forma_pagamento",
    "local",
    "quem",
    "categoria",
    "classificacao",
    "banco_origem",
    "tipo",
    "mes_ref",
    "tag_irpf",
    "obs",
]

HEADER_FILL = PatternFill(start_color="2F5496", end_color="2F5496", fill_type="solid")
HEADER_FONT = Font(color="FFFFFF", bold=True, size=11)
VALOR_FORMAT = "#,##0.00"


def _aplicar_estilo_header(ws: openpyxl.worksheet.worksheet.Worksheet) -> None:
    """Aplica estilo visual nos cabeçalhos."""
    for cell in ws[1]:
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center")


def _ajustar_largura_colunas(ws: openpyxl.worksheet.worksheet.Worksheet) -> None:
    """Ajusta a largura das colunas pelo conteúdo."""
    for col_idx, col in enumerate(ws.columns, 1):
        max_len = 0
        for cell in col:
            if cell.value is not None:
                max_len = max(max_len, len(str(cell.value)))
        largura = min(max_len + 3, 40)
        ws.column_dimensions[get_column_letter(col_idx)].width = largura


def _criar_aba_extrato(wb: openpyxl.Workbook, transacoes: list[dict]) -> None:
    """Cria a aba principal de extrato."""
    ws = wb.create_sheet("extrato")

    # Cabeçalhos
    for col_idx, col_nome in enumerate(COLUNAS_EXTRATO, 1):
        ws.cell(row=1, column=col_idx, value=col_nome)

    # Dados
    for row_idx, t in enumerate(transacoes, 2):
        for col_idx, col_nome in enumerate(COLUNAS_EXTRATO, 1):
            valor = t.get(col_nome)
            cell = ws.cell(row=row_idx, column=col_idx, value=valor)

            if col_nome == "valor":
                cell.number_format = VALOR_FORMAT
            elif col_nome == "data" and isinstance(valor, (date, datetime)):
                cell.number_format = "DD/MM/YYYY"

    _aplicar_estilo_header(ws)
    _ajustar_largura_colunas(ws)

    # Filtro automático
    if len(transacoes) > 0:
        ws.auto_filter.ref = f"A1:{get_column_letter(len(COLUNAS_EXTRATO))}{len(transacoes) + 1}"

    logger.info("Aba 'extrato': %d transações escritas", len(transacoes))


def _criar_aba_renda(wb: openpyxl.Workbook, transacoes: list[dict]) -> None:
    """Cria a aba de renda mensal."""
    ws = wb.create_sheet("renda")
    colunas = ["mes_ref", "fonte", "bruto", "inss", "irrf", "vr_va", "liquido", "banco"]

    for col_idx, col_nome in enumerate(colunas, 1):
        ws.cell(row=1, column=col_idx, value=col_nome)

    # Agrupar receitas por mês
    receitas_por_mes: dict[str, list[dict]] = {}
    for t in transacoes:
        if t.get("tipo") == "Receita":
            mes = t.get("mes_ref", "")
            receitas_por_mes.setdefault(mes, []).append(t)

    row_idx = 2
    for mes in sorted(receitas_por_mes.keys()):
        for t in receitas_por_mes[mes]:
            ws.cell(row=row_idx, column=1, value=mes)
            ws.cell(row=row_idx, column=2, value=t.get("local", ""))
            ws.cell(row=row_idx, column=3, value=t.get("valor", 0))
            ws.cell(row=row_idx, column=7, value=t.get("valor", 0))
            ws.cell(row=row_idx, column=8, value=t.get("banco_origem", ""))
            ws.cell(row=row_idx, column=3).number_format = VALOR_FORMAT
            ws.cell(row=row_idx, column=7).number_format = VALOR_FORMAT
            row_idx += 1

    _aplicar_estilo_header(ws)
    _ajustar_largura_colunas(ws)
    logger.info("Aba 'renda': %d linhas", row_idx - 2)


def _criar_aba_resumo_mensal(wb: openpyxl.Workbook, transacoes: list[dict]) -> None:
    """Cria a aba de resumo mensal gerada automaticamente."""
    ws = wb.create_sheet("resumo_mensal")
    colunas = [
        "mes_ref",
        "receita_total",
        "despesa_total",
        "saldo",
        "top_categoria",
        "top_gasto",
        "total_obrigatorio",
        "total_superfluo",
        "total_questionavel",
    ]

    for col_idx, col_nome in enumerate(colunas, 1):
        ws.cell(row=1, column=col_idx, value=col_nome)

    # Agrupar por mês
    dados_mes: dict[str, dict] = {}
    for t in transacoes:
        if t.get("tipo") == "Transferência Interna":
            continue

        mes = t.get("mes_ref", "")
        if mes not in dados_mes:
            dados_mes[mes] = {
                "receita": 0,
                "despesa": 0,
                "categorias": {},
                "classificacoes": {"Obrigatório": 0, "Supérfluo": 0, "Questionável": 0},
            }

        valor = t.get("valor", 0)
        if t.get("tipo") == "Receita":
            dados_mes[mes]["receita"] += valor
        elif t.get("tipo") in ("Despesa", "Imposto"):
            dados_mes[mes]["despesa"] += valor
            cat = t.get("categoria", "Outros")
            dados_mes[mes]["categorias"][cat] = dados_mes[mes]["categorias"].get(cat, 0) + valor
            clf = t.get("classificacao", "Questionável")
            if clf in dados_mes[mes]["classificacoes"]:
                dados_mes[mes]["classificacoes"][clf] += valor

    row_idx = 2
    for mes in sorted(dados_mes.keys()):
        d = dados_mes[mes]
        top_cat = max(d["categorias"], key=d["categorias"].get) if d["categorias"] else ""
        top_val = d["categorias"].get(top_cat, 0)

        ws.cell(row=row_idx, column=1, value=mes)
        ws.cell(row=row_idx, column=2, value=d["receita"])
        ws.cell(row=row_idx, column=3, value=d["despesa"])
        ws.cell(row=row_idx, column=4, value=d["receita"] - d["despesa"])
        ws.cell(row=row_idx, column=5, value=top_cat)
        ws.cell(row=row_idx, column=6, value=f"R$ {top_val:,.2f}")
        ws.cell(row=row_idx, column=7, value=d["classificacoes"]["Obrigatório"])
        ws.cell(row=row_idx, column=8, value=d["classificacoes"]["Supérfluo"])
        ws.cell(row=row_idx, column=9, value=d["classificacoes"]["Questionável"])

        for c in [2, 3, 4, 7, 8, 9]:
            ws.cell(row=row_idx, column=c).number_format = VALOR_FORMAT

        row_idx += 1

    _aplicar_estilo_header(ws)
    _ajustar_largura_colunas(ws)
    logger.info("Aba 'resumo_mensal': %d meses", row_idx - 2)


def _criar_aba_dividas(
    wb: openpyxl.Workbook,
    caminho_historico: Optional[Path] = None,
) -> None:
    """Cria a aba de dívidas ativas, importando do histórico se existir."""
    ws = wb.create_sheet("dividas_ativas")
    colunas = ["mes_ref", "custo", "valor", "status", "vencimento", "quem", "recorrente", "obs"]

    for col_idx, col_nome in enumerate(colunas, 1):
        ws.cell(row=1, column=col_idx, value=col_nome)

    row_idx = 2
    if caminho_historico and caminho_historico.exists():
        try:
            wb_hist = openpyxl.load_workbook(caminho_historico)
            if "Dívidas Ativas" in wb_hist.sheetnames:
                ws_hist = wb_hist["Dívidas Ativas"]
                for i, row in enumerate(ws_hist.iter_rows(min_row=2, values_only=True)):
                    valores = [v for v in row if v is not None]
                    if not valores:
                        continue
                    custo = row[0] if len(row) > 0 else ""
                    valor = row[1] if len(row) > 1 else 0
                    status = row[2] if len(row) > 2 else ""
                    obs = row[3] if len(row) > 3 else ""

                    ws.cell(row=row_idx, column=1, value=date.today().strftime("%Y-%m"))
                    ws.cell(row=row_idx, column=2, value=custo)
                    ws.cell(
                        row=row_idx, column=3, value=valor if isinstance(valor, (int, float)) else 0
                    )
                    ws.cell(row=row_idx, column=4, value=status)
                    ws.cell(row=row_idx, column=8, value=obs)

                    if isinstance(valor, (int, float)):
                        ws.cell(row=row_idx, column=3).number_format = VALOR_FORMAT

                    row_idx += 1

                logger.info("Aba 'dividas_ativas': importadas %d linhas do histórico", row_idx - 2)
        except Exception as e:
            logger.warning("Erro ao importar dívidas do histórico: %s", e)

    _aplicar_estilo_header(ws)
    _ajustar_largura_colunas(ws)


def _criar_aba_inventario(
    wb: openpyxl.Workbook,
    caminho_historico: Optional[Path] = None,
) -> None:
    """Cria a aba de inventário, importando e melhorando do histórico."""
    ws = wb.create_sheet("inventario")
    colunas = [
        "bem",
        "valor_aquisicao",
        "vida_util_anos",
        "depreciacao_anual",
        "perda_mensal",
    ]

    for col_idx, col_nome in enumerate(colunas, 1):
        ws.cell(row=1, column=col_idx, value=col_nome)

    row_idx = 2
    if caminho_historico and caminho_historico.exists():
        try:
            wb_hist = openpyxl.load_workbook(caminho_historico)
            if "Inventário" in wb_hist.sheetnames:
                ws_hist = wb_hist["Inventário"]
                for row in ws_hist.iter_rows(min_row=2, values_only=True):
                    bem = row[0] if len(row) > 0 else None
                    if bem is None or not isinstance(bem, str):
                        continue
                    valor_aq = row[1] if len(row) > 1 and isinstance(row[1], (int, float)) else 0
                    vida_util = row[2] if len(row) > 2 and isinstance(row[2], (int, float)) else 2
                    dep_anual = row[3] if len(row) > 3 and isinstance(row[3], (int, float)) else 0.1
                    perda = (valor_aq * dep_anual) / vida_util if vida_util > 0 else 0

                    ws.cell(row=row_idx, column=1, value=bem)
                    ws.cell(row=row_idx, column=2, value=valor_aq)
                    ws.cell(row=row_idx, column=3, value=vida_util)
                    ws.cell(row=row_idx, column=4, value=dep_anual)
                    ws.cell(row=row_idx, column=5, value=round(perda, 2))

                    ws.cell(row=row_idx, column=2).number_format = VALOR_FORMAT
                    ws.cell(row=row_idx, column=5).number_format = VALOR_FORMAT
                    row_idx += 1

                logger.info("Aba 'inventario': importados %d bens do histórico", row_idx - 2)
        except Exception as e:
            logger.warning("Erro ao importar inventário do histórico: %s", e)

    _aplicar_estilo_header(ws)
    _ajustar_largura_colunas(ws)


def _criar_aba_prazos(
    wb: openpyxl.Workbook,
    caminho_historico: Optional[Path] = None,
) -> None:
    """Cria a aba de prazos de vencimento."""
    ws = wb.create_sheet("prazos")
    colunas = ["conta", "dia_vencimento", "banco_pagamento", "auto_debito"]

    for col_idx, col_nome in enumerate(colunas, 1):
        ws.cell(row=1, column=col_idx, value=col_nome)

    row_idx = 2
    if caminho_historico and caminho_historico.exists():
        try:
            wb_hist = openpyxl.load_workbook(caminho_historico)
            if "Prazos" in wb_hist.sheetnames:
                ws_hist = wb_hist["Prazos"]
                for row in ws_hist.iter_rows(min_row=8, values_only=True):
                    # Dados podem estar nas colunas C e D (índices 2 e 3)
                    conta = (
                        row[2] if len(row) > 2 and row[2] else (row[0] if len(row) > 0 else None)
                    )
                    dia = row[3] if len(row) > 3 and row[3] else (row[1] if len(row) > 1 else None)
                    if conta and dia and str(conta).strip() != "Dias":
                        ws.cell(row=row_idx, column=1, value=conta)
                        ws.cell(row=row_idx, column=2, value=dia)
                        row_idx += 1

                logger.info("Aba 'prazos': importados %d prazos do histórico", row_idx - 2)
        except Exception as e:
            logger.warning("Erro ao importar prazos do histórico: %s", e)

    _aplicar_estilo_header(ws)
    _ajustar_largura_colunas(ws)


def _criar_aba_irpf(wb: openpyxl.Workbook, transacoes: list[dict]) -> None:
    """Cria a aba de dados relevantes para IRPF."""
    ws = wb.create_sheet("irpf")
    colunas = ["ano", "tipo", "fonte", "cnpj_cpf", "valor", "mes"]

    for col_idx, col_nome in enumerate(colunas, 1):
        ws.cell(row=1, column=col_idx, value=col_nome)

    row_idx = 2
    for t in transacoes:
        tag = t.get("tag_irpf")
        if tag is None:
            continue

        data_t = t.get("data")
        ano = data_t.year if hasattr(data_t, "year") else 0

        ws.cell(row=row_idx, column=1, value=ano)
        ws.cell(row=row_idx, column=2, value=tag)
        ws.cell(row=row_idx, column=3, value=t.get("local", ""))
        ws.cell(row=row_idx, column=5, value=t.get("valor", 0))
        ws.cell(row=row_idx, column=6, value=t.get("mes_ref", ""))
        ws.cell(row=row_idx, column=5).number_format = VALOR_FORMAT
        row_idx += 1

    _aplicar_estilo_header(ws)
    _ajustar_largura_colunas(ws)
    logger.info("Aba 'irpf': %d registros com tag IRPF", row_idx - 2)


def _criar_aba_analise(wb: openpyxl.Workbook, transacoes: list[dict]) -> None:
    """Cria a aba de análise com insights gerados."""
    ws = wb.create_sheet("analise")
    ws.cell(row=1, column=1, value="Análise gerada automaticamente")
    ws.cell(row=1, column=1).font = Font(bold=True, size=14)

    total_receitas = sum(t["valor"] for t in transacoes if t.get("tipo") == "Receita")
    total_despesas = sum(t["valor"] for t in transacoes if t.get("tipo") in ("Despesa", "Imposto"))
    total_transf = sum(t["valor"] for t in transacoes if t.get("tipo") == "Transferência Interna")

    linhas = [
        "",
        f"Total de transações processadas: {len(transacoes)}",
        f"Receita total: R$ {total_receitas:,.2f}",
        f"Despesa total: R$ {total_despesas:,.2f}",
        f"Saldo: R$ {total_receitas - total_despesas:,.2f}",
        f"Transferências internas: R$ {total_transf:,.2f}",
        "",
        "Detalhes por mês disponíveis na aba 'resumo_mensal'.",
    ]

    for i, linha in enumerate(linhas, 2):
        ws.cell(row=i, column=1, value=linha)

    ws.column_dimensions["A"].width = 60


def gerar_xlsx(
    transacoes: list[dict],
    caminho_saida: Path,
    caminho_historico: Optional[Path] = None,
) -> Path:
    """Gera o XLSX completo com todas as 8 abas."""
    wb = openpyxl.Workbook()
    # Remover aba padrão
    wb.remove(wb.active)

    _criar_aba_extrato(wb, transacoes)
    _criar_aba_renda(wb, transacoes)
    _criar_aba_dividas(wb, caminho_historico)
    _criar_aba_inventario(wb, caminho_historico)
    _criar_aba_prazos(wb, caminho_historico)
    _criar_aba_resumo_mensal(wb, transacoes)
    _criar_aba_irpf(wb, transacoes)
    _criar_aba_analise(wb, transacoes)

    caminho_saida.parent.mkdir(parents=True, exist_ok=True)
    wb.save(caminho_saida)

    logger.info("XLSX gerado: %s (%d transações, 8 abas)", caminho_saida, len(transacoes))
    return caminho_saida


# "A riqueza não consiste em ter grandes posses, mas em ter poucas necessidades." -- Epicteto
