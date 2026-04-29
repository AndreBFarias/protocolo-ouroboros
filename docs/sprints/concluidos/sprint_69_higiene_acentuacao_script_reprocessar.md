---
concluida_em: 2026-04-21
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 69
  title: "Higiene: acentuação PT-BR em scripts/reprocessar_documentos.py (INFRA)"
  touches:
    - path: scripts/reprocessar_documentos.py
      reason: "acentuação ausente em docstrings/prosa (Sprint 57 criou com lint desligado)"
  n_to_n_pairs: []
  forbidden: []
  tests:
    - cmd: "make lint"
      timeout: 60
  acceptance_criteria:
    - "make lint exit 0 sem suprimir ou adicionar # noqa para palavras PT-BR humanas"
    - "Violações atuais corrigidas: 'implementacao'→'implementação', 'codigo'→'código', 'nao'→'não', 'Nao'→'Não'"
    - "Identificador técnico 'periodo' em tupla de tipos canônicos do schema permanece sem acento (contrato N-para-N), mas com # noqa: accent explícito"
  proof_of_work_esperado: |
    make lint
    echo "exit=$?"
```

---

# Sprint 69 — Higiene acentuação script Sprint 57

**Status:** BACKLOG
**Prioridade:** P3
**Dependências:** nenhuma
**Issue:** SMOKE-M56-1

## Problema

`scripts/reprocessar_documentos.py` (criado pela Sprint 57) tem 7 violações de acentuação em prosa PT-BR humana (linhas 34, 36, 42, 345, 417). Sprint 57 finalizou com `make lint` exit 0 porque o checker oficial do projeto (`scripts/check_acentuacao.py`) trata contextualmente, mas o validador global reportou.

## Implementação

```bash
sed -i \
    -e 's/\bimplementacao\b/implementação/g' \
    -e 's/\bcodigo\b/código/g' \
    -e 's/\bnao\b/não/g' \
    -e 's/\bNao\b/Não/g' \
    scripts/reprocessar_documentos.py
```

Revisar o identificador técnico `periodo` na linha 282 (ou 245, checar): se é literal em tupla `("transacao", "documento", "periodo", ...)` que participa de contrato N-para-N com `src/graph/ingestor_documento.py`, adicionar `# noqa: accent` inline.

Rodar `make lint` e confirmar exit 0.

## Evidências Obrigatórias

- [ ] `make lint` exit 0
- [ ] Zero violações reais em prosa
- [ ] `# noqa: accent` aplicado só em identificadores técnicos

---

*"Deixar débito pequeno acumula ruído grande." — princípio de higiene"*
