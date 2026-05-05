# Ouroboros · Redesign v1

Sistema agentic-first de extração, validação e catalogação financeira.

## Estrutura

```
ouroboros-redesign-v1/
├── index.html              ← navegação principal
├── styleguide.html         ← tokens, tipografia, componentes
├── _shared/                ← tokens.css, components.css, glyphs.js, shell.js
└── mockups/                ← 16 telas
```

## 16 Mockups

**Inbox**
- 16-inbox · fila de ingestão

**Home**
- 01-visao-geral · KPIs + sprint + Ω animado

**Finanças**
- 02-extrato · transações + saldo + breakdown
- 03-contas · contas + cartões + utilização
- 04-pagamentos · calendário + próximos 14d
- 05-projecoes · 3 cenários 5 anos + marcos

**Documentos**
- 06-busca-global · facetas + snippets com highlight
- 07-catalogacao · banco normalizado
- 08-completude · matriz tipo × mês + gaps
- 09-revisor · revisão de divergências (j/k/a)
- 10-validacao-arquivos · diff ETL ↔ Opus

**Análise**
- 11-categorias · árvore + treemap + regras
- 12-analise · sankey, comparativo, heatmap (3 abas)
- 15-irpf · pacote anual

**Metas**
- 13-metas · financeiras (donuts) + operacionais (gauges)

**Sistema**
- 14-skills-d7 · dashboard analítico

## Atalhos globais

| Tecla | Ação |
|---|---|
| `g h` | Visão Geral |
| `g i` | Inbox |
| `g v` | Validação |
| `g r` | Revisor |
| `g f` | IRPF |
| `g c` | Catalogação |
| `/`   | Busca |
| `?`   | Ajuda |
| `Esc` | Fechar overlay |

## Sistema visual

- Tema dark Dracula adaptado · `tokens.css`
- Mono (JetBrains Mono / ui-monospace) para tudo que é dado
- Sans (Inter) só para texto descritivo
- Estado D7: graduado/calibrando/regredido/bloqueado mapeia 1:1 em cor
- Espaçamento base 4px · raios 2/4/8/12

## Componentes principais

KPI cards · diff viewer · timeline · pills D7 · tabelas densas de txn · progress bars · gauges · donuts · treemap · sankey · heatmap calendário · matriz de cobertura.
