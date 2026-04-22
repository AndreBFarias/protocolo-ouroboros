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
    def test_dry_run_nao_cria_nada(
        self, vault_sintetico: Path, grafo_rico: Path
    ) -> None:
        report = sr.sincronizar_rico(
            vault_sintetico, grafo_rico, dry_run=True, min_docs_por_fornecedor=2
        )
        assert report.documentos_escritos == 1
        assert not (vault_sintetico / "Pessoal" / "Casal").exists()

    def test_executar_cria_estrutura(
        self, vault_sintetico: Path, grafo_rico: Path
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
        self, vault_sintetico: Path, grafo_rico: Path
    ) -> None:
        """2 execuções consecutivas devem deixar inalteradas >= 1."""
        _ = sr.sincronizar_rico(vault_sintetico, grafo_rico, dry_run=False)
        report2 = sr.sincronizar_rico(vault_sintetico, grafo_rico, dry_run=False)
        assert report2.inalteradas >= 1
        assert report2.documentos_escritos == 0

    def test_edicao_manual_nao_sobrescreve(
        self, vault_sintetico: Path, grafo_rico: Path
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
        self, vault_sintetico: Path, tmp_path: Path
    ) -> None:
        report = sr.sincronizar_rico(
            vault_sintetico, tmp_path / "nao_existe.sqlite", dry_run=False
        )
        assert report.erros
        assert report.documentos_escritos == 0
