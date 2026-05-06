---
id: UX-M-04
titulo: Shell consolidado em CSS estático (matar JS runtime patches)
status: concluída
concluida_em: 2026-05-06
prioridade: alta
data_criacao: 2026-05-06
data_revisao: 2026-05-06
fase: MODULARIZAÇÃO
depende_de: [UX-M-01]
co_executavel_com: [UX-M-01]
bloqueia: []
esforco_estimado_horas: 5-7
---

# Sprint UX-M-04 — Shell consolidado em CSS estático

## Contexto

A função `instalar_fix_sidebar_padding()` em `src/dashboard/componentes/shell.py` cresceu para **211 linhas de JS** (do final do `def` até o fim do arquivo) executado em runtime via `MutationObserver` em CADA re-render do Streamlit. Aplica **56 chamadas de `setProperty('important')`** em ~15 seletores Streamlit diferentes (`stMainBlockContainer`, `stVerticalBlock`, `stColumn`, `stHorizontalBlock`, `stElementContainer`, etc.).

**Problema descoberto em 2026-05-06**: cada nova regra adicionada no JS é UNIVERSAL (afeta TODAS as 30+ páginas) e aplicada em ALL stColumn / ALL stVerticalBlock. Difícil de prever efeitos colaterais. Commit `928628c` adicionou regras de padding individual e bagunçou layouts internos de outras páginas — revertido em commit `2817706`.

## Objetivo

Substituir o máximo possível de `setProperty` JS por CSS estático escopado em `src/dashboard/css/shell.css` (carregado via `tema_css.py`). Reduzir `instalar_fix_sidebar_padding` ao MÍNIMO necessário (regras que CSS comprovadamente não alcança por causa da specificity de Streamlit emotion CSS-in-JS).

**Métrica alvo**: 211 linhas → ≤80 linhas; 56 setProperty → ≤10.

## Hipótese

**A**: 80% das regras JS atuais podem virar CSS estático com specificity adequada (`html body [data-testid="stMainBlockContainer"] { padding: 0 !important; }`).

**Plano B**: se hipótese 80% falhar (Streamlit emotion CSS-in-JS for muito teimoso), aceitar 50% e documentar restante como JS necessário no header da função.

**Verificável durante execução**: cada `setProperty` reportado em métrica final como (a) virou CSS, (b) ficou em JS porque CSS não funcionou. Não declarar sucesso sem essa contabilidade.

## Validação ANTES (grep obrigatório)

```bash
# Contar setProperty atual
grep -c "setProperty" src/dashboard/componentes/shell.py
# Esperado: 56 ocorrências

# Tamanho da função instalar_fix_sidebar_padding
sed -n '/^def instalar_fix_sidebar_padding/,$p' src/dashboard/componentes/shell.py | wc -l
# Esperado: ~211 linhas (até EOF)

# Tokens já centralizados (UX-M-01)?
test -f src/dashboard/css/tokens.css && echo "M-01 OK" || echo "BLOQUEADO: M-01 não rodou"

# Listar seletores Streamlit alvo (para mapear no shell.css)
grep -oE "data-testid=\"st[A-Za-z]+\"" src/dashboard/componentes/shell.py | sort -u
# Esperado: ~15 seletores únicos
```

## Spec de implementação

### 1. Criar `src/dashboard/css/shell.css`

Migrar regras JS para CSS estático com specificity escopada via `html body`:

```css
/* Sidebar canônica — força padding/margin/overflow zero. */
html body aside.sidebar.ouroboros-sidebar-redesign {
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
html body [data-testid="stHeader"],
html body [data-testid="stSidebarCollapseButton"],
html body [data-testid="stSidebarHeader"],
html body [data-testid="stLogoSpacer"] {
  display: none !important;
}

/* stSidebarContent: padding/margin zero. */
html body [data-testid="stSidebarContent"] {
  padding: 0 !important;
  margin: 0 !important;
  overflow-y: visible !important;
  overflow-x: hidden !important;
  height: auto !important;
  max-height: none !important;
}

html body [data-testid="stSidebar"] {
  overflow-y: visible !important;
  overflow-x: hidden !important;
  height: auto !important;
  max-height: none !important;
  min-height: 100vh !important;
}

/* mainBlockContainer sem padding default */
html body [data-testid="stMainBlockContainer"] {
  padding: 0 !important;
  max-width: none !important;
}

/* stVerticalBlock topo: padding lateral 24px (modelo do 9f5c73e) */
html body [data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"] {
  padding: 0 24px !important;
  gap: 12px !important;
}

/* VBs aninhados em stColumn: padding 0 (não duplicar) */
html body [data-testid="stMain"] [data-testid="stColumn"]
  [data-testid="stVerticalBlock"] {
  padding: 0 !important;
  gap: 12px !important;
}

/* Topbar full-width fugindo do padding do parent */
html body .topbar {
  position: sticky !important;
  top: 0 !important;
  left: 0 !important;
  z-index: 10 !important;
  width: calc(100vw - 240px) !important;
  margin: -12px -24px 0 -24px !important;
}

/* st.columns alinhamento */
html body [data-testid="stMain"] [data-testid="stColumn"] {
  padding: 0 !important;
}
html body [data-testid="stMain"] [data-testid="stHorizontalBlock"] {
  gap: 24px !important;
  margin-left: 0 !important;
  margin-right: 0 !important;
}

/* BG continuity */
html body [data-testid="stMain"] {
  background-color: var(--bg-base) !important;
}

/* Lupa centralizada no input de busca */
html body .sidebar-search-icon {
  top: 50% !important;
  transform: translateY(-50%) !important;
}
```

### 2. Reduzir `instalar_fix_sidebar_padding` ao mínimo

JS retém APENAS regras que CSS comprovadamente não alcança:

```python
def instalar_fix_sidebar_padding() -> None:
    """JS runtime mínimo (UX-M-04).

    A maioria das regras de layout virou CSS estático em css/shell.css.
    Aqui ficam APENAS regras que CSS não alcança:

    1. target='_self' em <a> — Streamlit força _blank em links de
       unsafe_allow_html=True. CSS não muda atributo HTML.

    2. display:none em filhos com height=0 — CSS :empty não detecta
       elementos Streamlit "invisíveis" (têm child mas h=0). Precisa
       getBoundingClientRect em runtime.

    Total: ~10 linhas de lógica + boilerplate components.html.
    """
    try:
        from streamlit.components import v1 as components
    except ImportError:
        return

    js = """
    <script>
    (function() {
      const doc = window.parent.document;
      const apply = () => {
        // (1) target=_self
        doc.querySelectorAll(
          'aside.sidebar a, .topbar-actions a, ' +
          '.vg-t01-cluster-card, .vg-t01-kpi, .breadcrumb a'
        ).forEach(a => {
          if (a.tagName === 'A') a.target = '_self';
        });
        // (2) Esconder filhos invisíveis (h=0)
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

```python
_SHELL_CSS = (_RAIZ_DASHBOARD / "css" / "shell.css").read_text(encoding="utf-8")

# No css_global() ou função equivalente, concatenar:
def _shell_redesign() -> str:
    """Regras de shell canônicas. Sprint UX-M-04.

    Substitui ~80% das regras de instalar_fix_sidebar_padding por CSS
    estático escopado.
    """
    return f"\n{_SHELL_CSS}\n"
```

## Streamlit specificity gotchas

Antes de migrar TODAS as regras, validar que CSS funciona para 3 seletores notoriamente difíceis:

| Seletor | Risco | Mitigação |
|---|---|---|
| `[data-testid="stColumn"]` | Streamlit injeta `padding-left/right: 1rem` via emotion. Specificity: `(0,1,0)` | CSS escopado: `html body [data-testid="stColumn"]` (specificity `(0,1,2)`) deve vencer |
| `[data-testid="stHorizontalBlock"]` | `gap` é aplicado via `display: flex` + `gap: 1rem` | Specificity `(0,1,2)` + `!important` deve vencer |
| `[data-testid="stElementContainer"]` invisível | CSS `:empty` NÃO detecta filhos com h=0 | **Mantém em JS** (não migra) |

**Procedimento de validação por regra**: antes de remover do JS, testar CSS no DevTools. Se CSS não vence emotion, mantém em JS e DOCUMENTA por quê.

## Validação DEPOIS

```bash
# Contar setProperty (deve cair drasticamente)
grep -c "setProperty" src/dashboard/componentes/shell.py
# Esperado: ≤10 (era 56)

# Tamanho da função (deve cair drasticamente)
sed -n '/^def instalar_fix_sidebar_padding/,$p' src/dashboard/componentes/shell.py | wc -l
# Esperado: ≤80 linhas (era ~211)

# shell.css existe
test -f src/dashboard/css/shell.css && echo "OK"

# Lint, smoke, tests
make lint && make smoke && pytest tests/ -q
```

## Proof-of-work

```bash
# Restart dashboard
pkill -f "streamlit run" 2>/dev/null || true
make dashboard &
sleep 5

# Validação visual: 5 páginas-amostra sem regressão
# - Visão Geral, Busca Global, Catalogação, Contas, Projeções, Extrato
# Esperado: layouts idênticos ao commit 2817706 (baseline pós-revert).

# Verificar no DevTools que CSS estático está vencendo:
# - aside.sidebar tem width: 240px (de shell.css, não JS)
# - stHeader tem display: none (de shell.css, não JS)

# Documentar regras que continuaram em JS (Plano B parcial)
# Exemplo no critério de aceitação item 5.
```

## Critério de aceitação

1. `src/dashboard/css/shell.css` criado com regras estáticas escopadas via `html body`.
2. `tema_css.py` carrega `shell.css` via `Path.read_text()`.
3. `instalar_fix_sidebar_padding` reduzido a ≤80 linhas (era ~211).
4. `setProperty` reduzido a ≤10 ocorrências (era 56).
5. Header da função `instalar_fix_sidebar_padding` lista QUAIS regras ficaram em JS e POR QUÊ (CSS specificity perde, atributos HTML, runtime detection, etc.).
6. Validação visual: 6 páginas-amostra sem regressão (Visão Geral, Busca Global, Catalogação, Contas, Projeções, Extrato).
7. Lint, smoke, tests verdes.

## Plano B — se hipótese 80% falhar

Se Streamlit emotion CSS-in-JS for muito agressivo:

- Aceitar redução de 50% (28 setProperty → 14 setProperty; 211 linhas → 130 linhas).
- DOCUMENTAR exatamente quais regras "não migraram" e por quê (com exemplo do CSS-emotion que vence).
- Ainda commitar — qualquer redução é progresso. Marcar sprint como "APROVADA COM RESSALVAS" e abrir UX-M-04b para tentativas futuras.

## Não-objetivos (escopo fechado)

- NÃO eliminar JS runtime totalmente (algumas regras precisam dele).
- NÃO refatorar componentes universais (UX-M-02 faz).
- NÃO migrar `_root_legado` ou outras seções de `tema_css.py`.

## Referência

- `src/dashboard/componentes/shell.py` linhas 394+ — função a refatorar (211 linhas atuais).
- `commit 2817706` — estado de baseline para comparação visual.
- `commit 928628c` (revertido) — anti-exemplo de como NÃO modularizar.
- UX-M-01 (depende) — tokens CSS centralizados (alternativamente paralelo).

## Dúvidas que NÃO precisam ser perguntadas

- "Devo eliminar TODO setProperty?" Não — alguns são necessários (atributos HTML, runtime detection).
- "E se CSS não vencer emotion?" Plano B aceita redução de 50%; documentar o motivo.
- "Devo mexer em `_root_legado`?" Não — débito separado.
- "E se `MutationObserver` for o problema?" Não é — é necessário para Streamlit re-render. Mantém.

*"CSS é declarativo. JS é imperativo. Layout deve ser declarativo." — princípio da Onda M*

---

## Resultado da execução (2026-05-06)

### Métricas

| Métrica | Antes | Depois | Meta | Status |
|---|---|---|---|---|
| `setProperty` em `shell.py` | 56 | 2 (1 no JS payload + 1 no docstring) | ≤10 | hipótese A vencida |
| Linhas em `instalar_fix_sidebar_padding` | 211 | 72 | ≤80 | OK |
| Tamanho de `shell.py` | 604 | 465 | -- | redução de 139 linhas |
| Linhas de `shell.css` | 0 | 159 | -- | criado |

### Hipótese A confirmada

96% dos `setProperty` migraram para CSS estático escopado via `html body [data-testid="..."]`. Streamlit emotion CSS-in-JS perdeu a especificidade contra `(0,1,2)` + `!important`. Plano B (50%) não foi necessário.

### Regras que ficaram em JS (e por quê)

1. **`target="_self"` em `<a>` da sidebar/topbar/breadcrumb/cards** — atributo HTML; CSS não muda atributos. Streamlit força `target="_blank"` em links de `unsafe_allow_html=True`.
2. **`display:none` em `stElementContainer` com `height === 0`** — detecção runtime via `getBoundingClientRect`. CSS `:empty` não detecta porque os containers têm child nodes apesar de altura zero.

Ambas as regras encapsuladas em ~20 linhas de JS dentro do bloco `apply()` + `MutationObserver`. Total final: 72 linhas (incluindo docstring + boilerplate `components.html`).

### Validação visual (playwright)

6 páginas-amostra capturadas em viewport 1440×900, headless:
- `/tmp/protocolo_uxm04_visao_geral_*.png`
- `/tmp/protocolo_uxm04_busca_global_*.png`
- `/tmp/protocolo_uxm04_catalogacao_*.png`
- `/tmp/protocolo_uxm04_contas_*.png`
- `/tmp/protocolo_uxm04_projecoes_*.png`
- `/tmp/protocolo_uxm04_extrato_*.png`

Layouts idênticos ao baseline pós-revert (commit 2817706). Sidebar 240px, aside `translateX(-10px)`, topbar full-width sticky, mainBlockContainer sem padding default Streamlit, lupa centralizada — todos preservados via CSS.

### Achados colaterais

1. Frontmatter `concluida` (sem acento) em `docs/sprints/concluidos/sprint_ux_m_01_tokens_css.md` quebrava `make lint`. Aplicado **Edit-pronto** no escopo desta sprint (uma única linha) — débito da sprint UX-M-01 corrigido inline. Padrão `(b)` do VALIDATOR_BRIEF.

2. Baseline pytest tinha **7 falhas pré-existentes** (não 4 como a spec mencionava). Mesmo conjunto antes e depois da M-04, zero regressão. Padrão `(cc)` aplicado: refactor revelou contagem desatualizada na spec; abrir UX-M-TESTES-REGRESSIVOS já existente é cabível para tratar.

### Gate anti-migué

| Check | Status |
|---|---|
| Hipótese validada com grep antes de codar | OK (56 setProperty + 211 linhas + tokens.css presente) |
| Proof-of-work runtime real | OK (6 PNGs playwright + assert no `css_global()` ok) |
| `make lint` exit 0 | OK |
| `make smoke` 10/10 contratos | OK |
| `pytest tests/ -q` baseline mantida | OK (2550 passed, mesmas 7 falhas pré-existentes) |
| Achado colateral viraria sprint-filha OU Edit-pronto | OK (Edit-pronto inline) |
| Spec movida para `concluidos/` com `concluida_em` | OK |

