---
concluida_em: 2026-05-05
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: UX-RD-FIX-06
  title: "Eliminar h1 duplicado (st.title global) e garantir 1 h1 visível por tela"
  prioridade: P0
  estimativa: 1h
  onda: C1
  origem: "AUDITORIA_REDESIGN_2026-05-05.md §7.4 e §8.7 (top problema #3)"
  depende_de: []
  bloqueia: []
  touches:
    - path: src/dashboard/app.py
      reason: "linha 238: st.title('Protocolo Ouroboros') executado quando logo_html é falsy. Brand já vem do shell HTML em sidebar. Remover para eliminar h1 duplicado."
    - path: tests/test_h1_unico_por_tela.py
      reason: "NOVO -- testa playwright que apenas 1 h1 visível por tela em 6 telas-amostra (Visão Geral, Revisor, Categorias, Inbox, Bem-estar/Hoje, Skills D7)"
  forbidden:
    - "Remover o brand 'Ouroboros' da sidebar (renderizado por _renderizar_brand_html no shell)"
    - "Quebrar fallback caso assets/ouroboros.svg não exista (logo_html None deve degradar para apenas o brand HTML, não para st.title)"
  hipotese:
    - "Validação direta no DOM mostrou 2 h1 visíveis simultaneamente em todas as telas: 'Protocolo Ouroboros' (st.title global, fs 28 #bd93f9) + page-title da seção (fs 28 com gradient text). O st.title vem de app.py:238 quando logo_html falsy. Mas auditoria mostrou que está sendo executado mesmo com logo presente -- investigar."
  tests:
    - cmd: "grep -n 'st.title.*Protocolo Ouroboros' src/dashboard/app.py"
      esperado: "zero ocorrências"
    - cmd: ".venv/bin/pytest tests/test_h1_unico_por_tela.py -v"
      esperado: "6/6 PASSED"
  acceptance_criteria:
    - "Em qualquer tela do dashboard, document.querySelectorAll('h1') filtrado por 'visivel' (width>0 && display != none) retorna EXATAMENTE 1"
    - "O h1 visível corresponde ao page-title da seção atual ('REVISOR' em Revisor, 'CATEGORIAS' em Categorias, etc.)"
    - "A sidebar continua mostrando o brand 'Ouroboros' (via .sidebar-brand do shell HTML)"
    - "Nenhum 'Protocolo Ouroboros' aparece como h1 (apenas como caption ou texto secundário)"
  proof_of_work_esperado: |
    nohup .venv/bin/streamlit run src/dashboard/app.py --server.port 8524 --server.headless true &
    sleep 6
    .venv/bin/python -c "
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(); page = b.new_context().new_page()
        for cluster, tab in [('Home', 'Visão Geral'), ('Documentos', 'Revisor'), ('Análise', 'Categorias'), ('Inbox', 'Inbox'), ('Bem-estar', 'Hoje'), ('Sistema', 'Skills D7')]:
            import urllib.parse
            url = f'http://127.0.0.1:8524/?cluster={urllib.parse.quote(cluster)}&tab={urllib.parse.quote(tab)}'
            page.goto(url); page.wait_for_timeout(4000)
            n_h1_visiveis = page.evaluate('Array.from(document.querySelectorAll(\"h1\")).filter(h => h.getBoundingClientRect().width > 0 && getComputedStyle(h).display !== \"none\").length')
            txts = page.evaluate('Array.from(document.querySelectorAll(\"h1\")).filter(h => h.getBoundingClientRect().width > 0).map(h => h.textContent.trim().slice(0,40))')
            assert n_h1_visiveis == 1, f'{cluster}/{tab}: esperado 1 h1, achou {n_h1_visiveis}: {txts}'
            print(f'OK {cluster}/{tab}: 1 h1 = {txts}')
        b.close()
    "
```

---

# Sprint UX-RD-FIX-06 — H1 duplicado por st.title global

**Status:** BACKLOG — Onda C1 (higiene crítica).

## 1. Contexto

Auditoria 2026-05-05 §8.7 confirmou via DOM real:

```
h1[1]: "Protocolo Ouroboros" (st.title global) -- visível, fs 28px, color #bd93f9 sólido
h1[2]: "Os arquivos da sua vida financeira..." (page-title hero) -- visível, fs 28px, JetBrains Mono
```

Em **todas as 6 telas amostradas** o primeiro h1 vem de `src/dashboard/app.py:238`:

```python
logo_html = logo_sidebar_html(largura_px=120)
if logo_html:
    st.markdown(logo_html, unsafe_allow_html=True)
else:
    st.title("Protocolo Ouroboros")
```

A intenção original era **fallback gracioso** quando o logo SVG não existe. Mas a auditoria mostrou que `Protocolo Ouroboros` aparece como h1 visível mesmo quando o logo está presente -- provavelmente o `st.title` está sendo executado em outro caminho. Investigar grep adicional.

**Resultado**: viola HTML/A11y (1 h1 por documento) e rouba foco visual da page-title da seção.

## 2. Hipótese verificável (Fase ANTES)

```bash
# 1) onde mais aparece st.title("Protocolo Ouroboros") ou similar
grep -rnE 'st\.title\(' src/dashboard/ 2>/dev/null

# 2) confirma 2 h1 visiveis hoje
nohup .venv/bin/streamlit run src/dashboard/app.py --server.port 8524 --server.headless true &
sleep 6
.venv/bin/python -c "
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(); page = b.new_context().new_page()
    page.goto('http://127.0.0.1:8524/?cluster=Documentos&tab=Revisor')
    page.wait_for_timeout(4000)
    h1s = page.evaluate('Array.from(document.querySelectorAll(\"h1\")).filter(h => h.getBoundingClientRect().width > 0).map(h => h.textContent.trim())')
    print(f'h1 visiveis HOJE: {h1s}')   # esperado: ['Protocolo Ouroboros', 'REVISOR']
    b.close()
"
pkill -f 'streamlit.*8524'
```

## 3. Tarefas

1. Rodar hipótese (§2).
2. Localizar **todas** as ocorrências de `st.title(`, `st.header(`, `<h1>` em `src/dashboard/`.
3. Em `src/dashboard/app.py` linhas 234-238, **remover** o `st.title("Protocolo Ouroboros")` do fallback. Substituir por:
   ```python
   logo_html = logo_sidebar_html(largura_px=120)
   if logo_html:
       st.markdown(logo_html, unsafe_allow_html=True)
   # else: brand já é renderizado pela sidebar HTML (renderizar_brand_html); sem fallback h1.
   ```
4. Se houver `st.title` ou h1 redundante em outras páginas (ex.: alguma `paginas/*.py` com `st.title("Algo")`), substituir por `st.markdown('<h1 class="page-title">ALGO</h1>', unsafe_allow_html=True)` para que (a) a tela tenha exatamente 1 h1 com classe `page-title`, (b) herde o estilo gradient + UPPERCASE do tema.
5. Criar `tests/test_h1_unico_por_tela.py` (template no §0 proof-of-work).
6. Rodar gauntlet.

## 4. Anti-débito

- Se `logo_sidebar_html()` retornar None com frequência (ex.: assets/ouroboros.svg ausente em CI): adicionar warning de log ao invés de fallback h1. Não recriar h1 redundante.
- Se uma página `paginas/X.py` quebrar por causa da remoção do h1 (ex.: testa que existe `<h1>X</h1>`): atualizar o teste para esperar `<h1 class="page-title">X</h1>`.

## 5. Validação visual

PNG comparativo de Revisor antes/depois mostrando:
- Antes: 2 h1 ("Protocolo Ouroboros" + "REVISOR")
- Depois: 1 h1 ("REVISOR" com page-title estilo correto)

## 6. Gauntlet

```bash
make lint                                                # exit 0
make smoke                                               # 10/10
.venv/bin/pytest tests/test_h1_unico_por_tela.py -v      # 6/6
.venv/bin/pytest tests/ -q --tb=no                       # baseline >=2520
grep -c 'st\.title' src/dashboard/app.py                 # zero
```

---

*"Há um único nome para cada coisa, e quem o sabe domina o mundo." -- Borges (paráfrase)*
