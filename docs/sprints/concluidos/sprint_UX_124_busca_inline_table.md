## 0. SPEC (machine-readable)

```yaml
sprint:
  id: UX-124
  title: "Busca renderiza tabela inline (sem 'Ir para Catalogacao filtrada')"
  prioridade: P1
  estimativa: 3h
  origem: "feedback dono 2026-04-27 (image 17) -- 'ir pra outra pagina nao e uma experiencia legal'; tabela deve aparecer na propria aba Busca Global"
  pre_requisito_de: [Sprint 100]
  touches:
    - path: src/dashboard/paginas/busca.py
      reason: "Quando roteador.kind == 'fornecedor', em vez de st.button('Ir para Catalogacao filtrada'), renderiza st.dataframe inline com transacoes do fornecedor"
    - path: src/dashboard/componentes/busca_resultado_inline.py
      reason: "NOVO -- funcao construir_dataframe_fornecedor(nome, df_extrato, mascarar_pii=True) retorna DataFrame com colunas Data/Valor/Local/Categoria/Banco/Documento"
    - path: tests/test_busca_inline.py
      reason: "NOVO -- 8 testes regressivos: dataframe construido corretamente, PII mascarada, filtro por fornecedor, integracao com filtros sidebar"
  forbidden:
    - "Quebrar Sprint UX-114 (roteador permanece intocado; so a UI de exibicao muda)"
    - "Quebrar mascaramento PII (4 sitios da Sprint 99)"
    - "Adicionar deps externas"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_busca_inline.py -v"
    - cmd: ".venv/bin/pytest tests/test_busca*.py tests/test_dashboard*.py -q"
    - cmd: "make smoke"
  acceptance_criteria:
    - "Quando rotear() retorna kind='fornecedor', UI mostra st.dataframe direto abaixo (sem botao de navegacao)"
    - "Coluna 'Data' (YYYY-MM-DD), 'Valor' (R$ formatado), 'Local' (mascarado para CPF/CNPJ), 'Categoria', 'Banco', 'Documento' (link rapido se houver)"
    - "Filtros sidebar (Mes, Pessoa, Forma de pagamento) impactam tabela inline"
    - "Botao Exportar CSV (UX-114 reusado) preservado abaixo da tabela"
    - "Mensagem 'Resultados para FORNECEDOR_X N transacoes' permanece"
    - "PII mascarada em descricao_original e local conforme padrao Sprint 99 (mascarar_pii)"
    - "Pelo menos 8 testes regressivos: tabela com 0/1/N linhas, mascaramento ativo, filtro por mes, filtro por pessoa, filtro por forma_pagamento, ordenacao por data DESC, integracao com export CSV, ausencia de st.button('Ir para Catalogacao')"
  proof_of_work_esperado: |
    .venv/bin/streamlit run src/dashboard/app.py --server.port 8520 --server.headless true &
    sleep 6
    # http://localhost:8520/?cluster=Documentos
    # Aba Busca Global -> clicar chip 'Boleto' (ou digitar 'BOLETO')
    # Esperado: tabela inline com transacoes do fornecedor BOLETO, SEM botao 'Ir para Catalogacao'

    grep -n "Ir para Catalogacao filtrada" src/dashboard/paginas/busca.py
    # = 0 matches (botao removido)

    grep -n "construir_dataframe_fornecedor\|st.dataframe" src/dashboard/paginas/busca.py
    # = >=2 matches (chamada + import)
```

---

# Sprint UX-124 -- Busca inline

**Status:** CONCLUÍDA (commit `7abda7a`, 2026-04-27 — 16 testes novos, busca renderiza tabela inline)

UX-114 entregou roteador funcional, mas resultado de fornecedor exibe botao 'Ir para Catalogacao filtrada' que NAVEGA para outra aba. Dono quer tabela INLINE na propria Busca Global. Sprint refactora apenas a UI de exibicao (roteador, índice e logica de busca permanecem intocados).

---

*"Resultado deve aparecer onde a busca foi iniciada. Navegar para outra pagina rompe o fluxo." -- principio do contexto preservado*
