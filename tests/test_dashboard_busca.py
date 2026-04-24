"""Testes da página Busca Global (Sprint 52).

Cobre:
- Helper `buscar_global` em cenários: grafo ausente, grafo vazio, fixture
  com fornecedor + documento + transação + item, grafo de produção (read-only).
- Retorno sempre com 4 chaves (fornecedores, documentos, transacoes, itens).  # noqa: accent
- Busca por substring da razão social casando fornecedor.
- Busca por CNPJ (substring) casando fornecedor.
- Renderização Streamlit via AppTest: input vazio, termo sem resultado,
  termo com resultado.
- Presença do `text_input` ANTES de qualquer `subtitulo_secao_html`
  (invariante: input é permanente no topo).
- Registro da tab "Busca Global" no menu lateral.

Todos os testes que tocam o grafo de produção são READ-ONLY.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from src.dashboard import dados as dashboard_dados

RAIZ = Path(__file__).resolve().parents[1]
GRAFO_PROD = RAIZ / "data" / "output" / "grafo.sqlite"


@pytest.fixture()
def grafo_busca(tmp_path, monkeypatch):
    """Grafo pequeno com fornecedor, documento, transação e item vinculados."""
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
    # fornecedor -- razão social tem "NEOENERGIA"
    conn.execute(
        "INSERT INTO node (id, tipo, nome_canonico, aliases, metadata) "
        "VALUES (?, ?, ?, ?, ?)",
        (
            1,
            "fornecedor",
            "NEOENERGIA DISTRIBUICAO BRASILIA",
            '["NEOENERGIA DF", "CEB-DIS"]',
            '{"cnpj": "00.394.460/0058-87", "categoria": "Energia"}',
        ),
    )
    # documento ligado ao fornecedor
    conn.execute(
        "INSERT INTO node (id, tipo, nome_canonico, metadata) "
        "VALUES (?, ?, ?, ?)",
        (
            2,
            "documento",
            "fatura_neoenergia_2026_04",
            '{"tipo_documento": "fatura_energia", '
            '"razao_social": "Neoenergia Brasília", '
            '"data_emissao": "2026-04-08", "total": 487.23}',
        ),
    )
    # transação ligada ao fornecedor
    conn.execute(
        "INSERT INTO node (id, tipo, nome_canonico, metadata) "
        "VALUES (?, ?, ?, ?)",
        (
            3,
            "transacao",
            "tx_neo_2026_04",
            '{"data": "2026-04-09", "local": "NEOENERGIA DF", '
            '"valor": 487.23, "banco": "Itaú", "tipo": "Despesa"}',
        ),
    )
    # item que menciona energia
    conn.execute(
        "INSERT INTO node (id, tipo, nome_canonico, metadata) "
        "VALUES (?, ?, ?, ?)",
        (
            4,
            "item",
            "energia_eletrica_residencial",
            '{"descricao": "Energia elétrica residencial (kWh)", '
            '"data_compra": "2026-04-08", "valor_total": 450.10, "qtde": 1}',
        ),
    )
    # fornecedor que NÃO casa com termo "neoenergia"
    conn.execute(
        "INSERT INTO node (id, tipo, nome_canonico, metadata) "
        "VALUES (?, ?, ?, ?)",
        (
            5,
            "fornecedor",
            "PADARIA KI-SABOR",
            '{"categoria": "Alimentação"}',
        ),
    )
    # arestas fornecido_por: doc→fornecedor e tx→fornecedor
    conn.execute(
        "INSERT INTO edge (src_id, dst_id, tipo) VALUES (?, ?, 'fornecido_por')",
        (2, 1),
    )
    conn.execute(
        "INSERT INTO edge (src_id, dst_id, tipo) VALUES (?, ?, 'fornecido_por')",
        (3, 1),
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(dashboard_dados, "CAMINHO_GRAFO", destino)
    dashboard_dados.buscar_global.clear()
    return destino


class TestBuscarGlobal:
    def test_retorna_quatro_secoes_vazias_quando_grafo_ausente(
        self, tmp_path, monkeypatch
    ):
        inexistente = tmp_path / "nao_existe.sqlite"
        monkeypatch.setattr(dashboard_dados, "CAMINHO_GRAFO", inexistente)
        dashboard_dados.buscar_global.clear()

        resultado = dashboard_dados.buscar_global("qualquer coisa")
        assert set(resultado.keys()) == {
            "fornecedores",
            "documentos",
            "transacoes",
            "itens",
        }
        for valor in resultado.values():
            assert valor == []

    def test_termo_vazio_retorna_listas_vazias(self, grafo_busca):
        resultado = dashboard_dados.buscar_global("")
        assert set(resultado.keys()) == {
            "fornecedores",
            "documentos",
            "transacoes",
            "itens",
        }
        assert all(v == [] for v in resultado.values())

    def test_buscar_global_retorna_4_secoes(self, grafo_busca):
        """Contrato explícito: sempre 4 chaves, independente do termo."""
        resultado = dashboard_dados.buscar_global("neoenergia")
        assert set(resultado.keys()) == {
            "fornecedores",
            "documentos",
            "transacoes",
            "itens",
        }

    def test_busca_por_substring_razao_social(self, grafo_busca):
        """Substring da razão social deve casar o fornecedor."""
        resultado = dashboard_dados.buscar_global("neoenergia")
        nomes = [f["nome_canonico"] for f in resultado["fornecedores"]]
        assert any("NEOENERGIA" in n for n in nomes)
        # fornecedor distinto NÃO deve aparecer
        assert not any("KI-SABOR" in n for n in nomes)

    def test_busca_por_cnpj_casa_fornecedor(self, grafo_busca):
        """CNPJ presente no metadata deve retornar o fornecedor."""
        resultado = dashboard_dados.buscar_global("00.394.460")
        nomes = [f["nome_canonico"] for f in resultado["fornecedores"]]
        assert any("NEOENERGIA" in n for n in nomes)

    def test_busca_case_insensitive(self, grafo_busca):
        """Maiúsculo e minúsculo devem retornar o mesmo resultado."""
        dashboard_dados.buscar_global.clear()
        r1 = dashboard_dados.buscar_global("neoenergia")
        dashboard_dados.buscar_global.clear()
        r2 = dashboard_dados.buscar_global("NEOENERGIA")
        assert len(r1["fornecedores"]) == len(r2["fornecedores"])

    def test_agregados_fornecedor_contam_documentos_e_transacoes(
        self, grafo_busca
    ):
        """Fornecedor retornado deve carregar agregados (docs + total)."""
        resultado = dashboard_dados.buscar_global("neoenergia")
        forn = resultado["fornecedores"][0]
        assert forn["total_documentos"] == 1
        # transação tem valor 487.23
        assert forn["total_gasto"] == pytest.approx(487.23, abs=0.01)

    def test_busca_transacao_por_local(self, grafo_busca):
        """Transação com local 'NEOENERGIA DF' deve casar."""
        resultado = dashboard_dados.buscar_global("neoenergia")
        assert len(resultado["transacoes"]) >= 1
        primeira = resultado["transacoes"][0]
        assert "data" in primeira
        assert "valor" in primeira
        assert "local" in primeira

    def test_busca_item_por_descricao(self, grafo_busca):
        """Item com descrição 'Energia elétrica' casa busca por 'energia'."""
        resultado = dashboard_dados.buscar_global("energia")
        descricoes = [i["descricao"] for i in resultado["itens"]]
        assert any("Energia" in d for d in descricoes)

    def test_termo_sem_match_retorna_listas_vazias(self, grafo_busca):
        resultado = dashboard_dados.buscar_global("xyzzy_inexistente")
        assert resultado["fornecedores"] == []
        assert resultado["documentos"] == []
        assert resultado["transacoes"] == []
        assert resultado["itens"] == []

    @pytest.mark.skipif(
        not GRAFO_PROD.exists(),
        reason="Grafo de produção não disponível neste ambiente",
    )
    def test_busca_no_grafo_producao_read_only(self):
        """Read-only sobre grafo real: busca não pode mutar arquivo."""
        tamanho_antes = GRAFO_PROD.stat().st_size
        dashboard_dados.buscar_global.clear()
        resultado = dashboard_dados.buscar_global("neoenergia")
        tamanho_depois = GRAFO_PROD.stat().st_size
        assert tamanho_antes == tamanho_depois
        assert set(resultado.keys()) == {
            "fornecedores",
            "documentos",
            "transacoes",
            "itens",
        }


class TestRenderizacaoStreamlit:
    """Testes de renderização usando streamlit.testing.v1.AppTest."""

    def test_pagina_renderiza_com_input_vazio(self, grafo_busca):
        """Sem termo: input e chips aparecem, resultados não.

        Sprint 92c: st.info foi substituido por callout_html em st.markdown;
        o texto agora vive em at.markdown com o HTML do callout.
        """
        from streamlit.testing.v1 import AppTest

        script = _script_teste_busca(grafo_busca, termo_inicial="")
        at = AppTest.from_string(script)
        at.run()
        assert not at.exception
        # text_input presente (input permanente no topo)
        assert len(at.text_input) >= 1
        # Com termo vazio, deve mostrar callout pedindo para digitar.
        textos_markdown = " ".join(m.value for m in at.markdown).lower()
        assert "digite" in textos_markdown or "sugest" in textos_markdown

    def test_pagina_renderiza_com_termo_sem_resultado(self, grafo_busca):
        """Termo sem match: callout 'nenhum resultado', sem crash.

        Sprint 92c: st.info virou callout_html em st.markdown.
        """
        from streamlit.testing.v1 import AppTest

        script = _script_teste_busca(grafo_busca, termo_inicial="xyzzy_xyz")
        at = AppTest.from_string(script)
        at.run()
        assert not at.exception
        textos_markdown = " ".join(m.value for m in at.markdown).lower()
        assert "nenhum" in textos_markdown

    def test_pagina_renderiza_com_termo_que_casa(self, grafo_busca):
        """Termo que casa: fornecedor aparece em markdown, sem crash."""
        from streamlit.testing.v1 import AppTest

        script = _script_teste_busca(grafo_busca, termo_inicial="neoenergia")
        at = AppTest.from_string(script)
        at.run()
        assert not at.exception
        markdowns = " ".join(m.value for m in at.markdown)
        # hero com "Busca Global" sempre presente
        assert "Busca Global" in markdowns
        # fornecedor renderizado
        assert "NEOENERGIA" in markdowns

    def test_pagina_renderiza_com_grafo_ausente(self, tmp_path, monkeypatch):
        """Grafo ausente: callout warning, não crasha.

        Sprint 92c: st.warning virou callout_html em st.markdown.
        """
        from streamlit.testing.v1 import AppTest

        inexistente = tmp_path / "nao_existe.sqlite"
        script = _script_teste_busca(inexistente, termo_inicial="")
        at = AppTest.from_string(script)
        at.run()
        assert not at.exception
        textos_markdown = " ".join(m.value for m in at.markdown).lower()
        assert "grafo" in textos_markdown

    def test_input_permanente_no_topo(self, grafo_busca):
        """Invariante: text_input aparece ANTES de qualquer resultado.

        Lê o código-fonte da página para garantir que `st.text_input` é
        invocado antes de qualquer `subtitulo_secao_html` que renderize
        seção de resultados. Decisão explícita do supervisor: input é
        permanente no topo, não modal.
        """
        fonte = (
            RAIZ / "src" / "dashboard" / "paginas" / "busca.py"
        ).read_text(encoding="utf-8")
        idx_input = fonte.find("st.text_input")
        idx_fornecedores = fonte.find('"Fornecedores encontrados')
        idx_timeline = fonte.find('"Timeline')
        idx_documentos = fonte.find('f"Documentos (')
        assert idx_input > 0, "text_input não encontrado no código"
        assert idx_input < idx_fornecedores
        assert idx_input < idx_timeline
        assert idx_input < idx_documentos


class TestMenuLateral:
    def test_menu_lista_busca_global(self):
        """O módulo app.py deve declarar a tab 'Busca Global' no st.tabs."""
        texto = (RAIZ / "src" / "dashboard" / "app.py").read_text(encoding="utf-8")
        assert '"Busca Global"' in texto
        assert "tab_busca" in texto
        assert "busca.renderizar" in texto


def _script_teste_busca(caminho_grafo: Path, termo_inicial: str = "") -> str:
    """Gera script Streamlit que monkey-patcha dados e renderiza busca."""
    return f"""
import sys
from pathlib import Path
RAIZ = Path({str(RAIZ)!r})
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import streamlit as st
from src.dashboard import dados as d
d.CAMINHO_GRAFO = Path({str(caminho_grafo)!r})
d.buscar_global.clear()

# injeta termo inicial via session_state ANTES do widget
st.session_state["busca_termo_input"] = {termo_inicial!r}

from src.dashboard.paginas import busca
busca.renderizar()
"""


# "O teste é a diferença entre acreditar e saber." -- princípio empirista
