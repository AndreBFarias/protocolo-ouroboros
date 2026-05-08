---
id: UX-V-2.2-FIX
titulo: Pagamentos — adicionar legenda rodapé + total mensal + setas navegação mês
status: concluída
concluida_em: 2026-05-08
commit: e4c0968
prioridade: alta
data_criacao: 2026-05-08
fase: PARIDADE_VISUAL
depende_de: [UX-V-2.2.A]
esforco_estimado_horas: 2
origem: docs/auditorias/AUDITORIA_PARIDADE_VISUAL_2026-05-08.md A3
mockup: novo-mockup/mockups/04-pagamentos.html
---

# Sprint UX-V-2.2-FIX — completar elementos da spec V-2.2 que ficaram fora

## Contexto

UX-V-2.2 declarou concluída em 2026-05-07. Inspeção 2026-05-08 mostrou que 3 elementos descritos explicitamente nas seções 3 e 6 da spec original ficaram ausentes do calendário:

- Legenda no rodapé com 4 pílulas (fixo · variável · cartão · em atraso).
- Total mensal "N pagamentos no mês · R$ X" no canto direito do rodapé.
- Setas de navegação `<` `>` ao lado do toggle SEG-DOM no header.

Lista lateral também mostra apenas 1 evento; depende de UX-V-2.2.A (enriquecer prazos com valores reais) para fazer sentido visualmente.

## Objetivo

1. Adicionar bloco `.cal-legenda` no rodapé do calendário (já existe parcialmente no CSS de V-2.2 mas não é renderizado).
2. Renderizar total mensal "N pagamentos no mês · R$ Y" via classe `.cal-legenda-total`.
3. Adicionar 2 botões de navegação no header (`<` mês anterior / `>` próximo) que ajustam o filtro `mes_selecionado`.

## Validação ANTES (grep)

```bash
grep -n "cal-legenda\|cal-nav-btn\|cal-legenda-total" src/dashboard/paginas/pagamentos.py src/dashboard/css/paginas/pagamentos.css
```

## Não-objetivos

- NÃO implementar pagamento funcional.
- NÃO mudar lógica de `_pagamentos_por_data`.
- NÃO duplicar setas em outros lugares (só header do calendário).

## Proof-of-work

```bash
make lint && make smoke
.venv/bin/pytest tests/ -k pagamentos -q
```

Captura visual: cluster=Finanças&tab=Pagamentos deve mostrar legenda + total mensal + setas navegação.

## Critério de aceitação

1. 4 pílulas de legenda renderizadas no rodapé.
2. Texto "N pagamentos no mês · R$ X" correto e tabular-nums.
3. Setas mudam mês renderizado (URL query atualizada).
4. Lint + smoke + baseline pytest.

## Referência

- Spec original: `sprint_ux_v_2_2_pagamentos.md` seções 3+6.
- Mockup: `04-pagamentos.html`.
- Sub-sprint hard-bloqueante: V-2.2.A.

*"Ver o mês inteiro com legenda é ver o orçamento como um todo." — princípio V-2.2-FIX*
