"""tests/test_check_spec.py -- Sprint META-SPEC-LINTER 2026-05-15.

Cobre o linter `scripts/check_spec.py`:

1. Spec canônica completa retorna OK (exit 0).
2. Spec sem `## Não-objetivos` é detectada como falha.
3. Spec com campo de frontmatter ausente é detectada.
4. `--auto-completar` adiciona `## Não-objetivos` sem destruir conteúdo.
5. `--soft` em backlog com falhas retorna exit 0 (não destrava `make lint`).

Padrões VALIDATOR_BRIEF aplicados: (b) acentuação PT-BR, (g) citação no
rodapé, (n) defesa em camadas (testa default + auto-completar + soft).
"""
from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from scripts.check_spec import (
    PLACEHOLDER_NAO_OBJETIVOS,
    auto_completar,
    main,
    validar_spec,
)

SPEC_VALIDA = dedent(
    """\
    ---
    id: TESTE-EXEMPLAR
    titulo: Spec exemplar para o teste do linter
    status: backlog
    prioridade: P2
    data_criacao: 2026-05-15
    esforco_estimado_horas: 1
    origem: "teste unitário do linter de specs"
    ---

    # Sprint TESTE-EXEMPLAR

    ## Contexto

    Spec exemplar usada como gabarito do teste.

    ## Hipótese e validação ANTES

    ```bash
    grep -l foo bar
    ```

    ## Objetivo

    Validar que o linter aceita esta forma canônica.

    ## Não-objetivos

    - Não testar semântica.

    ## Proof-of-work

    ```bash
    python scripts/check_spec.py spec.md
    ```

    ## Acceptance

    - Linter retorna OK.
    """
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _gravar(tmp_path: Path, nome: str, conteudo: str) -> Path:
    """Grava o conteúdo em `tmp_path/nome` e retorna o caminho."""
    caminho = tmp_path / nome
    caminho.write_text(conteudo, encoding="utf-8")
    return caminho


# ---------------------------------------------------------------------------
# Teste 1 -- spec exemplar passa
# ---------------------------------------------------------------------------


def test_spec_canonica_passa_sem_problemas(tmp_path: Path) -> None:
    """Spec com frontmatter completo e todas as seções deve passar."""
    spec = _gravar(tmp_path, "sprint_OK_2026-05-15.md", SPEC_VALIDA)
    problemas = validar_spec(spec)
    assert problemas == [], f"esperado lista vazia, recebi {problemas}"


# ---------------------------------------------------------------------------
# Teste 2 -- seção mandatória ausente
# ---------------------------------------------------------------------------


def test_falta_secao_nao_objetivos_e_reportada(tmp_path: Path) -> None:
    """Quando `## Não-objetivos` é removida, o linter reporta falha."""
    conteudo = SPEC_VALIDA.replace("## Não-objetivos\n\n- Não testar semântica.\n\n", "")
    spec = _gravar(tmp_path, "sprint_SEM_NAO_OBJETIVOS_2026-05-15.md", conteudo)
    problemas = validar_spec(spec)
    assert "secao_ausente:nao_objetivos" in problemas, (
        f"esperado secao_ausente:nao_objetivos em {problemas}"
    )


# ---------------------------------------------------------------------------
# Teste 3 -- campo de frontmatter ausente
# ---------------------------------------------------------------------------


def test_falta_campo_origem_no_frontmatter(tmp_path: Path) -> None:
    """Frontmatter sem o campo `origem` é falha."""
    conteudo = SPEC_VALIDA.replace('origem: "teste unitário do linter de specs"\n', "")
    spec = _gravar(tmp_path, "sprint_SEM_ORIGEM_2026-05-15.md", conteudo)
    problemas = validar_spec(spec)
    assert "campo_faltante:origem" in problemas, (
        f"esperado campo_faltante:origem em {problemas}"
    )


# ---------------------------------------------------------------------------
# Teste 4 -- auto-completar adiciona placeholder sem destruir
# ---------------------------------------------------------------------------


def test_auto_completar_adiciona_secao_sem_destruir_conteudo(tmp_path: Path) -> None:
    """`auto_completar` faz append da seção; conteúdo anterior fica intacto."""
    conteudo = SPEC_VALIDA.replace("## Não-objetivos\n\n- Não testar semântica.\n\n", "")
    spec = _gravar(tmp_path, "sprint_AUTOCOMPLETAR_2026-05-15.md", conteudo)
    modificou = auto_completar(spec)
    assert modificou is True
    final = spec.read_text(encoding="utf-8")
    assert PLACEHOLDER_NAO_OBJETIVOS.strip() in final
    # Conteúdo anterior preservado: ainda contém o cabeçalho do Acceptance.
    assert "## Acceptance" in final
    # Idempotência: segunda chamada não modifica.
    assert auto_completar(spec) is False


# ---------------------------------------------------------------------------
# Teste 5 -- main com --soft sempre retorna 0
# ---------------------------------------------------------------------------


def test_main_soft_retorna_zero_mesmo_com_falhas(tmp_path: Path) -> None:
    """Flag `--soft` permite `make lint` cobrindo backlog histórico sem travar."""
    # Spec sem nada do que se espera -- falha clara em modo estrito.
    spec_ruim = _gravar(
        tmp_path,
        "sprint_RUIM_2026-05-15.md",
        "# Spec sem frontmatter nem secoes\n",
    )
    # Estrito: exit 1.
    assert main([str(spec_ruim)]) == 1
    # Soft: exit 0 (reporta mesmo conjunto, decisão fica para hook estrito).
    assert main(["--soft", str(spec_ruim)]) == 0


# "A regra do gênio é estabelecer regras." -- Friedrich Nietzsche, Além do bem e do mal
