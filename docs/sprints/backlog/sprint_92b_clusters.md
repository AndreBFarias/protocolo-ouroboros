## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 92b
  title: "Reorganização em 5 clusters de navegação"
  depends_on:
    - sprint_id: 92a
      artifact: "fixes cirúrgicos mergeados"
  touches:
    - path: src/dashboard/app.py
      reason: "sidebar.radio(cluster) + st.tabs(sub-abas) por cluster"
    - path: src/dashboard/componentes/drilldown.py
      reason: "ler_filtros_da_url aceita param 'cluster'; navegação entre clusters"
    - path: tests/test_dashboard_app.py
      reason: "teste de renderização por cluster"
    - path: docs/adr/ADR-22-navegacao-clusters.md
      reason: "ADR registrando decisão"
  forbidden:
    - "Misturar mudança estrutural (clusters) com fixes visuais (92a)"
    - "Quebrar URLs existentes: ?tab=Extrato&categoria=X deve continuar funcionando"
  tests:
    - cmd: ".venv/bin/pytest tests/ -q"
    - cmd: "make lint"
    - cmd: "make smoke"
  acceptance_criteria:
    - "5 clusters funcionais: Hoje / Dinheiro / Documentos / Análise / Metas"
    - "Todas as 13 abas acessíveis via nova hierarquia"
    - "URL ?cluster=Dinheiro&tab=Extrato&categoria=Farmácia ativa cluster + aba + filtro"
    - "URL antiga ?tab=Extrato continua funcionando (backward compat — mapeamento implícito)"
    - "Streamlit sidebar.radio do cluster persistido em session_state"
    - "Zero regressão em pytest (>=1220 passed)"
    - "ADR-22 registra decisão + rollback plan"
    - "Screenshots das 5 telas iniciais (uma por cluster) em docs/screenshots/sprint_92b_*"
```

---

# Sprint 92b — reorganização em 5 clusters

**Status:** BACKLOG (criada pela Sprint 92 audit)
**Prioridade:** P0 estrutural (audita item 5 como blocker de arquitetura)
**Dependências:** Sprint 92a concluída
**Origem:** `docs/ux/audit_2026-04-23.md` §3 + §5 item 5

## Mapa dos clusters

| Cluster | Abas absorvidas | Hero number |
|---|---|---|
| Hoje | Visão Geral | 01 |
| Dinheiro | Extrato, Contas, Pagamentos, Projeções | 02-05 |
| Documentos | Catalogação, Completude, Busca Global, Grafo + Obsidian | 06-09 |
| Análise | Categorias, Análise, IRPF | 10-12 |
| Metas | Metas | 13 |

## Implementação proposta

```python
# app.py::main (pseudo)
cluster = st.sidebar.radio("Área", ["Hoje", "Dinheiro", "Documentos", "Análise", "Metas"])

if cluster == "Dinheiro":
    tab_extrato, tab_contas, tab_pagamentos, tab_projecoes = st.tabs([
        "Extrato", "Contas", "Pagamentos", "Projeções"
    ])
    # ...
```

## Backward compatibility

`ler_filtros_da_url` deve mapear aba antiga para cluster implícito:

```python
MAPA_ABA_PARA_CLUSTER = {
    "Visão Geral": "Hoje",
    "Extrato": "Dinheiro",
    "Contas": "Dinheiro",
    "Pagamentos": "Dinheiro",
    "Projeções": "Dinheiro",
    "Catalogação": "Documentos",
    "Completude": "Documentos",
    "Busca Global": "Documentos",
    "Grafo + Obsidian": "Documentos",
    "Categorias": "Análise",
    "Análise": "Análise",
    "IRPF": "Análise",
    "Metas": "Metas",
}
```

URL antiga `?tab=Extrato&categoria=Farmácia` -> cluster="Dinheiro", tab="Extrato", filtro="Farmácia".

## Armadilhas

- **Streamlit re-renderiza tudo em mudança de cluster.** Performance: cada cluster tem 1-4 páginas; mudança de cluster dispara 1-4 renders. Aceita.
- **Session_state namespace:** `cluster_ativo` é nova chave; não conflita com `filtro_*`/`avancado_*`/`seletor_*`.
- **Não quebrar `tests/test_dashboard_app.py`.** Mock de `st.tabs` e `st.radio` precisa atualizar.

## Proof-of-work

- 5 screenshots (um por cluster) em `docs/screenshots/sprint_92b_2026-xx-xx/`.
- pytest sem regressão.
- URL manual `http://localhost:8501/?tab=Extrato&categoria=Farmácia` deve abrir Dinheiro > Extrato com filtro aplicado (validação manual).

---

*"Arquitetura da informação é o esqueleto; sem esqueleto, o corpo não sustenta." -- princípio IA 101*
