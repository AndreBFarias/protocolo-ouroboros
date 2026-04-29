---
concluida_em: 2026-04-19
---

# Sprint 05 -- Relatórios e Projeções

## Status: Código integrado, validação pendente (issue #5 reaberta)
Issue: #5 (reaberta)

## Objetivo

Gerar relatórios mensais completos automaticamente e implementar projeções financeiras com cenários configuráveis. Adicionar páginas de projeção e metas ao dashboard.

## Entregas

- [x] Relatório mensal melhorado (seções de metas, projeção 6m/12m, IRPF acumulado)
- [x] Projetor de cenários (ritmo atual, pós-Infobase, meta apartamento)
- [x] Página Streamlit Projeções (3 cards de cenários, gráfico de patrimônio projetado)
- [x] Página Streamlit Metas (barras de progresso, prazos, prioridades)
- [x] mappings/metas.yaml com 7 metas reais do casal
- [ ] Validação visual via Chrome MCP
- [ ] Unificação de cálculos (relatorio.py importar de scenarios.py)

## Bugs identificados na análise de código

### Bug 1: Metas possivelmente invisíveis
- **Arquivo:** `src/dashboard/paginas/metas.py` linhas 177-205
- **Causa:** O código separa corretamente 5 metas_valor + 2 metas_binarias = 7 total. Mas `st.progress(0.0)` renderiza barra vazia no dark mode (#0E1117), indistinguível do fundo.
- **Correção:** Adicionar contagem visível no topo ("7 metas: 5 monetárias, 2 binárias"). Melhorar visibilidade da barra 0%.
- **Validação:** Chrome MCP -- contar 7 cards renderizados.

### Bug 2: Cenário pós-Infobase com saldo negativo
- **Arquivo:** `src/projections/scenarios.py` linha 116
- **Análise:** Fórmula `(receita_media - 7442) - despesa_media` está CORRETA. Sem Infobase, o casal fica em déficit. Não é bug, é projeção realista.
- **Correção:** Adicionar nota explicativa no card de projeções (`src/dashboard/paginas/projecoes.py`): "Cenário sem salário Infobase. Saldo negativo indica necessidade de ajuste."

### Bug 3: Duplicação de cálculo de médias
- **Arquivos:** `src/load/relatorio.py` linhas 90-147 e `src/projections/scenarios.py` linhas 30-61
- **Problema:** O relatório tem sua própria implementação de cálculo de médias 3 meses, separada do scenarios.py. Código duplicado pode divergir.
- **Correção:** Refatorar `relatorio.py:_gerar_secao_projecao()` para importar `_calcular_medias()` de scenarios.py. Fonte única de verdade.

### Edge cases já protegidos
- Divisão por zero: `n_real = len(meses_unicos) or 1` (scenarios.py:38)
- Metas sem prazo: `if prazo` em metas.py:80
- Meses sem dados: `_ultimos_n_meses` retorna lista vazia -> médias 0.0
- Saldo negativo: `_meses_ate_objetivo` retorna None, formatado como "Inalcançável"

## Assinaturas importantes

- `gerar_relatorio_mes(transacoes, mes_ref, transacoes_mes_anterior=None) -> str` (retorna STRING, não Path)
- `projetar_cenarios(transacoes) -> dict` com chaves cenario_atual, cenario_pos_infobase, cenario_meta_ape
- `_calcular_medias(transacoes, n_meses=3) -> dict[str, float]` com receita_media, despesa_media, saldo_medio

## Gauntlet

Fase `projecoes` cobre: médias mensais, meses_ate_objetivo, projeção acumulada 12m, cenários completos (4/4 OK).
Fase `relatorio` cobre: geração sem erro, seções obrigatórias presentes (2/2 OK).

## Arquivos a modificar

| Arquivo | Mudança |
|---------|---------|
| `src/dashboard/paginas/metas.py` | Contagem no topo, visibilidade barra 0% |
| `src/dashboard/paginas/projecoes.py` | Nota explicativa no cenário negativo |
| `src/load/relatorio.py` | Importar `_calcular_medias` de scenarios.py |

## Critério de sucesso

- [ ] Todas as 7 metas visíveis no dashboard (Chrome MCP)
- [ ] Cenários com números corretos (verificar com dados reais)
- [ ] Relatório usa mesma lógica de cálculo que scenarios.py
- [ ] Zero erros ao navegar entre todas as 6 tabs

## Dependências

Sprint 04 (categorização inteligente e validação).
