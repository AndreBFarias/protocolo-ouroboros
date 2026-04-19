## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 20
  title: "Dashboard Redesign: mockups primeiro, CSS depois"
  touches:
    - path: docs/mockups/2026-04-18_tela_inicial.md
      reason: "mockup ASCII da visão geral pós-redesign para validação prévia"
    - path: docs/mockups/2026-04-18_tela_extrato.md
      reason: "mockup do extrato com filtros dinâmicos"
    - path: docs/mockups/2026-04-18_tela_inteligencia_pendente.md
      reason: "mockup da nova página de proposições do supervisor"
    - path: docs/mockups/2026-04-18_relatorio_diagnostico.md
      reason: "mockup do render Obsidian do relatório diagnóstico"
    - path: src/dashboard/app.py
      reason: "injeção de CSS externo, max-width, remoção de chrome Streamlit"
    - path: src/dashboard/paginas/visao_geral.py
      reason: "novos cards KPI e tipografia hierárquica"
    - path: src/dashboard/paginas/contas.py
      reason: "aplicação do novo layout factory"
    - path: src/dashboard/paginas/irpf.py
      reason: "cards IRPF no novo padrão"
    - path: src/dashboard/estilos.py
      reason: "novo módulo com factory de layout Plotly e helpers de CSS"
  n_to_n_pairs:
    - [src/dashboard/estilos.py, src/dashboard/style.css]
    - [src/dashboard/app.py, src/dashboard/estilos.py]
  forbidden:
    - src/pipeline.py  # sprint de UI, não toca ETL
    - src/extractors/  # idem
    - src/transform/   # idem
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: "streamlit run src/dashboard/app.py --server.headless true &"
      timeout: 30
  acceptance_criteria:
    - "4 mockups aprovados por André em docs/mockups/ antes de qualquer linha de CSS"
    - "Dashboard com contraste WCAG AA (ratio >= 4.5:1 para texto normal)"
    - "Filtros de pessoa extraídos dinamicamente do DataFrame (não hardcoded)"
    - "Tipografia hierárquica consistente (6 níveis de escala)"
    - "Acentuação PT-BR correta em todos os arquivos"
    - "Zero emojis e zero menções a IA"
```

> Executar antes de começar: `make lint && ./run.sh --check`

---

# Sprint 20 -- Dashboard Redesign: mockups primeiro, CSS depois

**Status:** PENDENTE
**Data:** 2026-04-18
**Prioridade:** ALTA
**Tipo:** Feature
**Dependências:** Sprint 22 (Consolidação), Sprint 23 (Verdade nos Dados)
**Desbloqueia:** Sprint 36 (Métricas IA usa layout novo)
**Issue:** -- (abrir ao iniciar)
**ADR:** --

---

## Como Executar

**Comandos principais:**
- `make lint` -- ruff check + format + acentuação
- `make dashboard` -- sobe Streamlit para inspeção visual
- `./run.sh --check` -- health check do ambiente

### O que NÃO fazer

- NÃO escrever uma linha de CSS antes dos 4 mockups serem aprovados por André
- NÃO redesenhar componentes que serão substituídos pela Sprint 29a (busca global, grafo) -- escopar apenas o que é estável
- NÃO introduzir dependências frontend externas (bootstrap, tailwind CDN) sem justificativa
- NÃO quebrar layout Dracula existente -- adaptar, não substituir
- NÃO misturar escopo: bug de UI encontrado vira issue, não commit inline

---

## Problema

Dashboard atual tem identidade visual fraca: fontes sem hierarquia (13/14/16/18/20 -- diferenças imperceptíveis), cards sem destaque, margens apertadas, títulos competindo com legendas, contraste abaixo de WCAG AA em `texto_sec #6272A4`, filtros de pessoa hardcoded (`["Todos", "André", "Vitória"]`), zero representação visual das proposições do supervisor (Sprint 31).

Plano 30/60/90 §1.7 determina mockups ASCII primeiro (validação barata) e §2.1 a implementação CSS só depois. Isso evita o padrão histórico de "codar, não gostar, refazer" observado nas Sprints 3 e 7.

---

## O que já existe (NÃO duplicar)

| Sistema | Arquivo | O que faz |
|---------|---------|-----------|
| Tema Dracula | `src/dashboard/tema.py` | Paleta de cores + CSS inline (linhas 47-165) |
| App Streamlit | `src/dashboard/app.py` | 8 páginas, sidebar, navegação |
| Páginas | `src/dashboard/paginas/*.py` | visão geral, contas, irpf, metas, projeções, extrato |
| Assets | `src/dashboard/assets/icon.png` | Logo (513KB, precisa ser otimizado) |

---

## Implementação

### Fase 1.7 -- Mockups ASCII (entrega intermediária)

Criar 4 arquivos em `docs/mockups/`. Cada mockup é um bloco de texto em Markdown representando a tela com bordas ASCII, posições de elementos, hierarquia tipográfica anotada (ex.: `[TÍTULO 1.4rem/600]`), estados (filtros aplicados, hover), e anotações de contraste.

**Arquivos:**
- `docs/mockups/2026-04-18_tela_inicial.md` -- visão geral pós-redesign: header com logo, 3 cards KPI (receita/despesa/saldo), gráfico de evolução 12 meses, top categorias do mês, alertas do supervisor.
- `docs/mockups/2026-04-18_tela_extrato.md` -- tabela estilizada com sticky header, filtros dinâmicos (pessoa extraída do DF, categoria, classificação, intervalo de data), paginação.
- `docs/mockups/2026-04-18_tela_inteligencia_pendente.md` -- página alimentada pela Sprint 31: lista de proposições (regra/override/tag IRPF), preview de 3 exemplos por proposição, botões aprovar/rejeitar.
- `docs/mockups/2026-04-18_relatorio_diagnostico.md` -- render do Markdown diagnóstico (Sprint 21) dentro do dashboard via Obsidian-like styling.

**Bloqueio:** só passar para Fase 2.1 com aprovação explícita de André (commit ou comentário em cada arquivo de mockup).

### Fase 2.1 -- Implementação CSS

**Arquivo:** `src/dashboard/estilos.py` (novo módulo)

Centraliza:
- `carregar_css()` -- lê `src/dashboard/style.css` e injeta via `st.markdown("<style>...", unsafe_allow_html=True)`.
- `criar_layout_plotly(titulo: str, altura: int = 350) -> dict` -- factory com margins, legendas horizontais em `y=-0.25`, fundo transparente, grid sutil, hover com borda.
- `render_card_kpi(label: str, valor: str, delta: str | None = None) -> str` -- retorna HTML do card com label uppercase, valor grande, delta colorido.
- `escopo_pessoa(df) -> list[str]` -- extrai pessoas dinamicamente: `sorted(df["quem"].dropna().unique().tolist())`.

**Arquivo:** `src/dashboard/style.css` (novo)

Migrar CSS inline de `tema.py` + adicionar:
- Fonte Inter (Google Fonts) com fallback system.
- Escala tipográfica: título página 1.4rem/600, título seção 0.85rem/600/uppercase, label card 0.7rem/500, valor card 1.65rem/700, corpo 0.78rem, tabela 0.72rem.
- Cards: border-radius 12px, box-shadow sutil, hover `translateY(-2px)`.
- Tabelas: headers uppercase, sticky header, alternating rows.
- Remoção de chrome Streamlit: `#MainMenu`, `footer`, `header`, `.stDeployButton`.
- `max-width: 1360px` no container principal.
- Gap 16px entre colunas via `[data-testid="stHorizontalBlock"]`.
- Recalibrar `texto_sec` de `#6272A4` para `#8892B0` (WCAG AA).

**Arquivo:** `src/dashboard/app.py` -- chamar `carregar_css()` no topo após `st.set_page_config`.

**Arquivos de página:** substituir cards inline pelos retornados por `render_card_kpi`, substituir `fig.update_layout(**LAYOUT_PLOTLY)` por `fig.update_layout(**criar_layout_plotly(titulo))`.

**Escopo limitado:** não implementar busca global nem grafo (Sprint 29a) -- esses recebem design próprio após mockups da Fase 3.

---

## Armadilhas Conhecidas

| Ref | Armadilha | Como evitar |
|-----|-----------|-------------|
| A20.1 | Redesenhar antes da arquitetura de navegação (Sprint 29a) gera retrabalho | Escopar apenas componentes estáveis: cards KPI, tipografia, tabelas, layout Plotly. Grafo e busca global ficam para revisão pós-Fase 3 |
| A20.2 | `st.dataframe()` tem CSS interno que conflita com custom | Testar override específico; se falhar, renderizar tabela HTML manual |
| A20.3 | Plotly em dark mode exige eixos/grid claros, não escuros | Factory já define `rgba(255,255,255,0.06)` no grid |
| A20.4 | `max-width: 1360px` conflita com `layout="wide"` | Aplicar via CSS em `.block-container`, testar ambos os modos |
| A11 | Streamlit tabs trocam visualmente via JS | Se precisar trocar aba, usar `document.querySelectorAll('[role="tab"]')[N].click()` |

Referência: `docs/ARMADILHAS.md`

---

## Evidências Obrigatórias

- [ ] 4 mockups em `docs/mockups/2026-04-18_*.md` aprovados por André antes de Fase 2.1
- [ ] `make lint` passa sem erros
- [ ] `make dashboard` inicia sem erro
- [ ] Inspeção manual confirma contraste WCAG AA (usar DevTools)
- [ ] Filtro de pessoa funciona com DataFrame contendo só "Casal" (teste de borda)
- [ ] Fonte Inter carrega (verificar no DevTools -> Network)
- [ ] CLAUDE.md atualizado: remover Sprint 20 de "Pendentes" ao concluir

---

## Verificação end-to-end

```bash
make lint
make dashboard   # inspeção visual manual
ls docs/mockups/2026-04-18_*.md   # deve listar 4 arquivos
```

---

*"A simplicidade é a sofisticação suprema." -- Leonardo da Vinci*
