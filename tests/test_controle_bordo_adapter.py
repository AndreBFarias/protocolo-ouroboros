"""Testes do adapter Controle de Bordo (Sprint 70 — Fase IOTA).

Cobertura:
  - Config YAML (load, expansão de $BORDO_DIR, ordem de sources).
  - Classificação heurística sem mexer no sistema de arquivos.
  - Planejamento (planejar_roteamento) em vault sintético.
  - Preservação de originais em data/raw/originais/.
  - Skip de forbidden zones (ADR-18) e notas .md do vault.

Evita acessar `~/Controle de Bordo/` real para não depender do ambiente
do dev; usa `tmp_path` + monkeypatch de `BORDO_DIR`.
"""

from __future__ import annotations

import hashlib
import textwrap
from pathlib import Path

import pytest

from src.integrations import controle_bordo as cb

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def yaml_sintetico(tmp_path: Path) -> Path:
    """YAML mínimo com 1 source apontando para vault sintético."""
    vault = tmp_path / "vault"
    inbox = vault / "Inbox"
    inbox.mkdir(parents=True)

    yaml_path = tmp_path / "inbox_routing.yaml"
    yaml_path.write_text(
        textwrap.dedent(
            f"""
            inbox_sources:
              - path: "{inbox}"
                prioridade: 1
            tipos_absorvidos:
              - bancario_nubank_cc
              - bancario_itau_cc
              - boleto_servico
              - recibo_nao_fiscal
            preservar_original: true
            original_dir: {tmp_path / "originais"}
            hash_prefixo_chars: 16
            vault_forbidden:
              - .sistema
              - Trabalho
              - Segredos
              - Arquivo
            """
        ),
        encoding="utf-8",
    )
    return yaml_path


@pytest.fixture
def config_sintetica(yaml_sintetico: Path) -> cb.ConfigRoteamento:
    return cb.carregar_config(yaml_sintetico)


# ============================================================================
# Config
# ============================================================================


class TestConfigRoteamento:
    def test_carrega_yaml_basico(self, config_sintetica: cb.ConfigRoteamento) -> None:
        assert len(config_sintetica.sources) == 1
        assert "bancario_nubank_cc" in config_sintetica.tipos_absorvidos
        assert config_sintetica.preservar_original is True
        assert config_sintetica.hash_prefixo_chars == 16
        assert ".sistema" in config_sintetica.vault_forbidden

    def test_erro_quando_yaml_ausente(self, tmp_path: Path) -> None:
        inexistente = tmp_path / "nao_existe.yaml"
        with pytest.raises(FileNotFoundError):
            cb.carregar_config(inexistente)

    def test_vault_root_respeita_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("BORDO_DIR", "/opt/meu-vault")
        assert cb.vault_root() == Path("/opt/meu-vault")

    def test_vault_root_default_sem_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("BORDO_DIR", raising=False)
        esperado = Path.home() / "Controle de Bordo"
        assert cb.vault_root() == esperado

    def test_sources_preservam_ordem_prioridade(self, tmp_path: Path) -> None:
        yaml_path = tmp_path / "cfg.yaml"
        yaml_path.write_text(
            textwrap.dedent(
                f"""
                inbox_sources:
                  - path: "{tmp_path}/c"
                    prioridade: 3
                  - path: "{tmp_path}/a"
                    prioridade: 1
                  - path: "{tmp_path}/b"
                    prioridade: 2
                tipos_absorvidos: []
                preservar_original: false
                original_dir: /tmp/x
                hash_prefixo_chars: 8
                vault_forbidden: []
                """
            ),
            encoding="utf-8",
        )
        cfg = cb.carregar_config(yaml_path)
        nomes = [s.name for s in cfg.sources]
        assert nomes == ["a", "b", "c"]


# ============================================================================
# Planejamento
# ============================================================================


class TestPlanejarRoteamento:
    def _criar_arquivo(self, inbox: Path, nome: str, conteudo: bytes = b"x") -> Path:
        arquivo = inbox / nome
        arquivo.write_bytes(conteudo)
        return arquivo

    def test_nota_md_ficam_na_origem(
        self, yaml_sintetico: Path, tmp_path: Path
    ) -> None:
        inbox = tmp_path / "vault" / "Inbox"
        self._criar_arquivo(inbox, "minha-nota.md", b"# texto livre")
        cfg = cb.carregar_config(yaml_sintetico)
        plano = cb.planejar_roteamento(cfg)
        assert len(plano) == 1
        assert plano[0].acao == "skip_nota"
        assert plano[0].origem.name == "minha-nota.md"

    def test_extensao_nao_suportada_skip(
        self, yaml_sintetico: Path, tmp_path: Path
    ) -> None:
        inbox = tmp_path / "vault" / "Inbox"
        self._criar_arquivo(inbox, "app.bin", b"\x00")
        cfg = cb.carregar_config(yaml_sintetico)
        plano = cb.planejar_roteamento(cfg)
        assert plano[0].acao == "skip_extensao"

    def test_tipo_nao_absorvido_permanece(
        self, yaml_sintetico: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """PDF classificado como tipo fora de tipos_absorvidos fica na origem."""
        inbox = tmp_path / "vault" / "Inbox"
        self._criar_arquivo(inbox, "qualquer.pdf", b"%PDF-fake")

        # Força classificação para tipo fora da lista
        monkeypatch.setattr(
            cb,
            "_classificar",
            lambda _arquivo: ("algo_estranho_nao_mapeado", None),
        )
        cfg = cb.carregar_config(yaml_sintetico)
        plano = cb.planejar_roteamento(cfg)
        assert plano[0].acao == "skip_nao_identificado"
        assert plano[0].tipo == "algo_estranho_nao_mapeado"

    def test_tipo_financeiro_absorvido_vira_move(
        self, yaml_sintetico: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        inbox = tmp_path / "vault" / "Inbox"
        self._criar_arquivo(inbox, "extrato.pdf", b"%PDF-1.4\n")

        destino_sim = Path("/tmp/data/raw/andre/boletos")
        monkeypatch.setattr(
            cb,
            "_classificar",
            lambda _arquivo: ("boleto_servico", destino_sim),
        )
        cfg = cb.carregar_config(yaml_sintetico)
        plano = cb.planejar_roteamento(cfg)
        assert plano[0].acao == "move"
        assert plano[0].tipo == "boleto_servico"
        assert plano[0].destino == destino_sim

    def test_varredura_nao_recursiva(
        self, yaml_sintetico: Path, tmp_path: Path
    ) -> None:
        """Adapter não desce em Inbox/Pendentes/ — é domínio do motor do vault."""
        inbox = tmp_path / "vault" / "Inbox"
        pendentes = inbox / "Pendentes"
        pendentes.mkdir()
        (pendentes / "escondido.pdf").write_bytes(b"%PDF-fake")
        cfg = cb.carregar_config(yaml_sintetico)
        plano = cb.planejar_roteamento(cfg)
        # Nada deve aparecer: varredura é rasa
        assert len(plano) == 0

    def test_source_inexistente_nao_quebra(
        self, tmp_path: Path
    ) -> None:
        yaml_path = tmp_path / "cfg.yaml"
        yaml_path.write_text(
            textwrap.dedent(
                f"""
                inbox_sources:
                  - path: "{tmp_path}/nao_existe"
                    prioridade: 1
                tipos_absorvidos: []
                preservar_original: false
                original_dir: {tmp_path / "orig"}
                hash_prefixo_chars: 8
                vault_forbidden: []
                """
            ),
            encoding="utf-8",
        )
        cfg = cb.carregar_config(yaml_path)
        plano = cb.planejar_roteamento(cfg)
        assert plano == []


# ============================================================================
# Preservação
# ============================================================================


class TestPreservarOriginal:
    def test_copia_criada_com_sha256_prefixo(
        self, yaml_sintetico: Path, tmp_path: Path
    ) -> None:
        inbox = tmp_path / "vault" / "Inbox"
        arquivo = inbox / "fatura.pdf"
        conteudo = b"%PDF-1.4\n%EOF"
        arquivo.write_bytes(conteudo)

        cfg = cb.carregar_config(yaml_sintetico)
        destino = cb.preservar_original(arquivo, cfg)

        assert destino is not None
        assert destino.exists()
        sha = hashlib.sha256(conteudo).hexdigest()[:16]
        assert destino.name == f"{sha}.pdf"

    def test_idempotente_nao_sobrescreve(
        self, yaml_sintetico: Path, tmp_path: Path
    ) -> None:
        inbox = tmp_path / "vault" / "Inbox"
        arquivo = inbox / "a.pdf"
        arquivo.write_bytes(b"conteudo")
        cfg = cb.carregar_config(yaml_sintetico)

        primeira = cb.preservar_original(arquivo, cfg)
        assert primeira is not None
        mtime_original = primeira.stat().st_mtime

        segunda = cb.preservar_original(arquivo, cfg)
        assert segunda == primeira
        assert primeira.stat().st_mtime == mtime_original

    def test_desligado_via_config(self, tmp_path: Path) -> None:
        yaml_path = tmp_path / "cfg.yaml"
        yaml_path.write_text(
            textwrap.dedent(
                f"""
                inbox_sources: []
                tipos_absorvidos: []
                preservar_original: false
                original_dir: {tmp_path / "orig"}
                hash_prefixo_chars: 8
                vault_forbidden: []
                """
            ),
            encoding="utf-8",
        )
        cfg = cb.carregar_config(yaml_path)
        arquivo = tmp_path / "x.pdf"
        arquivo.write_bytes(b"x")
        assert cb.preservar_original(arquivo, cfg) is None


# ============================================================================
# Forbidden zones
# ============================================================================


class TestForbiddenZones:
    def test_arquivo_em_trabalho_e_ignorado(
        self, tmp_path: Path
    ) -> None:
        yaml_path = tmp_path / "cfg.yaml"
        inbox = tmp_path / "vault" / "Inbox"
        trabalho = inbox / "Trabalho"
        trabalho.mkdir(parents=True)
        sensivel = trabalho / "cliente-confidencial.pdf"
        sensivel.write_bytes(b"%PDF-top-secret")
        yaml_path.write_text(
            textwrap.dedent(
                f"""
                inbox_sources:
                  - path: "{inbox}"
                    prioridade: 1
                tipos_absorvidos: [boleto_servico]
                preservar_original: false
                original_dir: {tmp_path / "orig"}
                hash_prefixo_chars: 8
                vault_forbidden: [Trabalho]
                """
            ),
            encoding="utf-8",
        )
        cfg = cb.carregar_config(yaml_path)

        # Varredura é rasa: nem encontra arquivos em subpastas, então Trabalho
        # fica protegido pela não-recursividade. Mas o método _eh_forbidden deve
        # marcar explicitamente quando o caminho inclui a pasta forbidden.
        assert cb._eh_forbidden(sensivel, cfg) is True
        assert cb._eh_forbidden(inbox / "normal.pdf", cfg) is False


# ============================================================================
# CLI
# ============================================================================


class TestCLI:
    def test_dry_run_e_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        args = cb._parse_args([])
        assert args.dry_run is True

    def test_flag_executar_desliga_dry_run(self) -> None:
        args = cb._parse_args(["--executar"])
        assert args.dry_run is False

    def test_vault_override(self, tmp_path: Path) -> None:
        args = cb._parse_args(["--vault", str(tmp_path)])
        assert args.vault == tmp_path
