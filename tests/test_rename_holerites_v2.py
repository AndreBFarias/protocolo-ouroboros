"""Testes da Sprint INFRA-RENAME-HOLERITES.

Cobre o renomeador legível ``scripts/renomear_holerites_v2.py``:

- template gera nome esperado quando metadata é completo;
- fallback determinístico quando parser não casa;
- idempotência (2a rodada após --executar = 0 mudanças);
- atualização de ``caminho_canonico`` no grafo;
- dry-run não escreve no disco nem no grafo;
- PII mascarada no relatório MD/CSV;
- mapeamento entre nodes e arquivos por (empresa, mes_ref).
"""

from __future__ import annotations

import importlib
import json
import sqlite3
import sys
from pathlib import Path

import pytest

# Garante que o pacote `scripts` seja importável direto (sem `python -m`).
_RAIZ = Path(__file__).resolve().parent.parent
if str(_RAIZ) not in sys.path:
    sys.path.insert(0, str(_RAIZ))

# Carrega como módulo. O próprio script também se reexecuta como __main__.
renomear = importlib.import_module("scripts.renomear_holerites_v2")


# ============================================================================
# Helpers
# ============================================================================


def _criar_pdf_dummy(diretorio: Path, nome: str, conteudo: bytes = b"%PDF-dummy") -> Path:
    """Cria arquivo .pdf com conteúdo arbitrário (parser será mockado)."""
    diretorio.mkdir(parents=True, exist_ok=True)
    arquivo = diretorio / nome
    arquivo.write_bytes(conteudo)
    return arquivo


@pytest.fixture
def dir_holerites(tmp_path: Path) -> Path:
    """Diretório temporário com 2 holerites canônicos da Sprint 98."""
    pasta = tmp_path / "holerites"
    _criar_pdf_dummy(pasta, "HOLERITE_G4F_2026-04_aaaaaaaa.pdf", b"PDF-G4F-04")
    _criar_pdf_dummy(pasta, "HOLERITE_INFOBASE_2026-03_bbbbbbbb.pdf", b"PDF-INFO-03")
    return pasta


@pytest.fixture
def grafo_dummy(tmp_path: Path) -> Path:
    """SQLite mínimo com 2 nodes documento tipo holerite."""
    db = tmp_path / "grafo.sqlite"
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE node (id INTEGER PRIMARY KEY, tipo TEXT, metadata TEXT)")
    metadata_g4f = json.dumps(
        {
            "tipo_documento": "holerite",
            "razao_social": "G4F",
            "periodo_apuracao": "2026-04",
            "total": 5000.0,
        }
    )
    metadata_info = json.dumps(
        {
            "tipo_documento": "holerite",
            "razao_social": "INFOBASE",
            "periodo_apuracao": "2026-03",
            "total": 3500.0,
        }
    )
    cursor.execute(
        "INSERT INTO node (id, tipo, metadata) VALUES (1, 'documento', ?)",
        (metadata_g4f,),
    )
    cursor.execute(
        "INSERT INTO node (id, tipo, metadata) VALUES (2, 'documento', ?)",
        (metadata_info,),
    )
    conn.commit()
    conn.close()
    return db


# ============================================================================
# Helpers de normalização
# ============================================================================


class TestSlugEmpresa:
    def test_g4f_simples(self) -> None:
        assert renomear._slug_empresa("G4F") == "G4F"

    def test_remove_acentos_e_espacos(self) -> None:
        assert renomear._slug_empresa("Infobase Servicos") == "INFOBASE"

    def test_acentuacao_pt(self) -> None:
        assert renomear._slug_empresa("Tecnologia Avancada") == "TECNOLOGIA"

    def test_string_vazia_devolve_desconhecido(self) -> None:
        assert renomear._slug_empresa("") == "DESCONHECIDO"

    def test_apenas_caracteres_especiais(self) -> None:
        assert renomear._slug_empresa("!!!") == "DESCONHECIDO"


# ============================================================================
# Construção de nome canônico
# ============================================================================


class TestNomeCanonicoLegivel:
    def test_template_g4f(self) -> None:
        nome = renomear._nome_canonico_legivel(mes_ref="2026-04", empresa="G4F", liquido=5000.50)
        assert nome == "HOLERITE_2026-04_G4F_5000.pdf"

    def test_template_infobase_arredondamento(self) -> None:
        nome = renomear._nome_canonico_legivel(
            mes_ref="2026-03", empresa="Infobase", liquido=3500.49
        )
        assert nome == "HOLERITE_2026-03_INFOBASE_3500.pdf"

    def test_template_arredonda_para_cima(self) -> None:
        nome = renomear._nome_canonico_legivel(mes_ref="2025-12", empresa="G4F", liquido=8657.51)
        assert nome == "HOLERITE_2025-12_G4F_8658.pdf"


class TestNomeCanonicoFallback:
    def test_fallback_com_mes(self) -> None:
        nome = renomear._nome_canonico_fallback(mes_ref="2026-04", sha8="deadbeef")
        assert nome == "HOLERITE_2026-04_deadbeef.pdf"

    def test_fallback_sem_mes(self) -> None:
        nome = renomear._nome_canonico_fallback(mes_ref=None, sha8="cafebabe")
        assert nome == "HOLERITE_cafebabe.pdf"


# ============================================================================
# Construção da proposta (parser mockado)
# ============================================================================


class TestConstruirProposta:
    def test_template_quando_metadata_completo(
        self, dir_holerites: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            renomear,
            "_extrair_metadata_pdf",
            lambda _: ("2026-04", "G4F", 5000.0),
        )
        arquivo = dir_holerites / "HOLERITE_G4F_2026-04_aaaaaaaa.pdf"
        proposta = renomear._construir_proposta(arquivo)
        assert proposta.motivo == "template"
        assert proposta.destino.name == "HOLERITE_2026-04_G4F_5000.pdf"
        assert proposta.mudou is True

    def test_fallback_quando_metadata_incompleto(
        self, dir_holerites: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Parser retorna empresa mas sem liquido (caso real Infobase com OCR ruim).
        monkeypatch.setattr(
            renomear,
            "_extrair_metadata_pdf",
            lambda _: ("2026-04", "G4F", None),
        )
        arquivo = dir_holerites / "HOLERITE_G4F_2026-04_aaaaaaaa.pdf"
        proposta = renomear._construir_proposta(arquivo)
        assert proposta.motivo == "fallback"
        assert proposta.destino.name.startswith("HOLERITE_2026-04_")
        assert proposta.destino.name.endswith(".pdf")
        # Sufixo deve ser o sha8 (8 chars hex), não o valor.
        sufixo = proposta.destino.stem.split("_")[-1]
        assert len(sufixo) == 8
        assert all(c in "0123456789abcdef" for c in sufixo)

    def test_sem_mudanca_quando_destino_igual_origem(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        pasta = tmp_path / "holerites"
        # Calcula o nome já canônico antes de criar.
        nome_canonico = "HOLERITE_2026-04_G4F_5000.pdf"
        arquivo = _criar_pdf_dummy(pasta, nome_canonico, b"PDF-canonico")
        monkeypatch.setattr(
            renomear,
            "_extrair_metadata_pdf",
            lambda _: ("2026-04", "G4F", 5000.0),
        )
        proposta = renomear._construir_proposta(arquivo)
        assert proposta.motivo == "sem_mudanca"
        assert proposta.mudou is False


# ============================================================================
# Aplicação do rename
# ============================================================================


class TestAplicarRename:
    def test_renomeia_arquivo(self, dir_holerites: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            renomear,
            "_extrair_metadata_pdf",
            lambda _: ("2026-04", "G4F", 5000.0),
        )
        arquivo = dir_holerites / "HOLERITE_G4F_2026-04_aaaaaaaa.pdf"
        proposta = renomear._construir_proposta(arquivo)
        assert renomear._aplicar_rename(proposta) is True
        assert not arquivo.exists()
        assert (dir_holerites / "HOLERITE_2026-04_G4F_5000.pdf").exists()

    def test_idempotencia_destino_existe_mesmo_conteudo(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        pasta = tmp_path / "holerites"
        # Origem e destino com mesmo conteúdo (Sprint 98 já moveu uma vez).
        origem = _criar_pdf_dummy(pasta, "HOLERITE_G4F_2026-04_aaaaaaaa.pdf", b"X")
        destino = _criar_pdf_dummy(pasta, "HOLERITE_2026-04_G4F_5000.pdf", b"X")
        monkeypatch.setattr(
            renomear,
            "_extrair_metadata_pdf",
            lambda _: ("2026-04", "G4F", 5000.0),
        )
        proposta = renomear._construir_proposta(origem)
        # Deve remover origem porque o destino já existe com mesmo sha8.
        assert renomear._aplicar_rename(proposta) is True
        assert not origem.exists()
        assert destino.exists()

    def test_conflito_destino_diferente(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        pasta = tmp_path / "holerites"
        origem = _criar_pdf_dummy(pasta, "HOLERITE_G4F_2026-04_aaaaaaaa.pdf", b"AAA")
        _criar_pdf_dummy(pasta, "HOLERITE_2026-04_G4F_5000.pdf", b"BBB")
        monkeypatch.setattr(
            renomear,
            "_extrair_metadata_pdf",
            lambda _: ("2026-04", "G4F", 5000.0),
        )
        proposta = renomear._construir_proposta(origem)
        with pytest.raises(RuntimeError, match="Destino diferente"):
            renomear._aplicar_rename(proposta)


# ============================================================================
# Idempotência ponta-a-ponta
# ============================================================================


class TestIdempotencia:
    def test_segunda_rodada_zero_mudancas(
        self, dir_holerites: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def fake_metadata(arquivo: Path) -> tuple:
            if "G4F" in arquivo.name:
                return ("2026-04", "G4F", 5000.0)
            return ("2026-03", "INFOBASE", 3500.0)

        monkeypatch.setattr(renomear, "_extrair_metadata_pdf", fake_metadata)

        # 1a rodada -- aplica rename.
        propostas1 = renomear.coletar_propostas(dir_holerites)
        assert sum(1 for p in propostas1 if p.mudou) == 2
        for p in propostas1:
            renomear._aplicar_rename(p)

        # 2a rodada -- arquivos já estão canônicos.
        propostas2 = renomear.coletar_propostas(dir_holerites)
        assert sum(1 for p in propostas2 if p.mudou) == 0
        for p in propostas2:
            assert p.motivo == "sem_mudanca"


# ============================================================================
# Atualização do grafo
# ============================================================================


class TestAtualizarGrafo:
    def test_atualiza_caminho_canonico_dos_nodes(
        self, dir_holerites: Path, grafo_dummy: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def fake_metadata(arquivo: Path) -> tuple:
            if "G4F" in arquivo.name:
                return ("2026-04", "G4F", 5000.0)
            return ("2026-03", "INFOBASE", 3500.0)

        monkeypatch.setattr(renomear, "_extrair_metadata_pdf", fake_metadata)

        propostas = renomear.coletar_propostas(dir_holerites)
        atualizados = renomear._atualizar_grafo(propostas, db_path=grafo_dummy)
        assert atualizados == 2

        conn = sqlite3.connect(grafo_dummy)
        cursor = conn.cursor()
        cursor.execute("SELECT metadata FROM node ORDER BY id")
        for (md_json,) in cursor.fetchall():
            md = json.loads(md_json)
            assert "caminho_canonico" in md
            assert md["caminho_canonico"].endswith(".pdf")
            assert "HOLERITE_" in md["caminho_canonico"]
        conn.close()

    def test_grafo_inexistente_nao_quebra(
        self, dir_holerites: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            renomear,
            "_extrair_metadata_pdf",
            lambda _: ("2026-04", "G4F", 5000.0),
        )
        propostas = renomear.coletar_propostas(dir_holerites)
        atualizados = renomear._atualizar_grafo(propostas, db_path=tmp_path / "inexistente.sqlite")
        assert atualizados == 0


# ============================================================================
# Dry-run não escreve
# ============================================================================


class TestDryRun:
    def test_dry_run_nao_renomeia(
        self,
        dir_holerites: Path,
        grafo_dummy: Path,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        monkeypatch.setattr(
            renomear,
            "_extrair_metadata_pdf",
            lambda _: ("2026-04", "G4F", 5000.0),
        )
        monkeypatch.setattr(renomear, "_DIR_HOLERITES", dir_holerites)
        monkeypatch.setattr(renomear, "_DIR_OUTPUT", tmp_path / "output")
        monkeypatch.setattr(renomear, "_GRAFO_DB", grafo_dummy)
        monkeypatch.setattr(sys, "argv", ["renomear_holerites_v2.py"])

        rc = renomear.main()
        assert rc == 0

        # Arquivos originais ainda no lugar.
        assert (dir_holerites / "HOLERITE_G4F_2026-04_aaaaaaaa.pdf").exists()
        assert (dir_holerites / "HOLERITE_INFOBASE_2026-03_bbbbbbbb.pdf").exists()

        # Grafo não atualizado.
        conn = sqlite3.connect(grafo_dummy)
        cursor = conn.cursor()
        cursor.execute("SELECT metadata FROM node WHERE id=1")
        md = json.loads(cursor.fetchone()[0])
        assert "caminho_canonico" not in md
        conn.close()

        # Relatório gerado.
        relatorios = list((tmp_path / "output").glob("rename_holerites_v2_*.md"))
        assert len(relatorios) == 1


# ============================================================================
# PII mascarada no relatório
# ============================================================================


class TestRelatorioPII:
    def test_valor_mascarado_em_md(
        self,
        dir_holerites: Path,
        grafo_dummy: Path,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        monkeypatch.setattr(
            renomear,
            "_extrair_metadata_pdf",
            lambda _: ("2026-04", "G4F", 12345.67),
        )
        monkeypatch.setattr(renomear, "_DIR_HOLERITES", dir_holerites)
        monkeypatch.setattr(renomear, "_DIR_OUTPUT", tmp_path / "output")
        monkeypatch.setattr(renomear, "_GRAFO_DB", grafo_dummy)
        monkeypatch.setattr(sys, "argv", ["renomear_holerites_v2.py"])

        rc = renomear.main()
        assert rc == 0

        relatorios_md = list((tmp_path / "output").glob("*.md"))
        assert relatorios_md
        conteudo = relatorios_md[0].read_text(encoding="utf-8")
        # Valor real nunca aparece.
        assert "12345" not in conteudo
        assert "12.345" not in conteudo
        # Máscara presente.
        assert "R$ XXX,XX" in conteudo

    def test_valor_mascarado_em_csv(
        self,
        dir_holerites: Path,
        grafo_dummy: Path,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        monkeypatch.setattr(
            renomear,
            "_extrair_metadata_pdf",
            lambda _: ("2026-04", "G4F", 9999.99),
        )
        monkeypatch.setattr(renomear, "_DIR_HOLERITES", dir_holerites)
        monkeypatch.setattr(renomear, "_DIR_OUTPUT", tmp_path / "output")
        monkeypatch.setattr(renomear, "_GRAFO_DB", grafo_dummy)
        monkeypatch.setattr(sys, "argv", ["renomear_holerites_v2.py"])

        rc = renomear.main()
        assert rc == 0

        relatorios_csv = list((tmp_path / "output").glob("*.csv"))
        assert relatorios_csv
        conteudo = relatorios_csv[0].read_text(encoding="utf-8")
        assert "9999" not in conteudo
        assert "R$ XXX,XX" in conteudo


# "O teste é a evidência, não o discurso." -- princípio do proof-of-work
