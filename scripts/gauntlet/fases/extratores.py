"""Fase 1 do gauntlet: testa extratores com fixtures sintéticas."""

import shutil
import tempfile
import time
from pathlib import Path

from scripts.gauntlet.config import FIXTURES_DIR, ResultadoFase, ResultadoTeste
from src.utils.logger import configurar_logger

logger = configurar_logger("gauntlet.extratores")


def _testar_nubank_cartao(tmpdir: Path) -> ResultadoTeste:
    """Testa extrator Nubank cartão CSV (date,title,amount)."""
    from src.extractors.nubank_cartao import ExtratorNubankCartao

    inicio = time.time()
    fixture = FIXTURES_DIR / "nubank_cartao.csv"

    destino = tmpdir / "andre" / "nubank_cartao"
    destino.mkdir(parents=True, exist_ok=True)
    arquivo = destino / "nubank_cartao_2026-04.csv"
    shutil.copy(fixture, arquivo)

    try:
        extrator = ExtratorNubankCartao(arquivo)
        transacoes = extrator.extrair()
        n = len(transacoes)
        esperado = 10
        passou = n == esperado

        detalhe = f"{n} transações extraídas (esperado: {esperado})"
        if passou:
            bancos_ok = all(t.banco_origem == "Nubank" for t in transacoes)
            if not bancos_ok:
                origens = {t.banco_origem for t in transacoes}
                passou = False
                detalhe += f" | banco_origem inconsistente: {origens}"
        erro = ""
    except Exception as e:
        passou = False
        detalhe = ""
        erro = str(e)

    return ResultadoTeste(
        nome="nubank_cartao",
        passou=passou,
        tempo=time.time() - inicio,
        detalhe=detalhe,
        erro=erro,
    )


def _testar_nubank_cc(tmpdir: Path) -> ResultadoTeste:
    """Testa extrator Nubank CC CSV (Data,Valor,Identificador,Descrição)."""
    from src.extractors.nubank_cc import ExtratorNubankCC

    inicio = time.time()
    fixture = FIXTURES_DIR / "nubank_cc.csv"

    destino = tmpdir / "andre" / "nubank_cc"
    destino.mkdir(parents=True, exist_ok=True)
    arquivo = destino / "nubank_cc_2026-04.csv"
    shutil.copy(fixture, arquivo)

    try:
        extrator = ExtratorNubankCC(arquivo)
        transacoes = extrator.extrair()
        n = len(transacoes)
        esperado = 8
        passou = n == esperado

        detalhe = f"{n} transações extraídas (esperado: {esperado})"
        if passou:
            ids = [t.identificador for t in transacoes if t.identificador]
            ids_unicos = len(set(ids)) == len(ids)
            if not ids_unicos:
                passou = False
                detalhe += " | identificadores duplicados"
        erro = ""
    except Exception as e:
        passou = False
        detalhe = ""
        erro = str(e)

    return ResultadoTeste(
        nome="nubank_cc",
        passou=passou,
        tempo=time.time() - inicio,
        detalhe=detalhe,
        erro=erro,
    )


def executar() -> ResultadoFase:
    """Executa testes de todos os extratores com fixtures disponíveis."""
    fase = ResultadoFase(nome="extratores")
    inicio = time.time()

    with tempfile.TemporaryDirectory(prefix="gauntlet_ext_") as tmpdir:
        tmppath = Path(tmpdir)

        fase.testes.append(_testar_nubank_cartao(tmppath))
        fase.testes.append(_testar_nubank_cc(tmppath))

    fase.tempo_total = time.time() - inicio
    logger.info(
        "Fase extratores: %d/%d testes OK em %.2fs",
        fase.ok, fase.total, fase.tempo_total,
    )
    return fase


# "A experiência é simplesmente o nome que damos aos nossos erros." -- Oscar Wilde
