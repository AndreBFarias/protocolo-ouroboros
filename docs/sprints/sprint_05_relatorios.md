# Sprint 05 -- Relatórios e Projeções

## Status: Código integrado, validação superficial (issue #5 reaberta)
Issue: #5 (reaberta)

## Objetivo

Gerar relatórios mensais completos automaticamente e implementar projeções financeiras com cenários configuráveis. Adicionar páginas de projeção e metas ao dashboard.

## Entregas

- [x] Relatório mensal melhorado (seções de metas, projeção 6m/12m, IRPF acumulado)
- [x] Projetor de cenários (ritmo atual, pós-Infobase, meta apartamento)
- [x] Página Streamlit Projeções (3 cards de cenários, gráfico de patrimônio projetado)
- [x] Página Streamlit Metas (barras de progresso, prazos, prioridades)
- [x] mappings/metas.yaml com 7 metas reais do casal

## Validação realizada

- `ruff check` passa sem erros
- Pipeline `--tudo` roda sem erros com os novos arquivos
- Página Projeções aberta no browser: cenários renderizam com dados reais
- Página Metas aberta no browser: 3 metas visíveis com progresso e prazos
- app.py integra 6 tabs sem conflito

## Validação pendente

- [ ] Lógica dos cenários: números não verificados em profundidade
- [ ] Edge cases: meses sem dados, divisão por zero, metas sem prazo
- [ ] Cenário "Pós-Infobase": saldo mensal -R$ 7.349 -- verificar se está correto
- [ ] Relatórios melhorados: comparar com versão anterior item a item
- [ ] Metas: verificar que todas as 7 do YAML aparecem no dashboard

## Armadilhas conhecidas

- Código criado por subagente que ficou sem créditos antes de validar
- Projeções exigem modelagem numérica cuidadosa para não gerar resultados irreais
- Cenário pós-Infobase assume renda zero do André, o que gera saldo negativo

## Arquivos criados/modificados

| Arquivo | Descrição |
|---------|-----------|
| `src/projections/scenarios.py` | Projetor de cenários financeiros (174 linhas) |
| `src/projections/__init__.py` | Init do módulo projections |
| `src/dashboard/paginas/projecoes.py` | Página Streamlit de projeções (334 linhas) |
| `src/dashboard/paginas/metas.py` | Página Streamlit de metas (290 linhas) |
| `mappings/metas.yaml` | 7 metas financeiras configuráveis (43 linhas) |
| `src/load/relatorio.py` | Relatório melhorado (382 linhas) |
| `src/dashboard/app.py` | Modificado para 6 tabs |

## Critério de sucesso

- [ ] Todos os 7 metas do YAML visíveis no dashboard
- [ ] Cenários com números que batem com dados reais
- [ ] Relatórios com seções novas (metas, projeção, IRPF) preenchidas
- [ ] Zero erros ao navegar entre todas as 6 tabs

## Dependências

Sprint 04 (categorização inteligente e validação).
