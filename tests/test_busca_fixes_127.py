"""Testes regressivos da Sprint UX-127 -- 4 fixes finais na Busca Global.

Cobre:

- AC1: media query @max-width:700px no `css_global()` garante que o
  input de busca da sidebar não corte em viewport estreito.
- AC2: dropdown 'Tipo de busca' removido de `paginas/busca.py`. Constantes
  e helper `_filtrar_por_tipo_dropdown` permanecem (compatibilidade com
  testes regressivos antigos), mas o widget `st.selectbox` foi excluído
  e a função `_renderizar_controles` agora retorna `str` em vez de
  `tuple[str, str]`.
- AC3: bug "Documentos (0)" sempre. `_docs_vinculados_a_fornecedor`
  segue edge `fornecido_por` no grafo SQLite e retorna >= 1 quando o
  fornecedor tem documentos vinculados; `_mesclar_docs_dedup` preserva
  ids existentes e adiciona apenas extras inexistentes.
- AC4: nenhum botão "Ir para X" / `st.link_button` / `st.switch_page`
  em `paginas/busca.py`. `kind='aba'` mostra mensagem inline sem
  navegação automática; `kind='fornecedor'` já usa tabela inline
  (UX-124).
"""

from __future__ import annotations

import inspect
import re
import sqlite3
from pathlib import Path

import pytest

from src.dashboard import tema
from src.dashboard.paginas import busca as pag


class TestBuscaFixes127:
    """Bateria de regressivos para Sprint UX-127."""

    # -----------------------------------------------------------------
    # AC1 -- media query no css_global
    # -----------------------------------------------------------------

    def test_ac1_media_query_700px_existe(self) -> None:
        """`css_global()` declara @media (max-width: 700px) com regra
        que garante width: 100% e box-sizing: border-box no input de
        busca da sidebar.
        """
        css = tema.css_global()
        # Existe a media query com BREAKPOINT_MINIMO (700).
        assert "@media (max-width: 700px)" in css
        # Dentro da media query, há regra para o input da sidebar.
        bloco_700 = css.split("@media (max-width: 700px)", 1)[1]
        # Pegar bloco até próximo @media ou final.
        if "@media" in bloco_700[1:]:
            bloco_700 = bloco_700[: bloco_700.index("@media", 1)]
        assert "stSidebar" in bloco_700
        assert "stTextInput" in bloco_700
        assert "width: 100%" in bloco_700
        assert "box-sizing: border-box" in bloco_700

    # -----------------------------------------------------------------
    # AC2 -- dropdown 'Tipo de busca' removido
    # -----------------------------------------------------------------

    def test_ac2_selectbox_tipo_de_busca_removido(self) -> None:
        """Nenhum `st.selectbox(...Tipo de busca...)` na página."""
        codigo = inspect.getsource(pag)
        # Padrão canônico do widget; se aparecer, AC2 falha.
        assert re.search(r"st\.selectbox\([^)]*Tipo de busca", codigo) is None, (
            "st.selectbox('Tipo de busca', ...) deve ter sido removido"
        )

    def test_ac2_renderizar_controles_retorna_string(self) -> None:
        """`_renderizar_controles` agora retorna `str` (só o termo)."""
        sig = inspect.signature(pag._renderizar_controles)
        # Annotation pode vir como str literal (PEP 563/from __future__).
        anota = sig.return_annotation
        anota_str = anota if isinstance(anota, str) else getattr(anota, "__name__", str(anota))
        assert "tuple" not in anota_str.lower()
        assert anota_str == "str"

    def test_ac2_constantes_preservadas_para_compat(self) -> None:
        """Constantes auxiliares preservadas (testes antigos dependem)."""
        # Não removemos as constantes -- só o widget. Garantimos N-para-N.
        assert hasattr(pag, "OPCOES_DROPDOWN_TIPO")
        assert "Todos" in pag.OPCOES_DROPDOWN_TIPO
        assert hasattr(pag, "_filtrar_por_tipo_dropdown")

    # -----------------------------------------------------------------
    # AC3 -- contagem 'Documentos (N)' correta
    # -----------------------------------------------------------------

    def test_ac3_docs_vinculados_helper_existe(self) -> None:
        """Helper `_docs_vinculados_a_fornecedor` adicionado."""
        assert hasattr(pag, "_docs_vinculados_a_fornecedor")
        assert callable(pag._docs_vinculados_a_fornecedor)

    def test_ac3_docs_vinculados_grafo_inexistente_devolve_vazio(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Quando grafo não existe, devolve [] sem estourar."""
        monkeypatch.setattr(pag._dados, "CAMINHO_GRAFO", tmp_path / "fake.sqlite")
        saida = pag._docs_vinculados_a_fornecedor("Neoenergia")
        assert saida == []

    def test_ac3_docs_vinculados_match_via_edge(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Fixture: fornecedor com 2 docs vinculados via `fornecido_por`.

        Garante que retornamos N=2 quando o nome humano só existe no
        nome_canonico do fornecedor (não nos documentos). Reproduz o
        bug AC3 e verifica o fix.
        """
        db = tmp_path / "grafo_fixture.sqlite"
        conn = sqlite3.connect(db)
        conn.executescript(
            """
            CREATE TABLE node (
                id INTEGER PRIMARY KEY,
                tipo TEXT NOT NULL,
                nome_canonico TEXT,
                aliases TEXT,
                metadata TEXT
            );
            CREATE TABLE edge (
                src_id INTEGER NOT NULL,
                dst_id INTEGER NOT NULL,
                tipo TEXT NOT NULL
            );
            INSERT INTO node (id, tipo, nome_canonico, aliases, metadata) VALUES
                (1, 'fornecedor', 'NEOENERGIA DISTRIBUICAO BRASILIA',
                 '["NEO ENERGIA"]', '{"cnpj":"12.345.678/0001-99"}'),
                (10, 'documento', '00190000090281932500817390075178114740000012700',
                 NULL, '{"tipo_documento":"boleto_servico","total":250.00}'),
                (11, 'documento', '00190000090281932500817390074171414430000012700',
                 NULL, '{"tipo_documento":"boleto_servico","total":180.50}'),
                (99, 'documento', 'OUTRO_BOLETO_NAO_LIGADO',
                 NULL, '{"tipo_documento":"boleto_servico","total":42.00}');
            INSERT INTO edge (src_id, dst_id, tipo) VALUES
                (10, 1, 'fornecido_por'),
                (11, 1, 'fornecido_por');
            """
        )
        conn.commit()
        conn.close()

        monkeypatch.setattr(pag._dados, "CAMINHO_GRAFO", db)

        saida = pag._docs_vinculados_a_fornecedor("neoenergia")
        ids = sorted(d["id"] for d in saida)
        assert ids == [10, 11], (
            "AC3: 2 docs vinculados via edge `fornecido_por` -- valor "
            f"observado={ids} (esperado [10, 11])"
        )
        # Confere que os campos canônicos estão no formato esperado por
        # `_renderizar_tabela_documentos` (mesmas chaves de
        # `_buscar_documentos`).
        assert all("nome_canonico" in d and "tipo_documento" in d for d in saida)

    def test_ac3_mesclar_docs_dedup_preserva_ordem_e_remove_duplicatas(self) -> None:
        """`_mesclar_docs_dedup`: base primeiro, extras únicos depois."""
        base = [{"id": 1, "nome_canonico": "A"}, {"id": 2, "nome_canonico": "B"}]
        extras = [
            {"id": 2, "nome_canonico": "B-dup"},  # já em base, ignora
            {"id": 3, "nome_canonico": "C"},  # novo, adiciona
        ]
        saida = pag._mesclar_docs_dedup(base, extras)
        assert [d["id"] for d in saida] == [1, 2, 3]
        # Preservou o item original do `base` (não sobrescreveu).
        assert saida[1]["nome_canonico"] == "B"

    # -----------------------------------------------------------------
    # AC4 -- nenhum botão de navegação para outras abas
    # -----------------------------------------------------------------

    def test_ac4_zero_botoes_navegacao_em_busca_py(self) -> None:
        """grep canônico: 0 matches de `link_button` / `switch_page`
        em código executável.

        Permite ocorrências em docstrings/comentários (registro
        histórico do refactor), mas nenhum widget vivo.
        """
        codigo = inspect.getsource(pag)
        for padrao in (
            r"st\.link_button\(",
            r"st\.switch_page\(",
        ):
            assert re.search(padrao, codigo) is None, (
                f"Padrão '{padrao}' encontrado em busca.py: violação do AC4"
            )

        # `st.button("Ir para X", ...)` em runtime também viola.
        # Captura st.button em qualquer linha que não seja docstring/comentário.
        for linha in codigo.splitlines():
            stripped = linha.strip()
            if stripped.startswith("#") or stripped.startswith('"'):
                continue
            assert "Ir para aba" not in stripped or "st.button" not in stripped, (
                f"Linha viola AC4 (botão 'Ir para aba'): {linha!r}"
            )

    def test_ac4_renderizar_rota_aba_nao_chama_st_button(self) -> None:
        """Inspeciona `_renderizar_rota_rapida`: ramo `kind='aba'`
        não deve invocar `st.button`/`st.query_params.from_dict`/`st.rerun`
        em código executável (comentários são permitidos).
        """
        codigo = inspect.getsource(pag._renderizar_rota_rapida)
        ini_aba = codigo.index('kind == "aba"')
        fim_aba = codigo.index('elif kind == "fornecedor"', ini_aba)
        bloco_aba = codigo[ini_aba:fim_aba]
        # Filtra comentários e docstrings (linhas que começam com '#').
        linhas_executaveis = [
            ln for ln in bloco_aba.splitlines() if not ln.lstrip().startswith("#")
        ]
        bloco_executavel = "\n".join(linhas_executaveis)
        assert "st.button" not in bloco_executavel
        assert "st.rerun" not in bloco_executavel
        assert "from_dict" not in bloco_executavel


# "O honesto reconhece o limite do widget que não funciona." -- princípio do filtro real
