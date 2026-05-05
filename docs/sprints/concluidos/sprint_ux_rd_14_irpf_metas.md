---
concluida_em: 2026-05-05
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: UX-RD-14
  title: "IRPF + Metas reescritos: pacote anual + donuts/gauges"
  prioridade: P1
  estimativa: 3h
  onda: 4
  origem: "mockups 15-irpf.html + 13-metas.html"
  depende_de: [UX-RD-03]
  touches:
    - path: src/dashboard/paginas/irpf.py
      reason: "REESCRITA -- 8 categorias de tags (rendimento_tributavel, isento, dedutivel_medico/educacional, previdencia_privada, imposto_pago, inss_retido, doacao_dedutivel) com totalizadores; card lateral com botão 'Gerar pacote' -> data/aplicacoes/irpf_<ano>/{relatorio.pdf, dados.xlsx, dados.json, originais/}"
    - path: src/dashboard/paginas/metas.py
      reason: "REESCRITA -- donuts financeiros (reserva, casa, carro, etc) + gauges operacionais (cobertura, % determinístico, etc)"
    - path: src/exports/pacote_irpf.py
      reason: "NOVO -- gerador do pacote anual (compila PDF via reportlab + XLSX via openpyxl + JSON + cópia originais)"
    - path: tests/test_irpf_metas_redesign.py
      reason: "NOVO -- 8 testes: 8 categorias presentes, totalizadores corretos, geração pacote produz 4 artefatos, donuts/gauges renderizam"
  forbidden:
    - "Inventar deduções -- só lê de tags reais geradas por src/transform/irpf_tagger.py"
    - "Quebrar Sprint 25 (pacote IRPF) que está em backlog -- absorver lógica se já houver protótipo"
  hipotese:
    - "Sprint 25 (pacote IRPF completo) está em backlog histórico mas pode ter protótipo. Verificar via grep antes."
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_irpf_metas_redesign.py -v"
    - cmd: "make smoke"
  acceptance_criteria:
    - "IRPF: 8 categorias com label uppercase + valor mono + count + checklist 'tem comprovante?'"
    - "Card lateral 'Pacote IRPF <ano>': checklist (rendimentos, deduções, originais) + botão 'Gerar pacote'"
    - "Click 'Gerar pacote' produz data/aplicacoes/irpf_<ano>/{relatorio.pdf, dados.xlsx, dados.json, originais/} (4 artefatos)"
    - "Metas: donuts proporcionais (reserva 100%, ...) + gauges (cobertura 50%, % determinístico, etc)"
    - "Cores donuts: positivo verde, neutro cyan, negativo red"
    - "pytest baseline mantida"
  proof_of_work_esperado: |
    .venv/bin/streamlit run src/dashboard/app.py --server.port 8520 --server.headless true &
    sleep 6
    # ?cluster=Análise&tab=IRPF -- 8 categorias visíveis
    # Click 'Gerar pacote' -> arquivos em data/aplicacoes/irpf_2026/
    ls -la data/aplicacoes/irpf_2026/
    # = relatorio.pdf, dados.xlsx, dados.json, originais/
    # ?cluster=Metas&tab=Metas -- donuts + gauges visíveis
    # screenshot
```

---

# Sprint UX-RD-14 — IRPF + Metas

**Status:** BACKLOG

Sprint funcional importante: o pacote IRPF é **entrega anual real** —
abril/2027 esse botão precisa funcionar. Spec absorve Sprint 25 (backlog
histórico) inclusive.

**Specs absorvidas:** Sprint 25 (pacote IRPF) — backlog histórico fechado.

---

*"O que é deduzível precisa ser comprovável." — princípio do contribuinte*
