---
titulo: Índice da Onda M — Modularização Real do Dashboard
data_criacao: 2026-05-06
data_revisao: 2026-05-06
status: backlog
---

# Onda M — Modularização Real do Dashboard

## Motivação

Sessão de auditoria visual em 2026-05-06 expôs que após a Onda T (29 sprints de redesign página por página), o dashboard ainda tem:

- **17 páginas com `_CSS_LOCAL_*`** (50-300 linhas cada, com fallbacks duplicados).
- **`tema_css.py` com 1675 linhas** — CSS hard-coded em Python, espelhando o mockup canônico de forma duplicada.
- **`instalar_fix_sidebar_padding` com 211 linhas e 56 `setProperty`** que afeta TODAS as páginas globalmente.
- **17 funções HTML helpers em `tema.py`** (9 são componentes visuais que deveriam estar em fronteira única).
- **Tokens de design espalhados em 3 lugares** (`tema.py` Python, `tema_css.py` CSS hard-coded, `_CSS_LOCAL_*` por página).

Dono caracterizou o trabalho como "corno eterno" e exigiu modularização real antes de continuar com mais sprints visuais.

**Achado crítico da auditoria**: a fonte canônica JÁ EXISTE em `novo-mockup/_shared/`:
- `tokens.css` (138 linhas, 50+ tokens)
- `components.css` (387 linhas, 87 classes)

Onda M é principalmente sobre **importar a fonte canônica** em vez de manter cópia hard-coded em Python.

## Estrutura da Onda M (4 sprints)

| Sprint | Título | Depende de | Bloqueia | Esforço |
|---|---|---|---|---|
| UX-M-01 | Tokens CSS centralizados (`css/tokens.css`) | — | M-02, M-03 | 3-5h |
| UX-M-02 | Componentes universais HTML (`ui.py` consolidado) | M-01 | M-03, M-02.A..D | 8-10h |
| UX-M-03 | CSS canônico do mockup (`css/components.css`) | M-01, M-02 | M-02.A..D | 4-6h |
| UX-M-04 | Shell consolidado em CSS estático | M-01 | — | 5-7h |

**Total Onda M:** 20-28h (era 24-32h, refinado pós-auditoria 2026-05-06).

## Sub-sprints de migração de páginas (após M-02 + M-03)

UX-M-02 entrega `ui.py` mas não migra páginas. M-03 entrega CSS canônico. Migração de páginas vira sub-sprints:

| Sub-sprint | Cluster | Páginas | Esforço |
|---|---|---|---|
| UX-M-02.A | Documentos | busca, catalogacao, completude, revisor, validacao_arquivos, extracao_tripla, grafo_obsidian | 4h |
| UX-M-02.B | Finanças | extrato, contas, pagamentos, projecoes | 3h |
| UX-M-02.C | Análise + Metas + Inbox + Sistema | categorias, analise_avancada, irpf, metas, inbox, skills_d7 | 3h |
| UX-M-02.D | Bem-estar | 12 páginas be_* | 6h |

**Total migração:** 16h.

**Total Onda M completa (4 specs principais + 4 sub-sprints):** 36-44h.

## Ordem de execução (definitiva)

```
Sprint 1   ┐
UX-M-01    │   bloqueante: tokens.css → fundação
           │
Sprint 2   ┘   PARALELO com Sprint 1: UX-M-04 independe de M-01 (shell.css)
UX-M-04        (pode rodar em paralelo via subagents diferentes)
─────────────────────────────────────
gate: M-01 + M-04 verdes
─────────────────────────────────────
Sprint 3
UX-M-02         ui.py consolidado (depende de M-01 para tokens)
─────────────────────────────────────
gate: M-02 verde
─────────────────────────────────────
Sprint 4
UX-M-03         components.css copy (depende de M-02 estar pronto para
                consumir as classes)
─────────────────────────────────────
gate: M-03 verde — ui.py + classes canônicas funcionando
─────────────────────────────────────
Sprints 5-8     PARALELO total
UX-M-02.A    │
UX-M-02.B    │   migração das 30 páginas em paralelo via subagents
UX-M-02.C    │   (4 sub-sprints podem rodar simultâneas — não tocam
UX-M-02.D    ┘   código compartilhado).
```

## Critério de saída por sprint

Cada sprint só vira CONCLUÍDA quando:

1. Todos os critérios de aceitação da spec passam.
2. Lint OK + smoke 10/10 + pytest baseline mantida.
3. Validação visual: 5 páginas-amostra sem regressão (playwright batch).
4. Spec movida para `docs/sprints/concluidos/` com frontmatter `concluida_em: YYYY-MM-DD` + link para commit.
5. Próxima sprint na ordem é desbloqueada (dependência do frontmatter satisfeita).

## Critério de sucesso global

Após Onda M completa, criar uma página nova exige APENAS:

```python
from src.dashboard.componentes.ui import (
    page_header, kpi_card, group_card, data_row, callout_html
)

def renderizar(...):
    st.markdown(
        page_header("Minha Página", "Descrição.", "UX-XX-NN"),
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            kpi_card("LABEL", "VALOR", "sub"),
            unsafe_allow_html=True,
        )
    # ...
```

ZERO CSS local. ZERO `<style>`. ZERO classe própria. ZERO regra de layout duplicada.

## Antes vs Depois — métricas reais

| Métrica | Antes (commit 2817706) | Depois (Onda M completa) |
|---|---|---|
| `_CSS_LOCAL_*` em páginas | 17 | ≤2 (só layouts realmente únicos) |
| Fallbacks `var(--, var(--))` | ~100+ | 0 |
| Linhas em `instalar_fix_sidebar_padding` | 211 | ≤80 |
| `setProperty` no JS runtime | 56 | ≤10 |
| Linhas em `tema_css.py` | 1675 | ≤1300 (M-01 ~150 + M-03 ~300 redução) |
| Lugares para mexer em cor primária | 3+ | 1 (`tokens.css`) |
| Funções HTML em `tema.py` | 17 | 8 (utilitários) + 9 aliases shim |
| Linhas de código nas 30 páginas migradas | baseline | -30% (estimado) |

## Não-objetivos da Onda M

- NÃO buscar pixel-perfect com mockup em todas as páginas (Onda V futura, se houver).
- NÃO reescrever páginas que já estão funcionando — apenas migrar componentes repetidos.
- NÃO eliminar Streamlit (continua sendo o framework).
- NÃO migrar `_root_legado` ou outras seções de `tema_css.py` — débito separado.
- NÃO criar tokens novos — usar fonte canônica do mockup.
- NÃO dividir `components.css` em arquivos por componente — débito futuro M-03b.

## Referências

- `~/.claude/plans/pure-swinging-mitten.md` — auditoria honesta 2026-04-29.
- `~/.claude/plans/auditoria-honesta-da-magical-lovelace.md` — plano de endurecimento das specs M (2026-05-06).
- Commit `2817706` — baseline pós-revert que fecha o ciclo bagunça/correção.
- Commit `928628c` (revertido) — anti-exemplo de JS runtime universal que bagunçou layouts.
- Commit `4b62b0b` — specs Onda M criadas.
- `novo-mockup/_shared/tokens.css` — fonte canônica de tokens (138 linhas).
- `novo-mockup/_shared/components.css` — fonte canônica de componentes (387 linhas).
- `docs/SPRINTS_INDEX.md` — índice mestre de sprints.

## Como executar (recomendação operacional)

Cada sprint da Onda M deve rodar em **executor-sprint isolado** (subagent fresh, contexto limpo):

```bash
# Modo recomendado: dispatcher automático
/sprint-ciclo UX-M-01

# Ou manual (passo a passo controlado):
/executar-sprint UX-M-01

# Após M-01+M-04 verdes:
/executar-sprint UX-M-02

# Após M-02 verde:
/executar-sprint UX-M-03

# Migração paralela das 4 sub-sprints:
/executar-sprint UX-M-02.A &
/executar-sprint UX-M-02.B &
/executar-sprint UX-M-02.C &
/executar-sprint UX-M-02.D &
wait
```

Cada `/executar-sprint` cria subagent isolado que:
1. Lê CLAUDE.md + ESTADO_ATUAL + spec da sprint.
2. Valida hipótese via grep antes de codar.
3. Implementa edits com lint contínuo.
4. Valida runtime: smoke, pytest, validação visual.
5. Commita com mensagem canônica.
6. Move spec de backlog/ para concluidos/.
7. Reporta veredicto APROVADO / APROVADO_COM_RESSALVAS / REPROVADO.

*"Modular não é elegância. É sustentabilidade." — princípio da Onda M*
