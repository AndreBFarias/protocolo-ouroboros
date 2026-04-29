---
concluida_em: 2026-04-26
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 101
  title: "./run.sh --full-cycle: auto-cadeia inbox -> tudo (1 comando vs 2)"
  prioridade: P1
  estimativa: 1h
  origem: "auditoria 2026-04-26 -- NF da inbox não chega ao XLSX se usuario esquecer um dos 2 comandos"
  touches:
    - path: run.sh
      reason: "novo modo --full-cycle"
    - path: scripts/menu_interativo.py
      reason: "opcao 'Processar tudo (inbox + tudo)' em vez de 2 separadas"
  forbidden:
    - "Quebrar comandos --inbox e --tudo separados (mantem retrocompatibilidade)"
  tests:
    - cmd: "./run.sh --full-cycle --dry-run"
    - cmd: "make smoke"
  acceptance_criteria:
    - "./run.sh --full-cycle executa --inbox seguido de --tudo, parando se --inbox falhar"
    - "Comandos --inbox e --tudo separados continuam funcionando (regression)"
    - "Menu interativo ganha opcao '(R) Rota completa: inbox + tudo' como default"
  proof_of_work_esperado: |
    # Cenario do usuario: jogou foto na inbox, quer ver tudo no dashboard
    cp ~/foto-cupom.jpeg inbox/
    ./run.sh --full-cycle
    # Roda --inbox (move + renomeia + classifica)
    # Roda --tudo (extrai + grafo + XLSX)
    ./run.sh --dashboard
```

---

# Sprint 101 -- run.sh --full-cycle

**Status:** BACKLOG (P1, criada 2026-04-26)

Hoje: 2 comandos sequenciais (`--inbox` + `--tudo`). Usuario esquece o segundo. Sprint adiciona `--full-cycle` que faz os 2 em sequencia. Trivial em bash.

---

*"Um comando e melhor que dois quando ambos são sempre rodados juntos." -- principio do menor atrito*
