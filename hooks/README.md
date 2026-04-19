# Hooks de Validação -- Protocolo Ouroboros

Hooks de disciplina de código, portados da infra Luna e adaptados às regras do CLAUDE.md deste projeto.

Executados automaticamente por `scripts/pre-commit-check.sh` (logo após ruff check/format e verificação de acentuação).

---

## Classificação

- **T1 (bloqueante):** falha do hook aborta o commit.
- **T2 (aviso):** loga mensagem, mas não bloqueia. Útil para migração gradual.

---

## Inventário

| Hook | Tipo | Stage | O que valida |
|------|------|-------|--------------|
| `check_commit_author.sh` | T1 | pre-commit | Author/email do `git config` não contém nomes de IA (Claude/GPT/Copilot/etc.) |
| `remove_coauthor.sh` | T1 | commit-msg | Remove `Co-Authored-By:` de IA e bloqueia menções a IA no corpo |
| `check_commit_msg.py` | T1 | commit-msg | Formato Conventional Commits PT-BR (feat/fix/refactor/docs/test/perf/chore/build/ci) |
| `check_anonymity.py` | T1 | pre-commit | Auto-corrige (ou reporta em CI) menções a Claude/Anthropic/GPT/OpenAI em arquivos |
| `check_emojis.py` | T1 | pre-commit | Zero emojis em `.py`, `.sh`, `.md`, `.yaml`, `.toml`, etc. |
| `check_file_size.py` | T1 | pre-commit | Limite de 800 linhas por `.py` (CLAUDE.md seção 6) |
| `check_new_prints.py` | T1 | pre-commit | Bloqueia `print()` novos em `src/` (exceto `dashboard/`, `scripts/`, tests) |
| `check_logger_usage.sh` | T1 | pre-commit | `.py` que usa `print()` também precisa configurar logger |
| `check_silent_except.sh` | T1 | pre-commit | Proíbe `except:` vazio ou `except: pass` |
| `check_diff_anti_burla.py` | T1 | pre-commit | Bloqueia TODO/FIXME/HACK, `@pytest.mark.skip`, código comentado em linhas novas |
| `pre_push_protect_main.sh` | T1 | pre-push | Bloqueia push direto para `main` |
| `check_complexity.py` | T2 | pre-commit | Avisa quando função tem complexidade ciclomática >15 (bloqueia) ou >10 (warning) |
| `check_path_consistency.py` | T1 | pre-commit | Bloqueia paths obsoletos (`controle_de_bordo`, `financas.xlsx`, etc.) |
| `check_citacao_filosofo.py` | T2 | pre-commit | Valida que `.py` em `src/` termina com citação filosófica |
| `sprint_auto_move.py` | -- | pre-commit | (pré-existente) Move sprints de `proximas/` para `concluidas/` quando marcadas |

---

## Integração

O runner principal é `scripts/pre-commit-check.sh`. Ele executa na ordem:

1. `ruff check` e `ruff format --check`
2. Bloqueio de CPF/CNPJ em arquivos staged
3. `scripts/check_acentuacao.py` (T1)
4. Todos os hooks em `hooks/*.sh` e `hooks/*.py` (exceto `sprint_auto_move.py`, que roda no hook real do git)
5. `scripts/check_gauntlet_freshness.py` (T2)

Para instalar como hook real do git:

```bash
git config core.hooksPath scripts/git-hooks  # se existir setup
# ou usar pre-commit framework com .pre-commit-config.yaml
```

Atualmente o projeto usa invocação manual/CI de `pre-commit-check.sh`.

---

## Execução manual

### Rodar toda a suíte

```bash
bash scripts/pre-commit-check.sh
```

### Rodar um hook específico

```bash
# Hooks Python
.venv/bin/python hooks/check_file_size.py
.venv/bin/python hooks/check_emojis.py src/pipeline.py
.venv/bin/python hooks/check_citacao_filosofo.py --all

# Hooks shell
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

Não há whitelist. Se um arquivo precisa ultrapassar 800 linhas e é
legítimo (ex.: schema gerado, registry), refatorar para importar de
múltiplos módulos menores.

### Complexidade ciclomática

Atualmente sem whitelist. Funções que passam de 15 devem ser extraídas.

---

## Adaptações ao portar da Luna

- `check_file_size.py`: limite elevado de 300 para **800** (CLAUDE.md Ouroboros seção 6).
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
