# Sprint 04 - Inteligência de Categorização e Validação

## Objetivo

Elevar a precisão da categorização com aprendizado incremental, implementar deduplicação cruzada entre contas, adicionar tagging automático para IRPF e criar validador de integridade do pipeline.

## Entregas

- [ ] Categorizer aprendiz: leitura de overrides.yaml, detecção de novos padrões não mapeados
- [ ] Deduplicação inteligente: cruzamento CC x cartão de crédito
- [ ] Deduplicação inteligente: detecção de PIX entre contas próprias
- [ ] Deduplicação inteligente: mesma transação presente em 2 extratos distintos
- [ ] Tag IRPF automática: rendimentos tributáveis
- [ ] Tag IRPF automática: rendimentos isentos
- [ ] Tag IRPF automática: despesas dedutíveis
- [ ] Tag IRPF automática: impostos retidos
- [ ] Tag IRPF automática: saldos em 31/12
- [ ] Validador de integridade: receitas vs holerites
- [ ] Validador de integridade: conferência de saldos bancários
- [ ] Validador de integridade: alerta de transações sem categoria

## Dependências

Sprint 3 (dashboard funcional para visualização dos resultados de validação).

## Critério de Sucesso

Validador roda sem erros críticos. >= 95% das transações categorizadas automaticamente. Tags IRPF aplicadas corretamente nas transações elegíveis.

## Estimativa de Complexidade

**Alta.** Lógica de cruzamento entre fontes de dados, heurísticas de deduplicação e regras fiscais exigem atenção a edge cases. Estimativa: 2-3 semanas.
