---
concluida_em: 2026-05-04
debito_associado: DEBT-UX-RD-06.A
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: UX-RD-06
  title: "Extrato reescrito: tabela densa + breakdown lateral + drawer JSON"
  prioridade: P0
  estimativa: 4h
  onda: 2
  origem: "mockup novo-mockup/mockups/02-extrato.html"
  depende_de: [UX-RD-03]
  touches:
    - path: src/dashboard/paginas/extrato.py
      reason: "REESCRITA -- substitui st.dataframe por tabela HTML densa (.table) com row-h 32px, sticky header, JetBrains Mono em valores, hover/selected; breakdown lateral por categoria; saldo no topo"
    - path: src/dashboard/componentes/drawer_transacao.py
      reason: "NOVO -- drawer lateral 480px slide-in ao clicar linha; mostra JSON syntax-highlighted (.syn-key/string/number/bool/null) da transação + documento vinculado se houver"
    - path: tests/test_extrato_redesign.py
      reason: "NOVO -- 8 testes: tabela renderiza N linhas, breakdown soma == total, drawer abre/fecha, JSON sintático correto, deep-link ?cluster=Finanças&tab=Extrato preservado"
  forbidden:
    - "Tocar dados.py ou filtros (preservar comportamento atual)"
    - "Quebrar exportação CSV se existir"
    - "Quebrar autocomplete da busca global (UX-114)"
  hipotese:
    - "extrato.py atual (473L) usa st.dataframe + st.columns. Mockup pede tabela HTML custom. Confirmar via grep st.dataframe."
    - "Drawer no Streamlit: precisa de st.components.v1.html ou container fixed-position via CSS. Streamlit não tem drawer nativo."
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_extrato_redesign.py -v"
    - cmd: ".venv/bin/pytest tests/ -q"
    - cmd: "make smoke"
  acceptance_criteria:
    - "Saldo no topo: card com valor mono 32px + delta vs mês anterior"
    - "Tabela densa: row-h 32px, sticky thead, mono em valor/data, hover bg var(--bg-elevated)"
    - "Colunas: Data | Descrição | Categoria (com pill) | Valor (right-align mono tabular-nums) | Forma | Pessoa | Doc?"
    - "Breakdown lateral (1fr direita): top 5 categorias + barra horizontal proporcional + valor"
    - "Clicar linha: drawer abre com JSON formatado, syntax highlight (rosa/amarelo/roxo/laranja)"
    - "50+ linhas renderizam sem flicker visível (<200ms)"
    - "tabular-nums em todos os valores (alinhamento perfeito)"
    - "Deep-link ?cluster=Finanças&tab=Extrato funciona"
    - "pytest baseline mantida"
  proof_of_work_esperado: |
    grep -c "st.dataframe\|st.column" src/dashboard/paginas/extrato.py

    .venv/bin/streamlit run src/dashboard/app.py --server.port 8520 --server.headless true &
    sleep 6
    # 1. http://localhost:8520/?cluster=Finanças&tab=Extrato
    # 2. Conferir saldo topo + tabela densa + breakdown lateral
    # 3. Clicar linha 5 -> drawer abre com JSON da transação + syntax highlight
    # 4. Conferir alinhamento tabular: valores R$ alinhados pela vírgula
    # screenshot UX-RD-06.png vs 02-extrato.html
```

---

# Sprint UX-RD-06 — Extrato reescrito

**Status:** BACKLOG

Página mais densa do dashboard. Validação visual atenta a:
- alinhamento numérico (tabular-nums tem que funcionar);
- velocidade (50+ linhas sem lag);
- drawer com JSON syntax highlight (cores casam tokens --syn-*).

**Specs absorvidas:** nenhuma direta. UX-72 (filtro forma de pagamento) é
preservado como filtro de sidebar — drawer não duplica.

---

*"Os números não mentem; só precisam estar alinhados." — princípio tipográfico*
