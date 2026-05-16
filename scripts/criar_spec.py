#!/usr/bin/env python3
"""Gera arquivo de spec de sprint a partir do template canônico.

Uso
---

    python scripts/criar_spec.py <ID-DA-SPRINT>

Onde `<ID-DA-SPRINT>` é um slug livre em qualquer forma (kebab-case, CAIXA-ALTA,
snake_case). O script normaliza para CAIXA-ALTA-COM-HIFENS, monta o caminho
`docs/sprints/backlog/sprint_<ID>_<YYYY-MM-DD>.md` (data corrente) e escreve
um stub baseado em `docs/sprints/_TEMPLATE_SPRINT.md`. Se o template não
existir, gera um stub mínimo inline.

Comportamento determinístico
----------------------------

- Falha (exit 2) se arquivo de destino já existir, evitando sobrescrita
  silenciosa do trabalho do usuário.
- Substitui ocorrências de `<SLUG-EM-CAIXA-ALTA>` pelo ID normalizado.
- Substitui `data_criacao:` para a data corrente (padrão ISO).
- Stdout: caminho absoluto do arquivo gerado (consumível por shell).

Mantenedor: protocolo-ouroboros.
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

_RAIZ_REPO: Path = Path(__file__).resolve().parents[1]
_DIR_BACKLOG: Path = _RAIZ_REPO / "docs" / "sprints" / "backlog"
_PATH_TEMPLATE: Path = _RAIZ_REPO / "docs" / "sprints" / "_TEMPLATE_SPRINT.md"

_STUB_INLINE: str = """---
id: {id_slug}
titulo: <descrição curta em uma linha>
status: backlog
concluida_em: null
prioridade: P2
data_criacao: {data}
fase: OUTROS
epico: 0
depende_de: []
tipo_documental_alvo: null
---

# Sprint {id_slug}

## Contexto

Por que esta sprint existe. Cite arquivos/linhas reais quando aplicável.

## Objetivo

Uma frase declarando o resultado verificável esperado.

## Validação ANTES (grep obrigatório -- padrão (k))

```bash
rg "identificador_alvo" src/ --count
```

## Não-objetivos (escopo fechado -- padrão (t))

- O que esta sprint EXPLICITAMENTE não faz.

## Touches autorizados

- `src/.../arquivo.py` -- motivo

## Plano de implementação

Passos granulares em ordem.

## Acceptance

- `comando` retorna `<saída esperada>`.
- `make lint` exit 0.

## Proof-of-work runtime real (padrão (u))

```bash
./run.sh --smoke
```

## Padrão canônico aplicável

Liste padrões do BRIEF que se aplicam.

---

*"Citação opcional encerra a spec." -- autor*
"""


def normalizar_id(bruto: str) -> str:
    """Converte um identificador bruto para CAIXA-ALTA-COM-HIFENS canônico.

    Regras: trim, espaço/underline viram hífen, múltiplos hífens colapsam,
    só [A-Z0-9-] sobrevive, sem hífens nas pontas.
    """
    s = bruto.strip().upper()
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"[^A-Z0-9-]+", "", s)
    s = re.sub(r"-{2,}", "-", s)
    s = s.strip("-")
    if not s:
        raise ValueError("ID vazio após normalização")
    return s


def gerar_conteudo(id_slug: str, data_iso: str) -> str:
    """Carrega template canônico se existir, senão usa stub inline.

    Em ambos os casos substitui placeholders do template `<SLUG-EM-CAIXA-ALTA>`
    pelo `id_slug` real, e ajusta `data_criacao:` para `data_iso`.
    """
    if _PATH_TEMPLATE.exists():
        conteudo = _PATH_TEMPLATE.read_text(encoding="utf-8")
        conteudo = conteudo.replace("<SLUG-EM-CAIXA-ALTA>", id_slug)
        conteudo = re.sub(
            r"^data_criacao:.*$",
            f"data_criacao: {data_iso}",
            conteudo,
            count=1,
            flags=re.MULTILINE,
        )
        return conteudo
    return _STUB_INLINE.format(id_slug=id_slug, data=data_iso)


def construir_caminho(id_slug: str, data_iso: str) -> Path:
    """Caminho absoluto canônico do arquivo de spec a criar."""
    return _DIR_BACKLOG / f"sprint_{id_slug}_{data_iso}.md"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="criar_spec.py",
        description="Gera stub de spec de sprint em docs/sprints/backlog/.",
    )
    parser.add_argument(
        "id",
        help="Identificador da sprint (normalizado para CAIXA-ALTA-COM-HIFENS).",
    )
    parser.add_argument(
        "--data",
        default=date.today().isoformat(),
        help="Data ISO para data_criacao e sufixo do arquivo (padrão: hoje).",
    )
    args = parser.parse_args(argv)

    try:
        id_slug = normalizar_id(args.id)
    except ValueError as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 2

    _DIR_BACKLOG.mkdir(parents=True, exist_ok=True)
    caminho = construir_caminho(id_slug, args.data)
    if caminho.exists():
        print(
            f"erro: arquivo já existe em {caminho}; não será sobrescrito.",
            file=sys.stderr,
        )
        return 2

    caminho.write_text(gerar_conteudo(id_slug, args.data), encoding="utf-8")
    print(str(caminho))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# "O segredo da liberdade é a coragem." -- Péricles
