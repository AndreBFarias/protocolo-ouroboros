"""Testes da seção diagnóstica de relatórios (Sprint 21 / B1 2026-04-23)."""

from __future__ import annotations

from src.load.relatorio import (
    _mes_anterior_str,
    _meses_anteriores,
    gerar_secao_diagnostica,
)


def test_mes_anterior_dentro_do_ano() -> None:
    assert _mes_anterior_str("2026-04") == "2026-03"


def test_mes_anterior_cruza_ano() -> None:
    assert _mes_anterior_str("2026-01") == "2025-12"


def test_meses_anteriores_tres() -> None:
    assert _meses_anteriores("2026-04", 3) == ["2026-01", "2026-02", "2026-03"]


def test_diagnostico_comparativo_vs_mes_anterior() -> None:
    transacoes = [
        # Janeiro: R$ 100
        {"mes_ref": "2026-01", "tipo": "Despesa", "valor": 100.0, "categoria": "Alimentação"},
        # Fevereiro: R$ 100
        {"mes_ref": "2026-02", "tipo": "Despesa", "valor": 100.0, "categoria": "Alimentação"},
        # Março: R$ 100
        {"mes_ref": "2026-03", "tipo": "Despesa", "valor": 100.0, "categoria": "Alimentação"},
        # Abril: R$ 200 (+100% vs média, +100% vs março)
        {"mes_ref": "2026-04", "tipo": "Despesa", "valor": 200.0, "categoria": "Alimentação"},
    ]
    linhas = gerar_secao_diagnostica(transacoes, "2026-04")
    texto = "\n".join(linhas)
    assert "Diagnóstico comparativo" in texto
    assert "+100.0%" in texto


def test_alerta_categoria_nova_com_valor_alto() -> None:
    transacoes = [
        {"mes_ref": "2026-01", "tipo": "Despesa", "valor": 500.0, "categoria": "Alimentação"},
        {"mes_ref": "2026-02", "tipo": "Despesa", "valor": 500.0, "categoria": "Alimentação"},
        {"mes_ref": "2026-03", "tipo": "Despesa", "valor": 500.0, "categoria": "Alimentação"},
        # Abril: Alimentação estável + Farmácia nova R$ 300
        {"mes_ref": "2026-04", "tipo": "Despesa", "valor": 500.0, "categoria": "Alimentação"},
        {"mes_ref": "2026-04", "tipo": "Despesa", "valor": 300.0, "categoria": "Farmácia"},
    ]
    linhas = gerar_secao_diagnostica(transacoes, "2026-04")
    texto = "\n".join(linhas)
    assert "Alertas" in texto
    assert "Farmácia" in texto
    assert "primeira vez" in texto


def test_alerta_categoria_acima_150pct_da_media() -> None:
    transacoes = [
        {"mes_ref": "2026-01", "tipo": "Despesa", "valor": 100.0, "categoria": "Lazer"},
        {"mes_ref": "2026-02", "tipo": "Despesa", "valor": 100.0, "categoria": "Lazer"},
        {"mes_ref": "2026-03", "tipo": "Despesa", "valor": 100.0, "categoria": "Lazer"},
        # Abril: R$ 300 (200% acima da média)
        {"mes_ref": "2026-04", "tipo": "Despesa", "valor": 300.0, "categoria": "Lazer"},
    ]
    linhas = gerar_secao_diagnostica(transacoes, "2026-04")
    texto = "\n".join(linhas)
    assert "acima da média" in texto


def test_sem_historico_retorna_vazio() -> None:
    linhas = gerar_secao_diagnostica([], "2026-04")
    assert linhas == []


def test_ignora_transferencia_interna() -> None:
    transacoes = [
        {
            "mes_ref": "2026-01",
            "tipo": "Transferência Interna",
            "valor": 1000.0,
            "categoria": "Transf",
        },
        {
            "mes_ref": "2026-04",
            "tipo": "Despesa",
            "valor": 50.0,
            "categoria": "Alimentação",
        },
    ]
    linhas = gerar_secao_diagnostica(transacoes, "2026-04")
    texto = "\n".join(linhas)
    # Transferência NÃO deve aparecer como categoria com variação
    assert "Transf" not in texto or "Transferência Interna" not in texto
