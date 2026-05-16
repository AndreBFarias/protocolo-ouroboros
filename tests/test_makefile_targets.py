"""Testes dos 5 targets de observabilidade do Makefile (META-MAKEFILE-OBSERVABILIDADE).

Cada teste invoca `make <target>` via subprocess, garantindo:
- exit 0 mesmo em ambientes sem grafo ou sem `gerar_metricas_prontidao.py`;
- presença de strings-âncora na stdout que demonstram que o target executou;
- registro do target em `make help`.

Convenção: subprocess sempre roda da raiz do repositório. Usamos `sys.executable`
para PYTHON, garantindo independência de venv local.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

_RAIZ = Path(__file__).resolve().parents[1]
_MAKEFILE = _RAIZ / "Makefile"


def _make(*args: str) -> subprocess.CompletedProcess[str]:
    """Invoca `make <args>` na raiz do repo com PYTHON apontando para o intérprete atual."""
    cmd = ["make", *args, f"PYTHON={sys.executable}"]
    return subprocess.run(
        cmd,
        cwd=_RAIZ,
        check=False,
        capture_output=True,
        text=True,
    )


class TestHelpRegistraNovosTargets:
    """O target `help` deve listar os 5 novos comandos via convenção `## descrição`."""

    @pytest.fixture(scope="class")
    def saida_help(self) -> str:
        resultado = _make("help")
        assert resultado.returncode == 0, (
            f"`make help` falhou: stderr={resultado.stderr!r}"
        )
        return resultado.stdout

    @pytest.mark.parametrize(
        "alvo",
        ["graduados", "audit", "spec", "health-grafo", "propostas"],
    )
    def test_target_aparece_no_help(self, saida_help: str, alvo: str) -> None:
        assert alvo in saida_help, (
            f"Target `{alvo}` não aparece em `make help`. "
            "Confirme que possui sufixo `## descrição` no Makefile."
        )


class TestTargetGraduados:
    """`make graduados` invoca dossie_tipo.py listar-tipos."""

    def test_graduados_exit_zero(self) -> None:
        r = _make("graduados")
        assert r.returncode == 0, (
            f"`make graduados` retornou {r.returncode}. stderr={r.stderr!r}"
        )
        # Âncora canônica: dossie_tipo.py imprime quantidade de tipos canônicos.
        assert "Tipos canonicos" in r.stdout or "tipos" in r.stdout.lower(), (
            f"Saída inesperada de `make graduados`: {r.stdout!r}"
        )


class TestTargetAudit:
    """`make audit` deve completar com exit 0 mesmo sem o script de métricas."""

    def test_audit_fallback_graceful(self) -> None:
        r = _make("audit")
        assert r.returncode == 0, (
            f"`make audit` retornou {r.returncode}. stderr={r.stderr!r}"
        )
        script_metricas = _RAIZ / "scripts" / "gerar_metricas_prontidao.py"
        if not script_metricas.exists():
            assert "ainda não materializada" in r.stdout or "pendentes" in r.stdout, (
                f"Esperava mensagem de fallback, recebi: {r.stdout!r}"
            )


class TestTargetSpec:
    """`make spec` exige NOME e cria arquivo em docs/sprints/backlog/."""

    def test_spec_sem_nome_falha_com_exit_1(self) -> None:
        r = _make("spec")
        assert r.returncode != 0, (
            "`make spec` sem NOME deveria falhar; "
            "exit foi 0 — fail-safe quebrado."
        )
        assert "NOME" in r.stdout or "NOME" in r.stderr

    def test_spec_com_nome_cria_arquivo(self, tmp_path: Path) -> None:
        """Cria spec, valida path, frontmatter e cleanup."""
        nome_unico = "PYTEST-MAKEFILE-TARGETS-FIXTURE"
        r = _make("spec", f"NOME={nome_unico}")
        try:
            assert r.returncode == 0, (
                f"`make spec NOME={nome_unico}` falhou. stderr={r.stderr!r}"
            )
            # Stdout contém o caminho absoluto do arquivo criado.
            caminho_str = r.stdout.strip().splitlines()[-1]
            caminho = Path(caminho_str)
            assert caminho.exists(), f"Arquivo prometido em stdout não existe: {caminho}"
            assert caminho.parent.name == "backlog", (
                f"Arquivo deve viver em docs/sprints/backlog/, está em {caminho.parent}"
            )
            conteudo = caminho.read_text(encoding="utf-8")
            assert f"id: {nome_unico}" in conteudo, (
                "Frontmatter não substituiu placeholder do ID."
            )
            assert "status: backlog" in conteudo
        finally:
            # Cleanup determinístico mesmo se assertions falharem.
            for p in (_RAIZ / "docs" / "sprints" / "backlog").glob(
                f"sprint_{nome_unico}_*.md"
            ):
                p.unlink()


class TestTargetHealthGrafo:
    """`make health-grafo` deve tolerar ausência do grafo (fallback graceful)."""

    def test_health_grafo_sempre_exit_zero(self) -> None:
        r = _make("health-grafo")
        assert r.returncode == 0, (
            f"`make health-grafo` retornou {r.returncode}; "
            f"deveria ser graceful. stderr={r.stderr!r}"
        )
        grafo = _RAIZ / "data" / "output" / "grafo.sqlite"
        if not grafo.exists():
            assert "ausente" in r.stdout.lower() or "rode 'make tudo'" in r.stdout, (
                f"Mensagem de ausência esperada, recebi: {r.stdout!r}"
            )
        else:
            assert "Esquema OK" in r.stdout or "Nós:" in r.stdout, (
                f"Saída esperada com grafo presente: {r.stdout!r}"
            )


class TestTargetPropostas:
    """`make propostas` lista propostas com status: aberta."""

    def test_propostas_exit_zero(self) -> None:
        r = _make("propostas")
        assert r.returncode == 0, (
            f"`make propostas` retornou {r.returncode}. stderr={r.stderr!r}"
        )
        # Aceita dois mundos: zero pendentes ou N pendentes.
        assert (
            "Nenhuma proposta pendente." in r.stdout
            or "propostas pendentes:" in r.stdout
        ), f"Saída inesperada de `make propostas`: {r.stdout!r}"

    def test_propostas_ignora_obsoletas(self) -> None:
        """Propostas em `_obsoletas/` ou `_rejeitadas/` não devem aparecer."""
        r = _make("propostas")
        assert r.returncode == 0
        assert "_obsoletas" not in r.stdout, (
            "Target propostas vazou path obsoleta -- filtro deficiente."
        )
        assert "_rejeitadas" not in r.stdout, (
            "Target propostas vazou path rejeitada -- filtro deficiente."
        )


class TestPhonyDeclarado:
    """Sanity: novos targets devem estar em .PHONY para evitar conflito com paths."""

    def test_targets_no_phony(self) -> None:
        conteudo = _MAKEFILE.read_text(encoding="utf-8")
        # A primeira linha do Makefile lista todos os .PHONY.
        primeira_linha = conteudo.splitlines()[0]
        assert primeira_linha.startswith(".PHONY:")
        for alvo in ("graduados", "audit", "spec", "health-grafo", "propostas"):
            assert alvo in primeira_linha, (
                f"Target `{alvo}` ausente da declaração .PHONY: do Makefile."
            )
