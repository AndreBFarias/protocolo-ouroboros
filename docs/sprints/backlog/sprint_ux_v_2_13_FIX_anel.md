---
id: UX-V-2.13-FIX
titulo: Ciclo — anel SVG canônico de 28 dias com 4 fases coloridas + cards SINTOMAS + CRUZAMENTO
status: backlog
prioridade: media
data_criacao: 2026-05-08
fase: PARIDADE_VISUAL
depende_de: []
esforco_estimado_horas: 4
origem: docs/auditorias/AUDITORIA_PARIDADE_VISUAL_2026-05-08.md (página 25)
mockup: novo-mockup/mockups/25-ciclo.html
---

# Sprint UX-V-2.13-FIX — Ciclo com anel SVG completo no skeleton

## Contexto

UX-V-2.13 entregou skeleton parcial (silhueta de meia-roda cinza + 4 KPIs `--`). Spec original prometia "Anel circular SVG com fases + sintomas + cruzamento humor + cards de fase".

Mockup `25-ciclo.html` mostra:
- Anel circular SVG com 28 segmentos coloridos (menstrual rosa d1-5, folicular verde d6-13, fértil amarelo-verde d14-16, lútea rosa-vermelho d17-28).
- Centro do anel: `LÚTEA · d18 · de 28 · próxima menstruação · 24 abr · em 10 dias`.
- Card lateral SINTOMAS HOJE escala 0-3 (8 sintomas).
- Card lateral CRUZAMENTO CICLO × HUMOR (12 ciclos): humor médio por fase.
- 4 cards das fases no rodapé.

## Objetivo

1. Renderizar SVG completo do anel mesmo no skeleton (28 segmentos coloridos sem dado real do dia).
2. Centro mostra `--` quando sem registros.
3. Card SINTOMAS HOJE skeleton com 8 linhas (cólica/inchaço/dor de cabeça/sensibilidade/fadiga/mudança apetite/mudança humor/acne).
4. Card CRUZAMENTO HUMOR skeleton com 4 linhas (folicular/fértil/lútea/menstrual) com `--`.
5. 4 cards de fase no rodapé com descrições canônicas.

## Validação ANTES (grep)

```bash
wc -l src/dashboard/paginas/be_ciclo.py
grep -n "anel\|svg\|fase\|sintomas\|cruzamento" src/dashboard/paginas/be_ciclo.py | head
```

## Não-objetivos

- NÃO popular dia atual no anel sem dado real.
- NÃO calcular cruzamento humor sem >=3 ciclos completos.

## Proof-of-work

```bash
make lint && make smoke
.venv/bin/pytest tests/ -k be_ciclo -q
```

Captura visual: anel SVG colorido completo + cards laterais skeleton + 4 cards de fase.

## Critério de aceitação

1. SVG anel 28 segmentos colorido sempre visível.
2. Centro com `d-- de 28 · próxima --` no skeleton.
3. Cards laterais SINTOMAS + CRUZAMENTO presentes.
4. 4 cards de fase no rodapé.
5. Lint + smoke + baseline pytest.

## Referência

- Mockup: `25-ciclo.html`.
- Mob bloqueante: I-CICLO em Protocolo-Mob-Ouroboros.

*"Anel completo mostra o ciclo como um todo, mesmo sem ponto." — princípio V-2.13-FIX*
