---
concluida_em: 2026-05-06
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: UX-U-03
  title: "Page-header canônico (helper page_header.py + refactor 29 páginas)"
  prioridade: P0
  estimativa: 1 dia
  onda: U
  mockup_fonte: novo-mockup/_shared/components.css `.page-header`/`.page-title`/`.page-subtitle`/`.page-meta` (linhas 130-156)
  depende_de: [UX-U-02]
  bloqueia: [UX-U-04, UX-T-01..UX-T-29]
  touches:
    - path: src/dashboard/componentes/page_header.py
      reason: "NOVO -- helper renderizar_page_header(titulo, subtitulo='', sprint_tag='', pills=()) -> str que emite <header class='page-header'> com h1.page-title (UPPERCASE 40px gradient), p.page-subtitle, div.page-meta com sprint-tag + pills."
    - path: 29 paginas/*.py
      reason: "Refactor: cada página substitui seu st.markdown('# X') OU st.title() OU emissão direta de h1 inline pelo helper renderizar_page_header(). Padrão único cross-páginas."
    - path: tests/test_page_header_canonico.py
      reason: "NOVO -- testa que helper emite HTML correto; 6 telas-amostra (Visão Geral, Extrato, Revisor, Categorias, Bem-estar/Hoje, Skills D7) renderizam EXATAMENTE 1 h1.page-title com font-family JetBrains Mono, font-size canônico (depende viewport), text-transform UPPERCASE, gradient text via background-clip."
  forbidden:
    - "Manter qualquer st.markdown('# X') ou st.title() em paginas/*.py após refactor."
    - "Mudar o CSS .page-title (já está canônico em tema_css.py + components.css). Apenas garantir que TODAS as páginas aplicam a classe."
    - "Criar h1 fora do helper (regra: 1 h1 visível por tela; helper é a única fonte)."
  hipotese:
    - "Hoje algumas páginas usam <h1 class='page-title'> via emissão direta (Categorias, Revisor, Bem-estar/*, Inbox, Skills D7) e outras usam st.markdown('# X') ou st.markdown('## X') gerando h1/h2 sans plain (Extrato, Editor TOML, possivelmente outras). UX-RD-FIX-08 trouxe gradient + UPPERCASE para .page-title via CSS, mas só páginas que aplicam a CLASSE recebem o estilo."
  tests:
    - cmd: ".venv/bin/pytest tests/test_page_header_canonico.py -v"
      esperado: "10+ PASSED (helper unitário + 6 telas integração)"
    - cmd: "grep -rE 'st\\.title|st\\.markdown.*\\\\* \\|## ' src/dashboard/paginas/*.py"
      esperado: "ZERO ocorrências (todas migradas para o helper)"
  acceptance_criteria:
    - "src/dashboard/componentes/page_header.py exporta renderizar_page_header(titulo: str, subtitulo: str = '', sprint_tag: str = '', pills: list[dict] = ()) -> str"
    - "HTML emitido tem estrutura: <header class='page-header'><div><h1 class='page-title'>{titulo}</h1><p class='page-subtitle'>{subtitulo}</p></div><div class='page-meta'>{sprint_tag}{pills}</div></header>"
    - "29 páginas em src/dashboard/paginas/*.py usam o helper como ponto único de emissão de page-title"
    - "DOM de 6 telas amostra mostra: 1 h1 visível, font-family JetBrains Mono (ou ui-monospace fallback), font-size 40px (canônico) ou variante responsiva, text-transform UPPERCASE, background-image linear-gradient (gradient text)"
    - "Validação humana: dono navega entre 6 telas e confirma title HOMOGENIA visualmente (mesmo peso/tamanho/efeito gradient)"
  proof_of_work_esperado: |
    grep -rE 'st\.title\(|st\.markdown\(["\x27]# ' src/dashboard/paginas/*.py
    # Esperado: zero ocorrências (todas migradas)
    .venv/bin/pytest tests/test_page_header_canonico.py -v
    # Visual: dashboard rodando + capturas de 6 telas com page-title
```

---

# Sprint UX-U-03 — Page-header canônico

**Status:** BACKLOG — Onda U (estruturante).

## 1. Contexto

UX-RD-FIX-08 (arquivada) ajustou config.toml + tema_css.py para Inter (sans) + JetBrains Mono (mono). Páginas que aplicam `<h1 class="page-title">` recebem UPPERCASE 40px gradient corretamente. Mas várias páginas emitem `st.markdown("# Título")` ou `st.title("X")` que viram `<h1>` sem a classe — então caem no estilo padrão Streamlit (sans, 28px, sem caps, sem gradient).

Diagnóstico (auditoria 2026-05-05 + revisão 2026-05-06):

- **Páginas com `.page-title` aplicada (canônico)**: Categorias, Revisor, Inbox, Skills D7, Cruzamentos, Privacidade, Eventos, Bem-estar/Hoje, Visão Geral hero
- **Páginas SEM `.page-title` (variantes)**: Extrato (`# Extrato` lowercase), Editor TOML (sem caps + sem gradient), e outras a auditar

Esta sprint **unifica** via helper único `renderizar_page_header()`. 29 páginas convergem para o mesmo padrão.

## 2. Hipótese verificável (Fase ANTES)

```bash
# 1. inventário st.title / st.markdown('# X') em paginas/
grep -rnE '^\s*st\.title\(' src/dashboard/paginas/*.py | wc -l
grep -rnE 'st\.markdown\(["\x27]#[^#]' src/dashboard/paginas/*.py | wc -l

# 2. inventário h1.page-title canônico
grep -rnE '<h1 class="page-title">' src/dashboard/paginas/*.py | wc -l

# 3. captura dom h1 fonte por tela
nohup .venv/bin/streamlit run src/dashboard/app.py --server.port 8765 --server.headless true &
sleep 8
.venv/bin/python -c "
from playwright.sync_api import sync_playwright
import urllib.parse
TELAS = [('Home','Visão Geral'),('Finanças','Extrato'),('Documentos','Revisor'),('Análise','Categorias'),('Bem-estar','Hoje'),('Sistema','Skills D7')]
with sync_playwright() as p:
    b = p.chromium.launch(); page = b.new_context().new_page()
    for cluster, tab in TELAS:
        url = f'http://127.0.0.1:8765/?cluster={urllib.parse.quote(cluster)}&tab={urllib.parse.quote(tab)}'
        page.goto(url); page.wait_for_timeout(4500)
        info = page.evaluate('''() => {
            const h1s = Array.from(document.querySelectorAll('h1')).filter(h => h.getBoundingClientRect().width > 0);
            return h1s.map(h => ({
                tem_classe: h.className,
                txt: h.textContent.trim().slice(0,40),
                fs: getComputedStyle(h).fontSize,
                ff: getComputedStyle(h).fontFamily.slice(0,30),
                tt: getComputedStyle(h).textTransform,
                bg: getComputedStyle(h).backgroundImage.slice(0,40)
            }));
        }''')
        print(f'{cluster}/{tab}: {info}')
    b.close()
"
pkill -f 'streamlit.*8765'
```

## 3. Tarefas

1. Rodar hipótese ANTES e anotar quais páginas têm `.page-title` aplicada e quais não.

2. Criar `src/dashboard/componentes/page_header.py`:

   ```python
   """Page-header canônico do redesign.

   Único ponto de emissão de h1.page-title em src/dashboard/paginas/*.py.
   Garante consistência visual cross-páginas (UPPERCASE 40px JetBrains Mono
   gradient text). Mockup-fonte: novo-mockup/_shared/components.css linhas
   130-156 (.page-header, .page-title, .page-subtitle, .page-meta).

   Uso:
       from src.dashboard.componentes.page_header import renderizar_page_header
       st.markdown(
           renderizar_page_header(
               titulo="EXTRATO",
               subtitulo="Tabela densa com transações do período.",
               sprint_tag="UX-T-02",
               pills=[{"texto": "78 transações", "tipo": "d7-graduado"}],
           ),
           unsafe_allow_html=True,
       )
   """
   from __future__ import annotations
   import html as _html
   from typing import Iterable, TypedDict

   class Pill(TypedDict, total=False):
       texto: str
       tipo: str  # d7-graduado / d7-calibracao / d7-regredindo / humano-aprovado / etc.

   def _renderizar_pill(pill: Pill) -> str:
       tipo = pill.get("tipo", "d7-pendente")
       texto = _html.escape(str(pill.get("texto", "")))
       return f'<span class="pill pill-{tipo}">{texto}</span>'

   def renderizar_page_header(
       titulo: str,
       subtitulo: str = "",
       sprint_tag: str = "",
       pills: Iterable[Pill] = (),
   ) -> str:
       """Emite <header class='page-header'> canônico para st.markdown.

       Args:
           titulo: texto do h1 (será uppercased pelo CSS, não passe em UPPERCASE manual a menos que a fonte canônica peça).
           subtitulo: parágrafo descritivo curto.
           sprint_tag: ID da sprint (ex: UX-T-02). Vai como <span class="sprint-tag">.
           pills: lista de pills para o lado direito (status, contagens).

       Returns:
           HTML pronto para st.markdown(..., unsafe_allow_html=True).
       """
       titulo_html = _html.escape(titulo)
       subtitulo_html = (
           f'<p class="page-subtitle">{_html.escape(subtitulo)}</p>'
           if subtitulo
           else ""
       )
       sprint_tag_html = (
           f'<span class="sprint-tag">{_html.escape(sprint_tag)}</span>'
           if sprint_tag
           else ""
       )
       pills_html = "".join(_renderizar_pill(p) for p in pills)
       page_meta_html = (
           f'<div class="page-meta">{sprint_tag_html}{pills_html}</div>'
           if (sprint_tag_html or pills_html)
           else ""
       )
       return (
           f'<header class="page-header">'
           f'<div><h1 class="page-title">{titulo_html}</h1>{subtitulo_html}</div>'
           f'{page_meta_html}'
           f'</header>'
       )

   # "Tudo precisa de um título antes de existir." -- Borges (paráfrase)
   ```

3. **Refactor das 29 páginas** em `src/dashboard/paginas/*.py`. Para cada uma:
   - Localizar emissão atual de h1 (st.title, st.markdown('# X'), `<h1 class="page-title">` inline).
   - Substituir por chamada ao helper:
     ```python
     from src.dashboard.componentes.page_header import renderizar_page_header
     # ...
     st.markdown(
         renderizar_page_header(
             titulo="EXTRATO",
             subtitulo="Tabela densa com transações do período, breakdown por categoria e drawer detalhado com JSON sintático e documento vinculado.",
             sprint_tag="UX-T-02",
         ),
         unsafe_allow_html=True,
     )
     ```
   - Remover `st.markdown("# X")` ou `st.title("X")` antigos.

4. Criar `tests/test_page_header_canonico.py`:

   ```python
   import subprocess, time, urllib.parse
   import pytest
   from playwright.sync_api import sync_playwright

   PORT = 8772

   # === Testes unitários do helper ===

   def test_helper_emite_h1_page_title():
       from src.dashboard.componentes.page_header import renderizar_page_header
       html = renderizar_page_header("EXTRATO")
       assert '<h1 class="page-title">EXTRATO</h1>' in html

   def test_helper_inclui_subtitulo_quando_dado():
       from src.dashboard.componentes.page_header import renderizar_page_header
       html = renderizar_page_header("CONTAS", subtitulo="Saldos por banco")
       assert '<p class="page-subtitle">Saldos por banco</p>' in html

   def test_helper_omite_subtitulo_quando_vazio():
       from src.dashboard.componentes.page_header import renderizar_page_header
       html = renderizar_page_header("CONTAS")
       assert "page-subtitle" not in html

   def test_helper_inclui_sprint_tag():
       from src.dashboard.componentes.page_header import renderizar_page_header
       html = renderizar_page_header("X", sprint_tag="UX-T-01")
       assert '<span class="sprint-tag">UX-T-01</span>' in html

   def test_helper_inclui_pills():
       from src.dashboard.componentes.page_header import renderizar_page_header
       html = renderizar_page_header("X", pills=[{"texto":"439 docs","tipo":"d7-graduado"}])
       assert '<span class="pill pill-d7-graduado">439 docs</span>' in html

   def test_helper_escapa_html_no_titulo():
       from src.dashboard.componentes.page_header import renderizar_page_header
       html = renderizar_page_header("<script>alert(1)</script>")
       assert "&lt;script&gt;" in html
       assert "<script>alert(1)</script>" not in html

   # === Lint estrutural: nenhuma st.title/st.markdown('# X') em paginas/ ===

   def test_zero_st_title_em_paginas():
       import re, os
       infratores = []
       for arq in os.listdir("src/dashboard/paginas"):
           if not arq.endswith(".py") or arq.startswith("_"): continue
           texto = open(f"src/dashboard/paginas/{arq}").read()
           if re.search(r'^\s*st\.title\(', texto, re.MULTILINE):
               infratores.append(arq)
       assert not infratores, f"st.title() ainda presente em: {infratores}; migrar para page_header"

   def test_zero_st_markdown_h1_h2_em_paginas():
       import re, os
       infratores = []
       for arq in os.listdir("src/dashboard/paginas"):
           if not arq.endswith(".py") or arq.startswith("_"): continue
           texto = open(f"src/dashboard/paginas/{arq}").read()
           if re.search(r'st\.markdown\(["\'][\s]*#{1,2}[^#]', texto):
               infratores.append(arq)
       assert not infratores, f'st.markdown("# X") ou ("## X") presente em: {infratores}; migrar para page_header'

   # === Integração ao vivo: 6 telas amostra ===

   @pytest.fixture(scope="module")
   def streamlit_url():
       p = subprocess.Popen([".venv/bin/streamlit","run","src/dashboard/app.py","--server.port",str(PORT),"--server.headless","true"])
       time.sleep(8)
       yield f"http://127.0.0.1:{PORT}"
       p.terminate(); p.wait()

   TELAS_AMOSTRA = [
       ("Home", "Visão Geral", "VISÃO GERAL"),
       ("Finanças", "Extrato", "EXTRATO"),
       ("Documentos", "Revisor", "REVISOR"),
       ("Análise", "Categorias", "CATEGORIAS"),
       ("Bem-estar", "Hoje", "BEM-ESTAR · HOJE"),
       ("Sistema", "Skills D7", "SKILLS · D7"),
   ]

   @pytest.mark.parametrize("cluster,tab,h1_esperado", TELAS_AMOSTRA)
   def test_pagina_renderiza_h1_page_title(cluster, tab, h1_esperado, streamlit_url):
       with sync_playwright() as p:
           b = p.chromium.launch(); page = b.new_context().new_page()
           page.goto(f"{streamlit_url}/?cluster={urllib.parse.quote(cluster)}&tab={urllib.parse.quote(tab)}")
           page.wait_for_timeout(5000)
           info = page.evaluate("""() => {
               const h1s = Array.from(document.querySelectorAll('h1.page-title')).filter(h => h.getBoundingClientRect().width > 0);
               return h1s.map(h => ({txt: h.textContent.trim().toUpperCase(), fs: getComputedStyle(h).fontSize, tt: getComputedStyle(h).textTransform}));
           }""")
           assert len(info) == 1, f'esperado 1 h1.page-title visível em {cluster}/{tab}, achou {len(info)}'
           assert h1_esperado in info[0]["txt"], f'esperado titulo {h1_esperado!r}, achei {info[0]["txt"]!r}'
           assert info[0]["tt"] == "uppercase", f'page-title deve ser UPPERCASE; tt={info[0]["tt"]}'
           b.close()
   ```

5. Rodar gauntlet (§7).

## 4. Anti-débito

- Se alguma página tem h1 fora de paginas/* (ex.: dentro de componentes/heatmap_humor.py): mover para o helper OU justificar (alguns componentes podem ter h2/h3 internos legitimamente; só h1 cai na regra).
- Subtitulos/sprint-tags/pills: cada página da Onda T preenche conforme mockup específico. Nesta sprint só garantimos que o helper EXISTE e está funcionando.

## 5. Validação visual humana

Dono navega 6 telas amostra (Visão Geral, Extrato, Revisor, Categorias, Bem-estar/Hoje, Skills D7) e confirma:
- Page-title visualmente IDÊNTICO entre páginas (mesmo peso, mesmo tamanho, mesmo gradient text)
- Subtitulo aparece quando passado, ausente quando não

## 6. Gauntlet

```bash
make lint                                                # exit 0
make smoke                                               # 10/10
.venv/bin/pytest tests/test_page_header_canonico.py -v   # 10+/10+
.venv/bin/pytest tests/ -q --tb=no                       # baseline mantida
grep -rcE 'st\.title\(|st\.markdown\(["\x27]#[^#]' src/dashboard/paginas/  # zero ocorrências
```

---

*"Tudo precisa de um título antes de existir." -- Borges (paráfrase)*
