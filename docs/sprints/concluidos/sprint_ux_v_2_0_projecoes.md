---
id: UX-V-2.0
titulo: Projeções — sliders aporte/retorno/horizonte + 5 marcos + corrigir aporte zerado
status: concluída
concluida_em: 2026-05-08
commit: c9e8038
prioridade: alta
data_criacao: 2026-05-08
fase: PARIDADE_VISUAL
depende_de: []
esforco_estimado_horas: 4
origem: docs/auditorias/AUDITORIA_PARIDADE_VISUAL_2026-05-08.md (página 05) + M7
mockup: novo-mockup/mockups/05-projecoes.html
---

# Sprint UX-V-2.0 — Projeções como simulador interativo

## Contexto

Página Projeções não foi coberta por nenhuma sprint UX-V-2.x. Auditoria 2026-05-07 marcou BAIXA mas inspeção 2026-05-08 sobe para ALTA:

- Aporte Mensal Médio R$ 0,00 (KPI quebrado — "Em 5 anos" mostra crescimento, então aporte 0 é cálculo errado).
- 3 sliders (APORTE MENSAL / RETORNO A.A. / HORIZONTE select) ausentes — mockup tem com "recalcula em tempo real".
- Marcos lateral: dashboard mostra 2 (Reserva 100% / Entrada Apto), mockup mostra 5 (1ª centena / Reserva 6m / Entrada apto / 1/4 milhão / 1/2 milhão).
- "Independência Financeira: fora do horizonte" vs mockup "2042 · 16a" (sintoma do aporte 0).

## Objetivo

1. Corrigir cálculo de "Aporte Mensal Médio" extraindo do ritmo de saldo do extrato.
2. Adicionar 3 sliders interativos: APORTE MENSAL / RETORNO A.A. / HORIZONTE (5/10/15/20/25 anos).
3. Recalcular projeção em tempo real (`@st.cache_data` por slider value).
4. Marcos: 5 cards canônicos (1ª centena 100k / Reserva 6m / Entrada apto / 1/4 milhão / 1/2 milhão), mostrar "em N meses" para cada.
5. Independência Financeira: calcular ano em que patrimônio cobre 25× custo anual (FIRE).

## Validação ANTES (grep)

```bash
wc -l src/dashboard/paginas/projecoes.py
grep -n "aporte_mensal\|st.slider\|marcos\|independencia" src/dashboard/paginas/projecoes.py | head
```

## Não-objetivos

- NÃO implementar persistência de cenários nesta sprint.
- NÃO mudar gráfico Plotly (mockup tem SVG dashed; Plotly OK funcionalmente).

## Proof-of-work

```bash
make lint && make smoke
.venv/bin/pytest tests/ -k projecoes -q
```

Captura visual: cluster=Finanças&tab=Projeções com 3 sliders + 4 KPIs corretos + 5 marcos.

## Critério de aceitação

1. Aporte Mensal Médio com valor real.
2. 3 sliders funcionais.
3. 5 marcos com "em N meses".
4. Independência Financeira mostra ano (não "fora do horizonte" quando há aporte real).
5. Lint + smoke + baseline pytest.

## Referência

- Mockup: `05-projecoes.html`.

*"Projeção sem slider é tabela estática." — princípio V-2.0*
