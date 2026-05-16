---
id: INFRA-TEST-ISOLAR-LAST-SYNC
titulo: Isolar `test_soberania_preserva_moc_se0` para não tocar `.ouroboros/cache/` da raiz
status: concluída
concluida_em: 2026-05-16
prioridade: P1
data_criacao: 2026-05-15
fase: SANEAMENTO
epico: 8
depende_de: []
esforco_estimado_horas: 1
origem: "auditoria 2026-05-15. `.ouroboros/cache/last_sync.json` (raiz do repo) tem campo `vault_path: \"/tmp/pytest-of-andrefarias/pytest-167/test_soberania_preserva_moc_se0/vault\"` — path TEMPORÁRIO de pytest. Significa que algum teste modificou o arquivo \"real\" do repo com path de teste. Bug de isolamento: teste mexe em estado de produção."
---

# Sprint INFRA-TEST-ISOLAR-LAST-SYNC

## Contexto

Working tree dirty há 3 dias inclui `.ouroboros/cache/last_sync.json` modificado. O diff mostra que o campo `vault_path` aponta para `/tmp/pytest-of-andrefarias/pytest-167/...` — um path que só existe DURANTE execução do pytest. Conclusão: teste rodou, escreveu nesse arquivo da raiz, e deixou o resíduo.

Esse arquivo deveria ser tocado APENAS pelo runtime do projeto (sync do vault Obsidian). Testes deveriam:
1. Usar `tmp_path` fixture do pytest.
2. `monkeypatch` para apontar `.ouroboros/cache/` para tmp_path durante o teste.
3. Cleanup automático ao final.

## Hipótese e validação ANTES

H1: identificar teste que toca `.ouroboros/cache/`:

```bash
grep -rln "\.ouroboros/cache\|last_sync.json" tests/
# Esperado: ≥1 hit (provavelmente test_soberania_*)

grep -rln "test_soberania_preserva_moc" tests/
# Esperado: nome do arquivo
```

H2: confirmar que é write direto na raiz (não em tmp_path):

```bash
# Localizar test offending e ver se usa tmp_path
grep -A 30 "def test_soberania_preserva_moc" tests/*.py | head -50
# Esperado: ver se há tmp_path em parâmetros ou se hardcoda raiz
```

## Objetivo

1. Identificar o teste exato (procurar por `test_soberania_preserva_moc_se0`).
2. Refatorar para usar `tmp_path` fixture:
   ```python
   def test_soberania_preserva_moc_se0(tmp_path, monkeypatch):
       cache_dir = tmp_path / ".ouroboros" / "cache"
       cache_dir.mkdir(parents=True)
       monkeypatch.setenv("OUROBOROS_CACHE_DIR", str(cache_dir))
       # OU monkeypatch o módulo que define o path
       ...
   ```
3. Reverter `.ouroboros/cache/last_sync.json` ao estado de HEAD: `git checkout HEAD -- .ouroboros/cache/last_sync.json`.
4. Adicionar guard no `src/obsidian/sync.py` (ou onde quer que seja): variável env `OUROBOROS_CACHE_DIR` permite override do path para testes.
5. Adicionar pre-push hook que reverte automaticamente esse arquivo se estiver dirty com path `/tmp/`.

## Não-objetivos

- Não tocar outros testes (foco neste).
- Não criar mecanismo "global" de isolation (overkill por enquanto).
- Não alterar a lógica do sync em produção.

## Proof-of-work runtime-real

```bash
# 1. Revert resíduo
git checkout HEAD -- .ouroboros/cache/last_sync.json
git diff .ouroboros/cache/last_sync.json | wc -l
# Esperado: 0

# 2. Rodar o teste isolado
.venv/bin/pytest tests/ -k "test_soberania_preserva_moc" -v
# Esperado: pass

# 3. Verificar que NÃO modificou `.ouroboros/cache/`
git diff .ouroboros/cache/last_sync.json | wc -l
# Esperado: 0 (não vazou)
```

## Acceptance

- Teste refatorado usa `tmp_path` + `monkeypatch`.
- `.ouroboros/cache/last_sync.json` revertido ao HEAD.
- Pre-push hook (opcional) bloqueia commit do arquivo com path `/tmp/`.
- Pytest > 3019 (mesmo teste passa). Smoke 10/10. Lint exit 0.

## Padrões aplicáveis

- (k) Hipótese ANTES — confirmar nome exato do teste antes de tocar.
- (m) Branch reversível — `git checkout HEAD -- file` cirúrgico.
- (n) Defesa em camadas — fixture isolada + env var + pre-push.

---

*"Teste que ensuja produção não é teste, é experimento mal-feito." — princípio do laboratório limpo*
