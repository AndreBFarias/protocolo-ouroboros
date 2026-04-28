## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 100
  title: "Deep-link ?tab=X funcional dentro de cluster Streamlit"
  prioridade: P1
  estimativa: 2h
  origem: "auditoria 2026-04-26 -- ?tab=Busca+Global em ?cluster=Documentos abre Catalogacao"
  touches:
    - path: src/dashboard/app.py
      reason: "ler ?tab=X ao trocar cluster e injetar st.session_state['active_tab']"
    - path: src/dashboard/componentes/drilldown.py
      reason: "atualizar query_params quando usuario troca tab"
    - path: tests/test_dashboard_deeplink_tab.py
      reason: "regressao: ?tab=X dentro de cluster certo abre tab certa"
  forbidden:
    - "Quebrar drill-down existente (Sprint 73)"
    - "Adicionar deps externas (manter pure-Streamlit)"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_dashboard_deeplink_tab.py -v"
    - cmd: "make smoke"
  acceptance_criteria:
    - "?cluster=Documentos&tab=Busca+Global abre cluster Documentos com tab Busca Global ativa"
    - "?tab=Categorias sem cluster infere cluster=Analise via MAPA_ABA_PARA_CLUSTER (ja existe)"
    - "Trocar tab manualmente atualiza ?tab=X na URL (browser back funciona)"
    - "5 testes: cada cluster com 1 tab não-default deep-linkavel"
  proof_of_work_esperado: |
    # Antes
    curl -s "http://localhost:8520/?cluster=Documentos&tab=Busca+Global" | grep -i "Busca Global"
    # = nada (renderiza Catalogacao)
    
    # Depois
    [mesmo curl]
    # = match em "Busca Global" como aba ativa
```

---

# Sprint 100 -- Deep-link tab funcional

**Status:** CONCLUÍDA (P1, fechamento bookkeeping em 2026-04-27 pós-cluster UX v3)

## Decisão 2026-04-27 -- Fechamento oficial

Implementação técnica entregue em `c4397ea` / merge `24dd487`. Reabertura foi formal aguardando os 5 pré-requisitos UX. Todos mergeados em main na rodada cluster UX v1+v2+v3:

| Pré-requisito | Commit |
|---|---|
| UX-110 (Busca Global como primeira aba do cluster Documentos) | `61464e4` |
| UX-111 (token cor `#6272A4` → `#c9c9cc`) | `bdaa2ac` |
| UX-112 (padding/borda foco-ativo globais) | `a50608d` |
| UX-113 (sidebar refactor: campo Buscar primeiro + Área dropdown) | `5a57c4b` |
| UX-114 (Busca Global refactor: autocomplete + roteador tab/doc + tabela) | `4be89cf` |

Validação visual humana confirmou tab Busca Global ativa via `?cluster=Documentos&tab=Busca+Global` em commit técnico original; UX-110 a UX-114 endereçaram as ressalvas do componente Busca Global. Spirit da spec atendido.

**Sprint 100 = CONCLUÍDA. Move-se para `docs/sprints/concluidos/`.**

Streamlit `st.tabs(...)` não expoe API para ativar tab por nome. Sprint usa truque: `st.session_state['_active_tab_<cluster>']` lido do query_params na inicializacao + `st.tabs(...)` retorna lista; injeta JavaScript via `st.components.v1.html()` que clica na tab correspondente apos render.

Padrao ja documentado em `docs/ARMADILHAS.md #11`. Esta sprint formaliza solução reusavel.

## Decisão 2026-04-27 -- Sprint REABERTA

Implementação técnica do deep-link tab está **funcional** (validação visual confirmou tab Busca Global ativa via `?cluster=Documentos&tab=Busca+Global`). Mas o dono testou em browser real e identificou ressalvas substantivas no componente Busca Global e no design system que precisam ser tratadas antes de declarar "deep-link funcional" no espírito da spec.

**Pré-requisitos para fechar Sprint 100:**
- Sprint UX-110 (Busca Global como primeira aba do cluster Documentos)
- Sprint UX-111 (token cor `#6272A4` → `#c9c9cc`)
- Sprint UX-112 (padding/margin/borda foco-ativo globais)
- Sprint UX-113 (sidebar refactor: campo Buscar primeiro + Área dropdown)
- Sprint UX-114 (Busca Global refactor: autocomplete + dropdown tipos + filtros + roteador tab/doc)

Quando essas 5 UX-* fecharem, Sprint 100 vira CONCLUÍDA num mesmo commit-bookkeeping.

---

*"URL eh contrato. Quem clicou em link tem direito a chegar onde queria." -- principio do deep-link honesto*
