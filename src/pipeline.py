"""Orquestrador principal do pipeline ETL financeiro."""

import argparse
import sys
from datetime import datetime
from pathlib import Path

from src.extractors.contracheque_pdf import processar_holerites
from src.load.relatorio import gerar_relatorios
from src.load.xlsx_writer import gerar_xlsx
from src.transform.categorizer import Categorizer
from src.transform.deduplicator import deduplicar
from src.transform.irpf_tagger import aplicar_tags_irpf
from src.transform.normalizer import normalizar_transacao
from src.utils.logger import configurar_logger

logger = configurar_logger("pipeline")

RAIZ = Path(__file__).parent.parent
DIR_RAW = RAIZ / "data" / "raw"
DIR_OUTPUT = RAIZ / "data" / "output"
DIR_HISTORICO = RAIZ / "data" / "historico"
CONTROLE_ANTIGO = DIR_HISTORICO / "controle_antigo.xlsx"


def _descobrir_extratores() -> list:
    """Importa e retorna instâncias de todos os extratores disponíveis."""
    extratores = []

    try:
        from src.extractors.nubank_cartao import ExtratorNubankCartao

        extratores.append(ExtratorNubankCartao)
    except ImportError as e:
        logger.warning("Extrator nubank_cartao indisponível: %s", e)

    try:
        from src.extractors.nubank_cc import ExtratorNubankCC

        extratores.append(ExtratorNubankCC)
    except ImportError as e:
        logger.warning("Extrator nubank_cc indisponível: %s", e)

    try:
        from src.extractors.c6_cc import ExtratorC6CC

        extratores.append(ExtratorC6CC)
    except ImportError as e:
        logger.warning("Extrator c6_cc indisponível: %s", e)

    try:
        from src.extractors.c6_cartao import ExtratorC6Cartao

        extratores.append(ExtratorC6Cartao)
    except ImportError as e:
        logger.warning("Extrator c6_cartao indisponível: %s", e)

    try:
        from src.extractors.itau_pdf import ExtratorItauPDF

        extratores.append(ExtratorItauPDF)
    except ImportError as e:
        logger.warning("Extrator itau_pdf indisponível: %s", e)

    try:
        from src.extractors.santander_pdf import ExtratorSantanderPDF

        extratores.append(ExtratorSantanderPDF)
    except ImportError as e:
        logger.warning("Extrator santander_pdf indisponível: %s", e)

    try:
        from src.extractors.energia_ocr import ExtratorEnergiaOCR

        extratores.append(ExtratorEnergiaOCR)
    except ImportError as e:
        logger.warning("Extrator energia_ocr indisponível: %s", e)

    try:
        from src.extractors.ofx_parser import ExtratorOFX

        extratores.append(ExtratorOFX)
    except ImportError as e:
        logger.warning("Extrator ofx_parser indisponível: %s", e)

    try:
        from src.extractors.cupom_garantia_estendida_pdf import (
            ExtratorCupomGarantiaEstendida,
        )

        extratores.append(ExtratorCupomGarantiaEstendida)
    except ImportError as e:
        logger.warning("Extrator cupom_garantia_estendida_pdf indisponível: %s", e)

    try:
        from src.extractors.nfce_pdf import ExtratorNfcePDF

        extratores.append(ExtratorNfcePDF)
    except ImportError as e:
        logger.warning("Extrator nfce_pdf indisponível: %s", e)

    try:
        from src.extractors.danfe_pdf import ExtratorDanfePDF

        extratores.append(ExtratorDanfePDF)
    except ImportError as e:
        logger.warning("Extrator danfe_pdf indisponível: %s", e)

    return extratores


def _escanear_arquivos(diretorio: Path) -> list[Path]:
    """Escaneia recursivamente todos os arquivos em data/raw/."""
    extensoes = {".csv", ".xlsx", ".xls", ".pdf", ".ofx"}
    arquivos = []

    for arquivo in diretorio.rglob("*"):
        if arquivo.is_file() and arquivo.suffix.lower() in extensoes:
            # Ignorar arquivos duplicados com sufixo (1), (2)
            if " (1)" in arquivo.stem or " (2)" in arquivo.stem:
                logger.debug("Ignorando duplicata de download: %s", arquivo.name)
                continue
            arquivos.append(arquivo)

    logger.info("Encontrados %d arquivos para processar em %s", len(arquivos), diretorio)
    return sorted(arquivos)


def _extrair_tudo(arquivos: list[Path], classes_extratores: list) -> list[dict]:
    """Executa extração de todos os arquivos com os extratores disponíveis."""
    transacoes_brutas: list[dict] = []
    arquivos_processados = 0
    arquivos_ignorados = 0

    for arquivo in arquivos:
        processado = False
        for cls_extrator in classes_extratores:
            try:
                extrator = cls_extrator(arquivo)
                if extrator.pode_processar(arquivo):
                    resultado = extrator.extrair()
                    for t in resultado:
                        transacao_norm = normalizar_transacao(
                            data_transacao=t.data,
                            valor=t.valor,
                            descricao=t.descricao,
                            banco_origem=t.banco_origem,
                            tipo_extrato="cartao"
                            if "cartao" in t.banco_origem.lower() or t.forma_pagamento == "Crédito"
                            else "cc",
                            identificador=t.identificador,
                            subtipo=_inferir_subtipo(arquivo),
                            arquivo_origem=str(arquivo),
                        )
                        transacoes_brutas.append(transacao_norm)

                    arquivos_processados += 1
                    logger.info(
                        "Extraídas %d transações de %s (%s)",
                        len(resultado),
                        arquivo.name,
                        cls_extrator.__name__,
                    )
                    processado = True
                    break
            except Exception as e:
                logger.error(
                    "Erro ao processar %s com %s: %s", arquivo.name, cls_extrator.__name__, e
                )

        if not processado:
            arquivos_ignorados += 1
            logger.warning("Nenhum extrator compatível para: %s", arquivo.name)

    logger.info(
        "Extração concluída: %d arquivos processados, %d ignorados, %d transações brutas",
        arquivos_processados,
        arquivos_ignorados,
        len(transacoes_brutas),
    )
    return transacoes_brutas


def _inferir_subtipo(arquivo: Path) -> str | None:
    """Infere subtipo (pf/pj) pelo caminho do arquivo."""
    partes = str(arquivo).lower()
    if "pj" in partes:
        return "pj"
    if "pf" in partes:
        return "pf"
    return None


def _importar_historico() -> list[dict]:
    """Importa transações do XLSX histórico (ago/2022 - jul/2023)."""
    if not CONTROLE_ANTIGO.exists():
        logger.info("Arquivo histórico não encontrado: %s", CONTROLE_ANTIGO)
        return []

    import openpyxl

    transacoes = []
    try:
        wb = openpyxl.load_workbook(CONTROLE_ANTIGO)
        if "Extrato" not in wb.sheetnames:
            logger.warning("Aba 'Extrato' não encontrada no histórico")
            return []

        ws = wb["Extrato"]
        for row in ws.iter_rows(min_row=2, values_only=True):
            data_val = row[0] if len(row) > 0 else None
            gasto = row[1] if len(row) > 1 else None
            forma = row[2] if len(row) > 2 else ""
            local = row[3] if len(row) > 3 else ""
            quem = row[4] if len(row) > 4 else ""
            categoria = row[5] if len(row) > 5 else None
            classificacao = row[6] if len(row) > 6 else None

            if data_val is None or gasto is None:
                continue

            if isinstance(data_val, datetime):
                data_date = data_val.date()
            elif isinstance(data_val, str):
                try:
                    data_date = datetime.strptime(data_val, "%Y-%m-%d").date()
                except ValueError:
                    continue
            else:
                continue

            # Normalizar classificação corrompida do histórico
            clf_raw = str(classificacao).strip() if classificacao else "Questionável"
            clf_map = {
                "Obrigatório": "Obrigatório",
                "Obrigatórios": "Obrigatório",
                "Questionável": "Questionável",
                "Supérfluo": "Supérfluo",
            }
            clf_normalizada = clf_map.get(clf_raw, "Questionável")

            transacoes.append(
                {
                    "data": data_date,
                    "valor": abs(float(gasto)) if isinstance(gasto, (int, float)) else 0,
                    "forma_pagamento": str(forma) if forma else "Débito",
                    "local": str(local) if local else "",
                    "quem": str(quem) if quem else "Casal",
                    "categoria": str(categoria) if categoria else "Outros",
                    "classificacao": clf_normalizada,
                    "banco_origem": "Histórico",
                    "tipo": "Despesa",
                    "mes_ref": data_date.strftime("%Y-%m"),
                    "tag_irpf": None,
                    "obs": "Importado do histórico",
                    "_identificador": f"hist_{data_date.isoformat()}_{gasto}_{local}",
                    "_descricao_original": str(local),
                    "_arquivo_origem": str(CONTROLE_ANTIGO),
                }
            )

        logger.info("Histórico importado: %d transações (ago/2022 - jul/2023)", len(transacoes))
    except Exception as e:
        logger.error("Erro ao importar histórico: %s", e)

    return transacoes


def _filtrar_por_mes(transacoes: list[dict], mes: str) -> list[dict]:
    """Filtra transações por mês específico."""
    return [t for t in transacoes if t.get("mes_ref") == mes]


def executar(mes: str | None = None, processar_tudo: bool = False) -> None:
    """Executa o pipeline completo."""
    logger.info("=== Protocolo Ouroboros -- Pipeline ===")

    # 1. Descobrir extratores
    classes_extratores = _descobrir_extratores()
    logger.info("Extratores disponíveis: %d", len(classes_extratores))

    # 2. Escanear arquivos
    arquivos = _escanear_arquivos(DIR_RAW)

    # 3. Extrair transações
    transacoes = _extrair_tudo(arquivos, classes_extratores)

    # 4. Importar histórico
    historico = _importar_historico()
    transacoes.extend(historico)

    # 5. Deduplicar
    transacoes = deduplicar(transacoes)

    # 6. Categorizar
    categorizer = Categorizer()
    transacoes = categorizer.categorizar_lote(transacoes)

    # 7. Aplicar tags IRPF
    transacoes = aplicar_tags_irpf(transacoes)

    # 8. Filtrar por mês se necessário
    if mes and not processar_tudo:
        transacoes_filtradas = _filtrar_por_mes(transacoes, mes)
        logger.info("Filtrado para %s: %d transações", mes, len(transacoes_filtradas))
    else:
        transacoes_filtradas = transacoes

    # 9. Ordenar por data
    transacoes_filtradas.sort(key=lambda t: t.get("data", ""))

    # 10. Processar holerites (contracheques) -- fonte extra para a aba renda
    contracheques = processar_holerites(DIR_RAW / "andre" / "holerites")

    # 11. Gerar XLSX
    ano = mes[:4] if mes else str(datetime.now().year)
    caminho_xlsx = DIR_OUTPUT / f"ouroboros_{ano}.xlsx"
    gerar_xlsx(transacoes_filtradas, caminho_xlsx, CONTROLE_ANTIGO, contracheques)

    # 11. Gerar relatórios
    # Quando --mes é usado, passa transações completas (para projeções corretas)
    # mas filtra a geração apenas para o mês solicitado
    gerar_relatorios(
        transacoes, DIR_OUTPUT, meses_filtro=[mes] if (mes and not processar_tudo) else None
    )

    logger.info("=== Pipeline concluído ===")
    logger.info("XLSX: %s", caminho_xlsx)
    logger.info("Relatórios: %s", DIR_OUTPUT)


def main() -> None:
    """Entrypoint CLI."""
    parser = argparse.ArgumentParser(description="Pipeline ETL Financeiro")
    parser.add_argument("--mes", type=str, help="Mês para processar (YYYY-MM)")
    parser.add_argument("--tudo", action="store_true", help="Processar todos os dados")
    args = parser.parse_args()

    if not args.mes and not args.tudo:
        parser.print_help()
        sys.exit(1)

    executar(mes=args.mes, processar_tudo=args.tudo)


if __name__ == "__main__":
    main()


# "A verdadeira sabedoria está em reconhecer a própria ignorância." -- Sócrates
