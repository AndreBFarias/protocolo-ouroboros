# Sprint 01 - MVP: Pipeline ETL Financeiro

## Objetivo

Pipeline ETL financeiro mínimo viável. Processar extratos bancários de múltiplos bancos, categorizar transações, deduplicar e gerar saída consolidada em XLSX e relatório Markdown.

## Entregas

- [ ] Scaffold completo (estrutura de pastas, pyproject.toml, install.sh, run.sh)
- [ ] Inbox processor inteligente (detecta banco/tipo/pessoa, renomeia, move)
- [ ] Extrator Nubank CSV - formato cartão de crédito
- [ ] Extrator Nubank CSV - formato conta corrente
- [ ] Extrator C6 XLSX - conta corrente
- [ ] Extrator C6 XLS - fatura cartão
- [ ] Extrator Itaú PDF - extrato protegido por senha
- [ ] Extrator Santander PDF - fatura cartão Black Way
- [ ] Categorizador regex base (mappings iniciais por padrão de descrição)
- [ ] Deduplicador (UUID + hash + detecção de pares de transferência)
- [ ] XLSX writer (gera planilha com 8 abas)
- [ ] Relatório MD mensal (resumo textual por mês)
- [ ] Importação de histórico do XLSX antigo (migração de dados legados)

## Dependências

Nenhuma. Este é o sprint fundacional.

## Critério de Sucesso

`./run.sh --tudo` roda sem erros, gera XLSX consolidado + relatório Markdown mensal a partir dos extratos no inbox.

## Estimativa de Complexidade

**Alta.** Sprint mais denso do projeto. Envolve definição de arquitetura, múltiplos parsers com formatos distintos, lógica de deduplicação e geração de saída. Estimativa: 3-4 semanas.
