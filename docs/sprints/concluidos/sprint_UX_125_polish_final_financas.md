## 0. SPEC (machine-readable)

```yaml
sprint:
  id: UX-125
  title: "Polish final: body width 100% + rename Dinheiro->Financas + tabs Home espelham clusters + sidebar busca refinada"
  prioridade: P1
  estimativa: 1.5h
  origem: "feedback dono 2026-04-27 (image 18) -- 5 ajustes finais apos validacao do cluster v2"
  pre_requisito_de: [Sprint 100]
  touches:
    - path: src/dashboard/app.py
      reason: "ABAS_POR_CLUSTER['Home'] muda para ['Visao Geral', 'Financas', 'Documentos', 'Analise', 'Metas'] (espelha clusters; sem 'hoje'); roteamento de tabs atualizado"
    - path: src/dashboard/componentes/drilldown.py
      reason: "CLUSTERS_VALIDOS troca 'Dinheiro' por 'Financas'; MAPA_ABA_PARA_CLUSTER atualiza valores ('Extrato'->'Financas' etc.); CLUSTER_ALIASES recebe 'Dinheiro' -> 'Financas' (backward-compat)"
    - path: src/dashboard/componentes/busca_global_sidebar.py
      reason: "label do input muda de 'Buscar' para 'Busca Global'; placeholder fica vazio; altura/largura iguais aos selectboxes (44px)"
    - path: src/dashboard/tema.py
      reason: "css_global() ganha regra width: 100% no .main .block-container (remove max-width restritivo); input de busca da sidebar ganha mesmo min-height 44px que selectboxes"
    - path: tests/test_dashboard_*.py
      reason: "atualizar testes que mencionam 'Dinheiro' como cluster; novos testes para alias backward-compat"
  forbidden:
    - "Renomear arquivos fisicos das paginas-irmas (extrato.py/contas.py/etc. permanecem)"
    - "Mudar conteudo das paginas (so labels e cluster names)"
    - "Quebrar query_params: ?cluster=Dinheiro deve continuar resolvendo (alias)"
    - "Adicionar tokens novos"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_dashboard*.py -q"
    - cmd: "make smoke"
  acceptance_criteria:
    # AC1: body 100% horizontal
    - "Em css_global(), .main .block-container e/ou [data-testid='stMainBlockContainer'] tem max-width: 100% ou width: 100% sem restricao; faixa preta a direita do conteudo desaparece"
    # AC2: rename Dinheiro -> Financas
    - "CLUSTERS_VALIDOS contem 'Financas' (nao 'Dinheiro'); ordem mantida ['Home', 'Financas', 'Documentos', 'Analise', 'Metas']"
    - "MAPA_ABA_PARA_CLUSTER atualiza valores: 'Extrato' -> 'Financas', 'Contas' -> 'Financas', 'Pagamentos' -> 'Financas', 'Projecoes' -> 'Financas'"
    - "CLUSTER_ALIASES adiciona 'Dinheiro': 'Financas' (URLs antigas continuam resolvendo)"
    # AC3: tabs Home sem 'hoje', espelham clusters
    - "ABAS_POR_CLUSTER['Home'] = ['Visao Geral', 'Financas', 'Documentos', 'Analise', 'Metas']"
    - "Roteamento em app.py: tab 'Financas' -> renderizar(home_dinheiro), tab 'Documentos' -> renderizar(home_docs), tab 'Analise' -> renderizar(home_analise), tab 'Metas' -> renderizar(home_metas) (arquivos fisicos das paginas mantem nome para evitar git mv massivo)"
    # AC4: sidebar busca label e placeholder
    - "busca_global_sidebar.py usa label='Busca Global' (era 'Buscar') com label_visibility='visible' (mostra label); placeholder=''"
    # AC5: input busca altura igual aos selects
    - "css_global() aplica min-height: 44px no st.text_input da sidebar (mesma regra do AC3 da UX-119 para selectboxes); largura 100% do container"
    # Regressivos
    - "Pelo menos 8 testes regressivos: AC1 (max-width no css_global), AC2 (CLUSTERS_VALIDOS contem Financas), AC2 alias (Dinheiro resolve via alias), AC3 (ABAS_POR_CLUSTER['Home'] tem 5 valores corretos), AC4 (label e placeholder), AC5 (input altura 44px), regressao Sprint UX-121 (Hoje->Home alias preservado), regressao tabs cross-area"
  proof_of_work_esperado: |
    grep -c "\"Dinheiro\"\|'Dinheiro'" src/dashboard/ | head -5
    # = matches em CLUSTER_ALIASES + comentarios; nenhum runtime real

    grep -n "Financas" src/dashboard/componentes/drilldown.py
    # = >=4 matches (CLUSTERS_VALIDOS + 4 valores em MAPA_ABA_PARA_CLUSTER)

    grep -n "Busca Global\|Busca global" src/dashboard/componentes/busca_global_sidebar.py
    # = label do input

    .venv/bin/streamlit run src/dashboard/app.py --server.port 8520 --server.headless true &
    sleep 6
    # http://localhost:8520/?cluster=Home -- tabs ['Visao Geral', 'Financas', 'Documentos', 'Analise', 'Metas']
    # http://localhost:8520/?cluster=Dinheiro -- alias resolve para Financas
    # http://localhost:8520/?cluster=Financas -- canonico
```

---

# Sprint UX-125 -- Polish final + rename Dinheiro->Financas

**Status:** CONCLUÍDA (commit `dd8fe12`, 2026-04-27 — 22 testes novos, validação Playwright OK)

5 ajustes finais identificados pelo dono apos validar cluster v2 mergeado:

1. **Body 100% horizontal**: hoje a viewport tem ~1600px mas o `.block-container` tem `max-width` que deixa faixa preta a direita. Aproveitar todo o espaco.
2. **Rename "Dinheiro" -> "Financas"**: termo "Dinheiro" e ambiguo; "Financas" e mais profissional. Alias backward-compat preserva URLs antigas.
3. **Tabs do Home espelham clusters**: hoje são "Visao Geral / Dinheiro hoje / Docs hoje / Análise hoje / Metas hoje". Devem ser "Visao Geral / Financas / Documentos / Análise / Metas" (sem "hoje" repetitivo). Cada tab abre a mini-view ja existente (arquivos home_*.py mantem nome interno).
4. **Sidebar busca**: label muda de "Buscar" para "Busca Global"; placeholder vazio; altura 44px igual aos selectboxes (UX-119 AC3).
5. **Filtro Area** mostra valores: Home / Financas / Documentos / Análise / Metas.

Escopo cirurgico: tudo cabe em ~1.5h, toca apenas tema.py, drilldown.py, app.py, busca_global_sidebar.py + tests.

---

*"Coerencia entre filtro e tabs e a base do mental model. 'Hoje' repetido em 4 tabs e ruido." -- principio do espelho do filtro*
