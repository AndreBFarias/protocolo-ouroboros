---
titulo: Índice da Onda M — Modularização Real do Dashboard
data_criacao: 2026-05-06
data_revisao: 2026-05-06
status: concluída
concluida_em: 2026-05-06
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

## Estrutura da Onda M (4 sprints) — FASE CENTRAL CONCLUÍDA 2026-05-06

| Sprint | Título | Esforço estimado | Esforço real | Commit |
|---|---|---|---|---|
| UX-M-01 | Tokens CSS centralizados (`css/tokens.css`) | 3-5h | **30min** | CONCLUÍDA `bbedf2c` |
| UX-M-04 | Shell consolidado em CSS estático | 5-7h | **16min** | CONCLUÍDA `2947f2b` |
| UX-M-TESTES-REGRESSIVOS | 4 testes pré-Onda M (sprint-filha) | 1-2h | **30min** | CONCLUÍDA `da8f639` |
| UX-M-02 | Componentes universais HTML (`ui.py`) | 8-10h | **25min** | CONCLUÍDA `3ef1d66` |
| UX-M-03 | CSS canônico do mockup (`css/components.css`) | 4-6h | **25min** | CONCLUÍDA `2544160` |

**Total fase central:** ~2h25min (estimado 20-28h — economia 90% via subagents executor-sprint isolados).

**Métricas reais consolidadas:**
- `tema_css.py`: 1675 → 987 linhas (-688, **-41%**)
- `tema.py`: 723 → 454 linhas (-269, **-37%**)
- `shell.py`: 604 → 465 linhas (-139, -23%)
- `setProperty` JS runtime: 56 → 2 (**-96%**)
- 5 arquivos CSS canônicos: tokens.css, components.css, shell.css, overrides_streamlit.css, extensoes_dashboard.css
- `ui.py` criado com 14 funções (9 migradas + 3 novas + 2 re-exports)
- Pytest baseline: 2555 passed

## Sub-sprints de migração de páginas (após M-02 + M-03) — CONCLUÍDAS 2026-05-06

UX-M-02 entrega `ui.py` mas não migra páginas. M-03 entrega CSS canônico. Migração de páginas virou sub-sprints, executadas em paralelo via 4 subagents `executor-sprint` em worktrees isolados:

| Sub-sprint | Cluster | Páginas | Esforço estimado | Esforço real | Commit |
|---|---|---|---|---|---|
| UX-M-02.A | Documentos | busca, catalogacao, completude, revisor, validacao_arquivos, extracao_tripla, grafo_obsidian | 4h | **17m** | `e1ccd55` |
| UX-M-02.B | Finanças | extrato, contas, pagamentos, projecoes | 3h | **41m** | `c564b92` |
| UX-M-02.C | Análise + Metas + Inbox + Sistema | categorias, analise_avancada, irpf, metas, inbox, skills_d7 | 3h | **29m** | `6d36249` |
| UX-M-02.D | Bem-estar | 17 páginas be_* (4 com CSS local) | 6h | **65m** | `b413ac7` |

**Total sub-sprints**: 16h estimado → ~2h25min real (paralelos via subagents).

## Fixes residuais (zero débito) — 2026-05-06

Achados-bloqueio (padrão `(k)` empírico) reportados por A/B/C/D durante execução foram corrigidos pelo supervisor pessoalmente em 2 commits adicionais:

| Fix | Origem | Commit | Métrica |
|---|---|---|---|
| Extrair 6 CSS locais para `css/paginas/` (busca, catalogacao, extrato, categorias, inbox, skills_d7) + helper `carregar_css_pagina` em ui.py + bug "undefined" no Plotly title | A-RESIDUAL + B.1 + C overrides + B undefined | `9309ff8` | -971L em 6 paginas |
| Extrair 4 overrides de Bem-estar (be_hoje/humor/diario/eventos) para `css/paginas/be_*.css` | D overrides | `2a28aee` | -381L em 4 paginas |

**Total Onda M completa**: 36-44h estimado → ~3h real (subagents + supervisor pessoal).

## Métricas finais consolidadas (2026-05-06 fechamento)

- 30 páginas migradas para `ui.py` + classes canônicas.
- 10 arquivos CSS dedicados criados em `src/dashboard/css/paginas/`.
- Helper `carregar_css_pagina(nome)` adicionado em `ui.py` (segue padrão `tema_css.py:65` de `Path.read_text`).
- `_CSS_LOCAL_*` / `_estilos_locais()` removidos de TODAS as 10 páginas afetadas.
- `tema_plotly.py`: bug "undefined" do title corrigido (sub-objeto `title.font` removido — definir font sem text gerava placeholder visível).
- Cores migradas de `CORES[Python]` para tokens CSS canônicos (`var(--bg-surface)`, `var(--text-primary)`, etc.) em todos os CSS extraídos.
- **Redução total em linhas Python**: -1352L (-971L primeiro commit + -381L segundo).
- **pytest baseline**: 2555 passed + 14 skipped + 1 xfailed = 2570 total (mantida e os 22 fails preexistentes flaky resolvidos no caminho).
- **Validação visual side-by-side**: 9 páginas-amostra confrontadas mockup vs dashboard real via `claude-in-chrome`. Zero regressão.

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
