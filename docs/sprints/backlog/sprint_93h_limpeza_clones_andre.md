---
id: 93H-LIMPEZA-CLONES-ANDRE
titulo: 0. SPEC (machine-readable)
status: backlog
concluida_em: null
prioridade: P2
data_criacao: '2026-04-26'
fase: OUTROS
epico: 0
depende_de: []
tipo_documental_alvo: null
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 93h
  title: "Limpeza simetrica de clones SHA nas pastas do Andre (depois da Sprint 93g focar em PJ)"
  prioridade: P2
  estimativa: 30min
  origem: "auditoria 2026-04-26 ETL -- itau_cc 7.25x, santander 7.29x, c6_cartao 8x, nubank_cartao 8x clones"
  depends_on:
    - "Sprint 90a (preferencialmente concluída -- previne novos clones de holerites mal classificados)"
    - "Sprint 98 (renomeacao retroativa -- migra os holerites antes da limpeza)"
  touches:
    - path: scripts/limpar_clones_andre.py
      reason: "script one-shot complementar ao da Sprint 93g (que cobriu PJ Vitoria)"
  forbidden:
    - "Apagar arquivos em data/raw/originais/"
    - "Apagar SHAs unicos (apenas duplicatas)"
  tests:
    - cmd: ".venv/bin/python scripts/limpar_clones_andre.py --dry-run"
  acceptance_criteria:
    - "Script com --dry-run e --executar"
    - "Apos --executar, andre/itau_cc passa de 29 -> 4 fisicos (1 Itau real + 3 holerites apos Sprint 98 = so 1 fisico se Sprint 98 ja rodou)"
    - "andre/santander_cartao 102 -> 14 ou menos"
    - "andre/c6_cartao 24 -> 3"
    - "andre/nubank_cartao 32 -> 4"
    - "Log em scripts/limpeza_clones_andre_<data>.log"
  proof_of_work_esperado: |
    # Antes
    find data/raw/andre/itau_cc -name '*.pdf' | wc -l       # 29
    find data/raw/andre/itau_cc -name '*.pdf' | xargs -I{} sha256sum {} | sort -u | wc -l  # 4
    
    # Dry-run lista 25 deletes propostos
    .venv/bin/python scripts/limpar_clones_andre.py --dry-run
    
    # Executa
    .venv/bin/python scripts/limpar_clones_andre.py --executar
    
    # Depois
    find data/raw/andre/itau_cc -name '*.pdf' | wc -l       # 4
```

---

# Sprint 93h -- Limpeza simetrica clones SHA pastas do Andre

**Status:** BACKLOG (P2, criada 2026-04-26)

Sprint 93g (concluída 2026-04-24) deletou 91 clones de `vitoria/nubank_pj_*` e `andre/nubank_*`. Mas não tocou em `andre/itau_cc/`, `santander_cartao/`, `c6_cartao/`. Auditoria 2026-04-26 mostra ratios 7-8x persistentes. Sprint trivial: replica logica do 93g para essas pastas.

Idealmente roda DEPOIS de 90a + 98 (para que holerites mal classificados ja tenham sido movidos para `holerites/` antes de qualquer limpeza tocar em `itau_cc/`).

---

*"Simetria entre pessoas. Se Vitoria foi limpa, Andre também deve ser." -- principio anti-tendencia*
