---
concluida_em: 2026-05-06
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: UX-T-01
  title: "Visão Geral canônica (mockup 01-visao-geral.html)"
  prioridade: P0
  estimativa: 1 dia
  onda: T
  mockup_fonte: novo-mockup/mockups/01-visao-geral.html + novo-mockup/mockups/_visao-render.js
  depende_de: [UX-U-01, UX-U-02, UX-U-03, UX-U-04]
  bloqueia: [UX-T-02..UX-T-29 (em série), UX-Q-01]
  touches:
    - path: src/dashboard/paginas/visao_geral.py
      reason: "rebuild da página seguindo o mockup canônico: hero com linha 'Sprint atual', 4 KPIs agentic-first (Arquivos Catalogados / Paridade ETL↔Opus / Aguardando Humano / Skills Regredindo), bloco 'OS 5 CLUSTERS' com 6 cards descritivos clicáveis, ATIVIDADE RECENTE com 6 entries cronológicas, SPRINT ATUAL card no rodapé."
    - path: src/dashboard/app.py
      reason: "linha ~457 cluster=='Home' usa st.tabs([Visão Geral, Finanças, Documentos, Análise, Metas]) — tabs duplicam navegação da sidebar canônica. Substituir por dispatcher direto: chamar visao_geral.renderizar(...) sem tabs."
    - path: src/dashboard/componentes/visao_geral_widgets.py (novo)
      reason: "helpers extraídos: calcular_kpis_agentic, ler_atividade_recente, montar_cluster_card, montar_sprint_card."
    - path: tests/test_visao_geral_canonica.py (novo)
      reason: "testes: 4 KPIs visíveis, OS 5 CLUSTERS bloco, ATIVIDADE RECENTE 6 entries, SPRINT ATUAL card, topbar-actions com Atualizar+Ir para Validação, ZERO st.tabs no cluster Home."
  forbidden:
    - "Manter as 5 tabs (Visão Geral/Finanças/Documentos/Análise/Metas) no main quando cluster='Home'."
    - "Inventar dados nos KPIs — quando dado real não existir, exibir '-' ou '0' com graceful degradation (ADR-10)."
    - "Hardcodar timeline da ATIVIDADE RECENTE com dados fictícios — ler do grafo SQLite OU dos logs do pipeline."
  hipotese:
    - "Hoje visao_geral.py renderiza hero + KPIs financeiros (Receita/Despesa/Saldo/Reserva) + Receita×Despesa chart + bloco OS 6 CLUSTERS desconectado. Mockup canônico tem KPIs AGENTIC-FIRST (não-financeiros), ATIVIDADE RECENTE rica e SPRINT ATUAL card; tabs internas no cluster Home são duplicadas com sidebar."
  tests:
    - cmd: ".venv/bin/pytest tests/test_visao_geral_canonica.py -v"
      esperado: "8+ PASSED"
    - cmd: "make smoke"
      esperado: "10/10"
  acceptance_criteria:
    - "src/dashboard/paginas/visao_geral.py renderiza: hero (com linha Sprint atual), 4 KPIs agentic, OS 5 CLUSTERS com 6 cards, ATIVIDADE RECENTE com 6 entries, SPRINT ATUAL card."
    - "Topbar-actions populadas via componentes/topbar_actions.renderizar_grupo_acoes com 2 botões: Atualizar (recarrega) + Ir para Validação (->cluster=Documentos&tab=Extração+Tripla, primary)."
    - "app.py main() para cluster='Home' chama visao_geral.renderizar diretamente, sem st.tabs."
    - "Sub-páginas home_dinheiro/home_docs/home_analise/home_metas continuam exportadas (compat) mas não são chamadas pelo dispatcher do cluster Home."
    - "KPIs Arquivos Catalogados / Paridade ETL↔Opus / Aguardando Humano / Skills Regredindo são lidos de fontes reais (grafo SQLite, validacao_arquivos.csv, .ouroboros/cache); fallback graceful para '-' se ausente."
    - "ATIVIDADE RECENTE lê 6 entries cronológicas dos logs do pipeline (logs/) OU do grafo (criado_em DESC); cada entry tem horário, glyph, descrição com strong/code."
    - "SPRINT ATUAL card lê de docs/sprints/concluidos/ (sprint mais recente concluída) E de docs/sprints/backlog/ (sprint vigente em execução); fallback para spec atual se metadata não-disponível."
    - "Validação humana: dono compara mockup canônico × dashboard side-by-side e aceita visualmente; pelo menos 90% de fidelidade nos blocos visuais críticos."
  proof_of_work_esperado: |
    nohup .venv/bin/streamlit run src/dashboard/app.py --server.port 8765 --server.headless true &
    sleep 8
    .venv/bin/python -c "
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(); page = b.new_context(viewport={'width':1440,'height':900}).new_page()
        page.goto('http://127.0.0.1:8765/?cluster=Home&tab=Vis%C3%A3o+Geral'); page.wait_for_timeout(8000)
        info = page.evaluate('''() => {
            const titulo_kpis = Array.from(document.querySelectorAll('.kpi .l, .kpi-label')).map(e => e.textContent.trim());
            const cards_cluster = document.querySelectorAll('.cluster-card').length;
            const tl_items = document.querySelectorAll('.tl-item, .timeline > div').length;
            const sprint_atual = document.body.textContent.includes('Sprint atual');
            const topbar_btns = document.querySelectorAll('.topbar-actions a.btn, .topbar-actions button.btn').length;
            const home_tabs = document.querySelectorAll('section.main [data-baseweb=\"tab-list\"]').length;
            return {titulo_kpis, cards_cluster, tl_items, sprint_atual, topbar_btns, home_tabs};
        }''')
        print(info)
        # Esperado:
        # titulo_kpis inclui 'Arquivos catalogados', 'Paridade ETL ↔ Opus', 'Aguardando humano', 'Skills regredindo'
        # cards_cluster == 6
        # tl_items >= 6
        # sprint_atual == True
        # topbar_btns == 2
        # home_tabs == 0  (zero st.tabs no cluster Home)
        b.close()
    "
```

---

# Sprint UX-T-01 — Visão Geral canônica

**Status:** BACKLOG — Onda T (telas).

## 1. Contexto

Após Onda U entregar shell estrutural, a Visão Geral ainda mostra layout anterior (KPIs financeiros Receita/Despesa, tabs duplicadas com sidebar, sem ATIVIDADE RECENTE rica, sem SPRINT ATUAL card). Mockup canônico define a tela como **dashboard agentic-first**: KPIs medindo o pipeline (não as finanças), bloco descritivo dos 5 clusters, timeline cronológica, sprint vigente em destaque.

## 2. Hipótese verificável (Fase ANTES)

```bash
grep -nE 'def renderizar|hero_html|_clusters_html' src/dashboard/paginas/visao_geral.py | head
grep -nE 'cluster == "Home"|st\.tabs.*Visão Geral' src/dashboard/app.py | head
```

## 3. Tarefas

1. Rodar hipótese.
2. Reescrever `src/dashboard/paginas/visao_geral.py`:
   - `_kpis_agentic_html(metricas)` — 4 KPIs agentic.
   - `_clusters_block_html()` — bloco "OS 5 CLUSTERS" com 6 cards.
   - `_atividade_recente_html(entries)` — timeline com 6 entries.
   - `_sprint_atual_html(sprint_meta)` — card vigente.
   - `_hero_html()` mantido + linha "Sprint atual" no parágrafo.
   - `renderizar(dados, periodo, pessoa, ctx)` orquestra: topbar-actions → hero → kpis → grid (clusters | timeline+sprint).
3. Helpers em `src/dashboard/componentes/visao_geral_widgets.py`:
   - `calcular_kpis_agentic()` lê grafo SQLite + validacao_arquivos.csv.
   - `ler_atividade_recente(n=6)` lê logs/ ou grafo recente.
   - `ler_sprint_atual()` parseia frontmatter de specs em docs/sprints/.
4. Em `src/dashboard/app.py`, refatorar dispatcher do cluster Home:
   ```python
   if cluster == "Home":
       visao_geral.renderizar(dados, periodo, pessoa, ctx)
   ```
   Eliminar `st.tabs(...)` de 5 abas.
5. Topbar-actions: chamar `renderizar_grupo_acoes` no início de `visao_geral.renderizar`.
6. Criar `tests/test_visao_geral_canonica.py` (≥8 testes integração + helpers).
7. Capture mockup × dashboard side-by-side em `docs/auditorias/redesign-2026-05-06/T-01_*.png`.
8. Gauntlet (§7).

## 4. Anti-débito

- Sub-páginas `home_dinheiro/home_docs/home_analise/home_metas`: não chamadas pelo dispatcher; arquivar em sprint-filha futura (DEPRECATED-HOME-SUBVIEWS), mas manter os arquivos importáveis.
- Se grafo SQLite não tem dados: KPIs caem no fallback `'-'` com warning no log.

## 5. Validação visual humana

Dono abre `http://127.0.0.1:8765/?cluster=Home&tab=Vis%C3%A3o+Geral` e confirma 1:1 com mockup `01-visao-geral.html`.

## 6. Gauntlet

```bash
make lint
make smoke
.venv/bin/pytest tests/test_visao_geral_canonica.py -v
.venv/bin/pytest tests/ -q --tb=no
```

---

*"O início ressoa em todo o caminho." -- Heráclito (paráfrase)*
