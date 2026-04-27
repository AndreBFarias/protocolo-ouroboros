"""Testes da Sprint 59 -- fix chips de sugestão na Busca Global.

Cobertura focada nos acceptance criteria da Sprint 59:

1. Clicar no chip "neoenergia" popula `st.session_state["busca_termo_input"]`
   com o valor correto (contrato do callback `_aplicar_chip_sugestao`).
2. O `st.text_input` lê o valor de `st.session_state["busca_termo_input"]`
   -- keys casam (invariante N-para-N com o callback).
3. Busca executa e retorna resultados quando termo vem do chip.
4. Título da página NÃO contém o prefixo "52" (sincroniza com Sprint 63).
5. Chips NÃO ficam `disabled=True` (regressão da Sprint 52).

Complementa `test_dashboard_busca.py` (Sprint 52), que cobre o helper
`buscar_global` e a renderização geral. Aqui focamos no chip → input → busca.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from src.dashboard import dados as dashboard_dados
from src.dashboard.paginas import busca as pagina_busca

RAIZ = Path(__file__).resolve().parents[1]


@pytest.fixture()
def grafo_minimo(tmp_path, monkeypatch):
    """Grafo com um fornecedor 'NEOENERGIA' para validar busca ponta-a-ponta."""
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
    conn.execute(
        "INSERT INTO node (id, tipo, nome_canonico, metadata) "
        "VALUES (1, 'fornecedor', 'NEOENERGIA DISTRIBUICAO BRASILIA', "
        '\'{"cnpj": "00.394.460/0058-87", "categoria": "Energia"}\')'
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(dashboard_dados, "CAMINHO_GRAFO", destino)
    dashboard_dados.buscar_global.clear()
    return destino


class TestChipSugestaoCallback:
    """Sprint 59 acceptance #1: chip popula session_state com o termo."""

    def test_callback_aplicar_chip_existe_e_e_chamavel(self):
        assert callable(pagina_busca._aplicar_chip_sugestao)

    def test_callback_seta_session_state_com_valor(self, monkeypatch):
        """Callback deve gravar o valor recebido em `busca_termo_input`."""
        estado: dict[str, str] = {}
        # monkeypatcha st.session_state dentro do módulo da página para um dict
        import streamlit as st

        class FakeSessionState(dict):
            def __getattr__(self, item):
                try:
                    return self[item]
                except KeyError as exc:
                    raise AttributeError(item) from exc

            def __setattr__(self, item, value):
                self[item] = value

        fake = FakeSessionState()
        monkeypatch.setattr(st, "session_state", fake)

        pagina_busca._aplicar_chip_sugestao("neoenergia")
        assert fake["busca_termo_input"] == "neoenergia"

        pagina_busca._aplicar_chip_sugestao("farmácia")
        assert fake["busca_termo_input"] == "farmácia"
        # documento sobrescreve -- contrato esperado
        _ = estado


class TestChipsNaoDisabled:
    """Sprint 59 acceptance #4 (regressão Sprint 52): chips clicáveis."""

    def test_codigo_nao_passa_disabled_true_aos_chips(self):
        """Lê o fonte e garante que `disabled=True` foi removido dos chips."""
        fonte = (RAIZ / "src" / "dashboard" / "paginas" / "busca.py").read_text(encoding="utf-8")
        # a função canônica de chips não pode ter disabled=True ativo
        idx_loop = fonte.find("for idx, (col, sug) in enumerate")
        assert idx_loop > 0, "laço dos chips não encontrado"
        trecho = fonte[idx_loop : idx_loop + 600]
        assert "disabled=True" not in trecho, "chips não podem estar desabilitados -- Sprint 59"

    def test_chips_declaram_on_click_com_callback(self):
        """Fonte deve referenciar `_aplicar_chip_sugestao` como `on_click`."""
        fonte = (RAIZ / "src" / "dashboard" / "paginas" / "busca.py").read_text(encoding="utf-8")
        assert "on_click=_aplicar_chip_sugestao" in fonte


class TestKeyCasaComSessionState:
    """Sprint 59 acceptance #2: key do text_input = chave do session_state."""

    def test_text_input_usa_key_busca_termo_input(self):
        fonte = (RAIZ / "src" / "dashboard" / "paginas" / "busca.py").read_text(encoding="utf-8")
        assert 'key="busca_termo_input"' in fonte

    def test_callback_grava_na_mesma_key(self):
        """N-para-N: a chave escrita pelo callback precisa casar com a key do widget."""
        import inspect

        src = inspect.getsource(pagina_busca._aplicar_chip_sugestao)
        assert '"busca_termo_input"' in src


class TestTituloSemPrefixoSprint:
    """Sprint 59 acceptance #3: remover '52' do título."""

    def test_hero_nao_recebe_52(self):
        fonte = (RAIZ / "src" / "dashboard" / "paginas" / "busca.py").read_text(encoding="utf-8")
        # hero_titulo_html recebe "" como primeiro argumento
        assert 'hero_titulo_html(\n            "",\n            "Busca Global"' in fonte
        # e NÃO deve estar chamando com "52" literal
        assert 'hero_titulo_html(\n            "52"' not in fonte


class TestChipDisparaBuscaPontaAPonta:
    """Sprint 59 acceptance #1: fluxo completo chip → input → busca."""

    def test_injecao_via_session_state_dispara_busca(
        self, grafo_minimo, monkeypatch, tmp_path
    ):
        """Simula o chip: session_state['busca_termo_input'] = 'neoenergia'
        → renderiza página → resultados aparecem.
        """
        from streamlit.testing.v1 import AppTest

        # UX-124: tabela inline chama `carregar_dados()`. Patch via fixture
        # `monkeypatch` (com teardown automático) redireciona o XLSX para um
        # path inexistente para que `carregar_dados()` retorne {} rapidamente
        # (evita carregar o XLSX real ~5MB no AppTest e contaminar globais).
        xlsx_falso = tmp_path / "_inexistente.xlsx"
        monkeypatch.setattr(dashboard_dados, "CAMINHO_XLSX", xlsx_falso)
        dashboard_dados.carregar_dados.clear()

        script = f"""
import sys
from pathlib import Path
RAIZ = Path({str(RAIZ)!r})
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import streamlit as st
from src.dashboard import dados as d
d.CAMINHO_GRAFO = Path({str(grafo_minimo)!r})
d.CAMINHO_XLSX = Path({str(xlsx_falso)!r})
d.buscar_global.clear()
d.carregar_dados.clear()

# Simula o efeito do clique no chip "neoenergia":
# o callback `_aplicar_chip_sugestao` grava aqui antes do render.
st.session_state["busca_termo_input"] = "neoenergia"

from src.dashboard.paginas import busca
busca.renderizar()
"""
        at = AppTest.from_string(script)
        at.run()
        assert not at.exception
        # o fornecedor deve aparecer em algum markdown renderizado
        markdowns = " ".join(m.value for m in at.markdown)
        assert "NEOENERGIA" in markdowns
        # e o título NÃO deve conter o prefixo "52"
        assert ">52<" not in markdowns


# "Clicar e nada acontecer é pior que não ter botão." -- princípio de UX
