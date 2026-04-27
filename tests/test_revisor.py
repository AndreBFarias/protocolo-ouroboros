"""Testes da página Revisor Visual Semi-Automatizado -- Sprint D2.

Cobre:
  - ``listar_pendencias_revisao`` em 4 cenários (raw_classificar, raw_conferir,
    grafo low confidence, grafo sem link).
  - Persistência SQLite (UPSERT, idempotência, schema).
  - Geração de relatório Markdown com PII mascarada.
  - Mascaramento PII em texto livre (CPF/CNPJ formatados e crus).
  - Detecção de padrões recorrentes (>=3 reprovações).
  - Sugestor de patch YAML.
  - Registro da aba "Revisor" no MAPA_ABA_PARA_CLUSTER.

Todos os testes que tocam o grafo usam fixture sintético em ``tmp_path``.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from src.dashboard import dados as dashboard_dados
from src.dashboard.componentes.drilldown import MAPA_ABA_PARA_CLUSTER
from src.dashboard.paginas import revisor

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def grafo_com_pendencias(tmp_path):
    """Grafo sintético com 3 documentos: low_confidence, sem_link, vinculado."""
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
    # doc1 -- confidence baixa (deve aparecer)
    conn.execute(
        "INSERT INTO node (id, tipo, nome_canonico, metadata) VALUES (?, ?, ?, ?)",
        (
            1,
            "documento",
            "chave_low_conf",
            '{"tipo_documento": "nfce_modelo_65", "confidence": 0.5, '
            '"razao_social": "Padaria X", "arquivo_origem": "/tmp/x.pdf"}',
        ),
    )
    # doc2 -- sem aresta documento_de (deve aparecer como grafo_sem_link)
    conn.execute(
        "INSERT INTO node (id, tipo, nome_canonico, metadata) VALUES (?, ?, ?, ?)",
        (
            2,
            "documento",
            "chave_sem_link",
            '{"tipo_documento": "nfe_modelo_55", "razao_social": "Magazine Y"}',
        ),
    )
    # doc3 -- vinculado (NÃO deve aparecer)
    conn.execute(
        "INSERT INTO node (id, tipo, nome_canonico, metadata) VALUES (?, ?, ?, ?)",
        (
            3,
            "documento",
            "chave_vinculada",
            '{"tipo_documento": "boleto", "confidence": 0.95}',
        ),
    )
    conn.execute(
        "INSERT INTO node (id, tipo, nome_canonico, metadata) VALUES (?, ?, ?, ?)",
        (4, "transacao", "tx_dummy", "{}"),
    )
    conn.execute(
        "INSERT INTO edge (src_id, dst_id, tipo) VALUES (?, ?, 'documento_de')",
        (3, 4),
    )
    conn.commit()
    conn.close()
    return destino


@pytest.fixture()
def diretorios_raw(tmp_path):
    """Cria estrutura ``data/raw/_classificar`` e ``_conferir`` com arquivos
    sintéticos."""
    raw_root = tmp_path / "data" / "raw"
    classificar = raw_root / "_classificar"
    conferir = raw_root / "_conferir"
    classificar.mkdir(parents=True)
    conferir.mkdir(parents=True)
    (classificar / "doc_pendente_1.pdf").write_text("conteúdo PDF")
    (classificar / "doc_pendente_2.pdf").write_text("conteúdo PDF 2")
    (conferir / "cupom_dudoso").mkdir()
    (conferir / "cupom_dudoso" / "foto.jpg").write_text("imagem")
    return classificar, conferir


# ---------------------------------------------------------------------------
# listar_pendencias_revisao
# ---------------------------------------------------------------------------


class TestListarPendencias:
    def test_devolve_vazio_quando_tudo_ausente(self, tmp_path):
        pendencias = dashboard_dados.listar_pendencias_revisao(
            caminho_grafo=tmp_path / "ausente.sqlite",
            caminho_classificar=tmp_path / "ausente_class",
            caminho_conferir=tmp_path / "ausente_conf",
        )
        assert pendencias == []

    def test_lista_arquivos_em_classificar(self, diretorios_raw, tmp_path):
        classificar, conferir = diretorios_raw
        pendencias = dashboard_dados.listar_pendencias_revisao(
            caminho_grafo=tmp_path / "ausente.sqlite",
            caminho_classificar=classificar,
            caminho_conferir=tmp_path / "ausente_conf",
        )
        tipos = {p["tipo"] for p in pendencias}
        assert tipos == {"raw_classificar"}
        nomes = {Path(p["caminho"]).name for p in pendencias}
        assert nomes == {"doc_pendente_1.pdf", "doc_pendente_2.pdf"}

    def test_lista_diretorios_em_conferir(self, diretorios_raw, tmp_path):
        classificar, conferir = diretorios_raw
        pendencias = dashboard_dados.listar_pendencias_revisao(
            caminho_grafo=tmp_path / "ausente.sqlite",
            caminho_classificar=tmp_path / "ausente_class",
            caminho_conferir=conferir,
        )
        assert len(pendencias) == 1
        assert pendencias[0]["tipo"] == "raw_conferir"
        assert pendencias[0]["metadata"]["eh_diretorio"] is True

    def test_grafo_low_confidence_e_sem_link(self, grafo_com_pendencias, tmp_path):
        pendencias = dashboard_dados.listar_pendencias_revisao(
            caminho_grafo=grafo_com_pendencias,
            caminho_classificar=tmp_path / "ausente_class",
            caminho_conferir=tmp_path / "ausente_conf",
        )
        tipos = {p["tipo"] for p in pendencias}
        assert "grafo_low_confidence" in tipos
        assert "grafo_sem_link" in tipos
        # vinculado e high-confidence não aparece
        item_ids = {p["item_id"] for p in pendencias}
        assert "node_3" not in item_ids
        assert "node_1" in item_ids
        assert "node_2" in item_ids

    def test_ordenacao_por_prioridade(self, diretorios_raw, grafo_com_pendencias):
        classificar, conferir = diretorios_raw
        pendencias = dashboard_dados.listar_pendencias_revisao(
            caminho_grafo=grafo_com_pendencias,
            caminho_classificar=classificar,
            caminho_conferir=conferir,
        )
        prioridades = [p["prioridade"] for p in pendencias]
        assert prioridades == sorted(prioridades), (
            "pendências devem ser ordenadas por prioridade ascendente"
        )
        # raw_classificar (prio=1) vem antes de grafo_low_confidence (prio=3)
        assert pendencias[0]["tipo"] == "raw_classificar"


# ---------------------------------------------------------------------------
# Persistência SQLite
# ---------------------------------------------------------------------------


class TestPersistenciaSQLite:
    def test_garantir_schema_cria_tabela_e_indices(self, tmp_path):
        destino = tmp_path / "revisao.sqlite"
        revisor.garantir_schema(destino)
        assert destino.exists()
        conn = sqlite3.connect(destino)
        try:
            tabelas = {
                row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            }
            assert "revisao" in tabelas
            indices = {
                row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='index'")
            }
            assert "idx_revisao_ts" in indices
            assert "idx_revisao_dimensao" in indices
        finally:
            conn.close()

    def test_salvar_marcacao_inserts_e_upserts(self, tmp_path):
        destino = tmp_path / "revisao.sqlite"
        revisor.salvar_marcacao(destino, "item_a", "data", 1, "ok inicial")
        marcas = revisor.carregar_marcacoes(destino, "item_a")
        assert len(marcas) == 1
        assert marcas[0]["ok"] == 1
        assert marcas[0]["observacao"] == "ok inicial"

        # upsert: mesma chave (item_id, dimensao) sobrescreve
        revisor.salvar_marcacao(destino, "item_a", "data", 0, "errei")
        marcas = revisor.carregar_marcacoes(destino, "item_a")
        assert len(marcas) == 1
        assert marcas[0]["ok"] == 0
        assert marcas[0]["observacao"] == "errei"

    def test_salvar_marcacao_aceita_estado_nulo_nao_aplicavel(self, tmp_path):
        destino = tmp_path / "revisao.sqlite"
        revisor.salvar_marcacao(destino, "item_b", "itens", None, "")
        marcas = revisor.carregar_marcacoes(destino, "item_b")
        assert len(marcas) == 1
        assert marcas[0]["ok"] is None

    def test_carregar_marcacoes_inexistente_devolve_vazio(self, tmp_path):
        ausente = tmp_path / "nao_existe.sqlite"
        assert revisor.carregar_marcacoes(ausente) == []


# ---------------------------------------------------------------------------
# Mascaramento PII
# ---------------------------------------------------------------------------


class TestMascaramentoPII:
    def test_mascara_cpf_formatado(self):
        entrada = "supervisor André CPF 123.456.789-00 revisou cupom"
        saida = revisor.mascarar_pii(entrada)
        assert "123.456.789-00" not in saida
        assert "XXX.XXX.XXX-XX" in saida

    def test_mascara_cnpj_formatado(self):
        entrada = "fornecedor 12.345.678/0001-90 emitiu nota"
        saida = revisor.mascarar_pii(entrada)
        assert "12.345.678/0001-90" not in saida
        assert "XX.XXX.XXX/XXXX-XX" in saida

    def test_mascara_cpf_cru_11_digitos(self):
        entrada = "documento referência 12345678900 vinculado"
        saida = revisor.mascarar_pii(entrada)
        assert "12345678900" not in saida

    def test_mascara_cnpj_cru_14_digitos(self):
        entrada = "raiz 12345678000190 emitiu o documento"
        saida = revisor.mascarar_pii(entrada)
        assert "12345678000190" not in saida

    def test_texto_sem_pii_retorna_intacto(self):
        entrada = "tudo normal aqui, dimensão data correta"
        saida = revisor.mascarar_pii(entrada)
        assert saida == entrada

    def test_mascara_pii_em_string_vazia(self):
        assert revisor.mascarar_pii("") == ""


# ---------------------------------------------------------------------------
# Geração de relatório
# ---------------------------------------------------------------------------


class TestRelatorio:
    def test_relatorio_mascara_pii_em_observacao(self, tmp_path):
        destino_db = tmp_path / "revisao.sqlite"
        revisor.salvar_marcacao(
            destino_db,
            "item_x",
            "fornecedor",
            0,
            "razão social cita 12.345.678/0001-90",
        )
        marcacoes = revisor.carregar_marcacoes(destino_db)
        diretorio = tmp_path / "revisoes"
        destino_md = revisor.gravar_relatorio(marcacoes, diretorio)
        conteudo = destino_md.read_text(encoding="utf-8")
        assert "12.345.678/0001-90" not in conteudo
        assert "XX.XXX.XXX/XXXX-XX" in conteudo

    def test_relatorio_inclui_taxa_fidelidade(self, tmp_path):
        destino_db = tmp_path / "revisao.sqlite"
        revisor.salvar_marcacao(destino_db, "i1", "data", 1, "")
        revisor.salvar_marcacao(destino_db, "i1", "valor", 1, "")
        revisor.salvar_marcacao(destino_db, "i2", "data", 0, "")
        marcacoes = revisor.carregar_marcacoes(destino_db)
        relatorio = revisor.gerar_relatorio_markdown(marcacoes)
        # 2 OK / 3 avaliadas = 66.7%
        assert "66.7%" in relatorio or "66,7%" in relatorio
        assert "Taxa de fidelidade humana" in relatorio

    def test_gravar_relatorio_cria_arquivo_com_data_no_nome(self, tmp_path):
        destino_db = tmp_path / "revisao.sqlite"
        revisor.salvar_marcacao(destino_db, "i1", "data", 1, "")
        marcacoes = revisor.carregar_marcacoes(destino_db)
        diretorio = tmp_path / "revisoes"
        destino_md = revisor.gravar_relatorio(marcacoes, diretorio)
        assert destino_md.exists()
        # nome contém YYYY-MM-DD
        from datetime import datetime as _dt

        hoje = _dt.now().strftime("%Y-%m-%d")
        assert destino_md.name == f"{hoje}.md"


# ---------------------------------------------------------------------------
# Padrões recorrentes e sugestor de patch
# ---------------------------------------------------------------------------


class TestPadroesRecorrentes:
    def test_detecta_dimensao_reprovada_3_vezes(self, tmp_path):
        destino_db = tmp_path / "revisao.sqlite"
        revisor.salvar_marcacao(destino_db, "i1", "valor", 0, "")
        revisor.salvar_marcacao(destino_db, "i2", "valor", 0, "")
        revisor.salvar_marcacao(destino_db, "i3", "valor", 0, "")
        marcacoes = revisor.carregar_marcacoes(destino_db)
        padroes = revisor.detectar_padroes_recorrentes(marcacoes)
        assert len(padroes) == 1
        assert padroes[0]["dimensao"] == "valor"
        assert padroes[0]["contagem"] == 3

    def test_ignora_dimensao_com_menos_que_limite(self, tmp_path):
        destino_db = tmp_path / "revisao.sqlite"
        revisor.salvar_marcacao(destino_db, "i1", "data", 0, "")
        revisor.salvar_marcacao(destino_db, "i2", "data", 0, "")
        marcacoes = revisor.carregar_marcacoes(destino_db)
        padroes = revisor.detectar_padroes_recorrentes(marcacoes, limite=3)
        assert padroes == []

    def test_sugerir_patch_yaml_renderiza_blocos(self):
        padroes = [
            {"dimensao": "valor", "contagem": 5, "item_ids": ["i1", "i2", "i3"]},
        ]
        patch = revisor.sugerir_patch_yaml(padroes)
        assert "ajuste_valor_pos_revisao_humana" in patch
        assert "TODO_humano" in patch

    def test_sugerir_patch_vazio_quando_sem_padroes(self):
        patch = revisor.sugerir_patch_yaml([])
        assert "nenhum padrão" in patch.lower()


# ---------------------------------------------------------------------------
# Integração com app.py
# ---------------------------------------------------------------------------


class TestRegistroDaAba:
    def test_revisor_no_mapa_aba_para_cluster(self):
        assert MAPA_ABA_PARA_CLUSTER.get("Revisor") == "Documentos"

    def test_pagina_revisor_existe_e_importa(self):
        # smoke import: garante que o módulo carrega sem efeito colateral
        # (nenhuma chamada a streamlit fora de função)
        from src.dashboard.paginas import revisor as _revisor

        assert hasattr(_revisor, "renderizar")
        assert callable(_revisor.renderizar)


# "Testes que documentam alinhamento humano-máquina são duplamente úteis."
# -- princípio do alinhamento mensurável
