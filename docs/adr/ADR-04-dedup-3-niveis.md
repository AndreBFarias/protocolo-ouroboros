# ADR-04: Deduplicação em 3 níveis

## Status: Aceita

## Contexto

A mesma transação pode aparecer em múltiplas fontes:
- Pagamento de cartão Nubank aparece no extrato CC (como débito) e na fatura do cartão (como crédito)
- Arquivos duplicados na inbox (usuário arrasta "(1)", "(2)" do mesmo arquivo)
- PIX entre contas próprias aparece como saída em um banco e entrada em outro

Sem deduplicação, o total de despesas fica inflado e transferências internas contam como gastos.

## Decisão

Implementar deduplicação em 3 níveis complementares:

1. **UUID (Nubank CC)**: O extrato CSV do Nubank inclui coluna `Identificador` única por transação. Usado como chave primária para eliminar cópias exatas do mesmo arquivo.

2. **Hash cross-source**: Para transações sem UUID nativo, gera hash baseado em (data, valor_absoluto, descricao_normalizada). Detecta a mesma transação vinda de fontes diferentes.

3. **Pares de transferência**: Identifica pares débito/crédito entre contas próprias (ex: -R$500 Itaú + R$500 Nubank no mesmo dia) e marca ambos como `Transferência Interna`.

## Consequências

**Positivas:**
- Zero falsos positivos confirmados: nenhuma transação legítima foi removida indevidamente
- UUID do Nubank é confiável e elimina 100% das duplicatas de arquivos "(1)", "(2)"
- Pares de transferência evitam contar movimentação entre contas como gasto

**Negativas:**
- 16 coincidências legítimas residuais: transações diferentes com mesmo hash (mesmo valor, mesma data, descrição similar). Aceitas como margem tolerável.
- Hash cross-source depende de normalização de descrição, que varia entre bancos
- Deduplicação PIX entre contas próprias ainda é incompleta (hash não é suficiente quando descrições divergem)
- Deduplicação cruzada CC x cartão não totalmente resolvida (pendente)

---

*"É melhor estar aproximadamente certo do que precisamente errado." -- John Maynard Keynes*
