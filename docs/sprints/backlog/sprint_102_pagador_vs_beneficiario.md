## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 102
  title: "Pagador vs beneficiario: separar 'quem pagou' de 'quem se beneficia' (cenario IRPF cross-casal)"
  prioridade: P2
  estimativa: 3-4h
  origem: "auditoria 2026-04-26 -- Vitoria paga remedio do Andre via cartao dela; sistema atribui gasto a Vitoria mas dedutivel IRPF eh do Andre"
  touches:
    - path: src/transform/normalizer.py
      reason: "Transacao ganha campo opcional beneficiario alem de quem"
    - path: src/transform/irpf_tagger.py
      reason: "tag dedutivel_medico considera beneficiario, não quem"
    - path: src/load/xlsx_writer.py
      reason: "aba extrato ganha coluna beneficiario (default = quem)"
    - path: src/dashboard/paginas/irpf.py
      reason: "filtro por beneficiario em vez de quem na aba IRPF"
    - path: tests/test_pagador_vs_beneficiario.py
  forbidden:
    - "Quebrar contrato existente (quem default = beneficiario quando não explicitado)"
    - "Inferir beneficiario sem regra YAML (LLM-free)"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_pagador_vs_beneficiario.py -v"
    - cmd: "make smoke"
  acceptance_criteria:
    - "Transacao ganha campo opcional beneficiario (str, default = quem)"
    - "mappings/beneficiario_overrides.yaml permite regras manuais (descrição + beneficiario)"
    - "Aba IRPF do dashboard filtra por beneficiario, não quem"
    - "Cenario teste: tx Vitoria 'DROGARIA SOUZA & FARMA MED EXPRESS R$ 54,93' com override apontando beneficiario=Andre faz aba IRPF do Andre incluir essa despesa medica"
  proof_of_work_esperado: |
    # Antes
    .venv/bin/python -c "
    import openpyxl
    wb = openpyxl.load_workbook('data/output/ouroboros_2026.xlsx', read_only=True)
    irpf = wb['irpf']
    cnt_andre = sum(1 for r in irpf.iter_rows(min_row=2, values_only=True) if r[2] == 'Andre' and r[1] == 'despesa_medica')
    print(f'IRPF Andre despesa_medica: {cnt_andre}')
    "
    # Antes: count baixo (so quando Andre paga diretamente)
    
    # Aplicar override manual em mappings/beneficiario_overrides.yaml:
    #  - descrição: 'DROGARIA SOUZA & FARMA MED EXPRESS'
    #    beneficiario: 'Andre'
    #    razao: 'Lisdexanfetamina prescrita para TDAH do Andre'
    
    ./run.sh --tudo
    # Depois: count cresce, includo despesas pagas pela Vitoria mas para o Andre
```

---

# Sprint 102 -- Pagador vs beneficiario

**Status:** BACKLOG (P2, criada 2026-04-26)

Cenario detectado em 2026-04-26: Vitoria pagou DIMESILATO DE LISDEXANFETAMINA 50MG R$ 279,90 (medicamento controlado para TDAH do Andre). Hoje sistema atribui despesa = Vitoria, mas dedutivel IRPF deveria ir para Andre (se Vitoria for sua dependente OU vice-versa). Sistema precisa separar "quem pagou" (cartao usado) de "quem se beneficiou" (paciente).

Solução declarativa via `mappings/beneficiario_overrides.yaml`. Sem LLM. Humano aprova override apos ver no Sprint D2 revisor.

## Armadilhas

- **Default conservador**: se override não existe, beneficiario = quem (comportamento atual). Nenhum gasto vira IRPF do Andre por inferencia automatica.
- **PII**: overrides.yaml não deve conter receitas medicas literais. Apenas correspondencia descrição -> beneficiario.

---

*"Quem pagou nem sempre eh quem se beneficiou. IRPF reconhece essa diferenca." -- principio fiscal*
