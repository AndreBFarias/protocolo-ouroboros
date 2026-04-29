---
concluida_em: 2026-04-28
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: AUDIT-CONTRIBUINTE-METADATA
  title: "Sempre gravar metadata.contribuinte (mesmo vazio) em fornecedor sintetico"
  prioridade: P1
  estimativa: ~30min
  origem: "auditoria externa 2026-04-28 P1-02 -- contribuinte vazio não gravado quando razao_social ausente"
  touches:
    - path: src/graph/ingestor_documento.py
      reason: "linha 482-483 -- condicional 'if sintetico is not None and documento.get(...)' pula gravacao"
    - path: tests/test_fornecedor_sintetico_impostos.py
      reason: "novo teste: documento sem razao_social ainda grava metadata.contribuinte=''"
  forbidden:
    - "Mudar comportamento quando contribuinte tem valor (preserva hoje)"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_fornecedor_sintetico_impostos.py -v"
  acceptance_criteria:
    - "Documento sintetico sem razao_social grava metadata.contribuinte=''"
    - "Documento sintetico com razao_social preserva valor (sem regressao)"
    - "Audtoria via SQL pode consultar contribuinte sempre que tipo_documento eh sintetico"
```

---

# Sprint AUDIT-CONTRIBUINTE-METADATA

**Status:** BACKLOG (P1, criada 2026-04-28 pela auditoria externa)

## Motivação

Auditoria externa achou: em `src/graph/ingestor_documento.py:482-483`, a condicional só grava `metadata.contribuinte` quando `razao_social` original é truthy. Para documentos sem razao_social, o campo nunca é gravado -- audtoria fica cega ("o sintetico foi aplicado mas não sabemos qual era o contribuinte").

## Implementação

```python
if sintetico is not None:
    # Sempre grava (mesmo vazio) para sinalizar que sintetico foi aplicado
    metadata["contribuinte"] = documento.get("__contribuinte_original", "")
```

## Testes regressivos

- DAS PARCSN sem razao_social -> metadata.contribuinte == "".
- DAS PARCSN com razao_social -> metadata.contribuinte == "ANDRE...".
- NFCe (não-sintetico) -> metadata sem chave 'contribuinte' (preserva hoje).
