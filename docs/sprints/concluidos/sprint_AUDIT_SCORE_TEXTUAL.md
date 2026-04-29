---
concluida_em: 2026-04-28
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: AUDIT-SCORE-TEXTUAL
  title: "Score textual robusto -- ignorar palavras genericas e exigir 2+ matches"
  prioridade: P3
  estimativa: ~1h
  origem: "auditoria externa 2026-04-28 P3-02 -- _score_textual usa primeira palavra (pode ser 'BANCO', 'EMPRESA') causando falso-positivo"
  touches:
    - path: src/intake/ocr_fallback_similar.py
      reason: "_score_textual: usar 2+ palavras não-genericas em vez da primeira"
    - path: mappings/ocr_fallback_config.yaml
      reason: "novo campo palavras_genericas_blacklist"
    - path: tests/test_ocr_fallback_similar.py
      reason: "novos testes: 'BANCO BRADESCO' não casa com cupom de cartao Bradesco"
  forbidden:
    - "Mudar threshold de score combinado sem motivo"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_ocr_fallback_similar.py -v"
  acceptance_criteria:
    - "_score_textual ignora 'BANCO', 'EMPRESA', 'COMERCIO', 'SA', 'LTDA' como primeira palavra"
    - "Match exige 2+ palavras não-genericas casadas para retornar > 0.5"
    - "BANCO BRADESCO em cupom Visa generico não casa como similar"
```

---

# Sprint AUDIT-SCORE-TEXTUAL

**Status:** BACKLOG (P3, criada 2026-04-28 pela auditoria externa)

## Motivação

```python
# Atualmente em ocr_fallback_similar.py:198
if fornecedor and len(fornecedor) >= 4 and fornecedor.split()[0] in falho_combinado:
    matches += 1
```

`fornecedor.split()[0]`:
- "AMERICANAS S.A." -> "AMERICANAS" (especifico, OK)
- "BANCO BRADESCO S.A." -> "BANCO" (genérico, casa qualquer cupom de cartão)
- "EMPRESA BRASILEIRA DE CORREIOS" -> "EMPRESA" (genérico)

Score textual fica 0.5 (1/2) mesmo para arquivos completamente não relacionados.

## Implementação

```python
_PALAVRAS_GENERICAS = frozenset({
    "BANCO", "EMPRESA", "COMERCIO", "SA", "S.A.", "LTDA",
    "INDUSTRIA", "SERVICOS", "DISTRIBUIDORA", "CONSULTORIA",
})

def _palavras_especificas(razao: str) -> list[str]:
    """Filtra fornecedor preservando apenas palavras especificas."""
    return [p for p in razao.upper().split() if p not in _PALAVRAS_GENERICAS and len(p) >= 4]


def _score_textual(falho_nome, falho_texto, candidato_meta):
    fornecedor = (candidato_meta.get("razao_social") or "").upper()
    cnpj_raw = candidato_meta.get("cnpj_emitente") or ""
    cnpj = cnpj_raw.replace(".", "").replace("/", "").replace("-", "")
    falho_combinado = (falho_nome.upper() + " " + (falho_texto or "").upper())[:5000]
    matches = 0
    palavras = _palavras_especificas(fornecedor)
    matches += sum(1 for p in palavras[:3] if p in falho_combinado)
    if cnpj and len(cnpj) >= 8 and cnpj[:8] in falho_combinado.replace(" ", ""):
        matches += 1
    return min(1.0, matches / 3.0)
```

## Testes regressivos

1. "AMERICANAS S.A." em cupom Americanas -> score >= 0.33 (1+ palavra especifica).
2. "BANCO BRADESCO" em cupom Visa generico (sem 'BRADESCO') -> score == 0 (BANCO eh generico).
3. "EMPRESA BRASILEIRA DE CORREIOS" em cupom EBC -> score >= 0.66 (BRASILEIRA + CORREIOS).
4. CNPJ raiz casado adiciona +1 match.
