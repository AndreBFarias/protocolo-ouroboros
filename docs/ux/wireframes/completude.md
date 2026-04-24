# Wireframe — Completude (pós-92a)

**Contexto:** hoje o heatmap ocupa 100% da área visível com vermelho saturado,
desestimulando o retorno. O diagnóstico "precisamos de comprovantes" é real e
útil, mas precisa de dosagem visual — choque sem caminho de saída vira
desânimo.

**Viewport alvo:** 1600×1000.

---

## Layout — 12 colunas, 3 zonas

```
+-------------------------------------------------------------------------+
| SIDEBAR                     | AREA PRINCIPAL                            |
|                             |                                           |
|                             | [HERO] 13 — Completude documental         |
|                             | "Gap analysis por categoria e mês."       |
|                             |                                           |
|                             | ========== ZONA A — CONTROLES =========   |
|                             | [x] Mostrar só categorias com >=2 tx      |
|                             | [x] Ano-base: 2025 (default) [<] [>]      |
|                             |     ou [toggle] "Ver histórico completo"  |
|                             |                                           |
|                             | ========== ZONA B — HEATMAP =========     |
|                             | (cores suavizadas: laranja médio p/ 0%,   |
|                             |  amarelo p/ 50%, verde-claro p/ 100%)     |
|                             |                                           |
|                             |      | Jan | Fev | Mar | Abr | Mai | ... | |
|                             | Água |  0  |  0  |  0  | 50% |  0  |     | |
|                             | Saúd | 30% |  0  | 80% |100% |  0  |     | |
|                             | Nat  | --  | --  | 100%| 100%| --  |     | |
|                             | Imp  | 100%| 100%| 100%| 100%| 100%|     | |
|                             | Farm |  0  |  0  | 20% | 40% |  0  |     | |
|                             |                                           |
|                             | Clique numa célula para ver transações    |
|                             |                                           |
|                             | ========== ZONA C — ALERTAS ==========    |
|                             | [>] 3 críticos (zero cobertura recorrente)|
|                             |     - Farmácia: 8 meses sem comprovante   |
|                             |     - Água: 12 meses sem comprovante      |
|                             |     - Energia: 5 meses sem comprovante    |
|                             |                                           |
|                             | [>] 7 atenção (valor alto, faltante)      |
|                             | [>] 4 info (baixa prioridade)             |
|                             |                                           |
|                             | [ Exportar sem comprovante (CSV) ]        |
|                             |                                           |
|                             | ========== ZONA D — DETALHE =========     |
|                             | Mês: [2026-04 v]   Categoria: [Farmácia v]|
|                             | 2 de 2 transações sem comprovante         |
|                             | (tabela com data, local, valor)           |
+-------------------------------------------------------------------------+
```

---

## Mudanças vs atual (aba_13_completude.png)

- **(+) Zona A — Controles:** toggle "Mostrar só categorias com >=2 tx" reduz
  ruído; seletor de ano ou toggle "histórico completo" evita mostrar 7 anos
  empilhados em viewport de 1000px.
- **(+) Escala de cor suavizada:**
  - `0%` = laranja médio `#FFB86C` (antes vermelho saturado `#FF5555`)
  - `50%` = amarelo `#F1FA8C`
  - `100%` = verde claro `#50FA7B`
  - Gradiente = legível sem ser agressivo.
- **(+) Alertas em 3 grupos colapsáveis** ("crítico / atenção / info") em vez
  de lista única. Default: "crítico" expandido, demais colapsados.
- **(+) Categorias fora do range visíveis como "--"** (em vez de vazio) —
  previne interpretação errada "não havia transação".
- **(=) Export CSV** mantido.
- **(=) Detalhe mês × categoria** mantido.

---

## Estados

### Estado pós-backfill (cobertura real > 50%)

Heatmap fica majoritariamente verde-amarelo. Alertas caem para 0-2 entradas.
Callout de sucesso no topo: "Boa cobertura documental — mantenha assim."

### Estado sem categorias de tracking

Hoje exibe warning explicativo (OK, manter).

### Estado de grafo ausente

`carregar_ids_com_doc` retorna set vazio → resumo mostra 0% em tudo (correto);
adicionar banner "Grafo SQLite não populado — rode `make process` para
calcular cobertura real." Caso contrário usuário pensa que é bug.

---

## Psicologia do design

O problema de Completude hoje é **desânimo por design**. Proposta:

- Tela inicial default: **apenas ano atual + toggle "histórico"**. Reduz de
  7 anos × 9 categorias = 63 células para ~12×9 = ~108 → ~9×9 = ~81 células
  legíveis, porção menor vermelha.
- Paleta laranja em vez de vermelho reduz percepção de "crise total".
- Separação de alertas em 3 grupos permite o usuário **sentir progresso**
  quando ele resolve os "críticos" primeiro.

---

## Tokens usados

- `hero_titulo_html("13", "Completude documental", "...")`
- `callout_html("warning", "Farmácia: 8 meses sem comprovante...")` — helper novo
- `icon_html("alert-triangle", 16, CORES["alerta"])` em alertas
- Cores do heatmap alteradas (ver §Mudanças)
