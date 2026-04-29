---
concluida_em: 2026-04-28
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: AUDIT-IMPORT-CAMADA
  title: "Mover _extrair_preview de scripts/ para src/intake/preview.py (camada correta)"
  prioridade: P2
  estimativa: ~45min
  origem: "auditoria externa 2026-04-28 P2-01 -- src/intake/ocr_fallback_similar.py:349 importa de scripts/migrar_pessoa_via_cpf -- inversao de camada"
  touches:
    - path: src/intake/preview.py
      reason: "adicionar funcao _extrair_preview / extrair_preview publico"
    - path: scripts/migrar_pessoa_via_cpf.py
      reason: "trocar definicao local por import de src.intake.preview"
    - path: src/intake/ocr_fallback_similar.py
      reason: "trocar import lazy por import top-level de src.intake.preview"
    - path: tests/test_ocr_fallback_similar.py
      reason: "testes ja usam funcao indireta via reanalisar_pasta_conferir; verificar zero regressao"
  forbidden:
    - "Quebrar API publica de migrar_pessoa_via_cpf (preservar via re-export)"
  tests:
    - cmd: "make lint"
    - cmd: 'grep -rn "from scripts" src/ | wc -l  # esperado 0'
    - cmd: ".venv/bin/pytest tests/ -q"
  acceptance_criteria:
    - "src/ NAO contem nenhum 'from scripts.' ou 'import scripts.'"
    - "extrair_preview() exposto em src/intake/preview.py com mesma assinatura"
    - "scripts/migrar_pessoa_via_cpf.py importa do src/intake/preview"
    - "Validador futuro: grep -r 'from scripts\\.' src/ deve retornar vazio"
```

---

# Sprint AUDIT-IMPORT-CAMADA

**Status:** BACKLOG (P2, criada 2026-04-28 pela auditoria externa)

## Motivação

`src/intake/ocr_fallback_similar.py:349` faz import lazy:
```python
from scripts.migrar_pessoa_via_cpf import _extrair_preview as _ocr
```

Isso eh inversao de camada: `src/` (canone) nunca deveria importar de `scripts/` (operacional). `_extrair_preview` eh helper genérico de OCR/leitura de texto que pertence a `src/intake/preview.py` (modulo que ja existe).

## Implementação

1. Mover `_extrair_preview` para `src/intake/preview.py` (renomear publico para `extrair_preview`).
2. `scripts/migrar_pessoa_via_cpf.py` importa de `src.intake.preview`.
3. `src/intake/ocr_fallback_similar.py` troca import lazy por top-level.
4. Re-export em `scripts/migrar_pessoa_via_cpf` se houver backward-compat.

## Padrão canônico para registrar

`src/` nunca importa de `scripts/`. Validador futuro: `grep -r 'from scripts\.' src/ tests/test_*.py` deve retornar vazio.
