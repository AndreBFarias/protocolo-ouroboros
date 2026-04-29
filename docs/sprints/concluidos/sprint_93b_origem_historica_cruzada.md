---
concluida_em: 2026-04-24
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 93b
  title: "Propagar arquivo_origem + investigar extrator < XLSX (família B)"
  depends_on:
    - sprint_id: 93
      artifact: "docs/auditoria_extratores_2026-04-23.md"
  touches:
    - path: src/extractors/c6_cartao.py
      reason: "investigar por que XLSX tem mais linhas que o extrator em volume real"
    - path: src/extractors/nubank_cc.py
      reason: "idem -- variante nubank_pf_cc"
    - path: src/pipeline.py
      reason: "propagar arquivo_origem para coluna nova no XLSX (opcional, se for viável em 1 sprint)"
    - path: src/load/xlsx_writer.py
      reason: "escrever coluna arquivo_origem se já existe no dict de transações"
    - path: docs/auditoria_familia_B_2026-xx-xx.md
      reason: "relatório com diagnóstico + conclusão"
  forbidden:
    - "Alterar schema do grafo (N-para-N inviolável)"
    - "Mexer em c6_cartao e nubank_pf_cc em commits misturados"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/ -q"
    - cmd: "make smoke"
  acceptance_criteria:
    - "Relatório explica por que XLSX tem MAIS tx que o extrator bruto -- hipótese provável: origem histórica (controle_antigo.xlsx) cruzando com banco_origem=c6_cartao ou nubank_pf_cc"
    - "Se confirmado: documentar no relatório, AJUSTAR scripts/auditar_extratores.py para considerar origem histórica"
    - "Se bug: fix atômico por banco"
    - "Opcional: coluna arquivo_origem no XLSX aba extrato permite bisect futuro"
    - "scripts/auditar_extratores.py re-rodado pós-fix -- delta para c6_cartao e nubank_pf_cc reduzido"
```

---

# Sprint 93b — origem histórica cruzada (família B)

**Status:** BACKLOG
**Prioridade:** P1 (tributária de 93a)
**Origem:** `docs/auditoria_extratores_2026-04-23.md` §Família B

## Problema

Sprint 93 detectou que **c6_cartao** (144 tx extrator vs 24 XLSX, delta R$ 21k) e **nubank_pf_cc** (brutos vs XLSX) têm padrão invertido: XLSX tem MENOS transações que o extrator bruto.

Hipótese principal: **origem histórica**. O `controle_antigo.xlsx` importado com `banco_origem="Histórico"` (1181 tx) cobre período 2022-2023 onde c6_cartao e nubank_pf_cc também tinham dados próprios. Mas a importação histórica talvez se sobreponha E substitua transações que o extrator moderno reextrairia.

Hipótese secundária: bug no extrator que agrupa linhas (ex: c6_cartao pulando linhas sem valor).

## Escopo

### Fase 1 -- Diagnóstico

1. Para c6_cartao:
   - Listar tx brutas em volume (144 linhas).
   - Filtrar XLSX por `banco_origem="C6"` e `forma_pagamento="Crédito"` no mesmo mes_ref (24 linhas).
   - Identificar as ~120 linhas "perdidas".
   - Verificar se `banco_origem="Histórico"` no XLSX cobre aquele mes_ref + valores similares.

2. Para nubank_pf_cc: idem, cruzando com Histórico E nubank_cc do André.

### Fase 2 -- Decisão arquitetural

Se origem histórica cobre:
- Documentar no relatório que o delta é ESPERADO (histórico consolidou).
- Ajustar `scripts/auditar_extratores.py` para aceitar "coberto por Histórico" como válido.
- Nenhum fix de código.

Se não é histórico (bug real):
- Fix atômico no parser.
- Teste de regressão.

### Fase 3 -- Opcional: arquivo_origem no XLSX

Se o diagnóstico mostrar que precisamos de mais debugabilidade, adicionar coluna `arquivo_origem` na aba `extrato` do XLSX. O dict de transações já carrega `_arquivo_origem` internamente; basta escrever.

**Cuidado:** essa mudança altera schema do XLSX. Vale fazer só se a investigação mostrar que é crítico. Caso contrário, fica para sprint-filha.

## Armadilhas

- **Import do controle_antigo** roda no pipeline (passo 8), antes do extrair; sobrepõe pode ter substituído linhas novas silenciosamente.
- **Dedup por hash composto** pode unir tx moderna com tx histórica.
- **nubank_pf_cc divergir** pode ser questão diferente: dedup entre contas da Vitória.

---

*"Quando XLSX tem menos que o bruto, pergunte ao histórico antes de culpar o parser." -- princípio da origem rastreável*
