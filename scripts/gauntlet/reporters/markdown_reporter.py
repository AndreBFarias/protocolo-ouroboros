"""Gerador de GAUNTLET_REPORT.md com resultados das fases."""

import platform
import sys
from datetime import datetime

from scripts.gauntlet.config import ResultadoFase


def gerar_relatorio(
    fases: list[ResultadoFase],
    duracao_total: float,
) -> str:
    """Gera relatório markdown completo do gauntlet."""
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    python_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    total_testes = sum(f.total for f in fases)
    total_ok = sum(f.ok for f in fases)
    total_falhas = sum(f.falhas for f in fases)
    taxa = (total_ok / total_testes * 100) if total_testes > 0 else 0

    linhas: list[str] = []

    linhas.append("# Relatório Gauntlet -- Protocolo Ouroboros")
    linhas.append("")
    linhas.append(
        f"Data: {agora} | Duração: {duracao_total:.1f}s | Python {python_ver} | {platform.system()}"
    )
    linhas.append("")

    if total_falhas == 0:
        linhas.append(f"## Resultado Geral: {total_ok}/{total_testes} (100%)")
    else:
        linhas.append(f"## Resultado Geral: {total_ok}/{total_testes} ({taxa:.0f}%)")
    linhas.append("")

    linhas.append("| Fase | Testes | OK | Falha | Tempo |")
    linhas.append("|------|--------|----|-------|-------|")
    for fase in fases:
        linhas.append(
            f"| {fase.nome} | {fase.total} | {fase.ok} | {fase.falhas} | {fase.tempo_total:.1f}s |"
        )
    linhas.append("")

    linhas.append("---")
    linhas.append("")
    linhas.append("## Detalhes")
    linhas.append("")

    for fase in fases:
        marca = "[OK]" if fase.passou else "[FALHA]"
        linhas.append(f"### Fase: {fase.nome} {marca}")
        linhas.append("")

        for teste in fase.testes:
            if teste.passou:
                linhas.append(f"- [OK] {teste.nome}: {teste.detalhe}")
            else:
                erro_txt = f" | Erro: {teste.erro}" if teste.erro else ""
                linhas.append(f"- [FALHA] {teste.nome}: {teste.detalhe}{erro_txt}")

        linhas.append("")

    if total_falhas > 0:
        linhas.append("---")
        linhas.append("")
        linhas.append("## Falhas")
        linhas.append("")
        for fase in fases:
            for teste in fase.testes:
                if not teste.passou:
                    erro_txt = f" -- {teste.erro}" if teste.erro else ""
                    linhas.append(f"- **{fase.nome}.{teste.nome}**: {teste.detalhe}{erro_txt}")
        linhas.append("")

    linhas.append("---")
    linhas.append("")
    linhas.append('*"Medir é saber. Não medir é adivinhar." -- Lord Kelvin*')
    linhas.append("")

    return "\n".join(linhas)


# "Um bom relatório vale mais que mil desculpas." -- Provérbio corporativo
