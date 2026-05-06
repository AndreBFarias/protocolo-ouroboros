---
concluida_em: 2026-05-05
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: UX-RD-FIX-11
  title: "Deep-link funcional para as 12 abas Bem-estar declaradas após FIX-10"
  prioridade: P0
  estimativa: 4h
  onda: C4
  origem: "AUDITORIA_REDESIGN_2026-05-05.md §6.3 (top problema #1) + decisão A da FIX-10"
  depende_de: [UX-RD-FIX-10]
  bloqueia: []
  touches:
    - path: src/dashboard/app.py
      reason: "garantir que após FIX-10 o dispatcher abre a aba correta quando ?cluster=Bem-estar&tab=<aba>"
    - path: src/dashboard/componentes/drilldown.py
      reason: "MAPA_ABA_PARA_CLUSTER deve incluir Treinos, Marcos, Alarmes, Contadores, Tarefas apontando para 'Bem-estar' (já listadas em ABAS_POR_CLUSTER, mas validar mapa reverso)"
    - path: tests/test_deeplink_bemestar.py
      reason: "NOVO -- 12 testes (1 por aba) garantem que ?cluster=Bem-estar&tab=<aba> renderiza o page-title correto"
  forbidden:
    - "Manter qualquer expander dentro de Recap escondendo conteúdo (FIX-10 já removeu Cruzamentos/Privacidade/Editor TOML; não reintroduzir)"
    - "Ativar uma aba via JS quando a URL pede outra (deep-link deve ser declarativo)"
  hipotese:
    - "Após FIX-10, dispatcher tem 1:1 entre 12 abas e 12 páginas distintas (be_hoje, be_humor, be_diario, be_eventos, be_medidas, be_treinos, be_marcos, be_alarmes, be_contadores, be_ciclo, be_tarefas, be_recap). Esta sprint VALIDA que cada deep-link funciona via playwright e ajusta gerar_html_ativar_aba se algo não bate."
  tests:
    - cmd: ".venv/bin/pytest tests/test_deeplink_bemestar.py -v"
      esperado: "12/12 PASSED"
  acceptance_criteria:
    - "Para cada aba A em ['Hoje','Humor','Diário','Eventos','Medidas','Treinos','Marcos','Alarmes','Contadores','Ciclo','Tarefas','Recap']: navegar a `?cluster=Bem-estar&tab=A` resulta em DOM com tab[role=tab][aria-selected=true].textContent == A"
    - "page-title da página renderizada bate com o título canônico (ex.: tab=Alarmes -> page-title 'BEM-ESTAR · ALARMES')"
    - "Zero fallback para 'Hoje' quando URL pede outra aba"
    - "Drill-down também funciona em outros clusters (Análise, Documentos, Finanças, etc.) -- regressão testada"
    - "Drill-down quando URL pede aba **inexistente** (ex.: tab=Memorias) cai gracioso em Hoje COM aviso st.toast 'Aba Memorias não disponível -- redirecionado para Hoje'"
  proof_of_work_esperado: |
    nohup .venv/bin/streamlit run src/dashboard/app.py --server.port 8531 --server.headless true &
    sleep 6
    .venv/bin/python -c "
    from playwright.sync_api import sync_playwright
    import urllib.parse
    abas_bem_estar = ['Hoje','Humor','Diário','Eventos','Medidas','Treinos','Marcos','Alarmes','Contadores','Ciclo','Tarefas','Recap']
    titulos_canonicos = {
        'Hoje':'BEM-ESTAR · HOJE','Humor':'BEM-ESTAR · HUMOR','Diário':'BEM-ESTAR · DIÁRIO',
        'Eventos':'BEM-ESTAR · EVENTOS','Medidas':'BEM-ESTAR · MEDIDAS',
        'Treinos':'BEM-ESTAR · TREINOS','Marcos':'BEM-ESTAR · MARCOS',
        'Alarmes':'BEM-ESTAR · ALARMES','Contadores':'BEM-ESTAR · CONTADORES',
        'Ciclo':'CICLO MENSTRUAL','Tarefas':'BEM-ESTAR · TAREFAS','Recap':'RECAP'
    }
    with sync_playwright() as p:
        b = p.chromium.launch(); page = b.new_context().new_page()
        falhas = []
        for aba in abas_bem_estar:
            url = f'http://127.0.0.1:8531/?cluster=Bem-estar&tab={urllib.parse.quote(aba)}'
            page.goto(url); page.wait_for_timeout(4500)
            ativa = page.evaluate('document.querySelector(\"button[role=tab][aria-selected=true]\")?.textContent.trim()') or '(none)'
            h1 = page.evaluate('Array.from(document.querySelectorAll(\"h1\")).filter(h => h.getBoundingClientRect().width > 0).map(h => h.textContent.trim())')
            print(f'tab={aba} ativa={ativa} h1={h1}')
            if ativa != aba: falhas.append((aba, 'aba_errada', ativa))
            elif not any(titulos_canonicos[aba] in t.upper() for t in h1): falhas.append((aba, 'h1_errado', h1))
        assert len(falhas) == 0, f'deep-links quebrados: {falhas}'
        print(f'OK 12/12 deep-links Bem-estar funcionais')
        b.close()
    "
```

---

# Sprint UX-RD-FIX-11 — Deep-link funcional para 12 abas Bem-estar (decisão A)

**Status:** BACKLOG — Onda C4 (depende de FIX-10).

## 1. Contexto

Auditoria 2026-05-05 §6.3 confirmou que **5 abas Bem-estar (Treinos, Marcos, Alarmes, Contadores, Tarefas) caíam em "Hoje"** porque suas páginas não existiam (chamavam be_memorias / be_rotina via fraude). FIX-10 corrige criando 5 páginas reais e atualizando o dispatcher para 1:1.

Esta sprint **valida via playwright** que cada deep-link funciona após FIX-10. É um teste end-to-end, não escreve código novo (a menos que ajuste de `gerar_html_ativar_aba` seja necessário).

## 2. Hipótese verificável (Fase ANTES)

```bash
# 1) confirma FIX-10 mergeado (12 abas, dispatcher 1:1)
grep -A 15 '"Bem-estar":' src/dashboard/app.py | head -20

# 2) confirma 5 páginas novas existem
ls src/dashboard/paginas/be_treinos.py src/dashboard/paginas/be_marcos.py src/dashboard/paginas/be_alarmes.py src/dashboard/paginas/be_contadores.py src/dashboard/paginas/be_tarefas.py

# 3) confirma drilldown.py com 12 mapeamentos
grep -E 'Treinos|Marcos|Alarmes|Contadores|Tarefas' src/dashboard/componentes/drilldown.py | head -10
```

## 3. Tarefas

1. Rodar hipótese (§2). Se algum item falhar, FIX-10 ainda não está completa; **parar e revalidar FIX-10**.
2. Verificar `MAPA_ABA_PARA_CLUSTER` em `componentes/drilldown.py`. Se faltarem entradas para Treinos/Marcos/Alarmes/Contadores/Tarefas → "Bem-estar", adicionar:
   ```python
   MAPA_ABA_PARA_CLUSTER = {
       ...,
       "Treinos": "Bem-estar",
       "Marcos": "Bem-estar",
       "Alarmes": "Bem-estar",
       "Contadores": "Bem-estar",
       "Tarefas": "Bem-estar",
   }
   ```
3. Verificar `CLUSTER_ALIASES` para qualquer alias backward-compat (ex.: "treinos" minúsculo, "marcos"). Adicionar se necessário.
4. Verificar que `gerar_html_ativar_aba(aba_requerida, abas_do_cluster)` tem suporte a 12 abas. Streamlit st.tabs renderiza no DOM com índice; o JS injetado em `app.py:743+` clica na tab por índice. Se `aba_requerida` não estiver em `abas_do_cluster`, JS deve emitir warning + voltar para índice 0 com `st.toast`.
5. Criar `tests/test_deeplink_bemestar.py`:
   ```python
   import subprocess, time
   import pytest
   from playwright.sync_api import sync_playwright

   STREAMLIT_PORT = 8531
   ABAS = ["Hoje","Humor","Diário","Eventos","Medidas","Treinos","Marcos","Alarmes","Contadores","Ciclo","Tarefas","Recap"]
   TITULOS = {
       "Hoje":"BEM-ESTAR · HOJE","Humor":"BEM-ESTAR · HUMOR","Diário":"BEM-ESTAR · DIÁRIO",
       "Eventos":"BEM-ESTAR · EVENTOS","Medidas":"BEM-ESTAR · MEDIDAS",
       "Treinos":"BEM-ESTAR · TREINOS","Marcos":"BEM-ESTAR · MARCOS",
       "Alarmes":"BEM-ESTAR · ALARMES","Contadores":"BEM-ESTAR · CONTADORES",
       "Ciclo":"CICLO MENSTRUAL","Tarefas":"BEM-ESTAR · TAREFAS","Recap":"RECAP",
   }

   @pytest.fixture(scope="module")
   def streamlit_url():
       p = subprocess.Popen([".venv/bin/streamlit","run","src/dashboard/app.py","--server.port",str(STREAMLIT_PORT),"--server.headless","true"])
       time.sleep(7)
       yield f"http://127.0.0.1:{STREAMLIT_PORT}"
       p.terminate(); p.wait()

   @pytest.mark.parametrize("aba", ABAS)
   def test_deeplink_aba(aba, streamlit_url):
       import urllib.parse
       with sync_playwright() as p:
           b = p.chromium.launch()
           page = b.new_context().new_page()
           page.goto(f"{streamlit_url}/?cluster=Bem-estar&tab={urllib.parse.quote(aba)}")
           page.wait_for_timeout(4500)
           ativa = page.evaluate("document.querySelector('button[role=tab][aria-selected=true]')?.textContent.trim()")
           assert ativa == aba, f'tab={aba}, ativa={ativa}'
           h1s = page.evaluate("Array.from(document.querySelectorAll('h1')).filter(h => h.getBoundingClientRect().width > 0).map(h => h.textContent.trim())")
           assert any(TITULOS[aba] in h.upper() for h in h1s), f'tab={aba}: nenhum h1 contém {TITULOS[aba]}; h1s={h1s}'
           b.close()
   ```
6. Validar regressão de outros clusters: drill-down `?cluster=Análise&tab=Categorias`, `?cluster=Documentos&tab=Revisor`, `?cluster=Finanças&tab=Extrato` continuam funcionando.
7. Rodar gauntlet (§6).

## 4. Anti-débito

- Se algum deep-link falhar mesmo após FIX-10: investigar (a) typo na string da aba (`Diário` vs `Diario`), (b) mismatch case-sensitive, (c) JS de `gerar_html_ativar_aba` não recarregando.
- Limite: 3 iterações de debug. Após isso, criar **sprint UX-RD-FIX-11.B** detalhando o que está quebrando.
- Se URL pedir aba inexistente (ex.: `?cluster=Bem-estar&tab=Memorias`): garantir `st.toast` informativo + fallback para Hoje. Esse comportamento é coberto pela **FIX-14** que reabilita as 5 órfãs via deep-link interno.

## 5. Validação visual

PNG de cada uma das 12 abas Bem-estar acessadas via deep-link, salvo em `.playwright-mcp/auditoria/fix-11/be_<aba>.png`. Validador humano confirma visualmente que cada PNG corresponde ao mockup esperado.

## 6. Gauntlet

```bash
make lint                                                # exit 0
make smoke                                               # 10/10
.venv/bin/pytest tests/test_deeplink_bemestar.py -v      # 12/12
.venv/bin/pytest tests/ -q --tb=no                       # baseline mantida
```

---

*"Toda porta deve abrir para o que se promete atrás dela." -- Heráclito (paráfrase)*
