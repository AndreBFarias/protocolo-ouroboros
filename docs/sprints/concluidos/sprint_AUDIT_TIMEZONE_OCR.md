## 0. SPEC (machine-readable)

```yaml
sprint:
  id: AUDIT-TIMEZONE-OCR
  title: "Comparar apenas dates (sem timezone) em _score_temporal do OCR fallback"
  prioridade: P2
  estimativa: ~30min
  origem: "auditoria externa 2026-04-28 P2-03 -- datetime.fromisoformat() (naive) vs datetime.fromtimestamp() (local) podem causar erro de +/-1 dia"
  touches:
    - path: src/intake/ocr_fallback_similar.py
      reason: "linha 181-183 -- usar .date() em ambos os lados, comparar como date"
    - path: tests/test_ocr_fallback_similar.py
      reason: "novos testes em timezones distintos (mock TZ)"
  forbidden:
    - "Mudar a semântica de janela_dias (preserva intervalo logico)"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_ocr_fallback_similar.py -v"
  acceptance_criteria:
    - "_score_temporal usa date.fromisoformat e datetime.fromtimestamp(.., tz=UTC).date()"
    - "Erro de +/-1 dia em janela de 7 dias eliminado"
    - "Teste regressivo: arquivo gerado a 23:55 com candidato data=hoje retorna score 1.0 sem flutuacao"
```

---

# Sprint AUDIT-TIMEZONE-OCR

**Status:** BACKLOG (P2, criada 2026-04-28 pela auditoria externa)

## Motivação

```python
# Atualmente em ocr_fallback_similar.py:181-183
d_cand = datetime.fromisoformat(str(candidato_data)[:10])  # naive
d_falho = datetime.fromtimestamp(falho_mtime)              # local TZ
```

Em America/Sao_Paulo (UTC-3), arquivo criado as 23:55 hora local de uma data, comparado com `data_emissao` em ISO sem TZ -- `delta_dias` pode ser +/-1 dia. Para janela de 7 dias, isso eh 14% de erro.

## Implementação

```python
from datetime import date

def _score_temporal(falho_mtime, candidato_data, janela_dias):
    if not candidato_data:
        return 0.0
    try:
        d_cand = date.fromisoformat(str(candidato_data)[:10])
        d_falho = datetime.fromtimestamp(falho_mtime).date()
        delta_dias = abs((d_cand - d_falho).days)
        if delta_dias > janela_dias:
            return 0.0
        return 1.0 - (delta_dias / max(1, janela_dias))
    except (ValueError, TypeError):
        return 0.0
```

## Testes regressivos

1. Arquivo as 23:55 vs candidato hoje -> score 1.0 (sem flutuacao TZ).
2. Janela 7d, candidato exato -> 1.0.
3. Janela 7d, candidato 7d antes -> ~0.0.
4. Mock TZ via `os.environ["TZ"] = "UTC"` -> resultado idêntico.
