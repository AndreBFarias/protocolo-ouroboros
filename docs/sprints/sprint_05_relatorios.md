# Sprint 05 -- Relatórios e Projeções

## Status: Em andamento
Issue: #5

## Objetivo

Gerar relatórios mensais completos automaticamente e implementar projeções financeiras com cenários configuráveis. Adicionar páginas de projeção e metas ao dashboard.

## Entregas

- [ ] Relatório mensal melhorado (resumo executivo, alertas, acompanhamento de metas)
- [ ] Projetor de cenários (cenário atual, pós-Infobase, meta apartamento)
- [ ] Página Streamlit Projeções (gráfico de patrimônio, slider de economia, marcos)
- [ ] Página Streamlit Metas (barras de progresso, timeline, dependências)
- [ ] mappings/metas.yaml com metas financeiras do casal

## Armadilhas conhecidas

- Código criado por subagente sem validação completa (créditos esgotados antes de testar)
- Projeções exigem modelagem numérica cuidadosa para não gerar resultados irreais
- Páginas de metas e projeções dependem de dados históricos suficientes

## Arquivos criados/modificados

| Arquivo | Descrição |
|---------|-----------|
| `src/projections/scenarios.py` | Projetor de cenários financeiros (174 linhas) |
| `src/projections/__init__.py` | Init do módulo projections |
| `src/dashboard/paginas/projecoes.py` | Página Streamlit de projeções (334 linhas) |
| `src/dashboard/paginas/metas.py` | Página Streamlit de metas (290 linhas) |
| `mappings/metas.yaml` | Metas financeiras configuráveis (43 linhas) |
| `src/load/relatorio.py` | Relatório melhorado (382 linhas) |
| `src/dashboard/app.py` | Modificado para 6 tabs |

## Critério de sucesso

Páginas Projeções e Metas funcionais no dashboard. metas.yaml carregado corretamente. Relatórios melhorados com projeções. Todos os módulos executam sem erro.

## Dependências

Sprint 04 (categorização inteligente e validação).
