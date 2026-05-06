---
titulo: Índice da Onda M — Modularização Real do Dashboard
data_criacao: 2026-05-06
status: backlog
---

# Onda M — Modularização Real do Dashboard

## Motivação

Sessão de auditoria visual em 2026-05-06 expôs que após a Onda T (29 sprints de redesign página por página), o dashboard ainda tem:

- **17 páginas com `_CSS_LOCAL_*`** (50-300 linhas cada, com fallbacks duplicados).
- **4 páginas com `_page_header_html()` reescrito** (busca, catalogacao, contas, projecoes — corrigido em commit 2817706).
- **JS runtime de 120 linhas** com 30 `setProperty` em `instalar_fix_sidebar_padding` que afeta TODAS as páginas globalmente.
- **Tokens de design espalhados** em 3 lugares (`tema.py` Python, `tema_css.py` CSS, `_CSS_LOCAL_*` por página).

Dono caracterizou o trabalho como "corno eterno" e exigiu modularização real antes de continuar com mais sprints visuais.

## Estrutura da Onda M (4 sprints)

| Sprint | Título | Depende de | Esforço | Bloqueia |
|---|---|---|---|---|
| UX-M-01 | Tokens CSS centralizados em `css/tokens.css` | — | 4-6h | M-02, M-03, M-04 |
| UX-M-02 | Componentes universais HTML em `ui_canonico.py` | M-01 | 12-16h | M-03 |
| UX-M-03 | CSS escopado por componente em `css/components/` | M-01, M-02 | 4h | — |
| UX-M-04 | Shell consolidado em CSS estático | M-01 | 4-6h | — |

**Total estimado:** 24-32h.

## Sub-sprints de migração (após UX-M-02)

UX-M-02 entrega `ui_canonico.py` mas não migra páginas. Migração vira sub-sprints:

| Sub-sprint | Cluster | Páginas | Esforço |
|---|---|---|---|
| UX-M-02.A | Documentos | busca, catalogacao, completude, revisor, validacao | 4h |
| UX-M-02.B | Finanças | extrato, contas, pagamentos, projecoes | 3h |
| UX-M-02.C | Análise | categorias, analise, irpf | 2h |
| UX-M-02.D | Resto | Sistema/Inbox/Bem-estar (16 páginas) | 8h |

**Total migração:** 17h adicionais.

## Critério de sucesso global

Após Onda M completa, criar uma página nova exige APENAS:

```python
from src.dashboard.componentes.ui_canonico import (
    page_header, kpi_card, group_card, data_row, search_bar
)

def renderizar(...):
    st.markdown(page_header("Minha Página", "Descrição.", "UX-XX-NN"),
                unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(kpi_card("LABEL", "VALOR", "sub"), unsafe_allow_html=True)
    # ...
```

ZERO CSS local. ZERO `<style>`. ZERO classe própria. ZERO regra de layout duplicada.

## Antes vs Depois — métricas

| Métrica | Antes (commit 2817706) | Depois (Onda M completa) |
|---|---|---|
| `_CSS_LOCAL_*` em páginas | 17 | ≤2 (só layouts realmente únicos) |
| Fallbacks `var(--, var(--))` | ~100+ | 0 |
| Linhas em `instalar_fix_sidebar_padding` | ~120 | ≤40 |
| `setProperty` no JS runtime | ~30 | ≤5 |
| Lugares para mexer em cor primária | 3+ | 1 (`tokens.css`) |
| Linhas de código nas 30 páginas | baseline | -30% (estimado) |

## Ordem de execução recomendada

1. **UX-M-01** primeiro (tokens). Bloqueante de tudo.
2. **UX-M-04** em paralelo com M-01 (shell CSS estático). Independentes.
3. **UX-M-02** depois de M-01 (componentes universais).
4. **UX-M-03** depois de M-02 (CSS escopado dos componentes).
5. **Sub-sprints UX-M-02.A..D** podem rodar em paralelo após M-02+M-03 prontas.

## Não-objetivos da Onda M

- NÃO buscar pixel-perfect com mockup em todas as páginas (isso seria Onda V futura).
- NÃO reescrever páginas que já estão funcionando (apenas migrar componentes repetidos).
- NÃO eliminar Streamlit (continua sendo o framework).

## Referências

- `~/.claude/plans/pure-swinging-mitten.md` — auditoria honesta 2026-04-29.
- Commit `2817706` — baseline pós-revert que fecha o ciclo bagunça/correção.
- Commit `928628c` (revertido) — anti-exemplo de como NÃO escalar regras de layout.
- `docs/SPRINTS_INDEX.md` — índice mestre de sprints.

*"Modular não é elegância. É sustentabilidade." — princípio da Onda M*
