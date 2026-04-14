"""Fase 5 do gauntlet: testa geração de relatórios mensais."""

import time
from datetime import date

from scripts.gauntlet.config import ResultadoFase, ResultadoTeste
from src.utils.logger import configurar_logger

logger = configurar_logger("gauntlet.relatorio")


def _gerar_transacoes_sinteticas() -> list[dict]:
    """Gera transações para teste de relatório."""
    transacoes: list[dict] = []
    for i in range(5):
        transacoes.append({
            "data": date(2026, 4, i + 1),
            "valor": 1000.0 * (i + 1),
            "forma_pagamento": "Pix",
            "local": f"LOJA {i + 1}",
            "quem": "André",
            "categoria": "Delivery" if i == 0 else "Mercado",
            "classificacao": "Questionável" if i == 0 else "Obrigatório",
            "banco_origem": "Nubank",
            "tipo": "Despesa",
            "mes_ref": "2026-04",
            "tag_irpf": None,
            "obs": "",
            "_descricao_original": f"LOJA {i + 1}",
        })

    transacoes.append({
        "data": date(2026, 4, 1),
        "valor": 15000.0,
        "forma_pagamento": "Transferência",
        "local": "SALARIO G4F",
        "quem": "André",
        "categoria": "Salário",
        "classificacao": "N/A",
        "banco_origem": "Itaú",
        "tipo": "Receita",
        "mes_ref": "2026-04",
        "tag_irpf": None,
        "obs": "",
        "_descricao_original": "PAGTO SALARIO G4F",
    })

    return transacoes


def _testar_geracao() -> ResultadoTeste:
    """Testa se o relatório é gerado sem erros."""
    from src.load.relatorio import gerar_relatorio_mes

    inicio = time.time()
    transacoes = _gerar_transacoes_sinteticas()

    try:
        conteudo = gerar_relatorio_mes(transacoes, "2026-04")
        passou = isinstance(conteudo, str) and len(conteudo) > 100
        detalhe = f"Relatório gerado: {len(conteudo)} caracteres"
        erro = ""
    except Exception as e:
        passou = False
        detalhe = ""
        erro = str(e)

    return ResultadoTeste(
        nome="geracao_relatorio",
        passou=passou,
        tempo=time.time() - inicio,
        detalhe=detalhe,
        erro=erro,
    )


def _testar_secoes_obrigatorias() -> ResultadoTeste:
    """Verifica que seções obrigatórias estão presentes."""
    from src.load.relatorio import gerar_relatorio_mes

    inicio = time.time()
    transacoes = _gerar_transacoes_sinteticas()

    secoes_esperadas = [
        "# Relatório Financeiro",
        "## Resumo",
        "Receita:",
        "Despesa:",
        "Saldo:",
    ]

    try:
        conteudo = gerar_relatorio_mes(transacoes, "2026-04")

        faltando = [s for s in secoes_esperadas if s not in conteudo]
        passou = len(faltando) == 0

        detalhe = (
            f"Todas as {len(secoes_esperadas)} seções presentes"
            if passou
            else f"Faltando: {', '.join(faltando)}"
        )
        erro = ""
    except Exception as e:
        passou = False
        detalhe = ""
        erro = str(e)

    return ResultadoTeste(
        nome="secoes_obrigatorias",
        passou=passou,
        tempo=time.time() - inicio,
        detalhe=detalhe,
        erro=erro,
    )


def executar() -> ResultadoFase:
    """Executa todos os testes de relatório."""
    fase = ResultadoFase(nome="relatorio")
    inicio = time.time()

    fase.testes.append(_testar_geracao())
    fase.testes.append(_testar_secoes_obrigatorias())

    fase.tempo_total = time.time() - inicio
    logger.info(
        "Fase relatório: %d/%d testes OK em %.2fs",
        fase.ok, fase.total, fase.tempo_total,
    )
    return fase


# "O relatório não é o fim, é o começo da ação." -- Peter Drucker
