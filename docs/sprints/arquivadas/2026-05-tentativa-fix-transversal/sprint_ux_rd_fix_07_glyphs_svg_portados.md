---
concluida_em: 2026-05-05
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: UX-RD-FIX-07
  title: "Portar 52 glyphs SVG do mockup glyphs.js para componentes/glyphs.py"
  prioridade: P1
  estimativa: 1 dia (8h)
  onda: C2
  origem: "AUDITORIA_REDESIGN_2026-05-05.md §7.5, §8.6 (iconografia 0% portada)"
  depende_de: []
  bloqueia: []
  touches:
    - path: src/dashboard/componentes/glyphs.py
      reason: "NOVO -- biblioteca Python espelhando novo-mockup/_shared/glyphs.js (23 SVGs inline com estética mono-linha 1.5px)"
    - path: src/dashboard/componentes/shell.py
      reason: "linha 138-141: substituir <span class='sidebar-brand-glyph'>O</span> por glyph('ouroboros', 20)"
    - path: tests/test_glyphs.py
      reason: "NOVO -- testa que glyph(nome, tamanho) retorna SVG válido para os 23 nomes; viewBox=24x24; stroke-width 1.5; estrutura idêntica ao glyphs.js"
  forbidden:
    - "Importar Material Symbols como substituto (perde estética mono-linha do mockup)"
    - "Inline SVG diferente do glyphs.js do mockup (mesmo path data; mesma viewBox)"
  hipotese:
    - "Validação direta no DOM mostrou .sidebar-brand-glyph com text='O' e has_svg=False. Mockup glyphs.js (90 linhas) tem 23 ícones SVG inline. Necessário portar 1:1."
  tests:
    - cmd: ".venv/bin/pytest tests/test_glyphs.py -v"
      esperado: "23 testes (1 por glyph) PASSED + 4 testes contrato (viewBox, stroke, currentColor, accessibility role)"
    - cmd: "grep -c \"def glyph\" src/dashboard/componentes/glyphs.py"
      esperado: "1 (uma função pública renderiza qualquer glyph por nome)"
  acceptance_criteria:
    - "src/dashboard/componentes/glyphs.py exporta `glyph(nome: str, tamanho_px: int = 16, classe: str = '') -> str` que retorna string HTML com <svg viewBox='0 0 24 24' width=tamanho_px height=tamanho_px> contendo o path data correto do glyphs.js"
    - "Os 23 nomes funcionam: ouroboros, inbox, home, docs, analise, metas, financas, search, upload, download, diff, validar, rejeitar, revisar, drag, more, filter, expand, collapse, close, terminal, folder, arrow-left, arrow-right (= 24 com arrow-right; ajustar contagem se necessário)"
    - "Sidebar brand renderiza ouroboros SVG (não letra 'O') -- validar via DOM has_svg=true após mudança em shell.py"
    - "Glyph tem fill='none' stroke='currentColor' stroke-width='1.5' stroke-linecap='square' stroke-linejoin='miter' (estilo mono-linha do mockup)"
  proof_of_work_esperado: |
    .venv/bin/python -c "
    from src.dashboard.componentes.glyphs import glyph, GLYPHS
    print('total glyphs:', len(GLYPHS))   # esperado: 23 ou 24
    for nome in ['ouroboros','inbox','home','docs','analise','metas','financas']:
        svg = glyph(nome, 20)
        assert '<svg' in svg and 'viewBox=\"0 0 24 24\"' in svg, f'{nome}: SVG mal-formado'
        print(f'{nome}: OK')
    "
    nohup .venv/bin/streamlit run src/dashboard/app.py --server.port 8525 --server.headless true &
    sleep 6
    .venv/bin/python -c "
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(); page = b.new_context().new_page()
        page.goto('http://127.0.0.1:8525/')
        page.wait_for_timeout(4000)
        info = page.evaluate('''() => {
            const g = document.querySelector('.sidebar-brand-glyph');
            return g ? { has_svg: !!g.querySelector('svg'), inner: g.innerHTML.slice(0,80) } : null;
        }''')
        print('brand glyph:', info)   # esperado: has_svg: true, inner com '<svg'
        assert info and info['has_svg'], 'sidebar-brand-glyph deve conter <svg>'
        b.close()
    "
```

---

# Sprint UX-RD-FIX-07 — 52 glyphs SVG portados

**Status:** BACKLOG — Onda C2 (reconstrução estética).

## 1. Contexto

`novo-mockup/_shared/glyphs.js` (90 linhas) é a fonte canônica de iconografia do redesign. Contém 23 SVGs inline com estética **mono-linha 1.5px, traço quadrado, viewBox 24×24**, todos usando `currentColor` para herdar cor do contexto. Cobertura:

```
ouroboros  inbox    home     docs     analise   metas    financas
search     upload   download diff     validar   rejeitar revisar
drag       more     filter   expand   collapse  close    terminal
folder     arrow-left  arrow-right
```

Auditoria 2026-05-05 §8.6 confirmou que **nenhum** desses ícones foi portado para o dashboard. Resultado:
- `.sidebar-brand-glyph` mostra letra "O" (placeholder).
- Cluster headers da sidebar não têm ícones.
- Nenhuma página usa glyphs do mockup.

Esta sprint cria `src/dashboard/componentes/glyphs.py` que espelha 1:1 `glyphs.js` em Python.

## 2. Hipótese verificável (Fase ANTES)

```bash
# 1) inventário literal do mockup -- gerar lista de N glyphs
grep -cE "^\s+[a-z][a-z_-]+\s*:\s*'" novo-mockup/_shared/glyphs.js
# esperado: 52 (validado 2026-05-05)

# 2) listar nomes dos 52 glyphs em ordem de declaração
grep -oE "^\s+[a-z][a-z_-]+\s*:" novo-mockup/_shared/glyphs.js | sed 's/[: ]//g' | tee /tmp/glyphs_canonicos.txt
wc -l /tmp/glyphs_canonicos.txt   # esperado: 52

# 3) extrair par <nome, path-data> via Python
.venv/bin/python -c "
import re
with open('novo-mockup/_shared/glyphs.js') as f: js = f.read()
matches = re.findall(r\"^\s+([a-z][a-z_-]+)\s*:\s*'([^']+)'\", js, re.MULTILINE)
print(f'Total glyphs no mockup: {len(matches)}')
for nome, paths in matches[:5]:
    print(f'  {nome}: {paths[:60]}...')
"

# 4) confirma componente ainda não existe
ls src/dashboard/componentes/glyphs.py 2>/dev/null
# esperado: arquivo NÃO existe
```

## 3. Tarefas

1. Rodar hipótese.
2. Criar `src/dashboard/componentes/glyphs.py` com a estrutura:

   ```python
   """Biblioteca de glyphs SVG espelhando novo-mockup/_shared/glyphs.js.
   
   Estética canônica: mono-linha 1.5px, traço quadrado, viewBox 24x24,
   stroke=currentColor (herda cor do contexto), fill=none.
   """
   from __future__ import annotations
   from typing import Final
   import html as _html

   GLYPHS: Final[dict[str, str]] = {
       "ouroboros": '<circle cx="12" cy="12" r="7" fill="none"/><path d="M5.5 9.5 L4 8 L6 7"/><path d="M18.5 14.5 L20 16 L18 17"/>',
       "inbox":     '<path d="M3 13v5a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-5"/><path d="M3 13l3-8h12l3 8"/><path d="M3 13h5l1 3h6l1-3h5"/>',
       "home":      '<path d="M4 11l8-7 8 7v9a1 1 0 0 1-1 1h-4v-7h-6v7H5a1 1 0 0 1-1-1z"/>',
       "docs":      '<path d="M6 3h9l4 4v14H6z"/><path d="M14 3v5h5"/><path d="M9 13h7M9 17h7"/>',
       "analise":   '<path d="M3 20h18"/><path d="M5 20V8M10 20V4M15 20V11M20 20V6"/>',
       "metas":     '<circle cx="12" cy="12" r="8" fill="none"/><circle cx="12" cy="12" r="4" fill="none"/><circle cx="12" cy="12" r="1" fill="currentColor"/>',
       "financas":  '<path d="M3 20V8l4-3 5 3 5-3 4 3v12z"/><path d="M3 13h18M9 8v12M15 8v12"/>',
       # ... (continuar copiando do glyphs.js para os 23 ícones)
   }

   def glyph(nome: str, tamanho_px: int = 16, classe: str = "") -> str:
       """Retorna string HTML com <svg> inline para o glyph nomeado.
       
       Args:
           nome: chave em GLYPHS (case-sensitive). KeyError se ausente.
           tamanho_px: width/height do <svg> em pixels.
           classe: class CSS adicional (ex.: "sidebar-brand-glyph").
       """
       if nome not in GLYPHS:
           raise KeyError(f"glyph '{nome}' não existe. Disponíveis: {sorted(GLYPHS)}")
       paths = GLYPHS[nome]
       cls = f' class="{_html.escape(classe)}"' if classe else ""
       return (
           f'<svg{cls} width="{tamanho_px}" height="{tamanho_px}" '
           f'viewBox="0 0 24 24" fill="none" stroke="currentColor" '
           f'stroke-width="1.5" stroke-linecap="square" stroke-linejoin="miter" '
           f'aria-hidden="true">{paths}</svg>'
       )

   # "<citação filosófica final>"
   ```

3. Copiar **literalmente** os 23 path-data de `glyphs.js`. **NÃO** redesenhar -- são canônicos.
4. Em `src/dashboard/componentes/shell.py:135-141`, substituir:
   ```python
   # ANTES
   '<span class="sidebar-brand-glyph" aria-hidden="true">O</span>'
   # DEPOIS
   from src.dashboard.componentes.glyphs import glyph
   ...
   f'{glyph("ouroboros", 20, classe="sidebar-brand-glyph")}'
   ```
5. Aplicar o mesmo padrão em `_renderizar_sidebar_clusters_html()` -- adicionar glyph antes do nome do cluster (referência: components.css define `.sidebar-cluster-header` com gap 8px e suporta SVG inline).
6. Criar `tests/test_glyphs.py` com:
   - `test_total_glyphs_iguala_23()` (ou 24 se incluir arrow-right)
   - `test_cada_glyph_tem_viewbox_24x24()` para cada nome
   - `test_glyph_retorna_string_html_valida()`
   - `test_glyph_aceita_classe_extra()`
   - `test_glyph_inexistente_levanta_keyerror()`
   - `test_brand_renderiza_ouroboros_svg()` (integração com shell.py)
7. Rodar gauntlet (§6) e capturar PNG da sidebar com SVG ouroboros + cluster glyphs.

## 4. Anti-débito

- **NÃO redesenhar SVGs**. Copiar literal do glyphs.js. A divergência canônica é proibida.
- Se algum path-data tiver caractere especial conflitando com Python string literal: usar raw string `r'...'` ou escape adequado. **NÃO** mudar o conteúdo do path.
- Se faltar algum glyph no glyphs.js (ex.: usado em mockup mas não declarado): registrar achado colateral em sprint **UX-RD-FIX-07.B**.

## 5. Validação visual

PNG da sidebar mostrando:
- Brand: ícone ouroboros (círculo + 2 setas) em vez de letra "O"
- 8 cluster headers com glyphs ao lado do nome (Inbox icon, Home icon, etc.)

Comparar com `novo-mockup/mockups/00-shell-navegacao.html` -- visual deve casar.

## 6. Gauntlet

```bash
make lint                                          # exit 0
make smoke                                         # 10/10
.venv/bin/pytest tests/test_glyphs.py -v           # 27+ PASSED
.venv/bin/pytest tests/ -q --tb=no                 # baseline >=2520 + glyphs
wc -l src/dashboard/componentes/glyphs.py          # ~150 linhas (23 paths + helpers)
```

---

*"Quem desenha um traço só, desenha o mundo." -- Saul Steinberg (paráfrase)*
