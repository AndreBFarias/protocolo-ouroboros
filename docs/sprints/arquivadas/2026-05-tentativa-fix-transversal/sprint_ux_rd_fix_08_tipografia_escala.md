---
concluida_em: 2026-05-05
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: UX-RD-FIX-08
  title: "Restaurar escala tipográfica do mockup (Inter + JetBrains Mono em seletores corretos)"
  prioridade: P0
  estimativa: 1 dia (8h)
  onda: C2
  origem: "AUDITORIA_REDESIGN_2026-05-05.md §7.1, §8.1, §8.9 (top problema #5)"
  depende_de: []
  bloqueia: []
  touches:
    - path: .streamlit/config.toml
      reason: "linha font='monospace' faz Streamlit aplicar Source Code Pro globalmente. Trocar para 'sans serif' (Inter via tema_css) ou remover."
    - path: src/dashboard/tema_css.py
      reason: "garantir que --ff-sans (Inter) é aplicado em body global e --ff-mono (JetBrains Mono) só em seletores específicos (kpi-value, breadcrumb, page-title, .pill, code, pre, .mono, table.col-mono, .sprint-tag, kbd). Ajustar font-size base e escala 11/12/13/14/16/18/20/24/32/40 espelhando tokens do mockup. Importar Inter e JetBrains Mono via @import (Google Fonts ou self-host)."
    - path: tests/test_tipografia_escala.py
      reason: "NOVO -- testa via DOM ao vivo que .page-title fs=40px, .pill fs=11px, .kpi-label fs=11px ls=0.88px UPPERCASE, .kpi-value fs=32px JetBrains Mono"
  forbidden:
    - "Remover var(--ff-mono) de seletores legítimos (.kpi-value, .breadcrumb)"
    - "Aplicar !important fora dos overrides Streamlit"
    - "Mudar tamanho de fonte sem corresponder ao mockup; cada divergência tem causa-raiz documentada na auditoria"
  hipotese:
    - ".streamlit/config.toml linha 11: font='monospace'. Streamlit aplica fonte mono em TUDO (body, h1-h6, parágrafo, button) com seletor genérico de alta especificidade. Tema_css.py declara --ff-mono='JetBrains Mono' mas Streamlit override pisa em cima. Necessário: trocar config.toml para sans-serif e injetar Inter explicitamente."
  tests:
    - cmd: ".venv/bin/pytest tests/test_tipografia_escala.py -v"
      esperado: "12+ PASSED (1 por seletor canônico verificado)"
    - cmd: "grep '^font' .streamlit/config.toml"
      esperado: "font = \"sans serif\" ou linha removida"
  acceptance_criteria:
    - "DOM real em .page-title: font-family contém 'JetBrains Mono', font-size 40px, font-weight 500, letter-spacing -0.8px, text-transform UPPERCASE, background-image gradient"
    - "DOM real em parágrafo .page-subtitle: font-family contém 'Inter', font-size 13px, color text-secondary"
    - "DOM real em .pill: font-family contém 'JetBrains Mono', font-size 11px, font-weight 500, letter-spacing 0.04em (0.44px), text-transform UPPERCASE, border-radius 999px"
    - "DOM real em .kpi-label: font-family contém 'Inter', font-size 11px, font-weight 500, letter-spacing 0.08em (0.88px), text-transform UPPERCASE, color text-muted (#6c6f7d)"
    - "DOM real em .kpi-value: font-family contém 'JetBrains Mono', font-size 32px, font-weight 500"
    - "DOM real em sidebar-item: font-family contém 'Inter' (NÃO mono); font-size 13px"
    - "DOM real em breadcrumb .seg: font-family contém 'JetBrains Mono', font-size 12px, letter-spacing 0.04em UPPERCASE"
    - "DOM real em corpo (p, span genérico): font-family contém 'Inter'"
    - "Tela completa do dashboard tem dois claros estilos visuais (sans para corpo, mono para números/UI técnica), espelhando mockup"
    - "Sem regressão em nenhuma das 29 telas (re-rodar cap_dashboard.py + comparar fidelidade)"
  proof_of_work_esperado: |
    nohup .venv/bin/streamlit run src/dashboard/app.py --server.port 8526 --server.headless true &
    sleep 6
    .venv/bin/python -c "
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(); page = b.new_context(viewport={'width':1440,'height':900}).new_page()
        page.goto('http://127.0.0.1:8526/?cluster=An%C3%A1lise&tab=Categorias')
        page.wait_for_timeout(5000)
        info = page.evaluate('''() => {
            const props = (sel) => {
                const el = document.querySelector(sel);
                if (!el) return null;
                const cs = getComputedStyle(el);
                return { ff: cs.fontFamily.slice(0,40), fs: cs.fontSize, fw: cs.fontWeight, ls: cs.letterSpacing, tt: cs.textTransform, color: cs.color, bg: cs.backgroundImage.slice(0,40) };
            };
            return {
                page_title: props('.page-title'),
                pill: props('.pill'),
                kpi_label: props('.kpi-label'),
                kpi_value: props('.kpi-value'),
                breadcrumb_seg: props('.breadcrumb .seg'),
                paragraph: props('p, .page-subtitle')
            };
        }''')
        import json; print(json.dumps(info, indent=2, ensure_ascii=False))
        # contratos
        assert 'JetBrains' in info['page_title']['ff'], f\"page-title ff: {info['page_title']['ff']}\"
        assert info['page_title']['fs'] == '40px', f\"page-title fs: {info['page_title']['fs']}\"
        assert info['page_title']['tt'] == 'uppercase'
        assert 'Inter' in info['paragraph']['ff'], f'paragrafo ff: {info[\"paragraph\"][\"ff\"]}'
        print('OK contratos tipografia')
        b.close()
    "
```

---

# Sprint UX-RD-FIX-08 — Tipografia escala fina (Inter vs JetBrains Mono)

**Status:** BACKLOG — Onda C2 (reconstrução estética).

## 1. Contexto

Auditoria 2026-05-05 §7.1 e §8.1 mostrou que o dashboard aplica `"Source Code Pro", monospace` em **quase tudo** (sidebar items, parágrafos, KPI label, expander, dataframe, st.metric label). O mockup canônico separa rigorosamente:

- **Inter (sans)**: corpo, .sidebar-item, .kpi-label, .page-subtitle, .btn, .card-title.
- **JetBrains Mono**: .page-title, .breadcrumb, .kpi-value, .kpi-delta, .pill, .sprint-tag, .table thead, .col-mono, code, pre, kbd.

**Causa-raiz** (descoberta na investigação dos detalhes):

```toml
# .streamlit/config.toml
[theme]
font = "monospace"   # <-- Streamlit aplica Source Code Pro em TUDO
```

Mais escala de tokens canônica do mockup (`tokens.css:98-107`):

```
--fs-11: 11px;    --fs-12: 12px;    --fs-13: 13px;    --fs-14: 14px;
--fs-16: 16px;    --fs-18: 18px;    --fs-20: 20px;    --fs-24: 24px;
--fs-32: 32px;    --fs-40: 40px;
```

DOM real do dashboard usa apenas 13/15/18/28 -- perde a escala fina (faltam 11, 12, 14, 16, 20, 24, 32, 40).

## 2. Hipótese verificável (Fase ANTES)

```bash
# 1) confirma config.toml causa
grep 'font ' .streamlit/config.toml
# esperado: 'font = "monospace"'

# 2) confirma DOM atual com Source Code Pro vazando
nohup .venv/bin/streamlit run src/dashboard/app.py --server.port 8526 --server.headless true &
sleep 6
.venv/bin/python -c "
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(); page = b.new_context().new_page()
    page.goto('http://127.0.0.1:8526/?cluster=An%C3%A1lise&tab=Categorias')
    page.wait_for_timeout(5000)
    pt = page.evaluate(\"getComputedStyle(document.querySelector('.page-title')).fontFamily\")
    p_= page.evaluate(\"getComputedStyle(document.querySelector('p')).fontFamily\")
    print(f'page-title ff (HOJE): {pt}')   # esperado: contém 'Source Code Pro'
    print(f'paragrafo ff (HOJE): {p_}')    # esperado: contém 'Source Code Pro'
    b.close()
"
pkill -f 'streamlit.*8526'
```

## 3. Tarefas

1. Rodar hipótese.
2. Em `.streamlit/config.toml`, trocar:
   ```toml
   # ANTES
   font = "monospace"
   # DEPOIS
   font = "sans serif"
   ```
   Streamlit usará sans-serif default (Source Sans Pro). Mas iremos sobrescrever via CSS.
3. Em `src/dashboard/tema_css.py` adicionar bloco no início do CSS gerado (alta especificidade):

   ```css
   /* FIX-08: importar fontes web */
   @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

   /* FIX-08: body global usa Inter */
   html, body, .stApp, [data-testid="stAppViewContainer"], 
   [data-testid="stMarkdown"], [data-testid="stMarkdownContainer"],
   p, span, label, button, input, textarea, select {
       font-family: var(--ff-sans) !important;
   }

   /* FIX-08: elementos canônicos mono */
   .page-title, .breadcrumb, .breadcrumb .seg, .kpi-value, .kpi-delta,
   .pill, .sprint-tag, .col-mono, .col-num, .table thead th,
   .mono, .num, code, pre, kbd, .skill-instr, .skill-instr h4, .skill-instr code,
   [data-testid="stMetricValue"], .stCodeBlock {
       font-family: var(--ff-mono) !important;
       font-variant-numeric: tabular-nums;
   }
   ```
4. Forçar tamanhos canônicos via CSS:

   ```css
   /* FIX-08: escala canônica */
   .page-title { font-size: var(--fs-40); font-weight: 500; letter-spacing: -0.02em; text-transform: uppercase; }
   .page-subtitle { font-size: var(--fs-13); }
   .kpi-label { font-size: var(--fs-11); font-weight: 500; letter-spacing: 0.08em; text-transform: uppercase; color: var(--text-muted); }
   .kpi-value { font-size: var(--fs-32); font-weight: 500; letter-spacing: -0.02em; }
   .breadcrumb { font-size: var(--fs-12); letter-spacing: 0.04em; text-transform: uppercase; }
   .pill { font-size: var(--fs-11); font-weight: 500; letter-spacing: 0.04em; text-transform: uppercase; }
   .sprint-tag { font-size: var(--fs-11); font-weight: 500; letter-spacing: 0.04em; text-transform: uppercase; }
   .sidebar-item { font-size: var(--fs-13); }
   .sidebar-cluster-header { font-size: var(--fs-11); letter-spacing: 0.10em; text-transform: uppercase; color: var(--text-muted); }
   ```
   (Já existe parcialmente em `tema_css.py` -- garantir que está ativo, sem override Streamlit.)
5. Validar via DOM ao vivo (proof-of-work).
6. Criar `tests/test_tipografia_escala.py` com 12+ asserts (1 por seletor canônico).
7. Re-rodar **toda a auditoria visual** (`/tmp/auditoria_redesign/cap_dashboard.py`) e comparar PNGs antes/depois para garantir nenhuma regressão.
8. Rodar gauntlet completo.

## 4. Anti-débito

- Se Streamlit ainda override font-family por algum seletor não-listado: use DevTools, identifique o seletor real, adicione no §3.3. Limite: 5 iterações; depois disso, criar **sprint UX-RD-FIX-08.B** (achado colateral).
- Se @import Google Fonts falhar em ambiente offline: self-host as fontes em `assets/fonts/` e usar `@font-face` local. Criar **sprint UX-RD-FIX-08.C**.
- **NÃO** adicionar `!important` em seletores que ainda não são genéricos do Streamlit.

## 5. Validação visual

```bash
# Re-capturar 28 telas do dashboard com nova tipografia
nohup .venv/bin/streamlit run src/dashboard/app.py --server.port 8526 --server.headless true &
sleep 6
.venv/bin/python /tmp/auditoria_redesign/cap_dashboard.py
mv /tmp/auditoria_redesign/dashboard /tmp/auditoria_redesign/dashboard_pos_fix_08
# comparar visualmente vs /tmp/auditoria_redesign/mockups/
```

Critério: 28 PNGs do dashboard tem hierarquia tipográfica clara (page-title grande mono UPPERCASE com gradient; corpo em sans Inter; números mono).

## 6. Gauntlet

```bash
make lint                                                # exit 0
make smoke                                               # 10/10
.venv/bin/pytest tests/test_tipografia_escala.py -v      # 12+ PASSED
.venv/bin/pytest tests/ -q --tb=no                       # baseline >=2520
git diff .streamlit/config.toml                          # 1 linha
git diff src/dashboard/tema_css.py                       # blocos CSS adicionados
```

---

*"Cada letra tem um peso, cada peso tem um lugar." -- Eric Gill (paráfrase)*
