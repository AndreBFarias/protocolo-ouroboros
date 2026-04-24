"""Testes da página Catalogação (Sprint 51).

Cobre:
- Helper `carregar_documentos_grafo` em ambos os cenários (grafo ausente
  e grafo real da produção).
- Contrato da tabela (4 colunas exatas: Data, Fornecedor, Total, Status).
- Valores válidos de `status_linking`.
- Registro no menu lateral do dashboard (tab "Catalogação" listada).
- Renderização sem crash quando grafo está vazio.

Todos os testes que tocam o grafo de produção são READ-ONLY.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
import pytest

from src.dashboard import dados as dashboard_dados
from src.dashboard.paginas import catalogacao
from src.dashboard.paginas.catalogacao import COLUNAS_TABELA

RAIZ = Path(__file__).resolve().parents[1]
GRAFO_PROD = RAIZ / "data" / "output" / "grafo.sqlite"


@pytest.fixture()
def grafo_vazio(tmp_path, monkeypatch):
    """Cria grafo SQLite vazio em tmp + aponta dashboard.dados pra ele."""
    destino = tmp_path / "grafo.sqlite"
    conn = sqlite3.connect(destino)
    conn.executescript(
        """
        CREATE TABLE node (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          tipo TEXT NOT NULL,
          nome_canonico TEXT NOT NULL,
          aliases TEXT DEFAULT '[]',
          metadata TEXT DEFAULT '{}'
        );
        CREATE TABLE edge (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          src_id INTEGER NOT NULL,
          dst_id INTEGER NOT NULL,
          tipo TEXT NOT NULL,
          peso REAL DEFAULT 1.0,
          evidencia TEXT DEFAULT '{}'
        );
        """
    )
    conn.commit()
    conn.close()

    propostas = tmp_path / "propostas" / "linking"
    propostas.mkdir(parents=True)

    monkeypatch.setattr(dashboard_dados, "CAMINHO_GRAFO", destino)
    monkeypatch.setattr(dashboard_dados, "CAMINHO_PROPOSTAS_LINKING", propostas)
    dashboard_dados.carregar_documentos_grafo.clear()
    return destino, propostas


@pytest.fixture()
def grafo_dois_docs(tmp_path, monkeypatch):
    """Grafo pequeno com 2 documentos + 1 aresta documento_de + 1 proposta."""
    destino = tmp_path / "grafo.sqlite"
    conn = sqlite3.connect(destino)
    conn.executescript(
        """
        CREATE TABLE node (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          tipo TEXT NOT NULL,
          nome_canonico TEXT NOT NULL,
          aliases TEXT DEFAULT '[]',
          metadata TEXT DEFAULT '{}'
        );
        CREATE TABLE edge (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          src_id INTEGER NOT NULL,
          dst_id INTEGER NOT NULL,
          tipo TEXT NOT NULL,
          peso REAL DEFAULT 1.0,
          evidencia TEXT DEFAULT '{}'
        );
        """
    )
    # doc1 -- vinculado (tem documento_de)
    conn.execute(
        "INSERT INTO node (id, tipo, nome_canonico, metadata) VALUES (?, ?, ?, ?)",
        (
            1,
            "documento",
            "chave_doc_1",
            '{"tipo_documento": "nfce_modelo_65", '
            '"razao_social": "Padaria Fulana", '
            '"cnpj_emitente": "00.000.000/0001-00", '
            '"data_emissao": "2026-04-15", "total": 87.50}',
        ),
    )
    # doc2 -- sem transação
    conn.execute(
        "INSERT INTO node (id, tipo, nome_canonico, metadata) VALUES (?, ?, ?, ?)",
        (
            2,
            "documento",
            "chave_doc_2",
            '{"tipo_documento": "nfe_modelo_55", '
            '"razao_social": "Magazine Beltrana", '
            '"cnpj_emitente": "11.111.111/0001-11", '
            '"data_emissao": "2026-04-16", "total": 1289.00}',
        ),
    )
    # transação dummy para alvo de aresta documento_de
    conn.execute(
        "INSERT INTO node (id, tipo, nome_canonico, metadata) VALUES (?, ?, ?, ?)",
        (3, "transacao", "tx_dummy", "{}"),
    )
    conn.execute(
        "INSERT INTO edge (src_id, dst_id, tipo) VALUES (?, ?, 'documento_de')",
        (1, 3),
    )
    conn.commit()
    conn.close()

    propostas = tmp_path / "propostas" / "linking"
    propostas.mkdir(parents=True)
    # proposta conflito para chave_doc_2 (substring 20 chars)
    (propostas / "chave_doc_2_conflito_magalu.md").write_text("# proposta")

    monkeypatch.setattr(dashboard_dados, "CAMINHO_GRAFO", destino)
    monkeypatch.setattr(dashboard_dados, "CAMINHO_PROPOSTAS_LINKING", propostas)
    dashboard_dados.carregar_documentos_grafo.clear()
    return destino, propostas


class TestCarregarDocumentosGrafo:
    def test_retorna_dataframe_vazio_quando_grafo_ausente(self, tmp_path, monkeypatch):
        inexistente = tmp_path / "nao_existe.sqlite"
        monkeypatch.setattr(dashboard_dados, "CAMINHO_GRAFO", inexistente)
        dashboard_dados.carregar_documentos_grafo.clear()

        df = dashboard_dados.carregar_documentos_grafo()
        assert isinstance(df, pd.DataFrame)
        assert df.empty
        # schema estável mesmo vazio
        assert "doc_id" in df.columns
        assert "status_linking" in df.columns

    def test_retorna_dataframe_vazio_com_grafo_sem_documentos(self, grafo_vazio):
        df = dashboard_dados.carregar_documentos_grafo()
        assert df.empty
        assert list(df.columns) == [
            "doc_id",
            "tipo_documento",
            "cnpj_emitente",
            "razao_social",
            "data_emissao",
            "total",
            "status_linking",
            "arquivo_origem",
        ]

    def test_carrega_dois_documentos_reais_do_fixture(self, grafo_dois_docs):
        df = dashboard_dados.carregar_documentos_grafo()
        assert len(df) == 2
        assert set(df["tipo_documento"]) == {"nfce_modelo_65", "nfe_modelo_55"}

    def test_status_linking_vinculado_quando_tem_documento_de(self, grafo_dois_docs):
        df = dashboard_dados.carregar_documentos_grafo()
        doc1 = df[df["doc_id"] == 1].iloc[0]
        assert doc1["status_linking"] == "Vinculado"

    def test_status_linking_conflito_quando_proposta_existe(self, grafo_dois_docs):
        df = dashboard_dados.carregar_documentos_grafo()
        doc2 = df[df["doc_id"] == 2].iloc[0]
        assert doc2["status_linking"] == "Conflito"

    def test_status_linking_tres_valores_possiveis(self, grafo_dois_docs):
        """Domínio fechado: Vinculado, Sem transação, Conflito."""
        df = dashboard_dados.carregar_documentos_grafo()
        valores_aceitos = {"Vinculado", "Sem transação", "Conflito"}
        assert set(df["status_linking"].unique()).issubset(valores_aceitos)

    @pytest.mark.skipif(
        not GRAFO_PROD.exists(),
        reason="Grafo de produção não disponível neste ambiente",
    )
    def test_carrega_grafo_producao_read_only(self, monkeypatch):
        """Read-only sobre grafo real: não deve levantar exceção nem mutar."""
        sha_antes = GRAFO_PROD.stat().st_size
        dashboard_dados.carregar_documentos_grafo.clear()
        df = dashboard_dados.carregar_documentos_grafo()
        sha_depois = GRAFO_PROD.stat().st_size
        assert sha_antes == sha_depois
        assert isinstance(df, pd.DataFrame)
        # grafo de produção atual tem pelo menos 1 documento
        if not df.empty:
            assert "doc_id" in df.columns


class TestContarPropostasLinking:
    def test_zero_quando_diretorio_ausente(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            dashboard_dados,
            "CAMINHO_PROPOSTAS_LINKING",
            tmp_path / "inexistente",
        )
        assert dashboard_dados.contar_propostas_linking() == 0

    def test_conta_apenas_md_na_raiz_nao_subpastas(self, tmp_path, monkeypatch):
        base = tmp_path / "linking"
        base.mkdir()
        (base / "um.md").write_text("a")
        (base / "dois.md").write_text("b")
        (base / "_aprovadas").mkdir()
        (base / "_aprovadas" / "antiga.md").write_text("c")  # não deve contar
        monkeypatch.setattr(dashboard_dados, "CAMINHO_PROPOSTAS_LINKING", base)

        assert dashboard_dados.contar_propostas_linking() == 2


class TestContratoTabela:
    def test_tabela_tem_exatamente_4_colunas(self):
        assert len(COLUNAS_TABELA) == 4

    def test_colunas_sao_data_fornecedor_total_status(self):
        assert COLUNAS_TABELA == ["Data", "Fornecedor", "Total", "Status"]


class TestSeveridadeProposta:
    def test_conflito_no_nome_marca_alta(self):
        assert catalogacao._severidade_proposta("2026_conflito_x.md") == "alta"

    def test_duplo_marca_alta(self):
        assert catalogacao._severidade_proposta("magalu_duplo.md") == "alta"

    def test_threshold_marca_media(self):
        assert catalogacao._severidade_proposta("apolice-threshold.md") == "media"

    def test_ocr_marca_media(self):
        assert catalogacao._severidade_proposta("farmacia_ocr.md") == "media"

    def test_caso_default_marca_baixa(self):
        assert catalogacao._severidade_proposta("shell_orfao.md") == "baixa"


class TestRenderizacaoStreamlit:
    """Testes de renderização usando streamlit.testing.v1.AppTest."""

    def test_pagina_renderiza_sem_crash_com_grafo_ausente(
        self, tmp_path, monkeypatch
    ):
        """Graceful degradation: grafo ausente mostra warning, não crasha."""
        from streamlit.testing.v1 import AppTest

        inexistente = tmp_path / "nao_existe.sqlite"
        monkeypatch.setenv("OUROBOROS_TEST_GRAFO", str(inexistente))

        script = _script_teste_catalogacao(inexistente, tmp_path / "propostas")
        at = AppTest.from_string(script)
        at.run()
        assert not at.exception
        # Sprint 92c: warning/info migraram para callout_html via st.markdown.
        # Coletamos de todas as fontes para robustez à migração em andamento.
        textos = (
            [w.value for w in at.warning]
            + [i.value for i in at.info]
            + [m.value for m in at.markdown]
        )
        assert any("grafo" in t.lower() or "popule" in t.lower() for t in textos)

    def test_pagina_renderiza_com_grafo_vazio(self, grafo_vazio):
        """Grafo existe mas sem documentos: página sobe sem crash."""
        from streamlit.testing.v1 import AppTest

        destino, propostas = grafo_vazio
        script = _script_teste_catalogacao(destino, propostas)
        at = AppTest.from_string(script)
        at.run()
        assert not at.exception

    def test_pagina_renderiza_com_dois_documentos(self, grafo_dois_docs):
        """Grafo com 2 docs: página renderiza, sem exceção."""
        from streamlit.testing.v1 import AppTest

        destino, propostas = grafo_dois_docs
        script = _script_teste_catalogacao(destino, propostas)
        at = AppTest.from_string(script)
        at.run()
        assert not at.exception
        # quatro cards KPI (via markdown) -- checar que ao menos algum bloco
        # markdown foi renderizado
        assert len(at.markdown) > 0


class TestMenuLateral:
    def test_menu_lateral_lista_catalogacao(self):
        """O módulo app.py deve declarar a tab 'Catalogação' no st.tabs."""
        texto = (RAIZ / "src" / "dashboard" / "app.py").read_text(encoding="utf-8")
        assert '"Catalogação"' in texto
        assert "tab_catalogacao" in texto
        assert "catalogacao.renderizar" in texto


def _script_teste_catalogacao(caminho_grafo: Path, caminho_propostas: Path) -> str:
    """Gera script Streamlit que monkey-patcha dados e renderiza catalogação."""
    return f"""
import sys
from pathlib import Path
RAIZ = Path({str(RAIZ)!r})
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from src.dashboard import dados as d
d.CAMINHO_GRAFO = Path({str(caminho_grafo)!r})
d.CAMINHO_PROPOSTAS_LINKING = Path({str(caminho_propostas)!r})
d.carregar_documentos_grafo.clear()

from src.dashboard.paginas import catalogacao
catalogacao.renderizar()
"""


# "O teste é a diferença entre acreditar e saber." -- princípio empirista
