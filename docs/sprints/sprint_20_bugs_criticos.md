# Sprint 20 -- Bugs Críticos e Segurança

## Status: Concluída

## Objetivo

Corrigir os 3 bugs que crasham a aplicação, eliminar dados sensíveis do histórico git e proteger a pasta contexto. Tudo que impede o projeto de funcionar em produção.

---

## Entregas

### Crash: analise_avancada.py:266 -- margin duplicado

- [ ] Ler `analise_avancada.py:250-290` e identificar onde `margin` é definido duas vezes (provavelmente em `go.Figure(layout=...)` e depois em `fig.update_layout(margin=...)`)
- [ ] Remover a duplicata, manter apenas no `update_layout`
- [ ] Verificação: abrir dashboard, navegar para Análise, scrollar até Tendências Históricas. Depois confirmar que IRPF renderiza (atualmente crasha porque o erro bloqueia tudo depois)

### Crash: projeções idênticas em todos os 44 relatórios

- [ ] Bug em `src/load/relatorio.py:107-111`: `_gerar_secao_projecao()` passa TODAS as transações para `_calcular_medias()`. A função `_ultimos_n_meses()` pega os 3 últimos meses GLOBAIS, não relativos ao mês do relatório
- [ ] Fix: filtrar `transacoes` para `mes_ref <= mes_ref_atual` antes de passar para `_calcular_medias()`
- [ ] Rodar `make tudo` e comparar projeções de 2023-01 vs 2025-12 vs 2026-03 -- devem ser diferentes
- [ ] Verificação: `grep "Receita média" data/output/2025-12_relatorio.md` vs `2026-03_relatorio.md`

### Crash: classificação "None" no extrato do dashboard

- [ ] Investigar: o campo `classificacao` está vindo como `None` para transferências internas. Schema diz que deveria ser `N/A`
- [ ] Fix provável em `src/transform/normalizer.py` (garantir `classificacao = "N/A"` para tipo == "Transferência Interna")
- [ ] Verificação: abrir Extrato no dashboard, filtrar transferências

### Segurança: CONTEXTO.md no histórico git

- [ ] `CONTEXTO.md` foi commitado (commit `accdd0e`) com números de conta, CNPJ, valores de dívida
- [ ] Usar `git filter-repo` para remover completamente do histórico
- [ ] Requer `git push --force` após limpeza (coordenar com estado atual do remote)
- [ ] Verificação: `git log --all --full-history -- CONTEXTO.md` retorna vazio

### Segurança: proteger pasta contexto/

- [ ] `chmod 700 contexto/`
- [ ] Verificar que `contexto/` permanece no `.gitignore`
- [ ] Confirmar que `CONTEXTO_COMPLETO.md` (que contém CPF 051.273.731-22, senhas PDF, dados médicos) nunca foi commitado

---

## Critério de sucesso

- Dashboard abre sem erros em TODAS as 8 abas
- Aba IRPF renderiza
- Relatórios de meses diferentes mostram projeções diferentes
- `git log -- CONTEXTO.md` retorna vazio
- `make lint && make tudo && make validate` passam

---

*"Primeiro, não causar dano." -- Hipócrates*
