---
id: UX-V-2.2.B
titulo: Dividir pagamentos.py em módulos (838L excede limite 800L)
status: backlog
prioridade: baixa
data_criacao: 2026-05-07
fase: PARIDADE_VISUAL
depende_de: [UX-V-2.2]
origem: achado colateral durante execução UX-V-2.2 (executor sprint)
---

# Sprint UX-V-2.2.B — Modularizar pagamentos.py para conformar limite 800L

## Contexto

Após UX-V-2.2, `src/dashboard/paginas/pagamentos.py` ficou com 838 linhas
(passou de 755L → 838L). Excede o limite canônico do CLAUDE.md
(`(h)` -- 800 linhas por arquivo).

O excedente vem de funções novas necessárias para o calendário do mês:

- `_gerar_calendario_mes`
- `_pagamentos_por_data`
- `_calendario_html` (substituiu legacy)
- `_lista_proximos_html`

## Objetivo

Extrair as funções de calendário/lista para um módulo dedicado:

```
src/dashboard/componentes/calendario_pagamentos.py
```

Mantendo `pagamentos.py` ≤ 800L com apenas:
- `renderizar(...)` (orquestração)
- KPIs row html
- Page header html
- Sub-abas Boletos/Pix/Crédito

## Não-objetivos

- NÃO mudar comportamento visual.
- NÃO mudar assinaturas das funções públicas (`construir_eventos_calendario`,
  `calcular_kpis_pagamentos`, `gerar_celulas_calendario`,
  `_formatar_boletos_para_exibicao`).
- NÃO inventar testes novos -- preservar os 15 atuais.

## Validação ANTES (grep)

```bash
wc -l src/dashboard/paginas/pagamentos.py
grep -c "^def \|^_def " src/dashboard/paginas/pagamentos.py
```

## Critério de aceitação

1. `pagamentos.py` ≤ 800 linhas.
2. `calendario_pagamentos.py` exporta as 4 funções novas.
3. Lint OK + smoke 10/10.
4. 15 testes do cluster pagamentos passam sem alteração.

## Referência

- Sprint pai: UX-V-2.2.
- Padrão violado: VALIDATOR_BRIEF `(h)`.
