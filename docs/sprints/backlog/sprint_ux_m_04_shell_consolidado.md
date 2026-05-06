---
id: UX-M-04
titulo: Shell consolidado em CSS estático (matar JS runtime patches)
status: backlog
prioridade: alta
data_criacao: 2026-05-06
fase: MODULARIZAÇÃO
depende_de: [UX-M-01]
bloqueia: []
---

# Sprint UX-M-04 — Shell consolidado em CSS estático

## Contexto

A função `instalar_fix_sidebar_padding()` em `src/dashboard/componentes/shell.py` cresceu para ~120 linhas de JS executado em runtime via `MutationObserver` em CADA re-render do Streamlit. Aplica `setProperty('important')` em ~15 seletores diferentes (`stMainBlockContainer`, `stVerticalBlock`, `stColumn`, `stHorizontalBlock`, `stElementContainer`, etc.).

Problema: cada nova regra adicionada no JS é UNIVERSAL (afeta todas as 30+ páginas) e aplicada em ALL stColumn / ALL stVerticalBlock. Difícil de prever efeitos colaterais. Em 2026-05-06 o commit `928628c` adicionou regras de padding individual e bagunçou layouts internos de outras páginas — revertido em commit `2817706`.

## Objetivo

Substituir o máximo possível de `setProperty` JS por CSS estático escopado em `tema_css.py` (ou `css/shell.css`). Reduzir `instalar_fix_sidebar_padding` ao MÍNIMO necessário (regras que CSS não consegue alcançar por causa da specificity de Streamlit emotion CSS-in-JS).

## Hipótese

Pelo menos **70% das regras JS atuais podem virar CSS estático** com specificity adequada (`html body [data-testid="stMainBlockContainer"] { padding: 0 !important; }`). O restante (30%) depende de `MutationObserver` para tratar elementos invisíveis ou re-render do Streamlit.

Verificar esta hipótese durante implementação — pode ser 50% ou 90%, mas o ganho é proporcional.

## Validação ANTES (grep obrigatório)

```bash
# Contar setProperty atual
grep -c "setProperty" src/dashboard/componentes/shell.py
# Esperado: ~30 ocorrências

# Tamanho da função instalar_fix_sidebar_padding
awk '/def instalar_fix_sidebar_padding/,/^def /' src/dashboard/componentes/shell.py | wc -l
# Esperado: ~120 linhas

# Tokens já centralizados (UX-M-01)?
test -f src/dashboard/css/tokens.css && echo OK || echo FALTA-M01
```

## Spec de implementação

### 1. Criar `src/dashboard/css/shell.css`

Migrar regras JS para CSS estático:

```css
/* Sidebar canônica */
aside.sidebar.ouroboros-sidebar-redesign {
  margin: 0 !important;
  padding: 12px 0 !important;
  width: 240px !important;
  overflow-y: visible !important;
  overflow-x: hidden !important;
  height: auto !important;
  max-height: none !important;
  transform: translateX(-10px) !important;
}

/* Esconder elementos Streamlit indesejados */
[data-testid="stHeader"],
[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarHeader"],
[data-testid="stLogoSpacer"] {
  display: none !important;
}

/* Main block sem padding default */
[data-testid="stMainBlockContainer"] {
  padding: 0 !important;
  max-width: none !important;
}

/* stVerticalBlock topo: padding lateral 24px */
[data-testid="stMainBlockContainer"]
  > [data-testid="stVerticalBlock"] {
  padding: 0 24px !important;
  gap: 12px !important;
}

/* VBs aninhados em stColumn: sem padding */
[data-testid="stMain"] [data-testid="stColumn"]
  [data-testid="stVerticalBlock"] {
  padding: 0 !important;
  gap: 12px !important;
}

/* Topbar full-width fugindo do padding do parent */
.topbar {
  position: sticky !important;
  top: 0 !important;
  left: 0 !important;
  z-index: 10 !important;
  width: calc(100vw - 240px) !important;
  margin: -12px -24px 0 -24px !important;
}

/* st.columns alinhamento */
[data-testid="stMain"] [data-testid="stColumn"] {
  padding: 0 !important;
}
[data-testid="stMain"] [data-testid="stHorizontalBlock"] {
  gap: 24px !important;
  margin-left: 0 !important;
  margin-right: 0 !important;
}

/* BG continuity */
[data-testid="stMain"] {
  background-color: var(--bg-base) !important;
}

/* Lupa centralizada */
.sidebar-search-icon {
  top: 50% !important;
  transform: translateY(-50%) !important;
}
```

### 2. Reduzir `instalar_fix_sidebar_padding`

Manter APENAS regras que CSS não cobre:

```python
def instalar_fix_sidebar_padding() -> None:
    """JS runtime mínimo para regras que CSS não alcança.

    Maioria das regras de layout virou CSS estático em css/shell.css
    (carregado via tema_css.py). Aqui só ficam:
    - target='_self' em <a> (Streamlit força _blank)
    - display:none em filhos invisíveis (h=0) do stVerticalBlock para
      o gap não criar espaço (CSS :empty não detecta filhos com h=0).
    """
    js = """
    <script>
    (function() {
      const doc = window.parent.document;
      const apply = () => {
        // target=_self
        doc.querySelectorAll(
          'aside.sidebar a, .topbar-actions a, ' +
          '.vg-t01-cluster-card, .vg-t01-kpi, .breadcrumb a'
        ).forEach(a => {
          if (a.tagName === 'A') a.target = '_self';
        });
        // Esconder filhos com altura 0
        const sel = '[data-testid="stMain"] [data-testid="stVerticalBlock"]'
                  + ' > [data-testid="stElementContainer"]';
        doc.querySelectorAll(sel).forEach(c => {
          if (c.getBoundingClientRect().height === 0) {
            c.style.setProperty('display', 'none', 'important');
          }
        });
      };
      apply();
      const obs = new MutationObserver(apply);
      obs.observe(doc.body, {childList: true, subtree: true});
    })();
    </script>
    """
    components.html(js, height=0)
```

### 3. Carregar `shell.css` em `tema_css.py`

Adicionar no início do CSS injetado:

```python
_RAIZ_CSS = Path(__file__).resolve().parent / "css"
_SHELL_CSS = (_RAIZ_CSS / "shell.css").read_text(encoding="utf-8")
# ... emitir junto com tokens.css
```

## Proof-of-work

```bash
# Antes: contar setProperty
grep -c "setProperty" src/dashboard/componentes/shell.py
# Esperado ANTES: ~30

# Depois: contar setProperty
grep -c "setProperty" src/dashboard/componentes/shell.py
# Esperado DEPOIS: ≤5 (só os que realmente precisam de JS)

# Tamanho da função
awk '/def instalar_fix_sidebar_padding/,/^def /' src/dashboard/componentes/shell.py | wc -l
# Esperado DEPOIS: ≤40 linhas (era ~120)

# Validação visual: 5 páginas sem regressão
make dashboard
# Comparar Visão Geral, Busca Global, Catalogação, Contas, Projeções,
# Extrato. Layout idêntico ao estado atual (commit 2817706).
```

## Critério de aceitação

1. `src/dashboard/css/shell.css` criado com regras estáticas.
2. `tema_css.py` carrega `shell.css`.
3. `instalar_fix_sidebar_padding` reduzido a ≤40 linhas (era ~120).
4. JS restante tem APENAS regras que CSS comprovadamente não alcança.
5. Validação visual: 5 páginas-amostra sem regressão (Visão Geral, Busca Global, Catalogação, Contas, Projeções, Extrato).
6. Lint, smoke, tests verdes.

## Não-objetivos

- NÃO eliminar JS runtime totalmente (algumas regras precisam dele).
- NÃO refatorar componentes universais (isso é UX-M-02).

## Referência

- UX-M-01 (depende de) — tokens CSS centralizados.
- Commit `2817706` — estado de baseline para comparação visual.
- Commit `928628c` (revertido em `2817706`) — exemplo de como NÃO modularizar.

*"CSS é declarativo. JS é imperativo. Layout deve ser declarativo." — princípio da Onda M*
