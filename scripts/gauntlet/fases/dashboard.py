"""Fase 8 do gauntlet: testa que módulos do dashboard importam sem erro."""

import time

from scripts.gauntlet.config import ResultadoFase, ResultadoTeste
from src.utils.logger import configurar_logger

logger = configurar_logger("gauntlet.dashboard")

MODULOS_PAGINAS: list[str] = [
    "src.dashboard.paginas.visao_geral",
    "src.dashboard.paginas.categorias",
    "src.dashboard.paginas.extrato",
    "src.dashboard.paginas.contas",
    "src.dashboard.paginas.projecoes",
    "src.dashboard.paginas.metas",
]


def _testar_import(modulo: str) -> ResultadoTeste:
    """Testa que um módulo pode ser importado sem erro."""
    import importlib

    inicio = time.time()

    try:
        importlib.import_module(modulo)
        passou = True
        detalhe = f"{modulo} importado com sucesso"
        erro = ""
    except Exception as e:
        passou = False
        detalhe = ""
        erro = f"{type(e).__name__}: {e}"

    return ResultadoTeste(
        nome=f"import.{modulo.split('.')[-1]}",
        passou=passou,
        tempo=time.time() - inicio,
        detalhe=detalhe,
        erro=erro,
    )


def _testar_app_import() -> ResultadoTeste:
    """Testa que o app.py principal pode ser importado."""
    import importlib

    inicio = time.time()

    try:
        importlib.import_module("src.dashboard.app")
        passou = True
        detalhe = "src.dashboard.app importado com sucesso"
        erro = ""
    except Exception as e:
        passou = False
        detalhe = ""
        erro = f"{type(e).__name__}: {e}"

    return ResultadoTeste(
        nome="import.app",
        passou=passou,
        tempo=time.time() - inicio,
        detalhe=detalhe,
        erro=erro,
    )


def _testar_dados_import() -> ResultadoTeste:
    """Testa que o módulo de dados pode ser importado."""
    import importlib

    inicio = time.time()

    try:
        mod = importlib.import_module("src.dashboard.dados")
        tem_formatar = hasattr(mod, "formatar_moeda")
        passou = tem_formatar
        detalhe = f"dados importado, formatar_moeda: {tem_formatar}"
        erro = ""
    except Exception as e:
        passou = False
        detalhe = ""
        erro = f"{type(e).__name__}: {e}"

    return ResultadoTeste(
        nome="import.dados",
        passou=passou,
        tempo=time.time() - inicio,
        detalhe=detalhe,
        erro=erro,
    )


def executar() -> ResultadoFase:
    """Executa testes de import do dashboard."""
    fase = ResultadoFase(nome="dashboard")
    inicio = time.time()

    fase.testes.append(_testar_app_import())
    fase.testes.append(_testar_dados_import())

    for modulo in MODULOS_PAGINAS:
        fase.testes.append(_testar_import(modulo))

    fase.tempo_total = time.time() - inicio
    logger.info(
        "Fase dashboard: %d/%d testes OK em %.2fs",
        fase.ok,
        fase.total,
        fase.tempo_total,
    )
    return fase


# "A interface é o produto." -- Jef Raskin
