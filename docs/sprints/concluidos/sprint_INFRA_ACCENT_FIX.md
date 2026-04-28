## 0. SPEC (machine-readable)

```yaml
sprint:
  id: INFRA-ACCENT-FIX
  title: "Limpar 14 violações pré-existentes de acentuação que travavam make lint"
  prioridade: P3
  estimativa: ~30min
  origem: "ESTADO_ATUAL.md alerta -- make lint vermelho impede gauntlet de qualquer sprint subsequente (lição empírica Sprint 68b)"
  touches:
    - path: src/dashboard/tema.py
      reason: "linha 230 docstring de hero_titulo_html mencionava 'numero' cru"
    - path: tests/test_dashboard_tema.py
      reason: "linha 78 docstring de TestSprintUX122HeroSemNumero mencionava 'numero' cru"
    - path: docs/sprints/concluidos/sprint_INFRA_CONSOLIDA_V2.md
      reason: "linhas 72/82 -- 'nao' sem til em texto livre"
    - path: docs/sprints/concluidos/sprint_INFRA_RENAME_HOLERITES.md
      reason: "linha 66 -- 'concluida' sem agudo + 'nao' sem til"
    - path: docs/sprints/concluidos/sprint_UX_125_polish_final_financas.md
      reason: "linhas 74/76 -- 'Analise' sem agudo (3x) + 'sao' sem til"
    - path: docs/sprints/concluidos/sprint_UX_126_polish_iteracao_3.md
      reason: "linhas 78/87 -- 'sao' + 'nao'"
    - path: docs/sprints/concluidos/sprint_UX_127_fixes_busca.md
      reason: "linhas 75/77/81 -- 'nao' (3x) em texto e citação rodapé"
  forbidden:
    - "Renomear identificadores Python (numero como parâmetro de hero_titulo_html permanece)"
    - "Mexer em código que não seja docstring/comentário"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_dashboard_tema.py -q"
    - cmd: "make smoke"
  acceptance_criteria:
    - "make lint exit 0 (zero violações de acentuação)"
    - "pytest tests/test_dashboard_tema.py 126/126 passed (zero regressão)"
    - "make smoke 23/23 checagens + 8/8 contratos aritméticos"
    - "Identificadores Python (numero, descricao) preservados; só docstrings reescritas"
  proof_of_work_esperado: |
    # Antes
    make lint 2>&1 | grep -c "->"   # = 14
    # Depois
    make lint 2>&1 | grep -c "->"   # = 0
```

---

# Sprint INFRA-ACCENT-FIX -- Acentuação herdada

**Status:** CONCLUÍDA (2026-04-27, fechamento pós-Sprint 100)

## Contexto

Após a rodada cluster UX v3 + INFRA-RENAME-HOLERITES, `make lint` ficou vermelho com **14 violações pré-existentes** acumuladas como débito colateral das sprints UX-125/126/127, INFRA-CONSOLIDA-V2, INFRA-RENAME-HOLERITES, e duas em código (`src/dashboard/tema.py:230` e `tests/test_dashboard_tema.py:78`, ambas `numero` cru).

ESTADO_ATUAL.md já formalizava: *"LINT: 12 violações pré-existentes em specs antigas (INFRA-ACCENT-FIX P3 ~30min para limpar)"*. A lição empírica Sprint 68b é clara: lint vermelho herdado bloqueia o gauntlet de qualquer sprint subsequente. Sem fechar isto antes de avançar para INFRA-D2a, o validador da próxima sprint REPROVARIA por contaminação herdada.

## Estratégia aplicada

Por arquivo:

### Python (2 violações em docstring)

`numero` é nome de parâmetro Python de `hero_titulo_html` (sem acento por convenção do projeto: identificadores PT-BR ASCII). A violação estava em texto livre da docstring que mencionava `\`\`numero\`\`` cru. **Não renomeei o parâmetro** -- só reescrevi a docstring para evitar a palavra como token isolado em texto livre, mantendo a referência semântica:

- `tema.py:230` -- antes citava o parâmetro entre crases duplas; agora descreve como "o primeiro parâmetro virou opcional".
- `test_dashboard_tema.py:78` -- antes usava a forma `arg == ''` em prosa livre; agora descreve como "Quando o primeiro arg é ''".

Comportamento e API preservados. Linter Python ignora linhas com `=` adjacente (regra `_e_identificador`), então mencções em assinaturas tipo `numero=''` continuam OK.

### Markdown (12 violações em texto livre)

Substituições diretas das palavras: `nao` → `não`, `sao` → `são`, `Analise` → `Análise`, `concluida` → `concluída`. Em rodapés de citação (princípios), aplicada acentuação completa: `principio` → `princípio`, `poluicao` → `poluição`, `Botao` → `Botão`, `e` (verbo) → `é`.

## Resultado

| Métrica | Antes | Depois |
|---|---|---|
| `make lint` exit | 1 | **0** |
| Violações `'->'` em saída | 14 | **0** |
| `pytest tests/test_dashboard_tema.py` | 126 passed | **126 passed** |
| `make smoke` 8/8 | OK | **OK** |

## Achado meta

Esta é a 3ª sessão consecutiva em que `make lint` quebra por débito de acentuação herdado de sprints anteriores recém-mergeadas. Padrão observado: sprints fechadas em ritmo rápido (5+/dia) deixam o `make lint` vermelho porque o checker de acentuação roda no diretório TODO (incluindo specs novas com texto rascunhado em PT-BR sem acento). 

**Recomendação para sessões futuras**: incluir `make lint` na finalização padrão de cada sprint UX/spec-only (não só em sprints de código), via `scripts/finish_sprint.sh`. Não é escopo desta sprint; abrir como sprint-filha **INFRA-FINISH-LINT** se recorrer.

---

*"Acentuação correta em TUDO -- código, commits, docs, comentários." -- regra inviolável recauchutada*
