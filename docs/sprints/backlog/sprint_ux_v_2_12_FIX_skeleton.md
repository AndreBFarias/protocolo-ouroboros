---
id: UX-V-2.12-FIX
titulo: Medidas — skeleton-mockup canônico (6 cards + sparkline placeholder + tabela 6 semanas)
status: backlog
prioridade: alta
data_criacao: 2026-05-08
fase: PARIDADE_VISUAL
depende_de: []
esforco_estimado_horas: 3
origem: docs/auditorias/AUDITORIA_PARIDADE_VISUAL_2026-05-08.md (página 24) + M1
mockup: novo-mockup/mockups/24-medidas.html
---

# Sprint UX-V-2.12-FIX — Medidas com skeleton-mockup das 6 cards

## Contexto

UX-V-2.12 declarou paridade mas dashboard cai em fallback texto puro ("MEDIDAS · SEM REGISTROS AINDA") com 6 KPIs vazios. Mockup tem 6 cards (PESO/GORDURA/CINTURA/PRESSÃO/FREQ.REP/SONO MÉDIO) cada um com timestamp, valor + unidade, delta variação 30d e sparkline curvada + tabela "Histórico semanal · últimas 6 semanas".

Decisão dono 2026-05-08: endurecer skeleton-mockup canônico agora.

## Objetivo

1. Renderizar skeleton 6 cards mesmo quando vault sem dados:
   - Cada card com label, valor `--`, unidade, "delta vs 30d" placeholder, e sparkline-skeleton (linha cinza pontilhada).
2. Toggle PESSOA A · você / PESSOA B presente sempre.
3. Skeleton tabela "Histórico semanal · últimas 6 semanas" com 6 linhas de placeholder.
4. Texto explicação CTA mob no rodapé (não substitui skeleton).
5. Quando vault popula, cards reais aparecem (sem regressão).

## Validação ANTES (grep)

```bash
wc -l src/dashboard/paginas/be_medidas.py
grep -n "skeleton\|sparkline\|6 semanas\|fallback_estado_inicial" src/dashboard/paginas/be_medidas.py | head
```

## Não-objetivos

- NÃO inventar valores numéricos.
- NÃO mexer no schema (`V-2.12.A` cuida dos campos fisiológicos).

## Proof-of-work

```bash
make lint && make smoke
.venv/bin/pytest tests/ -k be_medidas -q
```

Captura visual: 6 cards skeleton + tabela skeleton + CTA mob no rodapé.

## Critério de aceitação

1. 6 cards skeleton sempre visíveis.
2. Sparkline-skeleton em cada card (linha cinza placeholder).
3. Tabela "Histórico semanal" com 6 linhas placeholder.
4. CTA mob no rodapé (não no lugar do skeleton).
5. Lint + smoke + baseline pytest.

## Referência

- Mockup: `24-medidas.html`.
- UX-V-03 (skeleton canônico).
- Sub-sprint complementar: V-2.12.A (schema fisiológico).

*"Skeleton é forma; forma comunica antes de dado chegar." — princípio V-2.12-FIX*
