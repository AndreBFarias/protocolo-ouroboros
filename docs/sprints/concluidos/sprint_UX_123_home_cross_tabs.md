## 0. SPEC (machine-readable)

```yaml
sprint:
  id: UX-123
  title: "Cluster Home com tabs cross-area (mini-views Dinheiro/Docs/Analise/Metas filtradas por hoje)"
  prioridade: P1
  estimativa: 3h
  origem: "feedback dono 2026-04-27 (image 12) -- cluster Home so tem 'Visao Geral'; deveria ter tabs com mini-views das outras 4 areas"
  depende_de: [UX-121]
  pre_requisito_de: [Sprint 100]
  touches:
    - path: src/dashboard/app.py
      reason: "ABAS_POR_CLUSTER['Home'] ganha 5 abas: ['Visao Geral', 'Dinheiro hoje', 'Docs hoje', 'Analise hoje', 'Metas hoje']; main() roteia para mini-views"
    - path: src/dashboard/paginas/home_dinheiro.py
      reason: "NOVO -- mini-view de Dinheiro filtrada para HOJE (transacoes do dia + saldo + receita/despesa)"
    - path: src/dashboard/paginas/home_docs.py
      reason: "NOVO -- mini-view de Documentos filtrada para HOJE (chegaram hoje + pendencias do dia)"
    - path: src/dashboard/paginas/home_analise.py
      reason: "NOVO -- mini-view de Analise filtrada para HOJE (top categoria do dia + heatmap mes)"
    - path: src/dashboard/paginas/home_metas.py
      reason: "NOVO -- mini-view de Metas (status atual com snapshot do dia)"
    - path: tests/test_dashboard_home_cross.py
      reason: "NOVO -- 8 testes regressivos cobrindo as 4 mini-views"
  forbidden:
    - "Duplicar logica das paginas originais -- importar/extrair funcoes pequenas"
    - "Quebrar paginas originais (Dinheiro, Documentos, Analise, Metas continuam funcionais nas areas proprias)"
    - "Adicionar deps externas"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_dashboard_home_cross.py -v"
    - cmd: ".venv/bin/pytest tests/test_dashboard*.py -q"
    - cmd: "make smoke"
  acceptance_criteria:
    - "ABAS_POR_CLUSTER['Home'] = ['Visao Geral', 'Dinheiro hoje', 'Docs hoje', 'Analise hoje', 'Metas hoje']"
    - "Cada mini-view filtra dados por data == today() ou ultimo dia disponivel"
    - "Cada mini-view tem 1-2 KPIs principais + 1 grafico/tabela compacto"
    - "Funcoes filtrar_para_hoje() e renderizar_kpi_compacto() reusadas entre as 4 paginas"
    - "Pelo menos 8 testes regressivos: 1 por mini-view (renderiza sem erro) + 1 por filtro de data + ordem das abas"
    - "Validacao visual: cluster Home mostra 5 abas; cada aba abre mini-view consistente com a area-irma original"
  proof_of_work_esperado: |
    grep -A 10 "Home" src/dashboard/app.py | head -15
    # = ABAS_POR_CLUSTER['Home'] com 5 itens

    .venv/bin/streamlit run src/dashboard/app.py --server.port 8520 --server.headless true &
    sleep 6
    # http://localhost:8520/?cluster=Home -- 5 tabs visiveis
    # http://localhost:8520/?cluster=Home&tab=Dinheiro+hoje -- mini-view de Dinheiro filtrada
```

---

# Sprint UX-123 -- Home cross-tabs

**Status:** CONCLUÍDA (commit `70f24fa`, 2026-04-27 — 5 páginas novas, 18 testes, validação Playwright OK em runtime real)

Cluster Home hoje so tem 1 aba ('Visao Geral'). Dono espera que Home seja o painel-resumo do dia, com tabs que dao um vislumbre rapido das demais 4 areas filtradas por hoje. Sprint cria 4 paginas novas (home_dinheiro/docs/analise/metas) reusando funções pequenas das paginas-irmas.

---

*"Home e o resumo do dia, não apenas a primeira parada." -- principio da entrada cognitiva rica*
