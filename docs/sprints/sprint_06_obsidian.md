# Sprint 06 -- Integração Obsidian

## Status: Código integrado, validação superficial (issue #6 reaberta)
Issue: #6 (reaberta)

## Objetivo

Integrar o pipeline financeiro com o vault Obsidian existente em ~/Controle de Bordo/. Relatórios financeiros devem aparecer no vault com backlinks, frontmatter e queries Dataview.

## Entregas

- [x] Sync automático: copia relatórios MD para vault após execução
- [x] Frontmatter YAML em cada relatório (tipo, mês, receita, despesa, saldo, tags)
- [x] 44 relatórios sincronizados para ~/Controle de Bordo/Pessoal/Financeiro/Relatórios/
- [x] 7 notas de metas criadas em ~/Controle de Bordo/Pessoal/Financeiro/Metas/
- [x] MOC "Dashboard Financeiro" com Dataview queries
- [x] `run.sh --sync` integrado

## Validação realizada

- `ruff check` passa sem erros
- 44 arquivos confirmados no vault
- 7 metas confirmadas no vault
- Frontmatter do relatório 2026-04 verificado (valores corretos)

## Validação pendente

- [ ] Dataview queries: abrir Obsidian e verificar se tabelas renderizam
- [ ] Frontmatter de TODOS os 44 relatórios (só 1 verificado)
- [ ] Idempotência: rodar sync 2x e verificar que não duplica dados
- [ ] Backlinks entre relatórios e metas: verificar navegação no Obsidian
- [ ] MOC: verificar que lista relatórios recentes e metas por prioridade

## Armadilhas conhecidas

- Dataview queries podem ter erro de sintaxe (não testadas no Obsidian real)
- Frontmatter gerado com regex de extração de valores -- pode falhar em formatos inesperados
- O vault ~/Controle de Bordo/ tem estrutura PARA existente que deve ser respeitada

## Arquivos criados/modificados

| Arquivo | Descrição |
|---------|-----------|
| `src/obsidian/__init__.py` | Init do módulo obsidian |
| `src/obsidian/sync.py` | Sincronizador com vault Obsidian (349 linhas) |
| `run.sh` | Adicionado case --sync |

## Critério de sucesso

- [ ] Dataview queries funcionais no Obsidian
- [ ] Frontmatter correto em todos os 44 relatórios
- [ ] Sync idempotente (rodar 2x = mesmo resultado)
- [ ] Backlinks navegáveis entre relatórios e metas

## Dependências

Sprint 05 (relatórios automáticos completos).
