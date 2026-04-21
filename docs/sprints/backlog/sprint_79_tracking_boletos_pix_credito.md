## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 79
  title: "Aba Pagamentos: tracking por forma (boletos/pix/crédito) com status e vencimentos"
  touches:
    - path: src/dashboard/paginas/pagamentos.py
      reason: "nova aba com 3 seções (Boletos, Pix, Crédito)"
    - path: src/analysis/pagamentos.py
      reason: "lógica de agrupamento e status"
    - path: src/dashboard/app.py
      reason: "registrar aba"
    - path: tests/test_pagamentos.py
      reason: "testes"
  n_to_n_pairs: []
  forbidden: []
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: ".venv/bin/pytest tests/test_pagamentos.py -v"
      timeout: 60
  acceptance_criteria:
    - "Nova aba 'Pagamentos' com 3 seções: Boletos, Pix, Crédito"
    - "Boletos: tabela com fornecedor/valor/vencimento/status (pago/pendente/atrasado), baseado na tabela `prazos` + grafo"
    - "Pix: agrupa pix por beneficiário top 20, total mensal, tendência"
    - "Crédito: faturas por cartão e mês, dia de corte/vencimento, total usado vs limite (se disponível)"
    - "Filtro forma de pagamento (Sprint 72) integrado nesta aba"
    - "Alertas: 'Fatura Nubank PF vence em 3 dias e ainda não foi paga'"
  proof_of_work_esperado: |
    # Screenshot das 3 seções
    # Teste: boleto pendente identificado corretamente
```

---

# Sprint 79 — Aba Pagamentos

**Status:** BACKLOG
**Prioridade:** P2
**Dependências:** Sprints 72 (filtro forma), 74 (vínculo doc-transação)
**Issue:** UX-ANDRE-07

## Problema

Andre quer rastreabilidade por forma de pagamento: ver todos os boletos juntos, todas as faturas de cartão, todos os pix acumulados.

## Implementação

```python
def renderizar():
    st.header("Pagamentos")
    tab_boletos, tab_pix, tab_credito = st.tabs(["Boletos", "Pix", "Crédito"])

    with tab_boletos:
        df = carregar_boletos()
        st.dataframe(df)
        alertas = identificar_vencimentos_proximos(df)
        for a in alertas:
            st.warning(a)

    with tab_pix:
        df = carregar_pix()
        top_beneficiarios = df.groupby("local")["valor"].sum().nlargest(20)
        st.bar_chart(top_beneficiarios)
        st.caption(f"Top 20 beneficiários de Pix: {top_beneficiarios.sum():,.2f}")

    with tab_credito:
        faturas = carregar_faturas_credito()
        for cartao, df_cartao in faturas.items():
            st.subheader(cartao)
            st.line_chart(df_cartao.set_index("mes_ref")["valor"])
```

## Evidências

- [ ] 3 seções funcionais
- [ ] Alertas de vencimento

---

*"Por forma de pagamento é como o banco pensa; precisamos pensar assim também." — princípio"*
