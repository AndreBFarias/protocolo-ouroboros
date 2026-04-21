## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 58
  title: "Atualizar CLAUDE.md e VALIDATOR_BRIEF.md com contagens reais"
  touches:
    - path: CLAUDE.md
      reason: "contagens do grafo desatualizadas; aba Análise não é DEPRECATED; Contas sem cabeçalho"
    - path: VALIDATOR_BRIEF.md
      reason: "histórico de sprints + padrões recorrentes + referência ao smoke aritmético"
    - path: docs/ROADMAP.md
      reason: "refletir sprints 55-66 no estado atual"
    - path: data/grafo.sqlite
      reason: "remover arquivo órfão de 0 bytes na raiz de data/"
  n_to_n_pairs:
    - ["CLAUDE.md:TRANSAÇÕES", "contagem real do ouroboros_2026.xlsx"]
    - ["CLAUDE.md:IRPF TAGS", "contagem real edge irpf no grafo"]
    - ["CLAUDE.md:SPRINTS", "estado real em docs/sprints/"]
  forbidden: []
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: ".venv/bin/python scripts/check_acentuacao.py --all"
      timeout: 30
    - cmd: "test ! -f data/grafo.sqlite"
      timeout: 5
  acceptance_criteria:
    - "CLAUDE.md header reflete contagens reais verificadas via query SQLite/pandas"
    - "Afirmação 'aba Análise marcada como DEPRECATED' removida — aba tem Sankey + Heatmap ricos"
    - "Contagem de sprints bate com realidade (arquivadas + concluídas + backlog)"
    - "VALIDATOR_BRIEF.md rodapé registra sprint 55-66 como follow-ups da auditoria 2026-04-21"
    - "VALIDATOR_BRIEF.md Contratos de Runtime referencia scripts/smoke_aritmetico.py (Sprint 56)"
    - "data/grafo.sqlite (0 bytes, raiz) removido; apenas data/output/grafo.sqlite ativo"
  proof_of_work_esperado: |
    .venv/bin/python <<'EOF'
    import sqlite3, pandas as pd
    con = sqlite3.connect('data/output/grafo.sqlite')
    n_nodes = con.execute("SELECT COUNT(*) FROM node").fetchone()[0]
    n_edges = con.execute("SELECT COUNT(*) FROM edge").fetchone()[0]
    df = pd.read_excel('data/output/ouroboros_2026.xlsx', sheet_name='extrato')
    # CLAUDE.md deve mencionar esses 2 números exatos
    import re
    conteudo = open('CLAUDE.md').read()
    assert str(n_nodes) in conteudo, f"CLAUDE.md não tem {n_nodes}"
    assert str(len(df)) in conteudo, f"CLAUDE.md não tem total transações={len(df)}"
    print(f"OK nodes={n_nodes} edges={n_edges} transacoes={len(df)}")
    EOF
```

---

# Sprint 58 — Atualizar docs de contexto

**Status:** BACKLOG
**Prioridade:** P2
**Dependências:** Sprint 55 (contagens novas) e Sprint 56 (referenciar smoke) recomendadas
**Issue:** AUDIT-2026-04-21-4

## Problema

Auditoria 2026-04-21 identificou divergências entre documentação e realidade:

| Item | CLAUDE.md diz | Realidade |
|---|---|---|
| Nodes no grafo | 7.378 | 7.417 |
| Edges no grafo | 24.506 | 24.572 |
| IRPF tags | 167 | 164 |
| Aba Análise | "DEPRECATED" | Sankey + Heatmap ricos |
| Contas aviso | "cabeçalho linha 1" | não aparece no dashboard |
| data/grafo.sqlite | não mencionado | arquivo órfão 0 bytes |

## Implementação

### Fase 1 — Recalcular e atualizar CLAUDE.md header

Linhas 2-10 do CLAUDE.md com os valores reais (obter via query).

### Fase 2 — Corrigir afirmações falsas

- Remover "[DEPRECATED]" das referências à aba análise.
- Atualizar descrição da aba Contas (não exibe snapshot).
- Atualizar seção "Mentiras corrigidas nesta revisão" com as novas descobertas.

### Fase 3 — Atualizar VALIDATOR_BRIEF.md

Adicionar rodapé:
```
*Atualizado em 2026-04-21 por validador manual (auditoria profunda dashboard):
 identificou bug estrutural #1 (classificador de tipo) que gerou sprints 55-66.
 Contratos runtime-real expandidos via scripts/smoke_aritmetico.py (Sprint 56).*
```

### Fase 4 — Limpar arquivo órfão

```bash
rm data/grafo.sqlite  # 0 bytes, não usado
```

Adicionar em `.gitignore` se não estiver.

## Evidências Obrigatórias

- [ ] CLAUDE.md header com contagens reais
- [ ] VALIDATOR_BRIEF.md rodapé atualizado
- [ ] data/grafo.sqlite órfão removido
- [ ] Proof-of-work script verde

---

*"Documentação que mente é pior que silêncio." — princípio"*
