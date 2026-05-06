"""Testes da página Grafo Visual + Obsidian Rico (Sprint 53).

Cobre:
- Renderização da página via AppTest (grafo vazio e com dados reais).
- Helper `carregar_subgrafo` (BFS 1-hop retorna vizinhos diretos).
- Helper `obter_fluxo_receita_categoria_fornecedor` com 3 seções.
- `gerar_moc_mensal` produz Markdown com wikilinks.
- Presença da tab "Grafo + Obsidian" no menu.
- Invariante: página NÃO usa Sankey (decisão explícita do supervisor,
  só bar charts).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from src.dashboard import dados as dashboard_dados

RAIZ = Path(__file__).resolve().parents[1]


@pytest.fixture()
def grafo_sprint53(tmp_path, monkeypatch):
    """Grafo com fornecedor central + documento + transação + período."""
    destino = tmp_path / "grafo_53.sqlite"
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
    # fornecedor central
    conn.execute(
        "INSERT INTO node (id, tipo, nome_canonico, metadata) VALUES (?, ?, ?, ?)",
        (
            1,
            "fornecedor",
            "NEOENERGIA DF",
            '{"cnpj": "00.394.460/0058-87", "categoria": "energia"}',
        ),
    )
    # documento ligado ao fornecedor
    conn.execute(
        "INSERT INTO node (id, tipo, nome_canonico, metadata) VALUES (?, ?, ?, ?)",
        (
            2,
            "documento",
            "fatura_neoenergia_2026_04",
            '{"tipo_documento": "fatura", "total": 487.23, '
            '"data_emissao": "2026-04-08", "razao_social": "Neoenergia"}',
        ),
    )
    # transação ligada ao fornecedor
    conn.execute(
        "INSERT INTO node (id, tipo, nome_canonico, metadata) VALUES (?, ?, ?, ?)",
        (
            3,
            "transacao",
            "tx_neo_2026_04",
            '{"valor": 487.23, "tipo": "Despesa", "local": "NEOENERGIA", '
            '"data": "2026-04-09", "banco": "Itaú"}',
        ),
    )
    # período
    conn.execute(
        "INSERT INTO node (id, tipo, nome_canonico, metadata) VALUES (?, ?, ?, ?)",
        (4, "periodo", "2026-04", "{}"),
    )
    # categoria
    conn.execute(
        "INSERT INTO node (id, tipo, nome_canonico, metadata) VALUES (?, ?, ?, ?)",
        (5, "categoria", "energia", '{"tipo_categoria": "despesa"}'),
    )
    # item
    conn.execute(
        "INSERT INTO node (id, tipo, nome_canonico, metadata) VALUES (?, ?, ?, ?)",
        (
            6,
            "item",
            "energia_kwh_residencial",
            '{"descricao": "Energia elétrica", "valor_total": 450.10}',
        ),
    )
    # arestas
    conn.execute(
        "INSERT INTO edge (src_id, dst_id, tipo) VALUES (?, ?, 'fornecido_por')",
        (2, 1),
    )
    conn.execute(
        "INSERT INTO edge (src_id, dst_id, tipo) VALUES (?, ?, 'fornecido_por')",
        (3, 1),
    )
    conn.execute(
        "INSERT INTO edge (src_id, dst_id, tipo) VALUES (?, ?, 'contem_item')",
        (2, 6),
    )
    conn.execute(
        "INSERT INTO edge (src_id, dst_id, tipo) VALUES (?, ?, 'ocorre_em')",
        (2, 4),
    )
    conn.execute(
        "INSERT INTO edge (src_id, dst_id, tipo) VALUES (?, ?, 'ocorre_em')",
        (3, 4),
    )
    conn.execute(
        "INSERT INTO edge (src_id, dst_id, tipo) VALUES (?, ?, 'categoria_de')",
        (6, 5),
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(dashboard_dados, "CAMINHO_GRAFO", destino)
    dashboard_dados.carregar_subgrafo.clear()
    dashboard_dados.obter_fluxo_receita_categoria_fornecedor.clear()
    return destino


class TestSubgrafo:
    def test_subgrafo_retorna_nodes_e_edges(self, grafo_sprint53):
        """Subgrafo de fornecedor retorna estrutura com 3 chaves principais."""
        sub = dashboard_dados.carregar_subgrafo(1, radius=1)
        assert set(sub.keys()) >= {"nodes", "edges", "center_id"}
        assert sub["center_id"] == 1
        assert isinstance(sub["nodes"], list)
        assert isinstance(sub["edges"], list)

    def test_subgrafo_raio_1_inclui_vizinhos_diretos(self, grafo_sprint53):
        """Raio 1 do fornecedor deve trazer documento e transação ligados."""
        sub = dashboard_dados.carregar_subgrafo(1, radius=1)
        ids = {n["id"] for n in sub["nodes"]}
        assert 1 in ids, "próprio fornecedor deve estar incluso"
        assert 2 in ids, "documento ligado via fornecido_por"
        assert 3 in ids, "transação ligada via fornecido_por"

    def test_subgrafo_vazio_quando_grafo_ausente(self, tmp_path, monkeypatch):
        """Grafo ausente: retorna estrutura vazia, não crasha."""
        inexistente = tmp_path / "nao_existe.sqlite"
        monkeypatch.setattr(dashboard_dados, "CAMINHO_GRAFO", inexistente)
        dashboard_dados.carregar_subgrafo.clear()
        sub = dashboard_dados.carregar_subgrafo(1, radius=1)
        assert sub["nodes"] == []
        assert sub["edges"] == []

    def test_subgrafo_raio_2_expande_alcance(self, grafo_sprint53):
        """Raio 2 deve alcançar nodes a 2 hops (ex: item via documento)."""
        dashboard_dados.carregar_subgrafo.clear()
        sub = dashboard_dados.carregar_subgrafo(1, radius=2)
        ids = {n["id"] for n in sub["nodes"]}
        # item (6) está a 2 hops: fornecedor(1) -- documento(2) -- item(6)
        assert 6 in ids

    def test_subgrafo_dedup_arestas(self, grafo_sprint53):
        """Arestas (src,dst,tipo) não devem repetir."""
        sub = dashboard_dados.carregar_subgrafo(1, radius=2)
        chaves = [(e["src_id"], e["dst_id"], e["tipo"]) for e in sub["edges"]]
        assert len(chaves) == len(set(chaves))


class TestFluxoAgregado:
    def test_fluxo_agregado_tres_secoes(self, grafo_sprint53, monkeypatch):
        """Retorno sempre tem 3 chaves de agregação + mes_ref."""
        # aponta XLSX para algo inexistente para forçar graceful
        monkeypatch.setattr(dashboard_dados, "CAMINHO_XLSX", Path("/tmp/nao_existe.xlsx"))
        dashboard_dados.carregar_dados.clear()
        dashboard_dados.obter_fluxo_receita_categoria_fornecedor.clear()
        fluxo = dashboard_dados.obter_fluxo_receita_categoria_fornecedor("2026-04")
        assert set(fluxo.keys()) == {"receita", "despesa", "fornecedor", "mes_ref"}
        assert fluxo["mes_ref"] == "2026-04"

    def test_fluxo_grafo_ausente_retorna_vazio(self, tmp_path, monkeypatch):
        """Sem XLSX, agregações voltam vazias sem crash."""
        monkeypatch.setattr(dashboard_dados, "CAMINHO_XLSX", tmp_path / "inexistente.xlsx")
        dashboard_dados.carregar_dados.clear()
        dashboard_dados.obter_fluxo_receita_categoria_fornecedor.clear()
        fluxo = dashboard_dados.obter_fluxo_receita_categoria_fornecedor("2026-04")
        assert fluxo["receita"] == []
        assert fluxo["despesa"] == []
        assert fluxo["fornecedor"] == []


class TestMOCMensal:
    def test_moc_mensal_contem_wikilinks(self, grafo_sprint53):
        """MOC gerado contém wikilinks para transação/documento/fornecedor."""
        from src.obsidian.sync import gerar_moc_mensal

        moc = gerar_moc_mensal("2026-04", caminho_grafo=grafo_sprint53)
        assert "[[transacao_3" in moc
        assert "[[documento_2" in moc
        assert "[[fornecedor_1" in moc

    def test_moc_mensal_frontmatter_valido(self, grafo_sprint53):
        """MOC começa com frontmatter YAML válido."""
        from src.obsidian.sync import gerar_moc_mensal

        moc = gerar_moc_mensal("2026-04", caminho_grafo=grafo_sprint53)
        assert moc.startswith("---")
        assert "tipo: moc" in moc
        assert 'mes: "2026-04"' in moc
        assert "receita_total:" in moc
        assert "despesa_total:" in moc
        assert "saldo:" in moc

    def test_moc_grafo_ausente_fallback(self, tmp_path):
        """Grafo ausente: MOC mínimo, não crasha."""
        from src.obsidian.sync import gerar_moc_mensal

        inexistente = tmp_path / "nao_existe.sqlite"
        moc = gerar_moc_mensal("2026-04", caminho_grafo=inexistente)
        assert "tipo: moc" in moc
        assert "sem dados" in moc.lower()


class TestRenderizacaoPagina:
    def test_pagina_renderiza_sem_crash_grafo_vazio(self, tmp_path, monkeypatch):
        """Grafo ausente: página mostra callout warning e não crasha.

        Sprint 92c: st.warning virou callout_html em st.markdown.
        """
        from streamlit.testing.v1 import AppTest

        inexistente = tmp_path / "nao_existe.sqlite"
        script = _script_teste(inexistente)
        at = AppTest.from_string(script)
        at.run()
        assert not at.exception
        textos_markdown = " ".join(m.value for m in at.markdown).lower()
        assert "grafo" in textos_markdown

    def test_pagina_renderiza_com_dados_reais(self, grafo_sprint53):
        """Grafo populado: página renderiza hero, selectbox e sem crash."""
        from streamlit.testing.v1 import AppTest

        script = _script_teste(grafo_sprint53)
        at = AppTest.from_string(script)
        at.run()
        assert not at.exception
        markdowns = " ".join(m.value for m in at.markdown)
        # UX-U-03: page-header canônico emite "GRAFO VISUAL + OBSIDIAN" em
        # UPPERCASE (CSS .page-title text-transform: uppercase). Comparação
        # case-insensitive garante presença do título sem acoplar a estilo.
        assert "grafo visual" in markdowns.lower()


class TestIntegracaoDashboard:
    def test_menu_lista_grafo_obsidian(self):
        """O módulo app.py deve declarar a tab 'Grafo + Obsidian'."""
        texto = (RAIZ / "src" / "dashboard" / "app.py").read_text(encoding="utf-8")
        assert '"Grafo + Obsidian"' in texto
        assert "tab_grafo_obsidian" in texto
        assert "grafo_obsidian.renderizar" in texto

    def test_nao_usa_sankey_apenas_bar_charts(self):
        """Invariante do supervisor: Sankey foi substituído por bar charts.

        A página de produção NÃO pode conter go.Sankey. Decisão explícita
        do supervisor no prompt da Sprint 53.
        """
        fonte = (RAIZ / "src" / "dashboard" / "paginas" / "grafo_obsidian.py").read_text(
            encoding="utf-8"
        )
        assert "go.Sankey" not in fonte, "Sankey proibido -- usar bar charts"
        # bar chart é o padrão: go.Bar deve aparecer
        assert "go.Bar" in fonte

    def test_listar_fornecedores_com_id(self, grafo_sprint53):
        """Helper retorna fornecedores ordenados com id + nome."""
        lista = dashboard_dados.listar_fornecedores_com_id()
        assert len(lista) >= 1
        assert all("id" in f and "nome_canonico" in f for f in lista)
        nomes = [f["nome_canonico"] for f in lista]
        assert any("NEOENERGIA" in n for n in nomes)


def _script_teste(caminho_grafo: Path) -> str:
    """Gera script Streamlit que monkey-patcha dados e renderiza a página."""
    return f"""
import sys
from pathlib import Path
RAIZ = Path({str(RAIZ)!r})
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import streamlit as st
from src.dashboard import dados as d
d.CAMINHO_GRAFO = Path({str(caminho_grafo)!r})
d.carregar_subgrafo.clear()
d.obter_fluxo_receita_categoria_fornecedor.clear()

from src.dashboard.paginas import grafo_obsidian
grafo_obsidian.renderizar(periodo="2026-04")
"""


# "Conhecer é conectar." -- Heráclito (parafraseado)
