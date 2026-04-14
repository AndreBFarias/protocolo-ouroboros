# Sprint 06 - Integração com Vault Obsidian

## Objetivo

Integrar o pipeline financeiro com o vault Obsidian existente em ~/Controle de Bordo/. Relatórios financeiros devem aparecer automaticamente no vault com backlinks, frontmatter e queries Dataview funcionais.

## Entregas

- [ ] Sync automático: copiar relatório MD para vault após execução de ./run.sh
- [ ] Backlinks entre relatórios mensais, metas e dívidas
- [ ] Frontmatter YAML em cada relatório (tags, aliases, datas, categorias para Dataview)
- [ ] Templates de relatório compatíveis com a estrutura existente do vault
- [ ] Dataview queries pré-configuradas (resumo mensal, evolução de metas, dívidas ativas)

## Dependências

Sprint 5 (relatórios automáticos completos).

## Critério de Sucesso

Relatórios aparecem no vault Obsidian com links navegáveis e queries Dataview retornando dados corretos.

## Nota

O vault já existe em ~/Controle de Bordo/ com estrutura PARA (Projects, Areas, Resources, Archives). A integração deve respeitar essa organização existente.

## Estimativa de Complexidade

**Média.** Maior desafio é manter compatibilidade com a estrutura PARA existente e garantir que frontmatter e backlinks sigam as convenções do vault. Estimativa: 1-1.5 semanas.
