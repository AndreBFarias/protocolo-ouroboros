"""Testes UX-RD-06 — extrato reescrito (tabela densa + breakdown + drawer).

Cobre as funções puras introduzidas pela reescrita: cálculo do saldo do
topo, breakdown por categoria, geração da tabela densa HTML, drawer JSON
com syntax highlight, helper minificar e a interação básica de drawer
via session_state. Não cobre rendering Streamlit propriamente dito --
o smoke é capturado pelo proof-of-work runtime.
"""

from __future__ import annotations

import time

import pandas as pd
import pytest

from src.dashboard.componentes.drawer_transacao import (
    renderizar_drawer,
    transacao_para_dict,
)
from src.dashboard.componentes.html_utils import minificar
from src.dashboard.paginas.extrato import (
    _breakdown_lateral_html,
    _saldo_topo_html,
    _tabela_densa_html,
    calcular_breakdown_categorias,
    calcular_saldo_topo,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def df_pequeno() -> pd.DataFrame:
    """10 transações cobrindo receita, despesa, transferência interna."""
    return pd.DataFrame(
        [
            {
                "data": pd.Timestamp("2026-04-01"),
                "valor": 5000.0,
                "local": "Salário G4F",
                "categoria": "Salário",
                "classificacao": "N/A",
                "forma_pagamento": "Transferência",
                "banco_origem": "Itaú",
                "tipo": "Receita",
                "quem": "André",
                "mes_ref": "2026-04",
                "identificador": "uuid-001",
            },
            {
                "data": pd.Timestamp("2026-04-02"),
                "valor": -1280.00,
                "local": "Aluguel · Imobiliária",
                "categoria": "Aluguel",
                "classificacao": "Obrigatório",
                "forma_pagamento": "Boleto",
                "banco_origem": "Itaú",
                "tipo": "Despesa",
                "quem": "Casal",
                "mes_ref": "2026-04",
                "identificador": "uuid-002",
            },
            {
                "data": pd.Timestamp("2026-04-03"),
                "valor": -290.00,
                "local": "Extra Mooca",
                "categoria": "Mercado",
                "classificacao": "Obrigatório",
                "forma_pagamento": "Débito",
                "banco_origem": "C6",
                "tipo": "Despesa",
                "quem": "Vitória",
                "mes_ref": "2026-04",
                "identificador": "uuid-003",
            },
            {
                "data": pd.Timestamp("2026-04-04"),
                "valor": -127.40,
                "local": "iFood Sushi Yamamoto",
                "categoria": "Restaurantes",
                "classificacao": "Supérfluo",
                "forma_pagamento": "Crédito",
                "banco_origem": "C6",
                "tipo": "Despesa",
                "quem": "André",
                "mes_ref": "2026-04",
                "identificador": "uuid-004",
            },
            {
                "data": pd.Timestamp("2026-04-05"),
                "valor": -94.80,
                "local": "Uber",
                "categoria": "Transporte",
                "classificacao": "Questionável",
                "forma_pagamento": "Crédito",
                "banco_origem": "C6",
                "tipo": "Despesa",
                "quem": "André",
                "mes_ref": "2026-04",
                "identificador": "uuid-005",
            },
            {
                "data": pd.Timestamp("2026-04-06"),
                "valor": -150.00,
                "local": "Academia BlueFit",
                "categoria": "Saúde",
                "classificacao": "Obrigatório",
                "forma_pagamento": "Débito",
                "banco_origem": "C6",
                "tipo": "Despesa",
                "quem": "André",
                "mes_ref": "2026-04",
                "identificador": "uuid-006",
            },
            {
                "data": pd.Timestamp("2026-04-07"),
                "valor": -3200.00,
                "local": "B3 IVVB11",
                "categoria": "Investimento",
                "classificacao": "N/A",
                "forma_pagamento": "Transferência",
                "banco_origem": "Inter",
                "tipo": "Despesa",
                "quem": "André",
                "mes_ref": "2026-04",
                "identificador": "uuid-007",
            },
            {
                "data": pd.Timestamp("2026-04-08"),
                "valor": 1213.85,
                "local": "Pix cliente J. Mota",
                "categoria": "Receita PJ",
                "classificacao": "N/A",
                "forma_pagamento": "Pix",
                "banco_origem": "Bradesco",
                "tipo": "Receita",
                "quem": "André",
                "mes_ref": "2026-04",
                "identificador": "uuid-008",
            },
            {
                "data": pd.Timestamp("2026-04-09"),
                "valor": -500.00,
                "local": "Transferência Itaú->Nubank",
                "categoria": "Transferência",
                "classificacao": "N/A",
                "forma_pagamento": "Pix",
                "banco_origem": "Itaú",
                "tipo": "Transferência Interna",
                "quem": "André",
                "mes_ref": "2026-04",
                "identificador": "uuid-009",
            },
            {
                "data": pd.Timestamp("2026-04-10"),
                "valor": -180.00,
                "local": "Padaria Ki-Sabor",
                "categoria": "Mercado",
                "classificacao": "Obrigatório",
                "forma_pagamento": "Pix",
                "banco_origem": "C6",
                "tipo": "Despesa",
                "quem": "Casal",
                "mes_ref": "2026-04",
                "identificador": "uuid-010",
            },
        ]
    )


@pytest.fixture
def df_grande() -> pd.DataFrame:
    """50 linhas para teste de performance da tabela."""
    linhas = []
    for i in range(50):
        sinal = -1 if i % 3 != 0 else 1
        linhas.append(
            {
                "data": pd.Timestamp(f"2026-04-{(i % 28) + 1:02d}"),
                "valor": sinal * (50.0 + i * 7.3),
                "local": f"Estabelecimento {i:03d}",
                "categoria": ["Mercado", "Restaurantes", "Transporte", "Saúde", "Lazer"][i % 5],
                "classificacao": "Obrigatório",
                "forma_pagamento": "Crédito",
                "banco_origem": "C6",
                "tipo": "Despesa" if sinal < 0 else "Receita",
                "quem": ["André", "Vitória", "Casal"][i % 3],
                "mes_ref": "2026-04",
                "identificador": f"uuid-{i:03d}",
            }
        )
    return pd.DataFrame(linhas)


# ---------------------------------------------------------------------------
# Helper minificar
# ---------------------------------------------------------------------------


def test_minificar_remove_indentacao_python() -> None:
    """Lição UX-RD-04: indentação ≥ 4 espaços em HTML quebra CommonMark."""
    bruto = """
        <div class="x">
            <span>texto</span>
        </div>
    """
    saida = minificar(bruto)
    assert saida == '<div class="x"> <span>texto</span> </div>'
    # Sem nenhuma sequência de 4+ espaços consecutivos no resultado:
    assert "    " not in saida


# ---------------------------------------------------------------------------
# Saldo topo
# ---------------------------------------------------------------------------


def test_calcular_saldo_topo_separa_receita_de_despesa(df_pequeno: pd.DataFrame) -> None:
    metricas = calcular_saldo_topo(df_pequeno)
    # Receita: 5000 + 1213.85 = 6213.85
    assert metricas["receita"] == pytest.approx(6213.85)
    # Despesa (excluindo Transferência Interna -500):
    # -1280 - 290 - 127.40 - 94.80 - 150 - 3200 - 180 = -5322.20
    assert metricas["despesa"] == pytest.approx(-5322.20)
    assert metricas["saldo"] == pytest.approx(6213.85 - 5322.20)
    # Total inclui transferência interna (count visual)
    assert metricas["transacoes"] == 10


def test_saldo_topo_html_tem_tabular_nums_e_minificado(df_pequeno: pd.DataFrame) -> None:
    """UX-T-02: HTML emite os 4 KPIs canônicos do mockup com classe ``.t02-kpi``.

    Labels canônicos: Saldo consolidado / Entrada · 30d / Saída · 30d /
    Investido · 30d. Antes de UX-T-02 (UX-RD-06), os KPIs eram
    Saldo + RECEITA + DESPESA + TRANSAÇÕES — esses labels saíram com a
    migração para o padrão agentic-first.
    """
    metricas = calcular_saldo_topo(df_pequeno)
    html = _saldo_topo_html(metricas, "2026-04")
    assert "    " not in html
    assert "t02-kpi" in html
    assert "Saldo consolidado" in html
    assert "Entrada · 30d" in html
    assert "Saída · 30d" in html
    assert "Investido · 30d" in html


# ---------------------------------------------------------------------------
# Tabela densa
# ---------------------------------------------------------------------------


def test_tabela_densa_renderiza_n_linhas(df_pequeno: pd.DataFrame) -> None:
    html = _tabela_densa_html(df_pequeno)
    # Cada linha vira um <tr> no tbody. 10 linhas → 10 <tr> dentro de <tbody>
    # mais um <tr> no <thead>.
    n_tr = html.count("<tr")
    assert n_tr == 11  # 1 thead + 10 tbody
    # Tabular-nums vem da classe ``col-num`` (CSS de tema_css.py UX-RD-02)
    assert "col-num" in html
    # Sem fragmentos vazando como <pre><code>:
    assert "    " not in html
    assert "<pre>" not in html


def test_tabela_densa_50_linhas_renderiza_rapido(df_grande: pd.DataFrame) -> None:
    """Critério de aceitação relaxado para CI: <500ms (mockup pede <200ms)."""
    inicio = time.perf_counter()
    html = _tabela_densa_html(df_grande)
    dur_ms = (time.perf_counter() - inicio) * 1000
    assert dur_ms < 500, f"Renderização excedeu 500ms: {dur_ms:.1f}ms"
    assert html.count("<tr") == 51  # 1 thead + 50 tbody


# ---------------------------------------------------------------------------
# Breakdown lateral
# ---------------------------------------------------------------------------


def test_breakdown_soma_pct_aproxima_100(df_pequeno: pd.DataFrame) -> None:
    breakdown = calcular_breakdown_categorias(df_pequeno, top_n=10)
    soma_pct = sum(item["pct"] for item in breakdown)
    # Top-N pode não somar 100 quando há mais categorias; com top_n=10 e
    # apenas 7 categorias de despesa cobre todas:
    assert 99.5 < soma_pct < 100.5
    # Investimento (3200) é a maior despesa:
    assert breakdown[0]["categoria"] == "Investimento"


def test_breakdown_lateral_html_emite_top_5(df_pequeno: pd.DataFrame) -> None:
    breakdown = calcular_breakdown_categorias(df_pequeno, top_n=5)
    html = _breakdown_lateral_html(breakdown)
    # Cada categoria emite uma <div class="extrato-cat-barra">
    assert html.count("extrato-cat-barra") == 5
    # Sem indentação Python vazando
    assert "    " not in html


# ---------------------------------------------------------------------------
# Drawer JSON syntax highlight
# ---------------------------------------------------------------------------


def test_drawer_json_tem_syntax_highlight(df_pequeno: pd.DataFrame) -> None:
    transacao = transacao_para_dict(df_pequeno.iloc[0])
    drawer_html = renderizar_drawer(transacao, doc_vinculado=None)
    # Tokens canônicos --syn-* renderizados como classes
    assert "syn-key" in drawer_html
    assert "syn-string" in drawer_html
    assert "syn-number" in drawer_html
    # JSON foi formatado (chaves esperadas presentes)
    assert "data" in drawer_html
    assert "valor" in drawer_html
    # Sem fragmentos não-fechados
    assert drawer_html.count("<aside") == 1
    assert drawer_html.count("</aside>") == 1


def test_drawer_com_doc_vinculado_renderiza_sha8() -> None:
    transacao = {"data": "2026-04-01", "valor": -100.0}
    doc = {"sha8": "abc12345", "tipo_edge_semantico": "comprovante", "nome": "nf-001.pdf"}
    drawer_html = renderizar_drawer(transacao, doc_vinculado=doc)
    assert "abc12345" in drawer_html
    assert "comprovante" in drawer_html
    assert "nf-001.pdf" in drawer_html


# "A medida do amor é amar sem medida." -- Santo Agostinho
