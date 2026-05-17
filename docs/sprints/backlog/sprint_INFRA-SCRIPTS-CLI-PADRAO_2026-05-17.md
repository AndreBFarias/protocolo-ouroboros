---
id: INFRA-SCRIPTS-CLI-PADRAO
titulo: "Padrão CLI canônico para scripts/ + --help em 10 órfãos + lib utils centralizada"
status: backlog
concluida_em: null
prioridade: P3
data_criacao: 2026-05-17
fase: SANEAMENTO
epico: 8
depende_de: []
esforco_estimado_horas: 2
origem: "auditoria independente 2026-05-17. 15+ scripts em `scripts/` reimplementam o mesmo boilerplate `sys.path.insert(0, str(Path(__file__).resolve().parents[1]))`. Quebra se estrutura do projeto muda. 10 scripts sem `--help` (descobrir o que fazem exige `head`/leitura). Difícil auto-discovery: dono não sabe quantos scripts existem nem qual roda primeiro."
---

# Sprint INFRA-SCRIPTS-CLI-PADRAO

## Contexto

Pasta `scripts/` tem 40+ arquivos `.py`. Estado atual:
- 15+ com `sys.path.insert(0, ...)` hardcoded.
- 10 sem `argparse.add_help` ou docstring usável.
- Sem `scripts/main.py` ou agregador (impossível listar todos via CLI).

Scripts órfãos detectados:
- `check_acentuacao.py`, `check_concluida_em.py`, `contar_inbox_pendentes.py`
- `auditar_estado.py`, `auditar_cobertura.py`, `auditar_extratores.py`
- `backfill_*.py` (3 deles)
- `audit_sprint_coverage.py`

## Hipótese e validação ANTES

```bash
# H1: scripts com sys.path.insert
grep -l "sys.path.insert" scripts/*.py | wc -l
# Esperado: >=15

# H2: scripts sem argparse
for f in scripts/*.py; do
  if ! grep -q "argparse\|--help" "$f" 2>/dev/null; then
    echo "$f"
  fi
done | head -15
```

## Objetivo

1. **Criar `scripts/_cli_util.py`** (NOVO):
   ```python
   """Boilerplate compartilhado para scripts/."""
   from __future__ import annotations
   import sys
   from pathlib import Path

   _RAIZ = Path(__file__).resolve().parents[1]
   if str(_RAIZ) not in sys.path:
       sys.path.insert(0, str(_RAIZ))

   def setup_path() -> Path:
       """Chame no topo de cada script para garantir imports relativos a src/."""
       return _RAIZ
   ```

2. **Refatorar scripts existentes** para usar `from scripts._cli_util import setup_path` em vez de `sys.path.insert` hardcoded.

3. **Adicionar argparse `--help`** aos 10 scripts órfãos (mensagens curtas).

4. **Criar `scripts/main.py`** ou estender `Makefile` com `make scripts-listar`:
   ```python
   #!/usr/bin/env python
   """Lista todos os scripts disponíveis com 1 linha cada."""
   import importlib.util
   import pathlib
   for p in sorted(pathlib.Path("scripts").glob("*.py")):
       if p.name.startswith("_") or p.name == "main.py":
           continue
       doc = ""
       with p.open() as f:
           for linha in f:
               if linha.startswith('"""'):
                   doc = linha[3:].strip().rstrip('"""')
                   break
       print(f"  {p.name:40s} {doc[:60]}")
   ```

5. **Documentar em `README.md` (seção Scripts CLI)** ou no `make help`.

## Não-objetivos

- Não alterar comportamento de scripts existentes.
- Não criar framework pesado (Typer, Click) — `argparse` basta.
- Não tocar scripts em `scripts/gauntlet/` ou `scripts/ci/`.

## Proof-of-work runtime-real

```bash
# Apos refactor:
grep -c "sys.path.insert" scripts/*.py
# Esperado: ~5 (só os que precisam de path customizado)

.venv/bin/python scripts/main.py 2>&1 | head -20
# Esperado: tabela com nome + descricao de cada script
```

## Acceptance

- `scripts/_cli_util.py` criado.
- ≥15 scripts refatorados para usar `setup_path()`.
- 10 scripts ganham `--help`.
- `scripts/main.py` lista todos.
- Pytest baseline mantida.
- Lint exit 0.

## Padrões aplicáveis

- (a) Edit incremental — refatoração mecânica.
- (e) PII never in INFO — não tocar PII em logs durante refactor.

---

*"Scripts sem help são caixas-pretas; com help, são ferramentas." — princípio do CLI honesto*
