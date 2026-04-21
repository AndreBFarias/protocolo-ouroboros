## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 76
  title: "Polish UX v1: fonte mínima 13px, logo acima do título, centralização, padding dos retângulos"
  touches:
    - path: src/dashboard/tema.py
      reason: "variável FONTE_MINIMA = 13; tokens globais"
    - path: src/dashboard/app.py
      reason: "CSS global: fonte mínima, centralizar header, logo"
    - path: src/dashboard/app.py
      reason: "usar assets/icon.png (já existe, 724x733 RGBA) como logo da sidebar"
    - path: src/dashboard/paginas/*.py
      reason: "padding interno dos retângulos das páginas (evitar texto colado)"
    - path: tests/test_ux_tokens.py
      reason: "testes dos tokens"
  n_to_n_pairs:
    - ["FONTE_MINIMA", "CSS rule: *, p, span, div { font-size: max(13px, ...) }"]
  forbidden: []
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: ".venv/bin/pytest tests/test_ux_tokens.py -v"
      timeout: 60
  acceptance_criteria:
    - "Nenhum texto renderizado no dashboard fica abaixo de 13px (validado via screenshot + assert na CSS)"
    - "Logo em assets/logo.svg (placeholder stylizado se não fornecido) renderizada acima do título 'Protocolo Ouroboros' na sidebar"
    - "Título e logo centralizados horizontalmente na sidebar"
    - "Padding interno de >=16px nos retângulos de todas as páginas (grafo, IRPF, metas, extrato)"
    - "Textos nunca ficam colados na borda do retângulo container"
    - "Screenshot ANTES/DEPOIS comparativo de 3 páginas"
  proof_of_work_esperado: |
    # Screenshot Visão Geral, Grafo, IRPF em viewport 1600x1000
    # Confirmar: logo visível, título centralizado, fontes >= 13px, padding >= 16px
```

---

# Sprint 76 — Polish UX v1

**Status:** BACKLOG
**Prioridade:** P1
**Dependências:** Sprint 62 (responsividade base)
**Issue:** UX-ANDRE-04

## Problema

Andre apontou explicitamente nos screenshots:
- Textos colados no retângulo da página (Grafo, Metas, IRPF)
- Fonte menor que 13px (ilegível)
- Falta logo acima de "Protocolo Ouroboros"
- Título + logo precisam ser centralizados

## Implementação

### Fonte mínima

`src/dashboard/tema.py`:

```python
FONTE_MINIMA = "13px"

CSS_FONTE_MINIMA = """
<style>
[data-testid="stAppViewContainer"] *,
[data-testid="stAppViewContainer"] p,
[data-testid="stAppViewContainer"] span,
[data-testid="stAppViewContainer"] div {
  font-size: max(13px, inherit) !important;
}
.plotly text { font-size: 13px !important; }
</style>
"""
```

### Logo + header centralizado

Usar `assets/icon.png` (já existe, PNG 724x733 RGBA). Sidebar em `app.py`:

```python
from pathlib import Path
import base64

def _logo_base64() -> str:
    caminho = Path(__file__).parent.parent.parent / "assets" / "icon.png"
    return base64.b64encode(caminho.read_bytes()).decode("ascii")

st.sidebar.markdown(
    f"""
    <div style='text-align:center; margin-bottom:1rem;'>
      <img src='data:image/png;base64,{_logo_base64()}' width='96' style='display:block;margin:0 auto;'/>
      <h1 style='margin-top:0.75rem; font-family:monospace; color:#bd93f9; text-align:center;'>Protocolo Ouroboros</h1>
    </div>
    """,
    unsafe_allow_html=True,
)
```

Cacheado em `st.session_state["logo_b64"]` para não re-ler a cada rerun.

### Padding dos retângulos

Inspecionar cada página (Grafo, IRPF, Metas) e adicionar container com `padding: 1rem`:

```python
with st.container(border=True):
    st.markdown('<div style="padding:1rem;">', unsafe_allow_html=True)
    # ... conteúdo
    st.markdown("</div>", unsafe_allow_html=True)
```

Ou via CSS global:

```css
.main .block-container { padding: 1.5rem !important; }
```

## Armadilhas

| A76-1 | `!important` no CSS pode quebrar tema Dracula | Aplicar apenas em `font-size`, nunca em `color`/`background` |
| A76-2 | Logo SVG base64 fica enorme inline | Salvar em `assets/` e ler uma vez em session_state |
| A76-3 | Plotly tem sua própria escala de fonte | Setar via `fig.update_layout(font=dict(size=13))` separadamente |

## Evidências

- [ ] Screenshot da sidebar com logo centralizada
- [ ] Screenshot de 3 páginas sem texto colado
- [ ] Inspect CSS mostra `font-size: 13px` mínimo
- [ ] Teste automático lendo a CSS gerada

---

*"Detalhe visual é respeito pelo olhar do usuário." — princípio"*
