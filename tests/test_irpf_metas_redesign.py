"""Testes UX-RD-14 — IRPF + Metas reescritos.

Cobre os 8 contratos de aceite da spec:

1. 8 categorias IRPF presentes via ``CATEGORIAS_IRPF``.
2. Totalizadores por categoria batem com soma de ``valor`` no dataset.
3. ``gerar_pacote(ano, dados, diretorio_base)`` produz 4 artefatos
   (relatorio.pdf, dados.xlsx, dados.json, originais/).
4. ``gerar_pacote`` é idempotente (chamar 2x não duplica).
5. Donuts financeiros: 3+ figuras Plotly válidas.
6. Gauges operacionais: 2+ figuras Plotly válidas.
7. Cor de atingimento respeita threshold (verde >= 100%, amarelo >= 50%,
   vermelho < 50%).
8. Page-header HTML expõe ``sprint-tag UX-RD-14`` e pill com ano-base.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import pytest

from src.dashboard.paginas import irpf as irpf_pagina
from src.dashboard.paginas import metas as metas_pagina
from src.dashboard.tema import CORES
from src.exports.pacote_irpf import (
    CATEGORIAS_IRPF,
    compilar_eventos,
    compilar_totais,
    gerar_pacote,
)

# ---------------------------------------------------------------------------
# Fixtures comuns
# ---------------------------------------------------------------------------


@pytest.fixture
def extrato_irpf() -> pd.DataFrame:
    """DataFrame mínimo com tag_irpf populada para os testes."""
    return pd.DataFrame(
        [
            {
                "data": "2026-01-15",
                "valor": 5000.0,
                "tag_irpf": "rendimento_tributavel",
                "banco_origem": "Itau",
                "cnpj_cpf": "12.345.678/0001-90",
                "mes_ref": "2026-01",
                "local": "G4F SOLUCOES",
                "_descricao_original": "G4F SOLUCOES PAGTO SALARIO",
            },
            {
                "data": "2026-02-15",
                "valor": 5000.0,
                "tag_irpf": "rendimento_tributavel",
                "banco_origem": "Itau",
                "cnpj_cpf": "12.345.678/0001-90",
                "mes_ref": "2026-02",
                "local": "G4F SOLUCOES",
                "_descricao_original": "G4F SOLUCOES",
            },
            {
                "data": "2026-03-10",
                "valor": -150.0,
                "tag_irpf": "dedutivel_medico",
                "banco_origem": "Nubank",
                "cnpj_cpf": "98.765.432/0001-10",
                "mes_ref": "2026-03",
                "local": "CLINICA SANTA MARIA",
                "_descricao_original": "CLINICA SANTA MARIA",
            },
            {
                "data": "2026-04-20",
                "valor": -80.0,
                "tag_irpf": "inss_retido",
                "banco_origem": "Itau",
                "cnpj_cpf": None,
                "mes_ref": "2026-04",
                "local": "INSS",
                "_descricao_original": "INSS RETIDO",
            },
            {
                "data": "2025-05-15",
                "valor": 3000.0,
                "tag_irpf": "rendimento_tributavel",
                "banco_origem": "Itau",
                "cnpj_cpf": None,
                "mes_ref": "2025-05",
                "local": "INFOBASE",
                "_descricao_original": "INFOBASE",
            },
        ]
    )


@pytest.fixture
def metas_mock() -> list[dict]:
    """Lista mínima de metas para testar donuts/gauges."""
    return [
        {
            "nome": "Reserva de emergência",
            "tipo": "valor",
            "valor_alvo": 10000.0,
            "valor_atual": 10000.0,
            "prazo": "2026-12",
            "prioridade": 1,
        },
        {
            "nome": "Viagem Japão",
            "tipo": "valor",
            "valor_alvo": 30000.0,
            "valor_atual": 15000.0,
            "prazo": "2027-03",
            "prioridade": 2,
        },
        {
            "nome": "Entrada apartamento",
            "tipo": "valor",
            "valor_alvo": 100000.0,
            "valor_atual": 20000.0,
            "prazo": "2028-06",
            "prioridade": 3,
        },
    ]


# ---------------------------------------------------------------------------
# Teste 1 -- 8 categorias canônicas IRPF
# ---------------------------------------------------------------------------


def test_irpf_oito_categorias_canonicas() -> None:
    """As 8 tags canônicas estão expostas em ``CATEGORIAS_IRPF`` e na meta visual."""
    assert len(CATEGORIAS_IRPF) == 8
    esperadas = {
        "rendimento_tributavel",
        "rendimento_isento",
        "dedutivel_medico",
        "dedutivel_educacional",
        "previdencia_privada",
        "imposto_pago",
        "inss_retido",
        "doacao_dedutivel",
    }
    assert set(CATEGORIAS_IRPF) == esperadas
    # Cada categoria tem metadado visual associado.
    for cat in CATEGORIAS_IRPF:
        assert cat in irpf_pagina.META_CATEGORIAS
        meta = irpf_pagina.META_CATEGORIAS[cat]
        assert "cor" in meta and meta["cor"]
        assert "descricao" in meta and meta["descricao"]


# ---------------------------------------------------------------------------
# Teste 2 -- totalizadores corretos
# ---------------------------------------------------------------------------


def test_irpf_totalizadores_batem_com_dataset(extrato_irpf: pd.DataFrame) -> None:
    """``compilar_totais`` reproduz a soma absoluta por categoria."""
    df_2026 = extrato_irpf[extrato_irpf["mes_ref"].str.startswith("2026")]
    eventos = compilar_eventos(df_2026)
    totais = compilar_totais(eventos)

    # Esperado em 2026: 2x R$5000 tributável; R$150 médico; R$80 INSS.
    assert totais["rendimento_tributavel"]["valor"] == pytest.approx(10000.0)
    assert totais["rendimento_tributavel"]["count"] == 2
    assert totais["dedutivel_medico"]["valor"] == pytest.approx(150.0)
    assert totais["dedutivel_medico"]["count"] == 1
    assert totais["inss_retido"]["valor"] == pytest.approx(80.0)
    assert totais["inss_retido"]["count"] == 1
    # Categorias não presentes no dataset ainda aparecem zeradas.
    assert totais["dedutivel_educacional"]["valor"] == 0.0
    assert totais["dedutivel_educacional"]["count"] == 0


# ---------------------------------------------------------------------------
# Teste 3 -- gerar_pacote produz 4 artefatos
# ---------------------------------------------------------------------------


def test_gerar_pacote_produz_quatro_artefatos(extrato_irpf: pd.DataFrame, tmp_path: Path) -> None:
    """Pacote contém relatorio.pdf, dados.xlsx, dados.json e originais/."""
    diretorio = gerar_pacote(2026, dados={"extrato": extrato_irpf}, diretorio_base=tmp_path)
    assert diretorio.exists()
    assert diretorio.name == "irpf_2026"
    assert (diretorio / "relatorio.pdf").exists()
    assert (diretorio / "dados.xlsx").exists()
    assert (diretorio / "dados.json").exists()
    assert (diretorio / "originais").exists()
    assert (diretorio / "originais").is_dir()
    # JSON tem schema canônico.
    payload = json.loads((diretorio / "dados.json").read_text(encoding="utf-8"))
    assert payload["ano_calendario"] == 2026
    assert "totais_por_categoria" in payload
    assert "eventos" in payload
    assert isinstance(payload["eventos"], list)
    # Eventos do ano filtrado: 4 (do fixture, ano 2026).
    assert len(payload["eventos"]) == 4


# ---------------------------------------------------------------------------
# Teste 4 -- gerar_pacote é idempotente
# ---------------------------------------------------------------------------


def test_gerar_pacote_idempotente(extrato_irpf: pd.DataFrame, tmp_path: Path) -> None:
    """Chamar gerar_pacote duas vezes mantém apenas 4 artefatos (sobrescreve)."""
    gerar_pacote(2026, dados={"extrato": extrato_irpf}, diretorio_base=tmp_path)
    diretorio = gerar_pacote(2026, dados={"extrato": extrato_irpf}, diretorio_base=tmp_path)
    # Diretório raiz tem exatamente 3 arquivos + 1 subdiretório (originais).
    arquivos = sorted(p.name for p in diretorio.iterdir())
    assert arquivos == ["dados.json", "dados.xlsx", "originais", "relatorio.pdf"]


# ---------------------------------------------------------------------------
# Teste 5 -- donuts financeiros (3+) renderizam
# ---------------------------------------------------------------------------


def test_metas_donuts_financeiros_renderizam(metas_mock: list[dict]) -> None:
    """Cada meta monetária produz um Plotly Figure com pelo menos 1 trace Pie."""
    figuras: list[go.Figure] = [metas_pagina._donut_meta(m) for m in metas_mock]
    assert len(figuras) >= 3
    for fig in figuras:
        assert isinstance(fig, go.Figure)
        # 1 trace do tipo Pie.
        traces_pie = [tr for tr in fig.data if tr.type == "pie"]
        assert len(traces_pie) == 1
        # Anotação central com percentual.
        assert fig.layout.annotations
        texto = str(fig.layout.annotations[0].text)
        assert "%" in texto


# ---------------------------------------------------------------------------
# Teste 6 -- gauges operacionais (2+) renderizam
# ---------------------------------------------------------------------------


def test_metas_gauges_operacionais_renderizam(extrato_irpf: pd.DataFrame) -> None:
    """``_calcular_metricas_operacionais`` produz pelo menos 2 métricas
    e cada uma vira um Plotly Indicator gauge."""
    metricas = metas_pagina._calcular_metricas_operacionais({"extrato": extrato_irpf})
    assert len(metricas) >= 2
    for metrica in metricas:
        fig = metas_pagina._gauge_metrica(metrica)
        assert isinstance(fig, go.Figure)
        traces_indicator = [tr for tr in fig.data if tr.type == "indicator"]
        assert len(traces_indicator) == 1
        # Modo do gauge inclui "gauge" para confirmar ser um gauge real.
        assert "gauge" in str(traces_indicator[0].mode)


# ---------------------------------------------------------------------------
# Teste 7 -- cor de atingimento por threshold
# ---------------------------------------------------------------------------


def test_cor_atingimento_thresholds() -> None:
    """Verde >= 100%, amarelo entre 50% e 100%, vermelho abaixo de 50%."""
    assert metas_pagina._cor_atingimento(1.0) == CORES["positivo"]
    assert metas_pagina._cor_atingimento(1.5) == CORES["positivo"]
    assert metas_pagina._cor_atingimento(0.75) == CORES["alerta"]
    assert metas_pagina._cor_atingimento(0.5) == CORES["alerta"]
    assert metas_pagina._cor_atingimento(0.49) == CORES["negativo"]
    assert metas_pagina._cor_atingimento(0.0) == CORES["negativo"]


# ---------------------------------------------------------------------------
# Teste 8 -- page-header IRPF expõe sprint-tag UX-RD-14 e pill ano-base
# ---------------------------------------------------------------------------


def test_irpf_page_header_html_canonico() -> None:
    """Header HTML inclui sprint-tag UX-RD-14 e pill com ano-base."""
    html = irpf_pagina._page_header_html("2026", 4, 3, 5230.0)
    assert "page-header" in html
    assert "page-title" in html
    assert "IRPF" in html
    assert 'class="sprint-tag"' in html
    assert "UX-RD-14" in html
    assert "Ano-base 2026" in html
    assert "3/8 categorias" in html


# ---------------------------------------------------------------------------
# Teste extra (bônus) -- compilar_eventos preserva CNPJ/CPF
# ---------------------------------------------------------------------------


def test_compilar_eventos_preserva_cnpj_cpf(extrato_irpf: pd.DataFrame) -> None:
    """Eventos com CNPJ válido aparecem com cnpj_cpf no payload."""
    df = extrato_irpf[extrato_irpf["mes_ref"].str.startswith("2026")]
    eventos = compilar_eventos(df)
    com_cnpj = [ev for ev in eventos if ev.get("cnpj_cpf")]
    sem_cnpj = [ev for ev in eventos if not ev.get("cnpj_cpf")]
    assert len(com_cnpj) == 3
    assert len(sem_cnpj) == 1
    # CNPJ é literal (sem mascaramento aqui -- mascaramento é só em log).
    assert all("/" in str(ev["cnpj_cpf"]) for ev in com_cnpj)


# "O que não pode ser medido não pode ser melhorado." -- Peter Drucker
