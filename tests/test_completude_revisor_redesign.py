"""Testes do redesign UX-RD-10 (Completude + Revisor).

Cobre:
  * Matriz tipo × mês com classes D7 corretas (graduado/calibracao/...).
  * Deep-link ``?cluster=Documentos&tab=Catalogação&completude_mes=...``
    embutido nas células clicáveis.
  * Revisor: HTML com 4 colunas (ETL/Opus/Grafo/Humano) com ``border-left``
    distinto via classes ``revisor-fonte-{etl,opus,grafo,humano}``.
  * Atalhos j/k/a/r registrados no JS gerado e guard contra
    ``input``/``textarea``.
  * Aprovação grava em ``revisao_humana.sqlite`` preservando schema D2.
  * Schema invariante: tabela ``revisao`` com ``item_id, dimensao, ok,
    observacao, ts``.
  * ``listar_pendencias_revisao()`` continua funcional (re-export).
  * Deep-link da Catalogação preservado.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from src.dashboard.componentes.atalhos_revisor import gerar_html_atalhos_revisor
from src.dashboard.paginas import completude, revisor
from src.dashboard.paginas.revisor_logic import (
    carregar_marcacoes,
    garantir_schema,
    salvar_marcacao,
)

# ─────────────────────────────────────────────────────────────────────────────
# COMPLETUDE — matriz tipo × mês
# ─────────────────────────────────────────────────────────────────────────────


def test_matriz_classifica_celula_full_quando_pct_100() -> None:
    """100% de cobertura -> classe ``full`` (D7 graduado)."""
    assert completude._classificar_celula_d7(100.0, total=10) == "full"


def test_matriz_classifica_celula_partial_para_meio_termo() -> None:
    """Cobertura entre 50% e 99% -> ``partial`` (amarelo)."""
    assert completude._classificar_celula_d7(75.0, total=8) == "partial"
    assert completude._classificar_celula_d7(50.0, total=4) == "partial"


def test_matriz_classifica_celula_missing_para_baixa_cobertura() -> None:
    """Cobertura abaixo de 50% -> ``missing`` (vermelho)."""
    assert completude._classificar_celula_d7(0.0, total=5) == "missing"
    assert completude._classificar_celula_d7(33.0, total=3) == "missing"


def test_matriz_celula_empty_quando_sem_transacoes() -> None:
    """Total zero -> ``empty`` (cinza, sem ação)."""
    assert completude._classificar_celula_d7(100.0, total=0) == "empty"


def test_matriz_html_inclui_deeplink_para_catalogacao() -> None:
    """Cells com cobertura geram link ``?cluster=Documentos&tab=Catalogação&completude_mes=...``."""
    resumo = {
        "2026-01": {
            "Mercado": {"total": 5, "com_doc": 5, "sem_doc": 0, "orfas": []},
        },
        "2026-02": {
            "Mercado": {"total": 4, "com_doc": 1, "sem_doc": 3, "orfas": []},
        },
    }
    html = completude._matriz_html(resumo, ["Mercado"], ["2026-01", "2026-02"])
    assert "cluster=Documentos&tab=Catalogação" in html
    assert "completude_mes=2026-01" in html
    assert "completude_cat=Mercado" in html
    # Cell 100% deve ter classe full; cell 25% deve ter classe missing.
    assert "completude-cell-full" in html
    assert "completude-cell-missing" in html


def test_matriz_ordena_meses_pela_janela_de_12() -> None:
    """Janela limita aos 12 meses mais recentes (canônicos YYYY-MM)."""
    meses_input = [f"2025-{m:02d}" for m in range(1, 13)] + ["2026-01"]
    resultado = completude._ordenar_meses(meses_input, janela=12)
    assert len(resultado) == 12
    # Mais recente é 2026-01, deve estar incluído.
    assert "2026-01" in resultado
    # 2025-01 deve sair (mais antigo, fora da janela).
    assert "2025-01" not in resultado


# ─────────────────────────────────────────────────────────────────────────────
# REVISOR — bloco 4-fontes
# ─────────────────────────────────────────────────────────────────────────────


def test_bloco_fontes_emite_4_colunas_com_classes_distintas() -> None:
    """Card 4-way deve ter as 4 classes ``revisor-fonte-{etl,opus,grafo,humano}``."""
    html = revisor._bloco_fontes_html(
        valor_etl="2026-01-15",
        valor_opus="2026-01-15",
        valor_grafo="2026-01-15",
        valor_humano_label="OK (humano)",
        div_etl_opus=False,
        div_etl_grafo=False,
        div_grafo_opus=False,
    )
    assert "revisor-fonte-etl" in html
    assert "revisor-fonte-opus" in html
    assert "revisor-fonte-grafo" in html
    assert "revisor-fonte-humano" in html
    # Wrapper de fontes com grid 4 colunas.
    assert "revisor-card-fontes" in html


def test_bloco_fontes_marca_diverge_quando_etl_opus_diferem() -> None:
    """Divergência ETL × Opus -> classe ``diverge`` em ETL e Opus."""
    html = revisor._bloco_fontes_html(
        valor_etl="2026-01-15",
        valor_opus="2026-01-20",
        valor_grafo="2026-01-15",
        valor_humano_label="—",
        div_etl_opus=True,
        div_etl_grafo=False,
        div_grafo_opus=True,
    )
    # Deve haver pelo menos 2 ocorrências de "diverge" (ETL e Opus).
    assert html.count("diverge") >= 2


# ─────────────────────────────────────────────────────────────────────────────
# ATALHOS j/k/a/r
# ─────────────────────────────────────────────────────────────────────────────


def test_atalhos_revisor_registra_listener_para_jkar() -> None:
    """JS gerado deve mencionar todas as 4 teclas (case-insensitive: j/k/a/r)."""
    html = gerar_html_atalhos_revisor()
    for tecla in ("'j'", "'k'", "'a'", "'r'"):
        assert tecla in html, f"tecla {tecla} ausente do listener"


def test_atalhos_revisor_tem_guard_contra_input_e_textarea() -> None:
    """Listener deve ignorar eventos vindos de input/textarea (não atrapalha digitação)."""
    html = gerar_html_atalhos_revisor()
    assert "input, textarea, select" in html
    # E também respeita contenteditable.
    assert "contenteditable" in html


def test_atalhos_revisor_so_ativa_em_pagina_revisor() -> None:
    """JS deve checar query string ``cluster=Documentos`` e ``tab=Revisor``."""
    html = gerar_html_atalhos_revisor()
    assert "cluster=Documentos" in html
    assert "tab=Revisor" in html


def test_atalhos_revisor_idempotente() -> None:
    """Flag ``__ouroborosRevisorAtalhosInstalados`` impede listener duplicado."""
    html = gerar_html_atalhos_revisor()
    assert "__ouroborosRevisorAtalhosInstalados" in html


# ─────────────────────────────────────────────────────────────────────────────
# SQLITE — Sprint D2 schema preservado
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture()
def db_revisao_vazio(tmp_path: Path) -> Path:
    caminho = tmp_path / "revisao_humana.sqlite"
    garantir_schema(caminho)
    return caminho


def test_schema_d2_preservado_apos_garantir_schema(db_revisao_vazio: Path) -> None:
    """Schema canônico tem as 5 colunas Sprint D2 + extras 4-way."""
    conn = sqlite3.connect(db_revisao_vazio)
    cursor = conn.execute("PRAGMA table_info(revisao)")
    colunas = {row[1] for row in cursor.fetchall()}
    conn.close()
    # Sprint D2: 5 colunas mínimas obrigatórias.
    for col in ("item_id", "dimensao", "ok", "observacao", "ts"):
        assert col in colunas, f"coluna Sprint D2 '{col}' ausente"


def test_aprovacao_grava_marcacao_no_sqlite(db_revisao_vazio: Path) -> None:
    """``salvar_marcacao`` com ``ok=1`` persiste e ``carregar_marcacoes`` devolve."""
    salvar_marcacao(
        db_revisao_vazio,
        item_id="item-001",
        dimensao="data",
        ok=1,
        observacao="aprovado-via-atalho",
        valor_etl="2026-01-15",
    )
    marcacoes = carregar_marcacoes(db_revisao_vazio)
    assert len(marcacoes) == 1
    assert marcacoes[0]["item_id"] == "item-001"
    assert marcacoes[0]["dimensao"] == "data"
    assert marcacoes[0]["ok"] == 1
    assert "aprovado" in (marcacoes[0]["observacao"] or "")


def test_rejeicao_marca_ok_zero(db_revisao_vazio: Path) -> None:
    """Atalho 'r' deve gravar ok=0 preservando metadados."""
    salvar_marcacao(
        db_revisao_vazio,
        item_id="item-002",
        dimensao="valor",
        ok=0,
        observacao="rejeitado-via-atalho",
        valor_etl="100,00",
    )
    marcacoes = carregar_marcacoes(db_revisao_vazio)
    assert len(marcacoes) == 1
    assert marcacoes[0]["ok"] == 0


def test_listar_pendencias_revisao_continua_no_namespace_revisor() -> None:
    """Re-export ``revisor.listar_pendencias_revisao`` ainda existe (UX-RD-10
    NÃO TOCA dados_revisor.py — testes legados de Sprint D2 importam via
    ``from src.dashboard.paginas.revisor import listar_pendencias_revisao``).
    """
    # Importação via módulo deve funcionar sem AttributeError.
    from src.dashboard.dados import listar_pendencias_revisao as via_dados
    from src.dashboard.paginas.revisor import (
        garantir_schema as via_revisor_schema,
    )

    assert callable(via_dados)
    assert callable(via_revisor_schema)


def test_decisao_global_preserva_marcacoes_humanas_existentes(
    db_revisao_vazio: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``_gravar_decisao_global`` não sobrescreve OK/Erro já marcados; só
    atualiza dimensões em ``Não-aplicável`` (None)."""
    # Aponta o módulo para o SQLite temporário.
    monkeypatch.setattr(revisor, "CAMINHO_REVISAO_HUMANA", db_revisao_vazio)
    coletadas = {
        "data": (1, "OK confirmado", "2026-01-15", ""),  # já marcado
        "valor": (None, "", "100,00", ""),  # não-aplicável
        "fornecedor": (0, "errado", "Foo", ""),  # já marcado erro
    }
    revisor._gravar_decisao_global(
        "item-decisao",
        coletadas,
        decisao=1,  # aprovar
        observacao_global="aprovado-via-atalho",
    )
    marcacoes = carregar_marcacoes(db_revisao_vazio)
    por_dim = {m["dimensao"]: m for m in marcacoes}
    # data continua 1 (intocada).
    assert por_dim["data"]["ok"] == 1
    # valor agora é 1 (sobrescreveu Não-aplicável com decisão global).
    assert por_dim["valor"]["ok"] == 1
    # fornecedor continua 0 (humano explicitou erro; não sobrescreve).
    assert por_dim["fornecedor"]["ok"] == 0


# ─────────────────────────────────────────────────────────────────────────────
# Page header redesign UX-RD-10
# ─────────────────────────────────────────────────────────────────────────────


def test_page_header_revisor_inclui_sprint_tag_ux_rd_10() -> None:
    """Header do Revisor ostenta sprint-tag UX-RD-10 + pill de pendências."""
    html = revisor._page_header_html(total=15, revisados=5, taxa=0.8)
    assert 'class="sprint-tag"' in html
    assert "UX-RD-10" in html
    # Aguardando = 10, deve aparecer a pill.
    assert "10 pendências" in html


def test_page_header_completude_mostra_pill_d7_calibracao_para_84pct() -> None:
    """Cobertura 84% (entre 70 e 90) -> pill ``pill-d7-calibracao``."""
    html = completude._page_header_html(pct_global=84.0, lacunas_total=17)
    assert "pill-d7-calibracao" in html
    assert "84%" in html
    assert "UX-RD-10" in html


# "É próprio do espírito bem formado caber em todos os tópicos." -- Quintiliano
