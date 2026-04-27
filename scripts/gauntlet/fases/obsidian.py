"""Fase 7 do gauntlet: testa sincronização com Obsidian em diretório temporário."""

import tempfile
import time
from pathlib import Path
from unittest.mock import patch

from scripts.gauntlet.config import FIXTURES_DIR, ResultadoFase, ResultadoTeste
from src.utils.logger import configurar_logger

logger = configurar_logger("gauntlet.obsidian")


def _testar_sync_relatorios(vault_tmp: Path, output_tmp: Path) -> ResultadoTeste:
    """Testa sincronização de relatórios para vault temporário."""
    from src.obsidian.sync import sincronizar_relatorios

    inicio = time.time()

    relatorio = output_tmp / "2026-04_relatorio.md"
    relatorio.write_text(
        "# Relatório Financeiro -- Abril 2026\n\n"
        "## Resumo\n\n"
        "- Receita: R$ 18.700,00\n"
        "- Despesa: R$ 8.000,00\n"
        "- Saldo: R$ 10.700,00\n",
        encoding="utf-8",
    )

    relatorios_path = vault_tmp / "Pessoal" / "Financeiro" / "Relatorios"

    try:
        with patch("src.obsidian.sync.RELATORIOS_PATH", relatorios_path):
            copiados = sincronizar_relatorios(output_tmp)

        passou = len(copiados) == 1
        destino = relatorios_path / "2026-04.md"
        existe = destino.exists()
        passou = passou and existe

        detalhe = f"{len(copiados)} relatórios sincronizados, arquivo existe: {existe}"
    except Exception as e:
        passou = False
        detalhe = ""
        return ResultadoTeste(
            nome="sync_relatorios",
            passou=False,
            tempo=time.time() - inicio,
            erro=str(e),
        )

    return ResultadoTeste(
        nome="sync_relatorios",
        passou=passou,
        tempo=time.time() - inicio,
        detalhe=detalhe,
    )


def _testar_frontmatter(vault_tmp: Path) -> ResultadoTeste:
    """Verifica que o frontmatter foi gerado corretamente."""
    inicio = time.time()

    relatorio = vault_tmp / "Pessoal" / "Financeiro" / "Relatorios" / "2026-04.md"

    if not relatorio.exists():
        return ResultadoTeste(
            nome="frontmatter",
            passou=False,
            tempo=time.time() - inicio,
            erro="Arquivo de relatório não encontrado",
        )

    conteudo = relatorio.read_text(encoding="utf-8")

    tem_frontmatter = conteudo.startswith("---")
    tem_tipo = "tipo:" in conteudo
    tem_mes = 'mes: "2026-04"' in conteudo
    tem_receita = "receita: 18700.0" in conteudo
    tem_tags = "tags:" in conteudo

    passou = tem_frontmatter and tem_tipo and tem_mes and tem_receita and tem_tags

    detalhes = []
    if not tem_frontmatter:
        detalhes.append("sem frontmatter")
    if not tem_tipo:
        detalhes.append("sem tipo")
    if not tem_mes:
        detalhes.append("sem mês")
    if not tem_receita:
        detalhes.append("sem receita")
    if not tem_tags:
        detalhes.append("sem tags")

    detalhe = "Frontmatter OK" if passou else f"Problemas: {', '.join(detalhes)}"

    return ResultadoTeste(
        nome="frontmatter",
        passou=passou,
        tempo=time.time() - inicio,
        detalhe=detalhe,
    )


def _testar_notas_metas(vault_tmp: Path) -> ResultadoTeste:
    """Testa criação de notas de metas no vault."""
    from src.obsidian.sync import criar_notas_metas

    inicio = time.time()

    metas_path = vault_tmp / "Pessoal" / "Financeiro" / "Metas"

    try:
        with (
            patch("src.obsidian.sync.METAS_PATH", metas_path),
            patch("src.obsidian.sync.METAS_YAML", FIXTURES_DIR / "metas_teste.yaml"),
        ):
            criadas = criar_notas_metas()

        passou = len(criadas) == 3
        detalhe = f"{len(criadas)} notas de metas criadas (esperado: 3)"
    except Exception as e:
        passou = False
        detalhe = ""
        return ResultadoTeste(
            nome="notas_metas",
            passou=False,
            tempo=time.time() - inicio,
            erro=str(e),
        )

    return ResultadoTeste(
        nome="notas_metas",
        passou=passou,
        tempo=time.time() - inicio,
        detalhe=detalhe,
    )


def _testar_idempotencia(vault_tmp: Path, output_tmp: Path) -> ResultadoTeste:
    """Testa que rodar sync 2x produz resultado idêntico."""
    from src.obsidian.sync import sincronizar_relatorios

    inicio = time.time()

    relatorios_path = vault_tmp / "Pessoal" / "Financeiro" / "Relatorios"
    destino = relatorios_path / "2026-04.md"

    try:
        with patch("src.obsidian.sync.RELATORIOS_PATH", relatorios_path):
            sincronizar_relatorios(output_tmp)
            conteudo_1 = destino.read_text(encoding="utf-8")

            sincronizar_relatorios(output_tmp)
            conteudo_2 = destino.read_text(encoding="utf-8")

        linhas_1 = [linha for linha in conteudo_1.split("\n") if not linha.startswith("created:")]
        linhas_2 = [linha for linha in conteudo_2.split("\n") if not linha.startswith("created:")]

        passou = linhas_1 == linhas_2
        detalhe = (
            "Idempotente (ignorando created)" if passou else "Conteúdo diverge entre execuções"
        )
    except Exception as e:
        passou = False
        detalhe = ""
        return ResultadoTeste(
            nome="idempotencia",
            passou=False,
            tempo=time.time() - inicio,
            erro=str(e),
        )

    return ResultadoTeste(
        nome="idempotencia",
        passou=passou,
        tempo=time.time() - inicio,
        detalhe=detalhe,
    )


def executar() -> ResultadoFase:
    """Executa todos os testes de integração Obsidian."""
    fase = ResultadoFase(nome="obsidian")
    inicio = time.time()

    with tempfile.TemporaryDirectory(prefix="gauntlet_obs_") as tmpdir:
        vault_tmp = Path(tmpdir) / "vault"
        output_tmp = Path(tmpdir) / "output"
        vault_tmp.mkdir()
        output_tmp.mkdir()

        fase.testes.append(_testar_sync_relatorios(vault_tmp, output_tmp))
        fase.testes.append(_testar_frontmatter(vault_tmp))
        fase.testes.append(_testar_notas_metas(vault_tmp))
        fase.testes.append(_testar_idempotencia(vault_tmp, output_tmp))

    fase.tempo_total = time.time() - inicio
    logger.info(
        "Fase obsidian: %d/%d testes OK em %.2fs",
        fase.ok,
        fase.total,
        fase.tempo_total,
    )
    return fase


# "A organização é a base de toda conquista duradoura." -- John Locke
