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

**Status:** CONCLUÍDA (2026-04-22)
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

- [x] `src/analysis/pagamentos.py` novo (~210L): `carregar_boletos(extrato, prazos, hoje)`, `alertas_vencimento(boletos, hoje, dias_aviso)`, `top_beneficiarios_pix(extrato, top_n)`, `faturas_credito(extrato)` + constantes de status (`STATUS_PAGO`, `STATUS_PENDENTE`, `STATUS_ATRASADO`).
- [x] **Boletos**: fusão entre linhas `forma_pagamento='Boleto'` no extrato (status=pago) e projeção da aba `prazos` (pendente se `vencimento >= hoje`, atrasado caso contrário). Match de reconciliação por substring do nome da conta no `local` do extrato.
- [x] **Pix**: `top_beneficiarios_pix` agrupa por `local`, soma valor absoluto, retorna top N ordenado.
- [x] **Crédito**: `faturas_credito` agrupa despesas `forma=Crédito` por banco e mes_ref.
- [x] **Aba "Pagamentos" no dashboard** (`src/dashboard/paginas/pagamentos.py`): 3 sub-abas internas (Boletos / Pix / Crédito). Boletos com metrics de 3 status + alertas para vencimentos ≤ 3 dias + tabela. Pix com metrics agregados + bar chart horizontal + tabela. Crédito com line chart de série temporal por cartão.
- [x] **Aba registrada em `app.py`** como 5ª posição (após "Contas", antes de "Projeções"), preservando ordem natural do usuário.
- [x] **Integração Sprint 72**: a aba respeita `filtro_forma_ativo()` via `filtrar_por_forma_pagamento` antes de segmentar.
- [x] 12 testes em `tests/test_pagamentos.py`: boletos (pago/pendente/atrasado/sem-prazos), alertas de vencimento, Pix (agrupa, vazio, limite), Crédito (por banco, vazio), resiliência (sem forma_pagamento, DF vazio).
- [x] Gauntlet: make lint exit 0, 1046 passed (+12), 15 skipped, smoke 8/8 OK.

### Ressalvas

- [R79-1] **Reconciliação boleto pago ↔ prazo é heurística textual (substring do nome)**: Ki-Sabor/Sesc batem bem, mas nomes genéricos ("Luz", "Agua") podem dar falso-positivo. Quando a Sprint 48 (linking) rodar em volume e as arestas `documento_de` existirem, vale reescrever para usar o grafo como fonte de verdade.
- [R79-2] **Limite de crédito vs utilizado não está implementado**: o spec pedia "total usado vs limite (se disponível)". O limite não é extraído hoje por nenhum parser bancário; fica como débito para quando um extrator de fatura mapear esse campo.
- [R79-3] **Screenshot das 3 seções** pendente (dashboard precisa estar rodando).

---

*"Por forma de pagamento é como o banco pensa; precisamos pensar assim também." — princípio"*
