---
titulo: Auditoria honesta de paridade visual pós-Onda V — supervisor pessoal
data: 2026-05-08
escopo: 28 páginas (29 mockups menos 00-shell-navegacao)
metodo: comparação side-by-side via claude-in-chrome MCP + playwright (Revisor) em viewport 1568×660
fonte_canonica: novo-mockup/mockups/*.html
fonte_real: http://localhost:8501 (commit c8d6abb pós-merge V-2 + cleanup duplicata)
referencia_anterior: docs/auditorias/AUDITORIA_PARIDADE_VISUAL_2026-05-07.md
---

# Auditoria de paridade visual — 2026-05-08

## Contexto

Pedido do dono: validar honestamente o que foi feito na Onda V (V-1 + V-2 = 22 sprints declaradas concluídas em 2026-05-07) buscando especificamente bugs, miguês, problemas de espaçamento, capitalização, acentuação e funcionalidade real do dashboard vs mockup canônico. Auditoria conduzida pessoalmente pelo Opus principal sem dispatching de subagentes (padrão `(p)` do VALIDATOR_BRIEF).

Esta auditoria expande a `AUDITORIA_PARIDADE_VISUAL_2026-05-07.md` com (a) verificação dos compromissos feitos pelas sprints V-2.1 a V-2.17 contra o estado real, (b) inspeção visual das 23 páginas restantes que a auditoria anterior não cobriu side-by-side, (c) varredura cruzada com tamanhos `.py`, frontmatters de spec e existência de CSS dedicado.

---

## Resultado executivo

| Onda | Sprints declaradas concluídas | Veredito honesto |
|---|--:|---|
| V-1 (transversal) | 5 | OK estrutural; 1 sub-sprint residual em backlog (V-04.A acentuação) |
| V-2 (paridade páginas) | 17 | 5 com migué grave / 7 com gaps médios / 3 OK / 2 com fallback degradado |
| Páginas SEM sprint UX-V dedicada | 11 (Extrato, Catalogação, Busca, IRPF, Inbox, Categorias, Skills D7-fallback, Hoje, Humor, Diário, Memórias-mockup-novo) | múltiplas sub-sprints V-3.1 a V-3.7 propostas e nunca criadas |

**Score honesto**: ~70-75% paridade visual real (vs declaração implícita 100% após "merge onda V-2 completa" no commit `90155cf`).

**Onda V-3 inteira (proposta na auditoria 2026-05-07)**: 0 sprints criadas em backlog.

**2 violações duras de limite 800L (`(h)`)**: `visao_geral.py = 996L`, `pagamentos.py = 838L`.

**1 bug funcional crítico**: roteamento `?tab=Catalogação` renderiza Busca Global.

---

## Achados consolidados — 28 páginas

### Páginas auditadas no side-by-side de hoje

| # | Página | Sprint | Status spec | Veredito | Classificação |
|---|---|---|---|---|---|
| 01 | Visão Geral | UX-V-2.7 | concluída | KPI Metas com contadores errados, Atividade Recente pobre (2 linhas vs 6 mockup), texto "ANALISE/EVENTOS" sem acento | ALTA (5 defeitos + violação 800L) |
| 02 | Extrato | sem | — | filt-bar inline ausente, lista por dia ausente | ALTA (V-3.1 não criada) |
| 03 | Contas | UX-V-2.1 | concluída | sparkline e barras uso OK; falta baseboard 4-campos OFX | MÉDIA |
| 04 | Pagamentos | UX-V-2.2 | concluída | calendário OK; falta legenda rodapé + total mensal + setas navegação + valor real (V-2.2.A em backlog) | ALTA (3 elementos da spec) |
| 05 | Projeções | sem | — | aporte mensal R$ 0,00, sliders ausentes, só 2 marcos vs 5 mockup | ALTA (não estava no plano V-2) |
| 06 | Busca Global | sem | — | facet-card lateral ausente, snippet highlight ausente | MÉDIA (V-3.2 não criada) |
| 07 | Catalogação | sem | — | **BUG ROTEAMENTO**: renderiza Busca Global | ALTÍSSIMA (V-3.3 não criada) |
| 08 | Completude | UX-V-2.3 | concluída | eixos invertidos (categorias trans vs tipos doc), 0% cobertura semantically wrong, sem legenda visível | ALTA |
| 09 | Revisor | sem | — | layout 4-pane (OFX/Rascunho/Opus/Humano) ausente, tabs ausentes, trace ausente | ALTA (V-4 não criada) |
| 10 | Validação Tripla | UX-V-2.4 | **frontmatter "backlog"** | feature central inoperante: Opus 100% vazio, status só SÓ ETL/SÓ HUMANO, título sem `ã`, sub-sprint INFRA não criada | ALTÍSSIMA |
| 11 | Categorias | sem | — | árvore + treemap OK; faltam botões e bloco regras | BAIXA |
| 12 | Análise | UX-V-2.6 | concluída | breadcrumb errado, tabs duplicadas, KPIs assimétricos, Investido R$ 0, Insights cortados | MÉDIA-ALTA (5 defeitos) |
| 13 | Metas | UX-V-2.5 | concluída | 6 cards + donut + 3 colunas OK; falta glyph + total acumulado | BAIXA |
| 14 | Skills D7 | UX-V-2.8 | concluída | mesmo padrão Rotina: fallback texto vs skeleton-mockup, CSS criado mas não consumido | ALTA |
| 15 | IRPF | sem | — | dropdown calendário proeminente, 2 categorias faltantes, barras sem cor, botões ausentes | MÉDIA (V-3.4 não criada) |
| 16 | Inbox | sem | — | 5 KPIs + dropzone + chips OK | BAIXA |
| 17 | Bem-estar Hoje | sem | — | sliders OK; cards laterais semanticamente diferentes do mockup | MÉDIA (V-3.5 não criada) |
| 18 | Humor heatmap | sem | — | heatmap renderiza; falta sparkline 30d e card STREAK | MÉDIA-ALTA (V-3.6 não criada) |
| 19 | Diário emocional | sem | — | layout 2-col vs mockup 3-col com facetas; form NOVA ENTRADA com tabs ausente | ALTA (V-3.7 não criada) |
| 20 | Rotina | UX-V-2.10 | concluída | fallback texto vs skeleton-mockup das 3 colunas; `be_rotina.css` não existe | ALTA |
| 21 | Recap | UX-V-2.17 | concluída | ADR-13 honrada; falta tabela comparativo 30D + 5 destaques + bloco narrativa manual | MÉDIA |
| 22 | Eventos | UX-V-2.9 | concluída | timeline + calendário visual + distribuição OK | BAIXA |
| 23 | Memórias | UX-V-2.11 | concluída | **MIGUÉ ARQUITETURAL**: dashboard ainda em layout antigo (Treinos/Fotos/Marcos), mockup propõe cápsulas multimídia em grid | ALTA |
| 24 | Medidas | UX-V-2.12 | concluída | mesmo padrão Medidas/Skills D7: fallback texto vs skeleton-mockup; schema sem GORDURA % (V-2.12.A em backlog) | ALTA |
| 25 | Ciclo | UX-V-2.13 | concluída | skeleton parcial (silhueta meia-roda + 4 KPIs `--`); falta anel SVG completo + cards SINTOMAS + CRUZAMENTO | MÉDIA |
| 26 | Cruzamentos | UX-V-2.14 | concluída | builder + 8 perguntas + insights structured — única Bem-estar com paridade alta | BAIXA |
| 27 | Privacidade | UX-V-2.15 | concluída | estrutura 4 níveis × bidirecional × campos OK; cards laterais aguardando vault B conectado | BAIXA |
| 28 | Editor TOML | UX-V-2.16 | **frontmatter "backlog"** | layout 2-col vs spec 3-col; preview ao vivo ausente; validação inline ausente; linhas numeradas ausentes | ALTA |

### Distribuição por classificação

- **ALTÍSSIMA** (2): Catalogação (bug roteamento), Validação Tripla (feature central inoperante).
- **ALTA** (12): Visão Geral, Extrato, Pagamentos, Projeções, Completude, Revisor, Skills D7, Diário, Rotina, Memórias, Medidas, Editor TOML.
- **MÉDIA-ALTA** (3): Análise, Humor, Ciclo.
- **MÉDIA** (5): Contas, Busca, IRPF, Hoje, Recap.
- **BAIXA** (6): Categorias, Metas, Inbox, Eventos, Cruzamentos, Privacidade.

---

## Migués transversais detectados

### M1. Fallback degradado em vez de skeleton-mockup canônico

UX-V-03 (transversal, concluída) prometia *"skeleton do mockup + CTA app mobile + última sync"* para páginas Bem-estar com dados ausentes. Implementação real virou *"texto explicativo + KPIs com `--` + CTA mob"* — sem skeleton.

**Páginas afetadas**: Rotina, Skills D7, Medidas. Ciclo entrega skeleton parcial (única).

**Decisão dono 2026-05-08**: endurecer skeleton-mockup canônico nas 3 páginas mob-dependentes + Skills D7.

### M2. Spec promete dado, dado não existe, sub-sprint INFRA não criada

UX-V-2.4 (Validação Tripla) é o caso paradigmático: spec promete `extracao_tripla.json` schema canônico mas nunca foi gerado. Coluna Opus 100% vazia. A própria spec dizia "se schema não existe, parar e propor sub-sprint INFRA-EXTRACAO-TRIPLA-SCHEMA" — não foi feito.

Mesmo padrão em escala menor: Skills D7 (`skill_d7_log.json`), Rotina (`rotina.toml`), Medidas (`medidas.json` schema antropométrico parcial).

### M3. Limite de linhas violado (`(h)`)

- `src/dashboard/paginas/visao_geral.py = 996 linhas`.
- `src/dashboard/paginas/pagamentos.py = 838 linhas` (V-2.2.B em backlog reconhece).

Sprint executor não respeitou padrão `(h)` em V-2.7. Modularização precisa em `componentes/atividade_recente.py` + `componentes/cards_clusters.py`.

### M4. Frontmatters inconsistentes (status backlog vs merge realizado)

- UX-V-2.4: `status: backlog` mas commit `f5c6e9f merge(ux-v-2.4)`.
- UX-V-2.16: `status: backlog` mas commits `e50eeb4` + `6619e6f merge(ux-v-2.16)`.

Migué documental, não de código. Indica que executor mergeu sem fazer step final de mover spec para `concluidos/`.

### M5. Bug funcional de roteamento (Catalogação)

`?cluster=Documentos&tab=Catalogac%C3%A3o` (URL canônica) renderiza visualmente a página Busca Global. Apenas o breadcrumb dinâmico mostra "DOCUMENTOS / CATALOGAÇÃO". A função `renderizar` da Catalogação ou a tabela de roteamento em `app.py` está apontando errado.

### M6. Sprints PROPOSTAS em auditoria anterior não criadas

A `AUDITORIA_PARIDADE_VISUAL_2026-05-07.md` propôs **Leva V-3** (7 sprints de cleanup MÉDIO/BAIXO) e **Leva V-4** (Revisor) — nada disso virou backlog em `docs/sprints/backlog/`.

Sprints faltantes:
- UX-V-3.1-EXTRATO-FILT
- UX-V-3.2-BUSCA-FACET
- UX-V-3.3-CATALOGACAO-FIX (precisa virar V-3.3-CATALOGACAO-FIX-ROTA antes pelo bug M5)
- UX-V-3.4-IRPF-FINISH
- UX-V-3.5-BE-HOJE-CARDS
- UX-V-3.6-BE-HUMOR-DEMO
- UX-V-3.7-BE-DIARIO
- UX-V-4-REVISOR

### M7. Sprint para Projeções nunca proposta

Projeções (página 05) tem 4 migués (aporte mensal R$ 0, sliders ausentes, só 2 marcos vs 5, "fora do horizonte"). Auditoria 2026-05-07 marcou BAIXA mas a inspeção visual de hoje sobe para ALTA. Não há nenhuma sprint UX-V cobrindo. Precisa UX-V-2.0-PROJECOES nova.

### M8. Páginas Bem-estar de Memórias com migué arquitetural (V-2.11)

Spec V-2.11 declarou paridade visual mas o dashboard ainda usa layout antigo (Treinos/Fotos/Marcos com heatmap) em vez da estrutura de cápsulas multimídia em grid que o mockup propõe. Quando dado mob aparecer, página seguirá com layout antigo.

### M9. Polish do shell global ainda incompleto (achados imediatos do dono 2026-05-08)

Inspeção visual ao vivo na sessão revelou 4 problemas no shell que afetam todas as páginas — não cobertos pelas sprints UX-U (estruturantes universais) nem pela Onda M (modularização CSS):

**M9.1 — Layout não usa 100% da largura do monitor**
- Há barras pretas/cinzas nas laterais; o app Streamlit ocupa ~1568px central enquanto o monitor pode ir além.
- Causa provável: configuração padrão `layout="wide"` do Streamlit ainda tem container central com `max-width` aplicado por algum CSS herdado de `tema_css.py` ou Streamlit-default não sobrescrito.
- Correção: aplicar `.main .block-container { max-width: 100% !important; padding-left/right: var(--sp-X); }` em CSS global do shell.

**M9.2 — Largura da sidebar corta o input "Buscar"**
- O placeholder "Buscar" da sidebar fica truncado; resta visível só o início da palavra.
- Atalho `/` no canto direito está colado na borda.
- Causa: largura fixa da sidebar Streamlit-default não foi ajustada ou está configurada com valor que não acomoda o input + atalho.
- Correção: ajustar `width` da sidebar em `tema_css.py` (sidebar canônica do mockup tem ~250-280px; verificar valor atual e aumentar se necessário).

**M9.3 — Ícone de lupa SVG desalinhado**
- O glyph SVG "Q" (lupa) aparece acima do baseline do texto "Buscar" — `vertical-align` ou `transform` errado.
- Correção: padronizar o SVG inline com `vertical-align: middle` ou `display: inline-flex; align-items: center` no `_components.css` da search-bar.

**M9.4 — Filtros globais (chip-bar) com polish ruim**
- Os 4 chips (granularidade · período · pessoa · forma) ficam soltos no topo, e quando clica num para abrir o popover, o dropdown é desproporcional (popover branco gigante em comparação ao chip).
- Auditoria 2026-05-07 já registrou (P1) que o filtro global precisava remodelagem em chip-bar canônica — UX-V-01-FILTRO-GLOBAL foi declarada concluída em 2026-05-07.
- Estado atual mostra que o que foi entregue NÃO atendeu ao polish esperado: popover Streamlit-nativo aparece desalinhado e desproporcional.
- Correção: revisar dimensões do popover (`st.popover` width / height), padding interno, e contraste das bordas para manter densidade do mockup.

**Classificação geral M9**: ALTA — afeta TODAS as páginas, contraria padrão `(w)` (anti-padrão JS global) e mostra que UX-V-01 e Onda M deixaram débitos de shell.

---

## Plano de correção (atualizado)

### Sprints novas a criar (16 specs)

**Onda V-FIX (correções em sprints já fechadas — 8 sprints novas)**

| ID | Tema | Esforço | Bloqueia |
|---|---|---|---|
| INFRA-EXTRACAO-TRIPLA-SCHEMA | Schema canônico `extracao_tripla.json` + popular Opus para >=3 amostras | 4h | V-2.4-FIX |
| UX-V-2.4-FIX | reescrever layout 3-col com lista por TIPO + título "EXTRAÇÃO TRIPLA" + tabela com badges CONSENSO/DIVERGENTE preenchidos | 3h | feature central |
| UX-V-2.7-FIX | corrigir card Metas + Atividade Recente (6 linhas + ícones tipados) + acentuação ANÁLISE/EVENTOS + dividir `visao_geral.py` 996L → <=800 | 3h | limite `(h)` |
| UX-V-2.2-FIX | adicionar legenda rodapé + total mensal + setas navegação no calendário Pagamentos | 2h | spec original |
| UX-V-2.3-FIX-EIXOS | reescrever heatmap Completude com eixo Y = tipos de doc (não categorias trans) + legenda visível | 4h | spec original |
| UX-V-2.6-FIX | corrigir breadcrumb + tabs duplicadas + layout KPIs simétrico + Investido + Insights Derivados completos | 3h | UX |
| UX-V-2.10-FIX | criar `be_rotina.css` + skeleton-mockup das 3 colunas alarmes/tarefas/contadores | 2h | UX-V-03 |
| UX-V-2.16-FIX | reescrever editor 3-col + preview ao vivo + validação inline + frontmatter | 6h | spec original |

**Onda V-3 (criar sprints da Leva V-3 + V-4 — 8 sprints novas)**

Especificar conforme tabela já redigida em `AUDITORIA_PARIDADE_VISUAL_2026-05-07.md` linhas 162-208 + 1 sprint nova:

- UX-V-3.1-EXTRATO-FILT (3h)
- UX-V-3.2-BUSCA-FACET (3h)
- UX-V-3.3-CATALOGACAO-FIX-ROTA (1h, bug funcional) + UX-V-3.3-CATALOGACAO-GRID (4h, feature)
- UX-V-3.4-IRPF-FINISH (2h)
- UX-V-3.5-BE-HOJE-CARDS (4h, com cards mockup-canônicos)
- UX-V-3.6-BE-HUMOR-DEMO (3h, sparkline + STREAK)
- UX-V-3.7-BE-DIARIO (3h, form 3-col + tabs)
- UX-V-4-REVISOR (4h, layout 4-pane)

**Sprints específicas adicionais**

- UX-V-2.0-PROJECOES (4h) — sliders + 5 marcos + corrigir aporte
- UX-V-2.11-FIX-CAPSULAS (5h) — substituir Treinos/Fotos/Marcos por grid de cápsulas multimídia + skeleton
- UX-V-2.12-FIX-SKELETON (3h) — skeleton-mockup com 6 cards + sparkline placeholder + tabela 6 semanas
- UX-V-2.13-FIX-ANEL (4h) — anel SVG canônico de 28 dias com 4 fases coloridas no skeleton
- UX-V-2.17-FIX (3h) — comparativo 30D estruturado + 5 destaques + bloco narrativa manual
- UX-V-2.8-FIX-SKELETON (3h) — skeleton-mockup com 5 KPIs + inventário 18 skills placeholder
- UX-V-SHELL-FIX (3h) — fixes M9.1+M9.2+M9.3+M9.4 do shell global (largura 100%, sidebar Buscar, alinhamento lupa, popover filtros) — atinge TODAS as páginas, prioridade alta

**Sub-sprints residuais já em backlog — executar em ordem**

V-2.2.A (precisa antes de V-2.2-FIX) → V-2.2-FIX → V-2.2.B → V-04.A → V-2.12.A → M-02.A → M-02.B1.

### Total de trabalho proposto

- Sprints novas a criar: **16 specs** (8 V-FIX + 8 V-3/V-4)
- Sprints específicas adicionais: **6 specs** (V-2.0, V-2.11-FIX, V-2.12-FIX, V-2.13-FIX, V-2.17-FIX, V-2.8-FIX)
- Sub-sprints residuais: **6** (já em backlog)

**Total: 28 sprints/sub-sprints, ~70-80h estimadas, paralelizável em 3-4 worktrees → ~20-25h wall clock**.

---

## Verificação end-to-end (após execução completa)

1. **Re-auditoria visual**: capturar 28 páginas side-by-side e gerar `AUDITORIA_PARIDADE_VISUAL_2026-05-XX.md` com score por página. Meta: >=85% das páginas em classificação BAIXA, zero ALTÍSSIMA.
2. **Tamanhos**: `wc -l src/dashboard/paginas/*.py | awk '$1>800'` retorna vazio.
3. **Acentuação**: `python3 ~/.config/zsh/scripts/validar-acentuacao.py --paths src/dashboard/` retorna 0 violações.
4. **Smoke + lint + pytest**: `make lint && make smoke && .venv/bin/pytest tests/ -q` baseline mantida (1.620+ passed).
5. **Bug roteamento**: `?tab=Catalogação` renderiza página Catalogação real (não Busca Global).
6. **Validação Tripla**: PARIDADE > 0% com >=3 amostras Opus preenchidas. Status DIVERGENTE/CONSENSO renderizando.

---

*"O que mede a si mesmo afia-se. Auditoria sem viés é a única que importa." — princípio do supervisor pessoal*
