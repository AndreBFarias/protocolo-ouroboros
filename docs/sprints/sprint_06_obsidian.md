# Sprint 06 -- Integração Obsidian

## Status: Em andamento
Issue: #6

## Objetivo

Integrar o pipeline financeiro com o vault Obsidian existente. Relatórios financeiros devem aparecer automaticamente no vault com backlinks, frontmatter YAML e queries Dataview funcionais.

## Entregas

- [ ] Sync automático para vault após execução do pipeline
- [ ] Frontmatter YAML em cada relatório (tags, aliases, datas)
- [ ] Backlinks entre relatórios mensais, metas e dívidas
- [ ] Dataview queries pré-configuradas (resumo mensal, evolução de metas)
- [ ] MOC (Map of Content) financeiro

## Armadilhas conhecidas

- Código criado por subagente sem validação completa (créditos esgotados antes de testar)
- Vault existe em ~/Controle de Bordo/ com estrutura PARA -- integração deve respeitar essa organização
- Frontmatter precisa ser compatível com plugins Dataview e Templater

## Arquivos criados/modificados

| Arquivo | Descrição |
|---------|-----------|
| `src/obsidian/__init__.py` | Init do módulo obsidian |
| `src/obsidian/sync.py` | Sincronizador vault-pipeline (349 linhas) |
| `run.sh` | Modificado: flag --sync adicionada |

## Critério de sucesso

Relatórios aparecem no vault com frontmatter correto. Dataview queries retornam dados corretos. Backlinks navegáveis entre documentos.

## Dependências

Sprint 05 (relatórios automáticos completos).
