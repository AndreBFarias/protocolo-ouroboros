---
id: UX-V-2.8-FIX
titulo: Skills D7 — skeleton-mockup canônico (5 KPIs + inventário 18 skills + cobertura)
status: backlog
prioridade: alta
data_criacao: 2026-05-08
fase: PARIDADE_VISUAL
depende_de: []
esforco_estimado_horas: 3
origem: docs/auditorias/AUDITORIA_PARIDADE_VISUAL_2026-05-08.md (página 14) + M1
mockup: novo-mockup/mockups/14-skills-d7.html
---

# Sprint UX-V-2.8-FIX — Skills D7 com skeleton canônico

## Contexto

UX-V-2.8 declarou paridade mas dashboard cai em fallback texto ("SKILLS D7 AINDA NÃO INICIALIZADO") com 4 KPIs `--`. Mockup `14-skills-d7.html` tem:

- 5 KPIs (não 4): Cobertura D7 78% / Taxa Graduação +3/Q1 / Regressões 30D 1 / Confiança Média 90.4% / Execuções 30D 3.836.
- Inventário lateral esquerda: 18 skills com ID/skill/D7/confiança%/execuções/tendência (s01 a s18).
- Lateral direita: DISTRIBUIÇÃO POR ESTADO (graduado/calibrando/regredido/bloqueado) + COBERTURA POR CLUSTER (Finanças/Documentos/Análise/Sistema) + legenda.

CSS dedicado `skills_d7.css` existe mas não é consumido (página entra em fallback antes).

## Objetivo

1. Renderizar 5 KPIs (não 4) com `--` quando log não existe.
2. Skeleton inventário com 18 linhas de placeholder (ID s01..s18 + label cinza).
3. Skeleton DISTRIBUIÇÃO POR ESTADO com 4 estados e contadores `--`.
4. Skeleton COBERTURA POR CLUSTER com 4 clusters e barras placeholder.
5. CTA "rode ./run.sh --tudo para popular" no rodapé (não no lugar do skeleton).
6. Garantir CSS é consumido sempre (não só no caminho com dado).

## Validação ANTES (grep)

```bash
grep -n "carregar_css_pagina\|fallback_estado_inicial\|inventario\|cobertura_cluster" src/dashboard/paginas/skills_d7.py | head
```

## Não-objetivos

- NÃO inventar dados de skills.
- NÃO mexer no formato `skill_d7_log.json`.

## Proof-of-work

```bash
make lint && make smoke
.venv/bin/pytest tests/ -k skills_d7 -q
```

Captura visual: 5 KPIs + inventário 18 skills skeleton + distribuição + cobertura + CTA rodapé.

## Critério de aceitação

1. 5 KPIs sempre visíveis (não 4).
2. Inventário 18 linhas (skeleton ou real).
3. Distribuição + Cobertura sempre presentes.
4. CSS dedicado consumido sempre.
5. Lint + smoke + baseline pytest.

## Referência

- Mockup: `14-skills-d7.html`.
- UX-V-03 (skeleton canônico).

*"Sistema sem painel de saúde é caixa preta." — princípio V-2.8-FIX*
