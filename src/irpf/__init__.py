"""Módulo de preparação do IRPF -- geração de pacotes, simulação e checklist."""

import argparse
import sys
from pathlib import Path

import pandas as pd

from src.irpf.checklist import gerar_checklist
from src.irpf.gerador_pacote import gerar_csvs_por_tipo, gerar_resumo
from src.irpf.simulador import simular
from src.utils.logger import configurar_logger

logger = configurar_logger("irpf")

XLSX_DIR = Path(__file__).resolve().parents[2] / "data" / "output"


def _encontrar_xlsx() -> Path | None:
    """Encontra o XLSX mais recente."""
    arquivos = sorted(XLSX_DIR.glob("ouroboros_*.xlsx"))
    return arquivos[-1] if arquivos else None


def _formatar_moeda(valor: float) -> str:
    """Formata valor como moeda brasileira."""
    sinal = "-" if valor < 0 else ""
    return f"{sinal}R$ {abs(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def executar(ano: int) -> None:
    """Executa geração completa do pacote IRPF."""
    xlsx = _encontrar_xlsx()
    if not xlsx:
        logger.error("XLSX não encontrado em %s", XLSX_DIR)
        sys.exit(1)

    logger.info("Gerando pacote IRPF %d a partir de %s", ano, xlsx.name)

    df = pd.read_excel(xlsx, sheet_name="extrato")
    transacoes = df.to_dict("records")

    transacoes_ano = [t for t in transacoes if str(t.get("mes_ref", "")).startswith(str(ano))]

    if not transacoes_ano:
        logger.warning("Nenhuma transação encontrada para o ano %d", ano)
        return

    saida = XLSX_DIR / f"irpf_{ano}"
    saida.mkdir(parents=True, exist_ok=True)

    csvs = gerar_csvs_por_tipo(transacoes_ano, saida)
    gerar_resumo(transacoes_ano, saida)

    rendimentos = sum(
        t.get("valor", 0) for t in transacoes_ano if t.get("tag_irpf") == "rendimento_tributavel"
    )
    inss = sum(t.get("valor", 0) for t in transacoes_ano if t.get("tag_irpf") == "inss_retido")
    medicas = sum(
        t.get("valor", 0) for t in transacoes_ano if t.get("tag_irpf") == "dedutivel_medico"
    )
    impostos = sum(t.get("valor", 0) for t in transacoes_ano if t.get("tag_irpf") == "imposto_pago")

    resultado = simular(rendimentos, inss, medicas, impostos, dependentes=0, ano=ano)

    checklist = gerar_checklist(transacoes_ano)

    logger.info("=" * 50)
    logger.info("IRPF %d -- Resumo", ano)
    logger.info("=" * 50)
    logger.info(
        "Transações com tag IRPF: %d",
        sum(1 for t in transacoes_ano if t.get("tag_irpf")),
    )
    logger.info("CSVs gerados: %d arquivos", len(csvs))
    logger.info("Rendimentos tributáveis: %s", _formatar_moeda(rendimentos))
    logger.info("INSS retido: %s", _formatar_moeda(inss))
    logger.info("Despesas médicas: %s", _formatar_moeda(medicas))
    logger.info("Impostos pagos: %s", _formatar_moeda(impostos))
    logger.info(
        "Regime recomendado: %s (economia de %s)",
        resultado["recomendado"],
        _formatar_moeda(resultado["economia"]),
    )
    logger.info("Saldo (completo): %s", _formatar_moeda(resultado["saldo_completo"]))
    logger.info(
        "Saldo (simplificado): %s",
        _formatar_moeda(resultado["saldo_simplificado"]),
    )
    logger.info(
        "Checklist: %d/%d documentos verificados",
        sum(1 for c in checklist if c["status"] == "Dados no sistema"),
        len(checklist),
    )
    logger.info("Pacote salvo em: %s", saida)


def main() -> None:
    """Entry point CLI."""
    parser = argparse.ArgumentParser(description="Geração de pacote IRPF")
    parser.add_argument("--ano", type=int, required=True, help="Ano-calendário")
    args = parser.parse_args()
    executar(args.ano)


if __name__ == "__main__":
    main()


# "A morte e os impostos são as duas únicas certezas na vida." -- Benjamin Franklin
