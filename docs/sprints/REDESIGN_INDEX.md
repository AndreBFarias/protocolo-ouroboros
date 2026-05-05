# Redesign Ouroboros — Índice mestre

> Índice das 19 sprints da reforma de UI do dashboard Streamlit para casar 1:1
> com os 28 mockups HTML em `novo-mockup/`. Plano canônico em
> `~/.claude/plans/lazy-noodling-wind.md`.

## Contexto e justificativa

Em 2026-05-04 o dono pediu reforma estrutural do dashboard, escolhendo:
- **Escopo cheio**: visual + Inbox real + Extração Tripla + cluster Bem-estar (12 telas).
- **Reescrita 1:1** com mockups HTML (não reskin). Mockup é fonte de verdade.

Mockups vivem em `novo-mockup/mockups/` (28 telas) com tokens canônicos em
`novo-mockup/_shared/tokens.css` e componentes em `novo-mockup/_shared/components.css`.

## Relação com plano ativo `pure-swinging-mitten`

O plano `~/.claude/plans/pure-swinging-mitten.md` Onda 6 reservou IDs
`UX-01..UX-09` para fixes pontuais (callout_html, WCAG-AA, drill-down Sankey,
pyvis fallback). A reescrita 1:1 com mockups **absorve esses 9 fixes** — cada
spec UX-RD-XX declara explicitamente quais UX-01..09 ela depreca.

## Branch

`git checkout -b ux/redesign-v1` — todas as 19 sprints partem dela.

## Validação canônica (padrão `(p)` do VALIDATOR_BRIEF)

Cada sprint é executada por subagente `executor-sprint` (contexto fresco) e
validada **visualmente pelo dono Opus principal** (não despacha
`validador-sprint`). Validação obrigatória:
1. Diff comparativo lado-a-lado mockup HTML × dashboard reformado.
2. Screenshot salvo em `docs/auditorias/redesign/<sprint-id>.png`.
3. Comando runtime real: `./run.sh --dashboard` + URL específica.
4. `make lint` + `make smoke` 10/10 + `pytest tests/ -q` baseline mantida.
5. Spec movida para `concluidos/` com `concluida_em: YYYY-MM-DD`.

## Tabela de sprints

| ID | Nome | Onda | Estimativa | Depende de | Mockup |
|---|---|---|---|---|---|
| UX-RD-01 | Tokens novos + paleta migrada | 0 | 2h | — | `_shared/tokens.css` |
| UX-RD-02 | tema_css.py reescrito sobre componentes shared | 0 | 3h | UX-RD-01 | `_shared/components.css` |
| UX-RD-03 | Shell global: sidebar 8-clusters + atalhos | 0 | 4h | UX-RD-02 | `00-shell-navegacao.html` |
| UX-RD-04 | Visão Geral reescrita | 1 | 3h | UX-RD-03 | `01-visao-geral.html` |
| UX-RD-05 | Skills D7 + Styleguide | 1 | 2h | UX-RD-03 | `14-skills-d7.html` + `styleguide.html` |
| UX-RD-06 | Extrato reescrito | 2 | 4h | UX-RD-03 | `02-extrato.html` |
| UX-RD-07 | Contas + Pagamentos | 2 | 3h | UX-RD-03 | `03-contas.html` + `04-pagamentos.html` |
| UX-RD-08 | Projeções | 2 | 2h | UX-RD-03 | `05-projecoes.html` |
| UX-RD-09 | Busca Global + Catalogação | 3 | 4h | UX-RD-03 | `06-busca-global.html` + `07-catalogacao.html` |
| UX-RD-10 | Completude + Revisor | 3 | 4h | UX-RD-03 | `08-completude.html` + `09-revisor.html` |
| UX-RD-11 | Extração Tripla (substitui validação por arquivo) | 3 | 4h | UX-RD-03 | `10-validacao-arquivos.html` (era extração tripla) |
| UX-RD-12 | Categorias | 4 | 3h | UX-RD-03 | `11-categorias.html` |
| UX-RD-13 | Análise (sankey + comparativo + heatmap) | 4 | 4h | UX-RD-03 | `12-analise.html` |
| UX-RD-14 | IRPF + Metas | 4 | 3h | UX-RD-03 | `15-irpf.html` + `13-metas.html` |
| UX-RD-15 | Inbox real | 5 | 4h | UX-RD-03 | `16-inbox.html` |
| UX-RD-16 | Bridge vault Bem-estar (estende mobile_cache) | 6 | 4h | UX-RD-03 + MOB-bridge-3 | — (backend) |
| UX-RD-17 | Bem-estar Hoje + Humor heatmap | 6 | 4h | UX-RD-16 | `17-bem-estar-hoje.html` + `18-humor-heatmap.html` |
| UX-RD-18 | Diário emocional + Eventos | 6 | 4h | UX-RD-16 | `19-diario-emocional.html` + `22-eventos.html` |
| UX-RD-19 | Bem-estar resto consolidado | 6 | 4h | UX-RD-16 | `20-rotina.html` + `21-recap.html` + `23-26` + `28` |

**Total estimado**: ~67h. Distribuído em sessões de 2-4h cada (1-2 sprints/sessão).

## Ordem recomendada

1. **Onda 0** (UX-RD-01..03) — sequencial, bloqueante.
2. **Onda 1** (UX-RD-04, 05) — sequencial após Onda 0.
3. **Ondas 2-4** (UX-RD-06..14) — podem paralelizar; default sequencial.
4. **Onda 5** (UX-RD-15) — independente após Onda 0.
5. **Onda 6** (UX-RD-16..19) — UX-RD-16 paralelizável com 2-5; demais sequencial após bridge.

## Specs absorvidas/depreciadas

| Spec | Status | Sprint que absorve |
|---|---|---|
| UX-01 (callout_html) | DEPRECADA | UX-RD-02 (tokens cobrem todos os callouts) |
| UX-02 (treemap WCAG) | DEPRECADA | UX-RD-12 (categorias usa palette nova compliant) |
| UX-03 (drill-down sankey/heatmap) | DEPRECADA | UX-RD-13 |
| UX-04 (Revisor responsivo) | DEPRECADA | UX-RD-10 |
| UX-05 (pyvis fallback) | DEPRECADA | UX-RD-09 (Grafo+Obsidian fora do escopo redesign — confirma fora) |
| UX-06 (logs falha grafo) | NÃO ABSORVIDA | mantida no plano ativo, backend |
| UX-07 (snapshot dinâmico contas) | DEPRECADA | UX-RD-07 |
| UX-08 (deep-link teste 13 abas) | RE-AVALIAR | UX-RD-03 mantém URL deep-link com novo shell |
| UX-09 (cleanup acentuação) | NÃO ABSORVIDA | sprint pequena de higiene, separada |

## Observabilidade da reforma

A skill `/auditar-cobertura-total` continua válida — não há contrato de
cobertura D7 sendo alterado. O que muda é só apresentação visual.

## Riscos materializados

| Risco | Mitigação | Sprint dona |
|---|---|---|
| Quebrar drill-down `?cluster=X&tab=Y` | UX-RD-03 reescreve shell preservando query params | UX-RD-03 |
| Perder Sprint 100 deep-link tabs | UX-RD-03 + cada UX-RD-XX da Onda 2-4 mantém âncora `tab=` | UX-RD-03 |
| Bridge Syncthing ausente no desktop | UX-RD-16 começa com `AskUserQuestion` confirmando path real | UX-RD-16 |
| pytest baseline 2.018 quebra | Cada sprint atualiza testes no escopo, nunca como follow-up | todas |
| Reskin parcial deixa inconsistência visual | Onda 0 é gate — dashboard quebrado é aceitável até Onda 0 fechar | UX-RD-01..03 |
| Frankenstein tokens vs hardcoded hex | `/validar-sprint` grep `#[0-9a-fA-F]{6}` em src/dashboard/ | todas |

---

*"Cada bloco é uma sprint pequena, lê-se de cima para baixo, executa-se em ordem." — adaptado de INSTRUCOES_PARA_CLAUDE_CODE.md*
