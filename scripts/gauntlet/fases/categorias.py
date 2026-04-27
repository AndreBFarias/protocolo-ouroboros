"""Fase 2 do gauntlet: testa categorização automática."""

import time

from scripts.gauntlet.config import (
    CATEGORIAS_ESPERADAS,
    CLASSIFICACOES_ESPERADAS,
    FIXTURES_DIR,
    ResultadoFase,
    ResultadoTeste,
)
from src.transform.categorizer import Categorizer
from src.utils.logger import configurar_logger

logger = configurar_logger("gauntlet.categorias")


def executar() -> ResultadoFase:
    """Testa regras de categorização com descrições conhecidas."""
    fase = ResultadoFase(nome="categorias")
    inicio = time.time()

    categorizer = Categorizer(
        caminho_regras=FIXTURES_DIR / "categorias_teste.yaml",
        caminho_overrides=None,
    )

    for descricao, categoria_esperada in CATEGORIAS_ESPERADAS.items():
        t_inicio = time.time()
        transacao = {
            "_descricao_original": descricao,
            "local": descricao,
            "valor": 100.0,
            "categoria": None,
            "classificacao": None,
            "tipo": None,
            "tag_irpf": None,
        }

        resultado = categorizer.categorizar(transacao)
        categoria_obtida = resultado.get("categoria")
        t_fim = time.time()

        passou = categoria_obtida == categoria_esperada
        detalhe = f"{descricao} -> {categoria_obtida} (esperado: {categoria_esperada})"

        if not passou:
            logger.warning("Categorização errada: %s", detalhe)

        fase.testes.append(
            ResultadoTeste(
                nome=f"cat.{descricao.lower().replace(' ', '_')[:30]}",
                passou=passou,
                tempo=t_fim - t_inicio,
                detalhe=detalhe,
            )
        )

    for descricao, classificacao_esperada in CLASSIFICACOES_ESPERADAS.items():
        t_inicio = time.time()
        transacao = {
            "_descricao_original": descricao,
            "local": descricao,
            "valor": 100.0,
            "categoria": None,
            "classificacao": None,
            "tipo": None,
            "tag_irpf": None,
        }

        resultado = categorizer.categorizar(transacao)
        classificacao_obtida = resultado.get("classificacao")
        t_fim = time.time()

        passou = classificacao_obtida == classificacao_esperada
        detalhe = (
            f"{descricao} -> classificação: {classificacao_obtida} "
            f"(esperado: {classificacao_esperada})"
        )

        fase.testes.append(
            ResultadoTeste(
                nome=f"cls.{descricao.lower().replace(' ', '_')[:30]}",
                passou=passou,
                tempo=t_fim - t_inicio,
                detalhe=detalhe,
            )
        )

    t_inicio = time.time()
    transacao_desconhecida = {
        "_descricao_original": "XYZLOJA999INVENTADA",
        "local": "XYZLOJA999INVENTADA",
        "valor": 50.0,
        "categoria": None,
        "classificacao": None,
        "tipo": None,
        "tag_irpf": None,
    }
    resultado = categorizer.categorizar(transacao_desconhecida)
    t_fim = time.time()

    passou_fallback = resultado.get("categoria") == "Outros"
    fase.testes.append(
        ResultadoTeste(
            nome="fallback_outros",
            passou=passou_fallback,
            tempo=t_fim - t_inicio,
            detalhe=f"Desconhecido -> {resultado.get('categoria')} (esperado: Outros)",
        )
    )

    fase.tempo_total = time.time() - inicio
    logger.info(
        "Fase categorias: %d/%d testes OK em %.2fs",
        fase.ok,
        fase.total,
        fase.tempo_total,
    )
    return fase


# "Quem não lê não pensa, e quem não pensa será para sempre um servo." -- Paulo Freire
