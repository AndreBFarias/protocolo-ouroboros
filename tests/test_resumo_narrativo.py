"""Testes do resumo narrativo (Sprint 33 / B2 2026-04-23)."""

from __future__ import annotations

from src.load.relatorio import gerar_resumo_narrativo


def test_sem_transacoes_retorna_vazio() -> None:
    assert gerar_resumo_narrativo([], "2026-04") == []


def test_narrativa_menciona_volume_e_totais() -> None:
    transacoes = [
        {
            "mes_ref": "2026-04",
            "tipo": "Despesa",
            "valor": 500.0,
            "categoria": "Alimentação",
            "classificacao": "Obrigatório",
        },
        {
            "mes_ref": "2026-04",
            "tipo": "Receita",
            "valor": 5000.0,
            "categoria": "Salário",
        },
    ]
    linhas = gerar_resumo_narrativo(transacoes, "2026-04")
    texto = "\n".join(linhas)
    assert "Resumo narrativo" in texto
    assert "2 transações" in texto
    assert "R$ 500,00" in texto or "500,00" in texto


def test_narrativa_compara_com_mes_anterior_estavel() -> None:
    transacoes = [
        {"mes_ref": "2026-03", "tipo": "Despesa", "valor": 1000.0, "categoria": "X"},
        {"mes_ref": "2026-04", "tipo": "Despesa", "valor": 1050.0, "categoria": "X"},
    ]
    linhas = gerar_resumo_narrativo(transacoes, "2026-04")
    texto = "\n".join(linhas)
    assert "praticamente estável" in texto.lower() or "seguiu o padrão" in texto.lower()


def test_narrativa_menciona_top3_categorias() -> None:
    transacoes = [
        {"mes_ref": "2026-04", "tipo": "Despesa", "valor": 1000.0, "categoria": "Aluguel"},
        {"mes_ref": "2026-04", "tipo": "Despesa", "valor": 500.0, "categoria": "Alimentação"},
        {"mes_ref": "2026-04", "tipo": "Despesa", "valor": 200.0, "categoria": "Transporte"},
    ]
    linhas = gerar_resumo_narrativo(transacoes, "2026-04")
    texto = "\n".join(linhas)
    assert "Aluguel" in texto
    assert "Alimentação" in texto
    assert "Transporte" in texto


def test_narrativa_alerta_superfluo_alto() -> None:
    transacoes = [
        {
            "mes_ref": "2026-04",
            "tipo": "Despesa",
            "valor": 300.0,
            "categoria": "Delivery",
            "classificacao": "Supérfluo",
        },
        {
            "mes_ref": "2026-04",
            "tipo": "Despesa",
            "valor": 100.0,
            "categoria": "Alimentação",
            "classificacao": "Obrigatório",
        },
    ]
    linhas = gerar_resumo_narrativo(transacoes, "2026-04")
    texto = "\n".join(linhas)
    assert "Atenção ao supérfluo" in texto or "supérfluo" in texto.lower()


def test_narrativa_saldo_positivo() -> None:
    transacoes = [
        {"mes_ref": "2026-04", "tipo": "Receita", "valor": 5000.0, "categoria": "Salário"},
        {"mes_ref": "2026-04", "tipo": "Despesa", "valor": 3000.0, "categoria": "Aluguel"},
    ]
    linhas = gerar_resumo_narrativo(transacoes, "2026-04")
    texto = "\n".join(linhas)
    assert "Saldo positivo" in texto
