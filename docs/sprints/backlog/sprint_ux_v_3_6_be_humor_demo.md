---
id: UX-V-3.6
titulo: Bem-estar Humor — sparkline 30d + card STREAK + skeleton heatmap
status: backlog
prioridade: media
data_criacao: 2026-05-08
fase: PARIDADE_VISUAL
depende_de: []
esforco_estimado_horas: 3
origem: docs/auditorias/AUDITORIA_PARIDADE_VISUAL_2026-05-08.md (página 18)
mockup: novo-mockup/mockups/18-humor-heatmap.html
---

# Sprint UX-V-3.6 — Humor com cards laterais ricos

## Contexto

Inspeção 2026-05-08: heatmap renderiza, 4 cards laterais (Média/Registros/Melhor/Pior) presentes. Faltam:
- Sparkline embaixo da MÉDIA 30 DIAS + delta "+0.18 vs 30d anteriores".
- Card "STREAK HUMOR >=4 X dias · recorde da janela 30d".
- Heatmap quase vazio porque mob não populou — fallback skeleton (decisão dono 2026-05-08: endurecer skeleton-mockup).

## Objetivo

1. Sparkline mini em MÉDIA 30 DIAS lendo de `humor.json` (30 últimos dias).
2. Card STREAK calculando dias consecutivos com humor>=4 + recorde da janela.
3. Quando heatmap tem 0 células: renderizar skeleton 13x7 com cor cinza muito claro (placeholder).
4. CTA mob "última sync: <data>" no topo lendo `last_sync.json`.

## Validação ANTES (grep)

```bash
grep -n "STREAK\|sparkline\|humor.json\|heatmap_skeleton" src/dashboard/paginas/be_humor.py | head
ls .ouroboros/cache/humor.json 2>&1 | head
```

## Não-objetivos

- NÃO inventar humor sintético.
- NÃO mudar heatmap quando há dados.

## Proof-of-work

```bash
make lint && make smoke
.venv/bin/pytest tests/ -k be_humor -q
```

Captura visual: card MÉDIA com sparkline, card STREAK abaixo, heatmap skeleton quando vazio.

## Critério de aceitação

1. Sparkline mini visível em MÉDIA 30 DIAS.
2. Card STREAK presente com valor real ou `--`.
3. Skeleton heatmap renderiza quando vazio.
4. Lint + smoke + baseline pytest.

## Referência

- Mockup: `18-humor-heatmap.html`.

*"Humor médio sem tendência é número solto." — princípio V-3.6*
