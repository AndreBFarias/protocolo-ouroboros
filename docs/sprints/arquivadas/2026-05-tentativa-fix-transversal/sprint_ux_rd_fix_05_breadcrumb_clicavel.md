---
concluida_em: 2026-05-05
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: UX-RD-FIX-05
  title: "Tornar breadcrumb clicável (.seg span -> a href)"
  prioridade: P1
  estimativa: 1h
  onda: C1
  origem: "AUDITORIA_REDESIGN_2026-05-05.md §8.5 (UX patterns -- breadcrumb não-clicável)"
  depende_de: []
  bloqueia: []
  touches:
    - path: src/dashboard/componentes/shell.py
      reason: "linhas ~265-269: trocar <span class='seg'> por <a class='seg' href='?cluster=X'> mantendo .seg.current como span (último segmento, não-clicável)"
    - path: tests/test_breadcrumb_clicavel.py
      reason: "NOVO -- 4 testes: segmentos não-current viram <a>; segmento current permanece <span>; href contém ?cluster=; clicar redireciona corretamente"
  forbidden:
    - "Quebrar visual: classe .seg deve manter mesma aparência mono UPPERCASE 12px text-secondary do mockup"
    - "Tornar último segmento clicável (página atual)"
  hipotese:
    - "shell.py:266-269 monta <span class='seg current' ou class='seg'> sempre como SPAN. Validação direta confirmou seg_current.is_link=false. Mockup pede .seg como link clicável (components.css:114-121)."
  tests:
    - cmd: "grep -nE \"<span class='seg\" src/dashboard/componentes/shell.py"
      esperado: "apenas .seg.current permanece span; demais segmentos são <a>"
    - cmd: ".venv/bin/pytest tests/test_breadcrumb_clicavel.py -v"
      esperado: "4/4 PASSED"
  acceptance_criteria:
    - "DOM real: nas telas Revisor (cluster=Documentos), breadcrumb tem 'OUROBOROS / Documentos / Revisor' onde 'Documentos' é <a href='?cluster=Documentos'> e 'Revisor' permanece span"
    - "Clicar em 'Documentos' no breadcrumb redireciona para ?cluster=Documentos&tab=<padrão> (primeira aba do cluster)"
    - "Estilo visual idêntico ao atual (mono UPPERCASE 12px ls 0.48px text-secondary; current = text-primary)"
    - "Hover em <a class='seg'> aplica text-decoration: underline (default <a>)"
  proof_of_work_esperado: |
    nohup .venv/bin/streamlit run src/dashboard/app.py --server.port 8523 --server.headless true &
    sleep 6
    .venv/bin/python -c "
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(); page = b.new_context().new_page()
        page.goto('http://127.0.0.1:8523/?cluster=Documentos&tab=Revisor')
        page.wait_for_timeout(4000)
        info = page.evaluate('''() => {
            const segs = document.querySelectorAll('.breadcrumb .seg');
            return Array.from(segs).map(s => ({
                tag: s.tagName,
                href: s.href || null,
                text: s.textContent.trim(),
                is_current: s.classList.contains('current')
            }));
        }''')
        print('breadcrumb:', info)
        # validar contrato:
        # primeiros n-1 segmentos devem ser A; ultimo SPAN current
        assert all(s['tag']=='A' for s in info[:-1]), 'segmentos não-current devem ser <a>'
        assert info[-1]['tag']=='SPAN' and info[-1]['is_current'], 'último segmento deve ser <span class=current>'
        print('OK contrato breadcrumb')
        b.close()
    "
```

---

# Sprint UX-RD-FIX-05 — Breadcrumb clicável

**Status:** BACKLOG — Onda C1 (higiene crítica).

## 1. Contexto

Auditoria 2026-05-05 §8.5 confirmou que `.breadcrumb .seg` é renderizado como `<span>` não-clicável em `componentes/shell.py:266-269`:

```python
# Implementação atual
classe = "seg current" if ultimo else "seg"
sep = "" if ultimo else '<span class="sep">/</span>'
partes_seg.append(f'<span class="{classe}">{rotulo}</span>{sep}')
```

Mockup canônico (`novo-mockup/_shared/components.css:114-121`) define `.breadcrumb .seg` como elemento clicável, e `.seg.current` como o segmento da página atual (não-clicável).

**Comportamento esperado**: clicar em "Documentos" no breadcrumb da tela "Revisor" deve redirecionar para `?cluster=Documentos` (primeira aba do cluster).

## 2. Hipótese verificável (Fase ANTES)

```bash
# 1) confirma estado atual
grep -nE "<span class='seg" src/dashboard/componentes/shell.py
# esperado: linha 269 mostra <span class='{classe}'>...</span>

# 2) confirma .seg .current contrato no mockup
grep -nA 5 "\.seg\b\|\.seg.current" novo-mockup/_shared/components.css
```

## 3. Tarefas

1. Rodar hipótese.
2. Em `src/dashboard/componentes/shell.py:265-269`, modificar o bloco de montagem do breadcrumb:

   ```python
   # NOVO
   ultimo = i == n - 1
   rotulo = html.escape(seg)
   sep = "" if ultimo else '<span class="sep">/</span>'
   if ultimo:
       partes_seg.append(f'<span class="seg current">{rotulo}</span>{sep}')
   else:
       # cluster pai: linkar para a primeira aba do cluster
       href_pai = _href_para(cluster=seg) if seg in CLUSTERS_VALIDOS else "?"
       partes_seg.append(
           f'<a class="seg" href="{html.escape(href_pai)}">{rotulo}</a>{sep}'
       )
   ```
   
   Importar `CLUSTERS_VALIDOS` de `src/dashboard/componentes/drilldown.py` se ainda não estiver importado.
3. Garantir que primeiro segmento ("OUROBOROS") aponta para `?cluster=Home`.
4. Criar `tests/test_breadcrumb_clicavel.py` com 4 testes:
   ```python
   def test_segmentos_intermediarios_sao_a():
       html = renderizar_topbar(cluster='Documentos', aba_ativa='Revisor', breadcrumb=['OUROBOROS', 'Documentos', 'Revisor'])
       assert '<a class="seg" href="?cluster=' in html

   def test_segmento_current_e_span():
       html = renderizar_topbar(cluster='Documentos', aba_ativa='Revisor', breadcrumb=['OUROBOROS', 'Documentos', 'Revisor'])
       assert '<span class="seg current">Revisor</span>' in html

   def test_href_aponta_cluster_valido():
       html = renderizar_topbar(cluster='Documentos', aba_ativa='Revisor', breadcrumb=['OUROBOROS', 'Documentos', 'Revisor'])
       assert 'href="?cluster=Documentos"' in html

   def test_breadcrumb_uma_so_classe_current():
       html = renderizar_topbar(cluster='Documentos', aba_ativa='Revisor', breadcrumb=['OUROBOROS', 'Documentos', 'Revisor'])
       assert html.count('class="seg current"') == 1
   ```
5. Garantir que CSS do `.seg` herda cor do parent (`<a>` precisa `color: inherit; text-decoration: none` em estado normal). Verificar em `tema_css.py` se já tem; se não, adicionar.
6. Rodar gauntlet (§6) e capturar PNG do breadcrumb (com hover).

## 4. Anti-débito

- Se houver mais que `cluster | tab` no breadcrumb (ex.: "Documentos / Revisor / Pendência X"): manter regra "todos exceto último viram <a>". O href do segmento intermediário deve ser o estado mais raso possível.
- Se `_href_para()` não existir, usar `?cluster=<seg>` direto.

## 5. Validação visual

```bash
# Capturar antes/depois com hover
nohup .venv/bin/streamlit run src/dashboard/app.py --server.port 8523 --server.headless true &
sleep 6
.venv/bin/python -c "
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(); page = b.new_context(viewport={'width':1440,'height':900}).new_page()
    page.goto('http://127.0.0.1:8523/?cluster=Documentos&tab=Revisor')
    page.wait_for_timeout(4000)
    page.screenshot(path='.playwright-mcp/auditoria/fix-05/breadcrumb_normal.png', full_page=False)
    page.hover('a.seg')
    page.wait_for_timeout(300)
    page.screenshot(path='.playwright-mcp/auditoria/fix-05/breadcrumb_hover.png', full_page=False)
    b.close()
"
```

## 6. Gauntlet

```bash
make lint                                                # exit 0
make smoke                                               # 10/10
.venv/bin/pytest tests/test_breadcrumb_clicavel.py -v    # 4/4
.venv/bin/pytest tests/ -q --tb=no                       # baseline >=2520
```

---

*"O caminho de volta é tão necessário quanto o de ida." -- Antoine de Saint-Exupéry (paráfrase)*
