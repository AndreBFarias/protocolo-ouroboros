---
id: UX-V-2.10-FIX
titulo: Rotina — criar be_rotina.css + skeleton-mockup das 3 colunas (alarmes/tarefas/contadores)
status: concluída
concluida_em: 2026-05-08
commit: 4d26e56
prioridade: alta
data_criacao: 2026-05-08
fase: PARIDADE_VISUAL
depende_de: []
esforco_estimado_horas: 2
origem: docs/auditorias/AUDITORIA_PARIDADE_VISUAL_2026-05-08.md A4 + M1
mockup: novo-mockup/mockups/20-rotina.html
---

# Sprint UX-V-2.10-FIX — Rotina com skeleton-mockup canônico no fallback

## Contexto

UX-V-03 (transversal) prometeu *"skeleton-mockup do layout final, igual ao mockup mas estilizado como placeholder claro"* para fallbacks de páginas Bem-estar com dado ausente. UX-V-2.10 herda isso.

Inspeção 2026-05-08 mostrou:
- `src/dashboard/css/paginas/be_rotina.css` NÃO existe.
- Fallback é parágrafo + 4 KPIs com `--`. Nenhuma das 3 colunas (ALARMES / TAREFAS HOJE / CONTADORES) aparece como skeleton.

Spec V-2.10 prometia "KPIs + 3 colunas" — KPIs entregues, 3 colunas não.

## Objetivo

1. Criar `src/dashboard/css/paginas/be_rotina.css` com classes canônicas das 3 colunas.
2. No fallback (sem rotina.toml), renderizar skeleton HTML estático com:
   - Header de cada coluna (`ALARMES — 0` / `TAREFAS — HOJE` / `CONTADORES — 0`) com botão `+` desabilitado.
   - 1-2 cards-skeleton vazios em cada coluna com classe `.skeleton-card` (cinza, opacidade 50%).
3. Quando rotina.toml existe, popular cards reais (já implementado pela V-2.10 original — preservar).

## Validação ANTES (grep)

```bash
test -f src/dashboard/css/paginas/be_rotina.css && echo OK || echo MISSING
grep -n "carregar_css_pagina\|fallback_estado_inicial\|alarmes\|tarefas\|contadores" src/dashboard/paginas/be_rotina.py | head
```

## Não-objetivos

- NÃO popular dados reais — só skeleton no fallback.
- NÃO mexer no editor TOML.

## Proof-of-work

```bash
test -f src/dashboard/css/paginas/be_rotina.css
make lint && make smoke
.venv/bin/pytest tests/ -k rotina -q
```

Captura visual: cluster=Bem-estar&tab=Rotina mostra skeleton das 3 colunas com cards cinzas vazios.

## Critério de aceitação

1. CSS dedicado existe e é consumido via `carregar_css_pagina("be_rotina")`.
2. 3 colunas renderizam mesmo com `0 alarmes · 0 tarefas · 0 contadores`.
3. Cards-skeleton com placeholder cinza visível.
4. Quando rotina.toml existe, cards reais aparecem (sem regressão).
5. Lint + smoke + baseline pytest.

## Referência

- Spec original: `sprint_ux_v_2_10_rotina.md`.
- UX-V-03 (skeleton canônico).
- Mockup: `20-rotina.html`.

*"Esqueleto sem carne ainda é forma — e forma comunica." — princípio V-2.10-FIX*
