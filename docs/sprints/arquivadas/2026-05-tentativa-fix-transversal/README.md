# 2026-05 — Tentativa "fix transversal" (arquivada)

Arquivado em 2026-05-06 quando a estratégia mudou.

Esta pasta guarda 14 specs UX-RD-FIX-01..14 + ROTEIRO_REDESIGN_FINAL.md, todas executadas em 2026-05-05 numa tentativa de corrigir divergências entre dashboard e mockup via **fixes transversais** (cada sprint corrigia um detalhe em N páginas).

## Resultado

- Métricas DOM ficaram verdes (lint exit 0, smoke 10/10, pytest 2530, h1 únicos, deep-link 12 abas Bem-estar + 5 órfãs).
- **Mas a percepção visual integrada continuou quebrada**: sidebar misturando widgets antigos (logo escudo, selectbox de Granularidade/Mês/Pessoa, Busca Global text input) com shell HTML novo, KPIs semanticamente errados na Visão Geral, layout esparso, bugs Plotly "undefined", page-title inconsistente entre páginas.

## Diagnóstico (2026-05-06)

A estratégia transversal acumula bagunça em vez de fechar tela por tela. Cada fix tocava 1 detalhe em várias páginas mas nenhuma página ficava 100% pronta. O dono pediu reorganização.

## Estratégia substituta

`docs/sprints/backlog/ROTEIRO_TELAS_2026-05-06.md` substituí este roteiro. Aborda em 3 ondas:

- **Onda U** (4 sprints): estruturantes universais (sidebar, topbar, page-header, filtros por página).
- **Onda T** (29 sprints): uma tela por sprint, layout 1:1 com mockup + funcional + dados + validação humana.
- **Onda Q** (3 sprints): quality gates finais.

## Importante

**Os fixes aplicados pelas UX-RD-FIX-01..14 PERMANECEM no código** (não foram revertidos). O que mudou é o **roteiro vigente**: as 14 specs deixaram de representar o plano atual. Ficam aqui como histórico.

Specs nesta pasta:
- 14 sprints `sprint_ux_rd_fix_NN_*.md`
- 1 roteiro mestre `ROTEIRO_REDESIGN_FINAL.md`

## Referências
- Auditoria honesta de 2026-05-05: `docs/auditorias/AUDITORIA_REDESIGN_2026-05-05.md`
- Plano operacional novo: `~/.claude/plans/auditoria-honesta-da-magical-lovelace.md`
