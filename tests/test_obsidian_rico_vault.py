"""Testes do sync rico bidirecional (Sprint 71)."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.graph.db import GrafoDB
from src.obsidian import sync_rico as sr

# ============================================================================
# slugify
# ============================================================================


class TestSlugify:
    def test_basico(self) -> None:
        assert sr.slugify("Serviço SOCIAL do Comércio") == "servico-social-do-comercio"

    def test_preserva_hifen_limita_80(self) -> None:
        slug = sr.slugify("a" * 200)
        assert len(slug) == 80

    def test_texto_vazio_fallback(self) -> None:
        assert sr.slugify("") == "sem-nome"

    def test_caracteres_especiais_viram_hifen(self) -> None:
        assert sr.slugify("Sesc / Boleto #42") == "sesc-boleto-42"


# ============================================================================
# YYYY-MM
# ============================================================================


class TestYyyymm:
    def test_data_completa(self) -> None:
        assert sr._yyyymm("2026-03-19") == "2026-03"

    def test_sem_data(self) -> None:
        assert sr._yyyymm(None) == "sem-data"
        assert sr._yyyymm("") == "sem-data"


# ============================================================================
# eh_seguro_sobrescrever
# ============================================================================


class TestEhSeguroSobrescrever:
    def test_nota_nova_e_sempre_segura(self, tmp_path: Path) -> None:
        assert sr.eh_seguro_sobrescrever(tmp_path / "nao_existe.md") is True

    def test_nota_com_tag_e_segura(self, tmp_path: Path) -> None:
        n = tmp_path / "a.md"
        n.write_text("conteudo\n#sincronizado-automaticamente\n", encoding="utf-8")
        assert sr.eh_seguro_sobrescrever(n) is True

    def test_nota_com_frontmatter_true_e_segura(self, tmp_path: Path) -> None:
        n = tmp_path / "b.md"
        n.write_text("---\nsincronizado: true\n---\n\n# corpo\n", encoding="utf-8")
        assert sr.eh_seguro_sobrescrever(n) is True

    def test_nota_editada_manualmente_nao_e_segura(self, tmp_path: Path) -> None:
        n = tmp_path / "c.md"
        n.write_text("---\nsincronizado: false\n---\n\nEditei na mão\n", encoding="utf-8")
        assert sr.eh_seguro_sobrescrever(n) is False

    def test_nota_sem_frontmatter_nem_tag_nao_e_segura(self, tmp_path: Path) -> None:
        n = tmp_path / "d.md"
        n.write_text("Só um parágrafo", encoding="utf-8")
        assert sr.eh_seguro_sobrescrever(n) is False


# ============================================================================
# Render templates
# ============================================================================


class TestRenderDocumento:
    def test_frontmatter_valido(self) -> None:
        meta = {
            "tipo_documento": "boleto_servico",
            "data_emissao": "2026-03-17",
            "fornecedor": "Sesc",
            "total": 103.93,
        }
        md = sr._render_documento(meta, "boleto-sesc-mar")
        assert md.startswith("---\n")
        assert "tipo: documento" in md
        assert "sincronizado: true" in md
        assert "tags: [sincronizado-automaticamente" in md
        assert "valor: 103.93" in md
        assert "#sincronizado-automaticamente" in md  # no corpo também

    def test_valor_formatado_ptbr(self) -> None:
        meta = {"total": 1234.56, "fornecedor": "x", "data_emissao": "2026-01-01"}
        md = sr._render_documento(meta, "doc-x")
        assert "R$ 1.234,56" in md


class TestRenderFornecedor:
    def test_inclui_qtd_e_dataview(self) -> None:
        md = sr._render_fornecedor("Sesc DF", {"categoria": "Lazer"}, 5)
        assert "qtd_documentos: 5" in md
        assert "```dataview" in md
        assert "categoria: Lazer" in md


# ============================================================================
# Idempotência + escrita
# ============================================================================


@pytest.fixture
def vault_sintetico(tmp_path: Path) -> Path:
    vault = tmp_path / "vault"
    vault.mkdir(parents=True)
    return vault


@pytest.fixture
def cache_isolado(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Isola ``.ouroboros/cache/`` para ``tmp_path`` durante o teste.

    Sprint INFRA-TEST-ISOLAR-LAST-SYNC (2026-05-16): testes que invocam
    ``sincronizar_rico(dry_run=False)`` disparam ``_gravar_last_sync``,
    que por default escreve em ``<raiz_repo>/.ouroboros/cache/last_sync.json``.
    Sem este isolamento, o working tree fica dirty após pytest.

    Via ``OUROBOROS_CACHE_DIR`` (lido pelo ``_gravar_last_sync``), aponta
    o destino para ``tmp_path / .ouroboros / cache``.
    """
    cache_dir = tmp_path / ".ouroboros" / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("OUROBOROS_CACHE_DIR", str(cache_dir))
    return cache_dir


@pytest.fixture
def grafo_rico(tmp_path: Path) -> Path:
    g = tmp_path / "grafo.sqlite"
    db = GrafoDB(g)
    db.criar_schema()
    db.upsert_node(
        tipo="documento",
        nome_canonico="boleto-sesc-2026-03",
        metadata={
            "tipo_documento": "boleto_servico",
            "data_emissao": "2026-03-17",
            "fornecedor": "Sesc",
            "total": 103.93,
        },
    )
    db.fechar()
    return g


class TestSincronizarRico:
    def test_dry_run_nao_cria_nada(self, vault_sintetico: Path, grafo_rico: Path) -> None:
        report = sr.sincronizar_rico(
            vault_sintetico, grafo_rico, dry_run=True, min_docs_por_fornecedor=2
        )
        assert report.documentos_escritos == 1
        assert not (vault_sintetico / "Pessoal" / "Casal").exists()

    def test_executar_cria_estrutura(
        self, vault_sintetico: Path, grafo_rico: Path, cache_isolado: Path
    ) -> None:
        report = sr.sincronizar_rico(
            vault_sintetico, grafo_rico, dry_run=False, min_docs_por_fornecedor=2
        )
        fin = vault_sintetico / "Pessoal" / "Casal" / "Financeiro"
        assert fin.exists()
        # Subpastas criadas
        for sub in ("Documentos", "Fornecedores", "Meses", "_Attachments"):
            assert (fin / sub).exists(), f"subpasta {sub} ausente"
        # Nota do documento
        nota = fin / "Documentos" / "2026-03" / "boleto-sesc-2026-03.md"
        assert nota.exists()
        conteudo = nota.read_text(encoding="utf-8")
        assert "sincronizado: true" in conteudo
        assert "valor: 103.93" in conteudo
        assert report.documentos_escritos == 1

    def test_idempotencia(
        self, vault_sintetico: Path, grafo_rico: Path, cache_isolado: Path
    ) -> None:
        """2 execuções consecutivas devem deixar inalteradas >= 1."""
        _ = sr.sincronizar_rico(vault_sintetico, grafo_rico, dry_run=False)
        report2 = sr.sincronizar_rico(vault_sintetico, grafo_rico, dry_run=False)
        assert report2.inalteradas >= 1
        assert report2.documentos_escritos == 0

    def test_edicao_manual_nao_sobrescreve(
        self, vault_sintetico: Path, grafo_rico: Path, cache_isolado: Path
    ) -> None:
        # Primeira rodada cria a nota
        sr.sincronizar_rico(vault_sintetico, grafo_rico, dry_run=False)
        nota = (
            vault_sintetico
            / "Pessoal"
            / "Casal"
            / "Financeiro"
            / "Documentos"
            / "2026-03"
            / "boleto-sesc-2026-03.md"
        )
        # Usuário edita — remove marcadores
        nota.write_text("# minha versao\nzero tag\n", encoding="utf-8")
        # Sync não deve sobrescrever
        report = sr.sincronizar_rico(vault_sintetico, grafo_rico, dry_run=False)
        assert report.notas_preservadas == 1
        assert nota.read_text(encoding="utf-8") == "# minha versao\nzero tag\n"

    def test_grafo_ausente_nao_quebra(
        self, vault_sintetico: Path, tmp_path: Path, cache_isolado: Path
    ) -> None:
        report = sr.sincronizar_rico(vault_sintetico, tmp_path / "nao_existe.sqlite", dry_run=False)
        assert report.erros
        assert report.documentos_escritos == 0


# ============================================================================
# MOC mensal (Sprint 87.6)
# ============================================================================


class _DocFake:
    """Substituto leve de `Node` para testar funções puras."""

    def __init__(
        self,
        nome_canonico: str | None,
        metadata: dict[str, object],
    ) -> None:
        self.nome_canonico = nome_canonico
        self.metadata = metadata


class TestAgregarDocsPorMes:
    def test_lista_vazia_devolve_dict_vazio(self) -> None:
        assert sr._agregar_docs_por_mes([]) == {}

    def test_agrupa_por_mes_ref(self) -> None:
        docs = [
            _DocFake(
                "boleto-a",
                {"data_emissao": "2026-03-05", "fornecedor": "Sesc", "total": 50.0},
            ),
            _DocFake(
                "boleto-b",
                {"data_emissao": "2026-03-22", "fornecedor": "CAESB", "total": 80.0},
            ),
            _DocFake(
                "boleto-c",
                {"data_emissao": "2026-04-10", "fornecedor": "Sesc", "total": 101.60},
            ),
        ]
        agregado = sr._agregar_docs_por_mes(docs)
        assert set(agregado.keys()) == {"2026-03", "2026-04"}
        assert len(agregado["2026-03"]["docs"]) == 2
        assert len(agregado["2026-04"]["docs"]) == 1

    def test_contabiliza_fornecedores_unicos(self) -> None:
        docs = [
            _DocFake(
                "doc-1",
                {"data_emissao": "2026-04-01", "fornecedor": "Sesc", "total": 100.0},
            ),
            _DocFake(
                "doc-2",
                {"data_emissao": "2026-04-15", "fornecedor": "Sesc", "total": 200.0},
            ),
            _DocFake(
                "doc-3",
                {"data_emissao": "2026-04-20", "fornecedor": "CAESB", "total": 80.0},
            ),
        ]
        agregado = sr._agregar_docs_por_mes(docs)
        abril = agregado["2026-04"]
        assert abril["fornecedores"] == {"Sesc", "CAESB"}
        assert len(abril["docs"]) == 3
        assert abril["total"] == pytest.approx(380.0)

    def test_docs_sem_data_vao_para_bucket_sentinela(self) -> None:
        docs = [
            _DocFake("sem-info", {"fornecedor": "X", "total": 10.0}),
        ]
        agregado = sr._agregar_docs_por_mes(docs)
        assert "sem-data" in agregado

    def test_doc_sem_nome_canonico_e_ignorado(self) -> None:
        docs = [
            _DocFake(
                None,
                {"data_emissao": "2026-04-10", "fornecedor": "X", "total": 1.0},
            ),
        ]
        agregado = sr._agregar_docs_por_mes(docs)
        assert agregado == {}


class TestRenderMocMensal:
    def _agregado_exemplo(self) -> dict[str, object]:
        docs = [
            _DocFake(
                "boleto-sesc-abril",
                {
                    "data_emissao": "2026-04-10",
                    "tipo_documento": "boleto_servico",
                    "fornecedor": "Sesc",
                    "total": 101.60,
                },
            ),
            _DocFake(
                "fatura-caesb-abril",
                {
                    "data_emissao": "2026-04-22",
                    "tipo_documento": "fatura_agua",
                    "fornecedor": "CAESB",
                    "total": 230.33,
                },
            ),
        ]
        return {
            "docs": docs,
            "fornecedores": {"Sesc", "CAESB"},
            "total": 331.93,
        }

    def test_contem_frontmatter(self) -> None:
        md = sr._render_moc_mensal("2026-04", self._agregado_exemplo())
        assert md.startswith("---\n")
        assert "tipo: moc" in md
        assert 'mes: "2026-04"' in md
        assert "sincronizado: true" in md
        assert "total_documentos: 2" in md
        assert "total_fornecedores: 2" in md
        assert "total_valor: 331.93" in md

    def test_contem_dataview_query(self) -> None:
        md = sr._render_moc_mensal("2026-04", self._agregado_exemplo())
        assert "```dataview" in md
        assert "FROM " in md
        assert '"Pessoal/Casal/Financeiro/Documentos/2026-04"' in md

    def test_lista_docs_em_tabela(self) -> None:
        md = sr._render_moc_mensal("2026-04", self._agregado_exemplo())
        # Cabeçalho de tabela
        assert "| Data | Tipo | Fornecedor | Valor | Nota |" in md
        # Linhas dos docs
        assert "2026-04-10" in md
        assert "2026-04-22" in md
        assert "boleto_servico" in md
        assert "R$ 101,60" in md
        assert "R$ 230,33" in md
        # Lista de fornecedores únicos com wikilink
        assert "[[Fornecedores/sesc|Sesc]]" in md
        assert "[[Fornecedores/caesb|CAESB]]" in md
        # Título humano em PT-BR
        assert "# Abril 2026" in md


@pytest.fixture
def grafo_multi_mes(tmp_path: Path) -> Path:
    g = tmp_path / "grafo_multi.sqlite"
    db = GrafoDB(g)
    db.criar_schema()
    db.upsert_node(
        tipo="documento",
        nome_canonico="boleto-sesc-mar-2026",
        metadata={
            "tipo_documento": "boleto_servico",
            "data_emissao": "2026-03-15",
            "fornecedor": "Sesc",
            "total": 98.50,
        },
    )
    db.upsert_node(
        tipo="documento",
        nome_canonico="boleto-sesc-abr-2026",
        metadata={
            "tipo_documento": "boleto_servico",
            "data_emissao": "2026-04-10",
            "fornecedor": "Sesc",
            "total": 101.60,
        },
    )
    db.fechar()
    return g


class TestSincronizarRicoMoc:
    def test_executar_gera_arquivos_meses(
        self, vault_sintetico: Path, grafo_multi_mes: Path, cache_isolado: Path
    ) -> None:
        report = sr.sincronizar_rico(vault_sintetico, grafo_multi_mes, dry_run=False)
        fin = vault_sintetico / "Pessoal" / "Casal" / "Financeiro"
        moc_mar = fin / "Meses" / "2026-03.md"
        moc_abr = fin / "Meses" / "2026-04.md"
        assert moc_mar.exists(), "MOC de março ausente"
        assert moc_abr.exists(), "MOC de abril ausente"
        assert report.mocs_gerados == 2

        conteudo_mar = moc_mar.read_text(encoding="utf-8")
        assert "tipo: moc" in conteudo_mar
        assert 'mes: "2026-03"' in conteudo_mar
        assert "Sesc" in conteudo_mar

    def test_soberania_preserva_moc_sem_tag(
        self, vault_sintetico: Path, grafo_multi_mes: Path, cache_isolado: Path
    ) -> None:
        """MOC editada manualmente (sem tag/frontmatter) não deve ser reescrita."""
        sr.sincronizar_rico(vault_sintetico, grafo_multi_mes, dry_run=False)
        moc_abr = vault_sintetico / "Pessoal" / "Casal" / "Financeiro" / "Meses" / "2026-04.md"
        # Usuário sobrescreve na mão, remove todos os marcadores
        moc_abr.write_text("# Abril — edição manual\n\nConteúdo humano\n", encoding="utf-8")
        report = sr.sincronizar_rico(vault_sintetico, grafo_multi_mes, dry_run=False)
        assert report.notas_preservadas >= 1
        assert moc_abr.read_text(encoding="utf-8") == "# Abril — edição manual\n\nConteúdo humano\n"


# ============================================================================
# _contar_docs_do_fornecedor (Sprint 87c)
# ============================================================================


class TestContarDocsDoFornecedor:
    def test_retorna_zero_quando_forn_id_none(self, tmp_path: Path) -> None:
        db = GrafoDB(tmp_path / "grafo.sqlite")
        db.criar_schema()
        assert sr._contar_docs_do_fornecedor(db, None) == 0
        db.fechar()

    def test_retorna_zero_quando_fornecedor_sem_documentos(self, tmp_path: Path) -> None:
        db = GrafoDB(tmp_path / "grafo.sqlite")
        db.criar_schema()
        forn_id = db.upsert_node("fornecedor", "SESC", metadata={"cnpj": "03288908000130"})
        assert sr._contar_docs_do_fornecedor(db, forn_id) == 0
        db.fechar()

    def test_contar_docs_do_fornecedor_retorna_contagem_real(self, tmp_path: Path) -> None:
        """Sprint 87c: bug silencioso pré-fix retornava 0 sempre.

        Cenário: 3 documentos distintos com aresta `fornecido_por` apontando
        para o mesmo fornecedor. A função deve retornar 3, não 0.
        """
        db = GrafoDB(tmp_path / "grafo.sqlite")
        db.criar_schema()
        forn_id = db.upsert_node("fornecedor", "SESC", metadata={"cnpj": "03288908000130"})
        for i in range(3):
            doc_id = db.upsert_node(
                "documento",
                f"BOLETO-{i}",
                metadata={
                    "tipo_documento": "boleto_servico",
                    "data_emissao": f"2026-0{i + 1}-15",
                },
            )
            db.adicionar_edge(doc_id, forn_id, "fornecido_por")

        assert sr._contar_docs_do_fornecedor(db, forn_id) == 3
        db.fechar()

    def test_ignora_arestas_de_outros_tipos(self, tmp_path: Path) -> None:
        """Apenas `fornecido_por` deve contar, não qualquer aresta para o fornecedor."""
        db = GrafoDB(tmp_path / "grafo.sqlite")
        db.criar_schema()
        forn_id = db.upsert_node("fornecedor", "SESC")
        doc_id = db.upsert_node(
            "documento",
            "BOLETO-A",
            metadata={"tipo_documento": "boleto_servico"},
        )
        outro_id = db.upsert_node("fornecedor", "OUTRO")
        db.adicionar_edge(doc_id, forn_id, "fornecido_por")
        db.adicionar_edge(outro_id, forn_id, "ocorre_em")  # tipo diferente, ignorar

        assert sr._contar_docs_do_fornecedor(db, forn_id) == 1
        db.fechar()
