---
concluida_em: 2026-04-28
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: AUDIT-CACHE-THREADSAFE
  title: "Trocar cache global mutavel por functools.lru_cache nos modulos de mappings"
  prioridade: P2
  estimativa: ~1h
  origem: "auditoria externa 2026-04-28 P2-02 -- _CONFIG_CACHE em ocr_fallback_similar e _SINTETICOS_CACHE em ingestor_documento são globais não-thread-safe"
  touches:
    - path: src/intake/ocr_fallback_similar.py
      reason: "_CONFIG_CACHE -> functools.lru_cache(maxsize=1)"
    - path: src/graph/ingestor_documento.py
      reason: "_SINTETICOS_CACHE -> functools.lru_cache(maxsize=1)"
    - path: tests/test_ocr_fallback_similar.py
      reason: "_resetar_cache_config substituido por cache.cache_clear()"
    - path: tests/test_fornecedor_sintetico_impostos.py
      reason: "_resetar_cache_sinteticos substituido por cache.cache_clear()"
  forbidden:
    - "Quebrar testes existentes que usam _resetar_cache_*"
    - "Mudar comportamento do load (lazy primeira chamada)"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/ -q"
  acceptance_criteria:
    - "_carregar_config decorada com @lru_cache(maxsize=1)"
    - "_carregar_fornecedores_sinteticos decorada com @lru_cache(maxsize=1)"
    - "Testes invocam .cache_clear() em vez de variavel global"
    - "Sprint INFRA-97a invariante (state contaminado entre testes) preservada"
```

---

# Sprint AUDIT-CACHE-THREADSAFE

**Status:** BACKLOG (P2, criada 2026-04-28 pela auditoria externa)

## Motivação

Padrao `global _CONFIG_CACHE` em vários módulos não eh thread-safe. Em pytest com `-n auto` (paralelo) dois workers podem corromper o cache. Lição empirica Sprint INFRA-97a registra exatamente esse problema.

## Implementação

```python
import functools

@functools.lru_cache(maxsize=1)
def _carregar_config() -> dict[str, Any]:
    if not _PATH_CONFIG.exists():
        return _config_default()
    with _PATH_CONFIG.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or _config_default()
```

Testes substituem `_resetar_cache_config()` por `_carregar_config.cache_clear()`.

## Padrão canônico para registrar

`global VARIAVEL_CACHE = None` eh antipadrao. Use `functools.lru_cache(maxsize=1)` para caches lazy de modulo.
