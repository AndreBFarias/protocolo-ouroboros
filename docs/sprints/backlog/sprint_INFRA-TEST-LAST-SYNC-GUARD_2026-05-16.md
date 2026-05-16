---
id: INFRA-TEST-LAST-SYNC-GUARD
titulo: "Pre-commit guard: bloquear `.ouroboros/cache/last_sync.json` com path `/tmp/`"
status: backlog
concluida_em: null
prioridade: P3
data_criacao: 2026-05-16
fase: SANEAMENTO
epico: 8
depende_de:
  - INFRA-TEST-ISOLAR-LAST-SYNC (concluída — isolou o teste, mas histórico já contaminado)
esforco_estimado_horas: 0.5
origem: "achado colateral do executor `a8d370537d639c597` (INFRA-TEST-ISOLAR-LAST-SYNC) 2026-05-16. Após isolar o teste, executor verificou histórico do arquivo: 6 commits passados (`ac41b24`, `f26bbec`, etc) já tinham `vault_path: \"/tmp/pytest-of-andrefarias/...\"` commitado. Resíduo de teste vazou para git ao longo do tempo. Sprint anterior corrige a fonte, mas falta defesa em camadas: hook pre-commit bloqueia novos vazamentos retroativos."
---

# Sprint INFRA-TEST-LAST-SYNC-GUARD

## Contexto

INFRA-TEST-ISOLAR-LAST-SYNC (commit `283736f`) refatorou `test_soberania_preserva_moc_sem_tag` para usar `tmp_path` + `monkeypatch` via fixture `cache_isolado`. Isso resolve a causa-raiz. Porém:

1. Outro teste no futuro pode reintroduzir o mesmo padrão sem usar a fixture.
2. Resíduo de execução manual (`./run.sh --dashboard` apontando para path errado durante dev) pode vazar.
3. Hook global de anonimato já bloqueia `.claude/` mas não detecta paths `/tmp/` em conteúdo de arquivos.

Defesa em camadas (padrão `n`): adicionar guard em pre-commit que abre o JSON e bloqueia se `vault_path` contém substring `/tmp/`.

## Hipótese e validação ANTES

```bash
# H1: confirmar arquivo é versionado (não gitignored)
git ls-files .ouroboros/cache/last_sync.json
# Esperado: hit

# H2: confirmar formato do arquivo
cat .ouroboros/cache/last_sync.json | python -c "
import json, sys
d = json.load(sys.stdin)
print('vault_path:', repr(d.get('vault_path')))
"
# Esperado: string (vazia ou path real)

# H3: ver histórico de commits com /tmp/
git log -p .ouroboros/cache/last_sync.json | grep -c "/tmp/"
# Esperado: ≥1 hit (resíduo histórico)
```

## Objetivo

1. **Hook `hooks/check_last_sync_clean.py`** (CRIAR):
   - Lê `.ouroboros/cache/last_sync.json` no staging.
   - Se `vault_path` contém `/tmp/`: imprime erro e exit 1.
   - Se vazio ou path real válido (`/home/`, `/Users/`, `~/`): exit 0.

2. **Wiring em `.pre-commit-config.yaml`**:
   ```yaml
   - id: bloquear-last-sync-com-tmp
     name: Bloquear .ouroboros/cache/last_sync.json com path /tmp/
     entry: python hooks/check_last_sync_clean.py
     language: python
     files: ^\.ouroboros/cache/last_sync\.json$
   ```

3. **Teste regressivo `tests/test_check_last_sync_clean.py`** — 3 testes:
   - Aceita `vault_path: ""`.
   - Aceita `vault_path: "/home/user/vault"`.
   - Rejeita `vault_path: "/tmp/pytest-of-andrefarias/..."`.

## Não-objetivos

- Não tocar produção do `sync_rico.py` (já tem suporte a `OUROBOROS_CACHE_DIR`).
- Não reescrever histórico (commits passados ficam como estão; só prevenir futuro).
- Não tocar outros caches (`humor-heatmap.json` etc).

## Proof-of-work runtime-real

```bash
# 1. Hook aceita arquivo limpo (estado atual após sprint anterior)
git add .ouroboros/cache/last_sync.json
python hooks/check_last_sync_clean.py .ouroboros/cache/last_sync.json
echo "exit: $?"
# Esperado: exit 0

# 2. Hook rejeita arquivo sujo (simulado)
cp .ouroboros/cache/last_sync.json /tmp/test_clean.json
python -c "
import json
d = json.load(open('/tmp/test_clean.json'))
d['vault_path'] = '/tmp/pytest-of-andrefarias/pytest-99/test_x/vault'
json.dump(d, open('/tmp/test_dirty.json','w'))
"
python hooks/check_last_sync_clean.py /tmp/test_dirty.json
echo "exit: $?"
# Esperado: exit 1 + mensagem
```

## Acceptance

- Hook criado e funcional.
- Wired em `.pre-commit-config.yaml`.
- 3 testes regressivos verdes em `tests/test_check_last_sync_clean.py`.
- `pre-commit run --files .ouroboros/cache/last_sync.json` exit 0.
- Pytest > 3024. Lint exit 0.

## Padrões aplicáveis

- (n) Defesa em camadas — fixture isolada (sprint anterior) + hook pre-commit.
- (k) Hipótese ANTES — grep no histórico confirmou contaminação.
- (l) Anti-débito — achado vira sprint concreta, não TODO.

## Arquivos a criar/modificar

- `hooks/check_last_sync_clean.py` (CRIAR)
- `.pre-commit-config.yaml` (Edit: adicionar entry)
- `tests/test_check_last_sync_clean.py` (CRIAR)

---

*"Isolamento da fonte é cura; guard no portão é vacina." — princípio da imunização preventiva*
