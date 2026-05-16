---
id: META-RUFF-FORMAT-NORMALIZAR
titulo: Rodar `ruff format` em `src/ tests/ scripts/` (186 arquivos com formatação pendente)
status: concluída
concluida_em: 2026-05-16
prioridade: P3
data_criacao: 2026-05-15
fase: SANEAMENTO
epico: 8
depende_de: []
esforco_estimado_horas: 0.5
origem: achado colateral da sprint META-HOOKS-AUDITAR-E-WIRAR (executor `af13dd9f`, 2026-05-15). `pre-commit run --all-files` detectou 186 arquivos que `ruff format` reformataria. Pendência de formatação repo-wide.
---

# Sprint META-RUFF-FORMAT-NORMALIZAR

## Contexto

`ruff format` é a versão `black`-like do ruff: reformata Python para padrão único (line length 100, trailing commas, etc). Já está wired em `.pre-commit-config.yaml` mas nunca foi rodado em massa — 186 arquivos divergem do estilo canônico.

Sprint é mecânica: 1 comando + commit. Risco baixo (apenas reformatação, sem mudança semântica), mas diff é grande (~186 arquivos). Commit dedicado tipo `style:` separa da história de mudanças funcionais.

## Hipótese e validação ANTES

```bash
.venv/bin/ruff format --check src/ tests/ scripts/ 2>&1 | tail -5
# Esperado: "186 files would be reformatted" ou similar
```

## Objetivo

1. Rodar `make format` (que invoca `ruff format` + `ruff check --fix`).
2. Confirmar pytest baseline mantida (formatação não muda semântica).
3. Commit único `style(ruff): formatação repo-wide canônica`.

## Não-objetivos

- Não tocar arquivos fora de `src/`, `tests/`, `scripts/`.
- Não rodar `ruff check --unsafe-fixes` (apenas safe).
- Não juntar com outras mudanças funcionais.

## Proof-of-work runtime-real

```bash
make format
.venv/bin/ruff format --check src/ tests/ scripts/
# Esperado: "All checks passed!" 0 files would be reformatted

.venv/bin/pytest tests/ -q --tb=no
# Esperado: baseline mantida
```

## Acceptance

- 186 arquivos reformatados em commit único.
- `ruff format --check` exit 0.
- Pytest > 3046. Smoke 10/10. Lint exit 0.

## Padrões aplicáveis

- (a) Edit incremental — formatação é estilo, não funcional.

---

*"Formatação consistente é gentileza para próximo leitor." — princípio do código educado*
