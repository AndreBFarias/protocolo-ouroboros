---
concluida_em: 2026-05-04
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: UX-RD-07
  title: "Contas + Pagamentos reescritos com cards de utilização e calendário 14d"
  prioridade: P0
  estimativa: 3h
  onda: 2
  origem: "mockups 03-contas.html + 04-pagamentos.html"
  depende_de: [UX-RD-03]
  touches:
    - path: src/dashboard/paginas/contas.py
      reason: "REESCRITA -- cards de contas (Itaú/Santander/C6/Nubank) + cards de cartões com progress bar de utilização (cor D7 conforme threshold). Aviso 'Snapshot 2023' com data dinâmica via mtime XLSX."
    - path: src/dashboard/paginas/pagamentos.py
      reason: "REESCRITA -- calendário próximos 14 dias (grid 7x2) com pillules nos dias que têm vencimento + lista detalhada lado direito"
    - path: tests/test_contas_pagamentos_redesign.py
      reason: "NOVO -- 6 testes: cards renderizam, utilização >80% pinta laranja, >100% vermelho, calendário 14 cells, lista vencimentos ordenada por data"
  forbidden:
    - "Tocar src/load/xlsx_writer.py (estrutura dos snapshots)"
    - "Hardcodar limites de utilização -- usar tokens D7 calibracao=80%, regredindo=100%"
  hipotese:
    - "contas.py linha 26-30 tem aviso hardcoded 'snapshot 2023'. Substituir por mtime do XLSX."
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_contas_pagamentos_redesign.py -v"
    - cmd: "make smoke"
  acceptance_criteria:
    - "Contas: card por banco com saldo atual + variação 30d + ícone glyph"
    - "Cartões: card por cartão com limite/uso/disponível + progress bar colorida (D7 graduado <60%, calibracao 60-80%, regredindo 80-100%, alerta >=100%)"
    - "Aviso snapshot com data dinâmica: 'Snapshot de DD/MM/YYYY -- atualização manual'"
    - "Pagamentos: calendário 7x2 com hoje destacado + dias com vencimento marcados (dot purple)"
    - "Lista vencimentos: data | conta | valor | banco_pagamento | auto_debito (toggle)"
    - "Deep-link ?cluster=Finanças&tab=Contas e tab=Pagamentos preservados"
    - "pytest baseline mantida"
  proof_of_work_esperado: |
    .venv/bin/streamlit run src/dashboard/app.py --server.port 8520 --server.headless true &
    sleep 6
    # 1. http://localhost:8520/?cluster=Finanças&tab=Contas -- cards visíveis, utilização colorida
    # 2. http://localhost:8520/?cluster=Finanças&tab=Pagamentos -- calendário 14d
    # screenshots vs 03-contas.html e 04-pagamentos.html
```

---

# Sprint UX-RD-07 — Contas + Pagamentos

**Status:** BACKLOG

**Specs absorvidas:** UX-07 (snapshot dinâmico contas — agora coberto).

---

*"O tempo não para; nossas contas também não." — adaptado de Cazuza*
