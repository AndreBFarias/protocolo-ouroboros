---
id: META-FIXTURES-CACHE-IGNORE
titulo: Decidir destino dos 12 caches versionados em `tests/fixtures/vault_sintetico/.ouroboros/cache/`
status: backlog
concluida_em: null
prioridade: P3
data_criacao: 2026-05-15
fase: SANEAMENTO
epico: 8
depende_de: []
esforco_estimado_horas: 0.5
origem: auditoria 2026-05-15. 12 arquivos JSON em `tests/fixtures/vault_sintetico/.ouroboros/cache/` modificados em 2026-05-13. Diff é APENAS `gerado_em` (timestamp). Conteúdo deterministicamente idêntico. Cada `./run.sh --tudo` ou rodada de teste regera. Cria noise permanente em `git status`. Padrão (cc) — refactor revela teste frágil.
---

# Sprint META-FIXTURES-CACHE-IGNORE

## Contexto

Diff típico de uma fixture:
```
-  "gerado_em": "2026-05-12T20:33:19-03:00",
+  "gerado_em": "2026-05-13T22:49:39-03:00",
```

Restante do JSON é idêntico. 12 arquivos com esse mesmo padrão. Working tree fica permanentemente "dirty" só por timestamp.

**Decisão arquitetural pendente do dono** — 2 opções:

### Opção A — `.gitignore` + regerar em conftest.py (RECOMENDADO)
- Adicionar `tests/fixtures/vault_sintetico/.ouroboros/cache/` em `.gitignore`.
- `conftest.py` com fixture `autouse` chama gerador antes dos testes que precisam.
- Working tree limpo permanentemente.
- **Trade-off**: CI precisa gerar cache toda vez (~1s overhead).

### Opção B — Commit com `gerado_em` fixo
- Gerador grava `gerado_em: "2026-01-01T00:00:00+00:00"` em modo "fixture determinística" (env var ou flag).
- Caches versionados com timestamp constante.
- Working tree limpo enquanto fixtures não são tocadas semanticamente.
- **Trade-off**: gerador precisa branch "modo teste" vs "modo produção".

## Hipótese e validação ANTES

H1: 12 fixtures dirty com diff só de timestamp:

```bash
for f in tests/fixtures/vault_sintetico/.ouroboros/cache/*.json; do
  diff_lines=$(git diff "$f" | grep -cE "^[-+]")
  ts_only=$(git diff "$f" | grep -cE "^[-+].*gerado_em")
  if [ "$diff_lines" -gt 0 ] && [ "$diff_lines" -le "$((ts_only + 2))" ]; then
    echo "$f: só timestamp"
  fi
done
# Esperado: 12 hits
```

H2: identificar gerador:

```bash
grep -rln "gerado_em.*isoformat\|vault_sintetico.*cache\|test_soberania" src/ tests/ | head
# Esperado: gerador em src/obsidian/sync.py ou src/mobile_cache/
```

## Objetivo

Aguardar decisão do dono (Opção A ou B). Depois:

### Se Opção A:
1. Adicionar regex em `.gitignore`:
   ```
   # Caches sintéticos de fixture (regerados em conftest)
   tests/fixtures/vault_sintetico/.ouroboros/cache/*.json
   ```
2. `tests/conftest.py` adiciona fixture autouse:
   ```python
   @pytest.fixture(autouse=True, scope="session")
   def _regenerar_caches_fixture():
       from src.mobile_cache.gerador import gerar_caches_para_vault
       vault = Path(__file__).parent / "fixtures/vault_sintetico"
       gerar_caches_para_vault(vault)
   ```
3. Verificar que `make test` continua verde sem caches versionados.

### Se Opção B:
1. Identificar gerador (provavelmente em `src/mobile_cache/`).
2. Adicionar flag `OUROBOROS_FIXTURE_MODE=true` → timestamp fixo `"2026-01-01T00:00:00Z"`.
3. Reverter os 12 arquivos para versão com timestamp fixo.
4. Documentar em `docs/MANUAL_TESTES.md`.

## Não-objetivos

- Não criar 2 versões do gerador (Opção B usa flag, mesmo arquivo).
- Não mover fixtures para outra pasta.
- Não tocar testes que dependem dessas fixtures (devem continuar verdes).

## Proof-of-work runtime-real

### Para Opção A:
```bash
git rm --cached tests/fixtures/vault_sintetico/.ouroboros/cache/*.json
make test 2>&1 | tail -5
# Esperado: passes com regeração via conftest

git status --porcelain tests/fixtures/vault_sintetico/.ouroboros/cache/ | wc -l
# Esperado: 0 (cache não-tracked)
```

### Para Opção B:
```bash
OUROBOROS_FIXTURE_MODE=true .venv/bin/python -m src.mobile_cache.gerador --vault tests/fixtures/vault_sintetico
grep "gerado_em" tests/fixtures/vault_sintetico/.ouroboros/cache/*.json | head
# Esperado: todos com "2026-01-01T00:00:00+00:00"

git diff --stat tests/fixtures/vault_sintetico/.ouroboros/cache/
# Esperado: 0 (idempotente após o fix)
```

## Acceptance

- Opção escolhida pelo dono (A ou B).
- Working tree limpo após implementação.
- Pytest > 3019 (testes existentes continuam verdes).
- Documentação atualizada em README ou MANUAL_TESTES.

## Padrões aplicáveis

- (cc) Refactor revela teste frágil.
- (n) Defesa em camadas — gitignore + conftest (Opção A) ou env var + commit (Opção B).

---

*"Fixture deve ser ou esquecida pelo git ou imune ao tempo; nunca um pé-no-saco intermediário." — princípio do laboratório limpo*
