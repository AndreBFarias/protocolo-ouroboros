"""Gerador de pacote CSV para declaração do IRPF."""

import csv
from pathlib import Path

from src.utils.logger import configurar_logger

logger = configurar_logger("irpf_gerador")


def gerar_csvs_por_tipo(transacoes: list[dict], diretorio: Path) -> list[Path]:
    """Gera CSVs separados por tipo de tag IRPF."""
    diretorio.mkdir(parents=True, exist_ok=True)

    por_tipo: dict[str, list[dict]] = {}
    for t in transacoes:
        tag = t.get("tag_irpf")
        if isinstance(tag, str) and tag:
            por_tipo.setdefault(tag, []).append(t)

    arquivos: list[Path] = []
    for tipo, registros in sorted(por_tipo.items()):
        caminho = diretorio / f"{tipo}.csv"
        with open(caminho, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "data",
                    "local",
                    "valor",
                    "categoria",
                    "banco_origem",
                    "mes_ref",
                ],
            )
            writer.writeheader()
            for r in sorted(registros, key=lambda x: x.get("data", "")):
                writer.writerow(
                    {
                        "data": r.get("data", ""),
                        "local": r.get("local", ""),
                        "valor": f"{r.get('valor', 0):.2f}",
                        "categoria": r.get("categoria", ""),
                        "banco_origem": r.get("banco_origem", ""),
                        "mes_ref": r.get("mes_ref", ""),
                    }
                )
        arquivos.append(caminho)
        logger.info("CSV gerado: %s (%d registros)", caminho.name, len(registros))

    return arquivos


def gerar_resumo(transacoes: list[dict], diretorio: Path) -> Path:
    """Gera CSV de resumo consolidado com totais por tipo."""
    diretorio.mkdir(parents=True, exist_ok=True)
    caminho = diretorio / "resumo_irpf.csv"

    totais: dict[str, float] = {}
    contagens: dict[str, int] = {}
    for t in transacoes:
        tag = t.get("tag_irpf")
        if isinstance(tag, str) and tag:
            totais[tag] = totais.get(tag, 0) + t.get("valor", 0)
            contagens[tag] = contagens.get(tag, 0) + 1

    with open(caminho, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["tipo", "quantidade", "valor_total"])
        for tipo in sorted(totais.keys()):
            writer.writerow([tipo, contagens[tipo], f"{totais[tipo]:.2f}"])

    logger.info("Resumo IRPF gerado: %s", caminho)
    return caminho


# "Ordem é a primeira lei do céu." -- Alexander Pope
