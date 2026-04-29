"""Testes do smoke aritmético (scripts/smoke_aritmetico.py).

Valida comportamento do script via subprocess em cenários sintéticos:
- XLSX saudável: exit 0, output "10/10 contratos OK".
- XLSX com despesa negativa: strict exit 1, output contém "VIOLAÇÃO".
- XLSX com resumo_mensal divergente do extrato: strict exit 1.
- XLSX ausente: exit 0 com aviso (graceful degradation).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parent.parent
SMOKE = RAIZ / "scripts" / "smoke_aritmetico.py"


def _xlsx_saudavel(caminho: Path) -> None:
    """Gera XLSX sintético que passa todos os 8 contratos."""
    extrato = pd.DataFrame(
        [
            {
                "data": "2026-01-10",
                "valor": 6000.00,
                "forma_pagamento": "Pix",
                "local": "G4F",
                "quem": "André",
                "categoria": None,
                "classificacao": None,
                "banco_origem": "Itaú",
                "tipo": "Receita",
                "mes_ref": "2026-01",
                "tag_irpf": None,
                "obs": None,
            },
            {
                "data": "2026-01-15",
                "valor": 500.00,
                "forma_pagamento": "Débito",
                "local": "Supermercado",
                "quem": "Casal",
                "categoria": "Alimentação",
                "classificacao": "Obrigatório",
                "banco_origem": "Nubank",
                "tipo": "Despesa",
                "mes_ref": "2026-01",
                "tag_irpf": None,
                "obs": None,
            },
            {
                "data": "2026-01-20",
                "valor": 100.00,
                "forma_pagamento": "Boleto",
                "local": "INSS",
                "quem": "André",
                "categoria": "Impostos",
                "classificacao": "Obrigatório",
                "banco_origem": "Itaú",
                "tipo": "Imposto",
                "mes_ref": "2026-01",
                "tag_irpf": None,
                "obs": None,
            },
            {
                "data": "2026-01-25",
                "valor": 300.00,
                "forma_pagamento": "Pix",
                "local": "Transferência para Vitória",
                "quem": "André",
                "categoria": None,
                "classificacao": None,
                "banco_origem": "Itaú",
                "tipo": "Transferência Interna",
                "mes_ref": "2026-01",
                "tag_irpf": None,
                "obs": None,
            },
            {
                "data": "2026-01-25",
                "valor": 300.00,
                "forma_pagamento": "Pix",
                "local": "Transferência recebida de André",
                "quem": "Vitória",
                "categoria": None,
                "classificacao": None,
                "banco_origem": "Nubank (PF)",
                "tipo": "Transferência Interna",
                "mes_ref": "2026-01",
                "tag_irpf": None,
                "obs": None,
            },
        ]
    )
    renda = pd.DataFrame(
        [
            {
                "mes_ref": "2026-01",
                "fonte": "G4F",
                "bruto": 6000.00,
                "inss": 660.00,
                "irrf": 500.00,
                "vr_va": 70.00,
                "liquido": 4840.00,
                "banco": None,
            }
        ]
    )
    with pd.ExcelWriter(caminho, engine="openpyxl") as w:
        extrato.to_excel(w, sheet_name="extrato", index=False)
        renda.to_excel(w, sheet_name="renda", index=False)


def _xlsx_com_despesa_negativa(caminho: Path) -> None:
    """Gera XLSX sintético com violação do contrato despesa_nao_negativa."""
    _xlsx_saudavel(caminho)
    # Substitui a linha de despesa por uma com valor negativo.
    df = pd.read_excel(caminho, sheet_name="extrato")
    renda = pd.read_excel(caminho, sheet_name="renda")
    mask = df["tipo"] == "Despesa"
    df.loc[mask, "valor"] = -500.00
    with pd.ExcelWriter(caminho, engine="openpyxl") as w:
        df.to_excel(w, sheet_name="extrato", index=False)
        renda.to_excel(w, sheet_name="renda", index=False)


def _xlsx_com_resumo_divergente(caminho: Path) -> None:
    """Gera XLSX sintético com resumo_mensal incoerente com o extrato.

    Cobre os contratos novos resumo_mensal_receita_coerente e
    resumo_mensal_despesa_coerente (ANTI-MIGUE-04).
    """
    _xlsx_saudavel(caminho)
    df = pd.read_excel(caminho, sheet_name="extrato")
    renda = pd.read_excel(caminho, sheet_name="renda")
    # Resumo mente: declara receita_total bem maior que a soma real.
    resumo = pd.DataFrame(
        [
            {
                "mes_ref": "2026-01",
                "receita_total": 99999.99,
                "despesa_total": 600.00,
                "saldo": 99399.99,
                "top_categoria": "Alimentação",
                "top_gasto": "Supermercado",
                "total_obrigatorio": 600.00,
                "total_superfluo": 0.0,
                "total_questionavel": 0.0,
            }
        ]
    )
    with pd.ExcelWriter(caminho, engine="openpyxl") as w:
        df.to_excel(w, sheet_name="extrato", index=False)
        renda.to_excel(w, sheet_name="renda", index=False)
        resumo.to_excel(w, sheet_name="resumo_mensal", index=False)


def _rodar_smoke(xlsx: Path | None, strict: bool = False) -> subprocess.CompletedProcess:
    cmd = [sys.executable, str(SMOKE)]
    if xlsx is not None:
        cmd += ["--xlsx", str(xlsx)]
    if strict:
        cmd.append("--strict")
    return subprocess.run(cmd, capture_output=True, text=True, cwd=RAIZ)


def test_xlsx_saudavel_retorna_exit_zero(tmp_path):
    xlsx = tmp_path / "saudavel.xlsx"
    _xlsx_saudavel(xlsx)

    resultado = _rodar_smoke(xlsx, strict=True)

    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
    assert "10/10 contratos OK" in resultado.stdout


def test_xlsx_com_despesa_negativa_falha_em_strict(tmp_path):
    xlsx = tmp_path / "violacao.xlsx"
    _xlsx_com_despesa_negativa(xlsx)

    resultado = _rodar_smoke(xlsx, strict=True)

    assert resultado.returncode == 1, resultado.stdout + resultado.stderr
    assert "VIOLAÇÃO" in resultado.stdout
    assert "despesa_nao_negativa" in resultado.stdout


def test_xlsx_com_resumo_divergente_falha_em_strict(tmp_path):
    xlsx = tmp_path / "resumo_divergente.xlsx"
    _xlsx_com_resumo_divergente(xlsx)

    resultado = _rodar_smoke(xlsx, strict=True)

    assert resultado.returncode == 1, resultado.stdout + resultado.stderr
    assert "VIOLAÇÃO" in resultado.stdout
    assert "resumo_mensal_receita_coerente" in resultado.stdout


def test_xlsx_ausente_retorna_zero_com_aviso(tmp_path):
    xlsx = tmp_path / "nao_existe.xlsx"

    resultado = _rodar_smoke(xlsx, strict=True)

    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
    assert "não encontrado" in resultado.stdout


def test_smoke_real_responde_em_modo_observador():
    """Smoke sobre XLSX real do projeto: modo observador sempre retorna 0."""
    xlsx_real = RAIZ / "data" / "output" / "ouroboros_2026.xlsx"
    if not xlsx_real.exists():
        pytest.skip("XLSX real não disponível neste ambiente")

    resultado = _rodar_smoke(None, strict=False)

    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
    assert "[SMOKE-ARIT]" in resultado.stdout


# "A prova pequena é a que impede o desastre grande." -- Epicteto
