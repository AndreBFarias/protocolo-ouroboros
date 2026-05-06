---
concluida_em: 2026-05-05
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: UX-RD-FIX-14
  title: "Reabilitar rota interna para 5 páginas órfãs (Memórias, Rotina, Cruzamentos, Privacidade, Editor TOML)"
  prioridade: P1
  estimativa: 6h
  onda: C5
  origem: "Achado colateral da FIX-10 (decisão A): 5 páginas Bem-estar perderam rota top-level. Precisam de rota interna."
  depende_de: [UX-RD-FIX-10, UX-RD-FIX-11]
  bloqueia: []
  touches:
    - path: src/dashboard/app.py
      reason: "adicionar handler para query param &secao=<orfa> que renderiza a página órfã DENTRO da aba ativa (Recap por padrão), preservando a hierarquia de 12 abas"
    - path: src/dashboard/paginas/be_recap.py
      reason: "adicionar bloco de cards-link no topo da Recap apontando para Memórias, Rotina, Cruzamentos, Privacidade, Editor TOML via ?cluster=Bem-estar&tab=Recap&secao=X"
    - path: src/dashboard/paginas/be_memorias.py
      reason: "adicionar nav cards no topo apontando para Treinos, Marcos, Fotos como sub-rotas (já tem treinos/marcos via tab; Fotos via ?secao=Fotos dentro de Memórias)"
    - path: src/dashboard/paginas/be_rotina.py
      reason: "adicionar nav cards no topo apontando para Alarmes, Contadores, Tarefas (via tab existente)"
    - path: tests/test_deeplink_orfaos.py
      reason: "NOVO -- 5 testes deep-link interno: ?cluster=Bem-estar&tab=Recap&secao=Memorias renderiza be_memorias.renderizar; idem Rotina, Cruzamentos, Privacidade, Editor-TOML"
  forbidden:
    - "Adicionar as 5 órfãs como abas top-level (mockup tem só 12; expandir para 17 quebra a hierarquia visual)"
    - "Reintroduzir os expanders dentro de Recap que FIX-10 removeu"
    - "Esconder as órfãs sem deixar acessível por nenhuma rota -- mockup 20, 23, 26, 27, 28 precisam de caminho navegável"
  hipotese:
    - "Após FIX-10 (decisão A), 5 mockups (20-rotina, 23-memorias, 26-cruzamentos, 27-privacidade, 28-rotina-toml) ficaram sem rota top-level. Soluçao: introduzir query param &secao=<X> que renderiza essas páginas DENTRO da aba ativa (preferência: Recap como hub). Cards de navegação na Recap fazem a descoberta visual."
  tests:
    - cmd: ".venv/bin/pytest tests/test_deeplink_orfaos.py -v"
      esperado: "5/5 PASSED"
    - cmd: "grep -nE 'secao=' src/dashboard/app.py"
      esperado: "handler dedicado lê st.query_params['secao'] e dispatch para a página órfã"
  acceptance_criteria:
    - "URL `?cluster=Bem-estar&tab=Recap&secao=Memorias` mostra a página be_memorias (página-índice + sub-cards Treinos/Marcos/Fotos) DENTRO do contexto Recap (mantendo as 12 abas top-level)"
    - "URL `?cluster=Bem-estar&tab=Recap&secao=Rotina` mostra be_rotina (página-índice apontando para Alarmes/Contadores/Tarefas)"
    - "URL `?cluster=Bem-estar&tab=Recap&secao=Cruzamentos` mostra be_cruzamentos"
    - "URL `?cluster=Bem-estar&tab=Recap&secao=Privacidade` mostra be_privacidade"
    - "URL `?cluster=Bem-estar&tab=Recap&secao=Editor-TOML` mostra be_editor_toml"
    - "Página Recap (sem &secao=) mostra cards de navegação no topo apontando para essas 5 órfãs com ícones glyphs (FIX-07) + label"
    - "Sem &secao= e sem param: Recap renderiza conteúdo normal (KPIs do período)"
    - "Sem regressão das 12 abas top-level: cada uma continua renderizando sua página real"
  proof_of_work_esperado: |
    nohup .venv/bin/streamlit run src/dashboard/app.py --server.port 8534 --server.headless true &
    sleep 6
    .venv/bin/python -c "
    from playwright.sync_api import sync_playwright
    import urllib.parse
    orfaos = [('Memorias','MEMÓRIAS'), ('Rotina','ROTINA'), ('Cruzamentos','CRUZAMENTOS'), ('Privacidade','PRIVACIDADE'), ('Editor-TOML','EDITOR')]
    with sync_playwright() as p:
        b = p.chromium.launch(); page = b.new_context().new_page()
        falhas = []
        for secao, h1_esperado in orfaos:
            url = f'http://127.0.0.1:8534/?cluster=Bem-estar&tab=Recap&secao={secao}'
            page.goto(url); page.wait_for_timeout(4500)
            h1s = page.evaluate('Array.from(document.querySelectorAll(\"h1\")).filter(h => h.getBoundingClientRect().width > 0).map(h => h.textContent.trim().toUpperCase())')
            print(f'secao={secao} h1s={h1s}')
            if not any(h1_esperado in h for h in h1s):
                falhas.append((secao, h1s))
        assert not falhas, f'deep-link interno quebrado: {falhas}'
        print('OK 5/5 órfãs acessíveis via deep-link interno')
        b.close()
    "
```

---

# Sprint UX-RD-FIX-14 — Rota interna para 5 páginas órfãs

**Status:** BACKLOG — Onda C5 (acabamento). Depende de FIX-10 e FIX-11.

## 1. Contexto

A decisão A da FIX-10 priorizou implementar Treinos, Marcos, Alarmes, Contadores, Tarefas como abas top-level. Resultado:

- 12 abas no menu Bem-estar com 12 páginas reais 1:1.
- 5 páginas órfãs (be_memorias, be_rotina, be_cruzamentos, be_privacidade, be_editor_toml) **continuam existindo no código** mas sem rota top-level.
- 5 mockups inteiros (20-rotina, 23-memorias, 26-cruzamentos, 27-privacidade, 28-rotina-toml) ficam **sem caminho navegável**.

Esta sprint **fecha a lacuna** sem expandir para 17 abas (que divergiria do mockup que tem 12 itens no shell sidebar).

**Solução**: deep-link interno via query param `&secao=<X>`. Quando presente, a aba ativa renderiza a página órfã correspondente em vez do conteúdo padrão. Cards de navegação na Recap fazem a descoberta visual.

## 2. Hipótese verificável (Fase ANTES)

```bash
# 1) confirma 5 órfãs existem como código (mas não são chamadas no dispatcher)
ls src/dashboard/paginas/be_memorias.py src/dashboard/paginas/be_rotina.py src/dashboard/paginas/be_cruzamentos.py src/dashboard/paginas/be_privacidade.py src/dashboard/paginas/be_editor_toml.py

# 2) confirma FIX-10 removeu chamadas das órfãs do dispatcher
grep -c "be_memorias.renderizar\|be_rotina.renderizar\|be_cruzamentos.renderizar\|be_privacidade.renderizar\|be_editor_toml.renderizar" src/dashboard/app.py
# esperado: 0 nas linhas do dispatcher 12 abas (a partir de ~580); pode haver em outras seções com outra rota

# 3) confirma mockups que pedem rotas
ls novo-mockup/mockups/{20,23,26,27,28}-*.html
```

## 3. Tarefas

### 3.1 Adicionar handler de `&secao=` em `src/dashboard/app.py`

No dispatcher de Bem-estar, antes de renderizar a aba ativa, ler `st.query_params.get("secao")`. Se houver, chamar a página órfã correspondente em vez do conteúdo padrão da aba.

```python
# constante no topo do app.py
SECAO_PARA_ORFA = {
    "Memorias": be_memorias,
    "Rotina": be_rotina,
    "Cruzamentos": be_cruzamentos,
    "Privacidade": be_privacidade,
    "Editor-TOML": be_editor_toml,
}

# dentro do handler do cluster Bem-estar (após criar as 12 tabs)
secao_orfa = st.query_params.get("secao", "")
if secao_orfa in SECAO_PARA_ORFA:
    # renderiza a órfã na aba ativa em vez do conteúdo padrão
    aba_atual = st.session_state.get(CHAVE_SESSION_ABA_ATIVA, "Recap")
    # NÃO renderizar tabs duplicadas; só substituir o conteúdo da aba atual
    SECAO_PARA_ORFA[secao_orfa].renderizar(dados, periodo, pessoa, ctx)
    return  # ou st.stop() para não continuar renderizando o dispatcher das 12 abas

# dispatcher 12 abas (FIX-10) continua normal
```

### 3.2 Cards de navegação na Recap

Em `src/dashboard/paginas/be_recap.py`, adicionar no início de `renderizar()` (antes do conteúdo padrão Recap):

```python
def renderizar(dados, periodo, pessoa, ctx) -> None:
    # se ?secao=X estiver setada, NÃO mostrar o conteúdo padrão (orfã está sendo renderizada pelo handler)
    if st.query_params.get("secao"):
        return  # handler de app.py já chamou a órfã

    # cards-nav para 5 órfãs no topo
    st.markdown(minificar('''
        <header class="page-header">
          <h1 class="page-title">RECAP</h1>
          <p class="page-subtitle">Resumo do período + descoberta de páginas adicionais.</p>
        </header>
        <section class="kpi-grid">
          <a class="kpi card interactive" href="?cluster=Bem-estar&tab=Recap&secao=Memorias">
            <div class="kpi-label">PÁGINA</div>
            <div class="kpi-value" style="font-size: var(--fs-20)">Memórias</div>
            <div class="kpi-delta">Treinos · Marcos · Fotos</div>
          </a>
          <a class="kpi card interactive" href="?cluster=Bem-estar&tab=Recap&secao=Rotina">
            <div class="kpi-label">PÁGINA</div>
            <div class="kpi-value" style="font-size: var(--fs-20)">Rotina</div>
            <div class="kpi-delta">Alarmes · Contadores · Tarefas</div>
          </a>
          <a class="kpi card interactive" href="?cluster=Bem-estar&tab=Recap&secao=Cruzamentos">
            <div class="kpi-label">PÁGINA</div>
            <div class="kpi-value" style="font-size: var(--fs-20)">Cruzamentos</div>
            <div class="kpi-delta">Humor × Eventos × Ciclo</div>
          </a>
          <a class="kpi card interactive" href="?cluster=Bem-estar&tab=Recap&secao=Privacidade">
            <div class="kpi-label">PÁGINA</div>
            <div class="kpi-value" style="font-size: var(--fs-20)">Privacidade</div>
            <div class="kpi-delta">A ↔ B</div>
          </a>
          <a class="kpi card interactive" href="?cluster=Bem-estar&tab=Recap&secao=Editor-TOML">
            <div class="kpi-label">PÁGINA</div>
            <div class="kpi-value" style="font-size: var(--fs-20)">Editor TOML</div>
            <div class="kpi-delta">rotina/*.toml</div>
          </a>
        </section>
    '''), unsafe_allow_html=True)

    # ... resto do conteúdo Recap original (KPIs do período)
```

### 3.3 Atualizar páginas-índice (be_memorias, be_rotina) com botão "Voltar"

Cada órfã renderizada via deep-link deve ter botão para voltar à Recap:

```python
# em cada página órfã, no topo da renderizar():
voltar_url = "?cluster=Bem-estar&tab=Recap"
st.markdown(f'''
    <a class="btn btn-ghost btn-sm" href="{voltar_url}">← Voltar para Recap</a>
''', unsafe_allow_html=True)
```

### 3.4 Tests `tests/test_deeplink_orfaos.py`

```python
import subprocess, time, urllib.parse
import pytest
from playwright.sync_api import sync_playwright

PORT = 8534
ORFAS = [
    ("Memorias", "MEMÓRIAS"),
    ("Rotina", "ROTINA"),
    ("Cruzamentos", "CRUZAMENTOS"),
    ("Privacidade", "PRIVACIDADE"),
    ("Editor-TOML", "EDITOR"),
]

@pytest.fixture(scope="module")
def streamlit_url():
    p = subprocess.Popen([".venv/bin/streamlit","run","src/dashboard/app.py","--server.port",str(PORT),"--server.headless","true"])
    time.sleep(7)
    yield f"http://127.0.0.1:{PORT}"
    p.terminate(); p.wait()

@pytest.mark.parametrize("secao,h1_esperado", ORFAS)
def test_deeplink_secao_orfa(secao, h1_esperado, streamlit_url):
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_context().new_page()
        page.goto(f"{streamlit_url}/?cluster=Bem-estar&tab=Recap&secao={secao}")
        page.wait_for_timeout(4500)
        h1s = page.evaluate("Array.from(document.querySelectorAll('h1')).filter(h => h.getBoundingClientRect().width > 0).map(h => h.textContent.trim().toUpperCase())")
        assert any(h1_esperado in h for h in h1s), f'secao={secao}: nenhum h1 contém {h1_esperado}; h1s={h1s}'
        b.close()

def test_recap_padrao_mostra_5_cards_nav(streamlit_url):
    """Acessar ?cluster=Bem-estar&tab=Recap sem &secao= mostra 5 cards-nav para as órfãs."""
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_context().new_page()
        page.goto(f"{streamlit_url}/?cluster=Bem-estar&tab=Recap")
        page.wait_for_timeout(4500)
        n_links = page.evaluate("document.querySelectorAll('a.kpi.card.interactive[href*=\"secao=\"]').length")
        assert n_links == 5, f'esperado 5 cards-nav, achou {n_links}'
        b.close()
```

## 4. Anti-débito

- **NÃO** introduzir as 5 órfãs como abas top-level. O mockup tem 12 abas; expandir para 17 viola hierarquia visual.
- **NÃO** reintroduzir expanders dentro de Recap (FIX-10 removeu propositalmente).
- Se Streamlit não suportar `st.query_params.get("secao")` na versão usada: fallback para `st.experimental_get_query_params()`. Verificar versão Streamlit primeiro.
- Se ao renderizar a órfã via `&secao=` o dispatcher principal das 12 abas continuar processando (renderizando duplicado): usar `st.stop()` após `SECAO_PARA_ORFA[secao_orfa].renderizar(...)`.

## 5. Validação visual

```bash
nohup .venv/bin/streamlit run src/dashboard/app.py --server.port 8534 --server.headless true &
sleep 6
mkdir -p .playwright-mcp/auditoria/fix-14
.venv/bin/python -c "
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(); page = b.new_context(viewport={'width':1440,'height':900}).new_page()
    # captura Recap com cards
    page.goto('http://127.0.0.1:8534/?cluster=Bem-estar&tab=Recap')
    page.wait_for_timeout(5000)
    page.screenshot(path='.playwright-mcp/auditoria/fix-14/recap_com_cards_nav.png', full_page=True)
    # captura cada órfã
    for secao in ['Memorias','Rotina','Cruzamentos','Privacidade','Editor-TOML']:
        page.goto(f'http://127.0.0.1:8534/?cluster=Bem-estar&tab=Recap&secao={secao}')
        page.wait_for_timeout(4500)
        page.screenshot(path=f'.playwright-mcp/auditoria/fix-14/orfa_{secao.lower()}.png', full_page=True)
    b.close()
"
```

Validador humano confere: 5 PNGs órfãs aparecem dentro do contexto Recap com botão "Voltar" + conteúdo da página órfã.

## 6. Gauntlet

```bash
make lint                                                # exit 0
make smoke                                               # 10/10
.venv/bin/pytest tests/test_deeplink_orfaos.py -v        # 6/6 (5 órfãs + 1 cards-nav)
.venv/bin/pytest tests/ -q --tb=no                       # baseline mantida
```

---

*"Toda página merece uma porta, mesmo que seja por dentro de outra." -- adaptado de Borges*
