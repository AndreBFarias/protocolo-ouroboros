# Hooks de Validação -- Protocolo Ouroboros

Hooks de disciplina de código, portados da infra Luna e adaptados às regras do CLAUDE.md deste projeto.

Executados pelo `pre-commit` framework via `.pre-commit-config.yaml`.
O script manual `scripts/pre-commit-check.sh` segue disponível como fallback.

---

## Classificação

- **T1 (bloqueante):** falha do hook aborta o commit.
- **T2 (aviso):** loga mensagem, mas não bloqueia. Útil para migração gradual.

---

## Mapa de decisão (auditoria 2026-05-15 -- sprint META-HOOKS-AUDITAR-E-WIRAR)

Cada hook recebeu uma decisão clara: **WIRAR** (ativo em `.pre-commit-config.yaml`),
**ARQUIVAR** (movido para `hooks/_arquivado/`, não executa) ou **MOVER** (não é hook,
relocado para `scripts/`).

### Hooks ativos -- WIRADOS em `.pre-commit-config.yaml`

- `check_dados_financeiros.py` -- Decisão: WIRAR (já ativo antes desta sprint). Tipo T1, stage pre-commit. Bloqueia CPF/CNPJ/conta/PIX em commits de `.py`. Padrão (e).
- `check_emojis.py` -- Decisão: WIRAR. Tipo T1, stage pre-commit. Zero emojis em `.py`, `.sh`, `.md`, `.yaml`, `.toml`, etc. Padrão (c).
- `check_anonymity.py` -- Decisão: WIRAR. Tipo T1, stage pre-commit. Auto-corrige menções a Claude/Anthropic/GPT/OpenAI. Padrão (d).
- `check_citacao_filosofo.py` -- Decisão: WIRAR. Tipo T2, stage pre-commit, `files: ^src/`. Valida que `.py` em `src/` termina com citação filosófica. Padrão (g).
- `check_path_consistency.py` -- Decisão: WIRAR. Tipo T1, stage pre-commit. Bloqueia paths obsoletos do projeto (modulos legados pre-rebranding e nomes de output deprecados). Padrão (f).
- `check_diff_anti_burla.py` -- Decisão: WIRAR. Tipo T1, stage pre-commit. Bloqueia TODO/FIXME/HACK, `@pytest.mark.skip`, código comentado em linhas novas.
- `check_new_prints.py` -- Decisão: WIRAR. Tipo T1, stage pre-commit, `files: ^src/.*\.py$`. Bloqueia `print()` novos em `src/` (exceto `dashboard/`, `scripts/`, tests). Padrão (e).
- `check_logger_usage.sh` -- Decisão: WIRAR. Tipo T1, stage pre-commit, `files: ^src/.*\.py$`. `.py` que usa `print()` precisa configurar logger. Padrão (e).
- `check_silent_except.sh` -- Decisão: WIRAR. Tipo T1, stage pre-commit. Proíbe `except:` vazio ou `except: pass` em `src/`.
- `check_commit_author.sh` -- Decisão: WIRAR. Tipo T1, stage pre-commit. Author/email do `git config` não contém nomes de IA. Padrão (d).
- `check_commit_msg.py` -- Decisão: WIRAR. Tipo T1, stage commit-msg. Formato Conventional Commits PT-BR (`feat`, `fix`, `refactor`, etc.).
- `remove_coauthor.sh` -- Decisão: WIRAR. Tipo T1, stage commit-msg. Remove `Co-Authored-By:` de IA e bloqueia menções a IA no corpo. Padrão (d).
- `pre_push_protect_main.sh` -- Decisão: WIRAR. Tipo T1, stage pre-push. Bloqueia push direto para `main`.

Total: **13 hooks ativos** (12 novos + 1 já existente).

### Hooks arquivados -- em `hooks/_arquivado/`

- `check_complexity.py` -- Decisão: ARQUIVAR. Métrica de complexidade ciclomática. Faz sentido em equipes grandes; para projeto pessoal de uma pessoa, supervisor humano controla na revisão. Reativável se a equipe crescer.
- `check_file_size.py` -- Decisão: ARQUIVAR. Regra (h) "800L máximo" formalmente REVOGADA em 2026-05-12 (sessão 14 do supervisor). Coesão semântica supera contagem de linhas.

Ver `hooks/_arquivado/README.md` para detalhes e procedimento de reativação.

### Não é hook -- MOVIDO para `scripts/`

- `hooks/sprint_auto_move.py` -> `scripts/sprint_auto_move.py` -- Decisão: MOVER. Não valida nada (não é um check). É utilitário que move sprints com `**Status:** CONCLUÍDA` de `docs/sprints/producao/` para `docs/sprints/concluidos/`. Pertence a `scripts/`, não a `hooks/`.

---

## Integração

Os 13 hooks são executados pelo `pre-commit` framework conforme suas stages declaradas em `.pre-commit-config.yaml`:

```bash
# Instalar uma vez por clone:
pre-commit install --install-hooks
pre-commit install --hook-type commit-msg
pre-commit install --hook-type pre-push
```

Após isso, todos os 13 hooks rodam automaticamente nos eventos certos:

- **pre-commit:** `check_emojis`, `check_anonymity`, `check_citacao_filosofo`, `check_path_consistency`, `check_diff_anti_burla`, `check_new_prints`, `check_logger_usage`, `check_silent_except`, `check_commit_author`, `check_dados_financeiros`, `ruff`, `ruff-format`.
- **commit-msg:** `check_commit_msg`, `remove_coauthor`.
- **pre-push:** `pre_push_protect_main`.

O script `scripts/pre-commit-check.sh` segue disponível como fallback manual (útil para depurar um hook específico fora do framework).

---

## Execução manual

### Rodar toda a suíte

```bash
bash scripts/pre-commit-check.sh
```

### Rodar um hook específico

```bash
# Via pre-commit framework (recomendado):
pre-commit run check-emojis --all-files
pre-commit run check-anonymity --files src/pipeline.py

# Invocação direta (debug):
.venv/bin/python hooks/check_emojis.py src/pipeline.py
.venv/bin/python hooks/check_citacao_filosofo.py --all
bash hooks/check_silent_except.sh
bash hooks/check_commit_author.sh
```

### Rodar em arquivos específicos

Todos os hooks Python aceitam lista de arquivos como argumentos:

```bash
.venv/bin/python hooks/check_emojis.py arquivo1.py arquivo2.md
```

Se nenhum argumento for passado, a maioria dos hooks usa `git diff --cached` (arquivos staged).

---

## Exceções e supressão

### Acentuação (`# noqa: accent`)

Em linha específica de `.py`, `.md` ou `.sh`:

```python
# "descricao" aqui é chave técnica  # noqa: accent
```

### Anonimato (`check_anonymity.py`)

Arquivos em `EXCLUSIONS` dentro do hook são ignorados. Nomes técnicos como
`ANTHROPIC_API_KEY`, `anthropic.Anthropic`, `provider=`, `import anthropic`
são reconhecidos como legítimos via `TECH_EXCEPTIONS`.

### Tamanho de arquivo

Regra revogada em 2026-05-12. Hook arquivado em `hooks/_arquivado/check_file_size.py`.

### Complexidade ciclomática

Hook arquivado em `hooks/_arquivado/check_complexity.py` (over-engineering para projeto pessoal). Revisão de complexidade fica a cargo do supervisor humano.

---

## Adaptações ao portar da Luna

- `check_new_prints.py`: `BLOCKED_DIRS` reescrito para os módulos do Ouroboros (`src/extractors/`, `src/transform/`, `src/load/`, etc.), com isenção explícita para `src/dashboard/` e `scripts/`.
- `check_anonymity.py`: `EXCLUSIONS` atualizadas para paths do Ouroboros; `TECH_EXCEPTIONS` adicionado para proteger identificadores técnicos (`ANTHROPIC_API_KEY`, `import anthropic`, etc.).
- `check_path_consistency.py`: regex Luna-specific removidas; adicionados paths obsoletos do Ouroboros (`controle_de_bordo`, `financas.xlsx`).
- `check_diff_anti_burla.py`: `EXEMPT_PATHS` trocados (de `dev-journey/`, `scripts/hooks/` para `hooks/`, `docs/`, `scripts/`).
- `check_logger_usage.sh`: grep de logger ampliado para reconhecer `src.utils.logger`, `logging.getLogger`, `import logging`.
- `check_silent_except.sh`: detecção adicional de `except: pass` além de `except:` vazio.
- Todas as citações finais revisadas para PT-BR.

---

## Hook original do Ouroboros

- `check_citacao_filosofo.py` -- novo; valida que arquivos `.py` em `src/` terminam com comentário de citação filosófica (CLAUDE.md regra 10).

---

## Hooks NÃO portados da Luna

Hooks da Luna que dependem de infra Luna-specific (dev-journey, registry, gauntlet, subsistemas) e não foram portados:

- `check_adr_compliance.py`, `check_assets_integrity.py`, `check_bugfix_tracker.py`, `check_canonical_alignment.py`, `check_circular_imports.py`, `check_config_shadowing.py`, `check_doc_freshness.py`, `check_doc_links.py`, `check_doc_structure.py`, `check_entity_hardcode.py`, `check_gauntlet_freshness.py` (Ouroboros já tem versão própria em `scripts/`), `check_intent_router.py`, `check_max_depth.py`, `check_meta_rules.py`, `check_model_safety.py`, `check_offline_first.py`, `check_ollama_safety.py`, `check_orphan_code.sh`, `check_prompt_parity.py`, `check_registry*.py`, `check_requirements_sync.py`, `check_subsistema_docs.py`, `check_visual_evidence.py`, `check_zero_mocks.py`.

Se algum se tornar relevante (ex.: `check_requirements_sync.py` se o projeto passar a versionar `requirements.txt` ao lado do `pyproject.toml`), basta portar seguindo o mesmo padrão deste diretório.
