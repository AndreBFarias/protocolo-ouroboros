# Wireframe — Extrato (pós-92a/b)

**Contexto:** Extrato atual funciona bem mas tem 3 falhas identificadas na
auditoria: sem paginação, sem hero, sem legenda inline da coluna "Doc?".

**Viewport alvo:** 1600×1000.

---

## Layout — 12 colunas

```
+-------------------------------------------------------------------------+
| SIDEBAR                     | AREA PRINCIPAL                            |
|                             |                                           |
| (igual ao wireframe Hoje)   | [HERO] 03 — Extrato                       |
|                             | "Transações do período filtrado."         |
|                             |                                           |
|                             | +-- FILTROS ATIVOS (breadcrumb) --+       |
|                             | | categoria: Farmácia [x]          |       |
|                             | | (chips removíveis com X)         |       |
|                             | +----------------------------------+       |
|                             |                                           |
|                             | [lupa] Buscar por local ________________  |
|                             |                                           |
|                             | [>] Filtros avançados                     |
|                             |                                           |
|                             | Mostrando 1-25 de 78   [< 1 2 3 4 >]      |
|                             |                                           |
|                             | +---+----+------+---------+--------+----+ |
|                             | |Dia|Valor|Local|Categoria|Class   |Doc?| |
|                             | +---+----+------+---------+--------+----+ |
|                             | |01 |2,38|IOF  |Juros    |Obrig.  |[!] | |
|                             | |01 |1,36|IOF  |Juros    |Obrig.  |[!] | |
|                             | |01 |53,2|Juros|Juros    |Obrig.  |[v] | |
|                             | |...|    |     |         |        |    | |
|                             | +---+----+------+---------+--------+----+ |
|                             |                                           |
|                             | Legenda: [v] vinculado [!] faltante [-] na|
|                             |                                           |
|                             | [Exportar CSV]                            |
|                             |                                           |
|                             | --- Inspecionar transação ---             |
|                             | [Escolha: 01/04 R$ 2,38 IOF...  v] [Ver] |
+-------------------------------------------------------------------------+
```

---

## Mudanças vs atual (aba_03_extrato.png)

- **(+) Hero numerado** ("03 — Extrato") coerente com demais abas.
- **(+) Paginação nativa** do `st.dataframe` — 25 linhas por página por default.
  Header "Mostrando 1-25 de 78" fora do dataframe para visibilidade.
- **(+) Input de busca com ícone lupa** à esquerda (Feather SVG inline).
- **(+) Legenda da coluna "Doc?"** logo abaixo da tabela — explicita `[v]`
  (check-circle verde) e `[!]` (alert-triangle laranja).
- **(=) Breadcrumb de drill-down** já existe (`_renderizar_breadcrumb`) — apenas
  migrar para helper `breadcrumb_drilldown_html` da Sprint 92c.
- **(=) Filtros avançados** expander permanece — keys continuam `avancado_*`
  (não colide com drill-down `filtro_*`).
- **(=) Inspecionar transação** permanece — selectbox + botão são compromisso
  Streamlit (documentado em R74-2).
- **(-)** Texto "78 transações encontradas" em violeta destacado — substituído
  pelo header de paginação "Mostrando X de Y".

---

## Estados

### Estado vazio após filtro

```
+-------------------------------------------+
| Nenhuma transação com os filtros atuais.  |
| Experimente:                              |
| - Remover filtros de drill-down (chips X) |
| - Desselecionar categoria em avançados    |
| - Ampliar granularidade (Mês > Ano)       |
+-------------------------------------------+
```

### Estado com muitos filtros ativos

Se `len(filtros) > 3`, breadcrumb quebra em 2 linhas com scroll horizontal
(overflow-x: auto) em vez de expandir verticalmente demais.

---

## Performance

Extrato com >10k linhas precisa evitar `df.apply(_marcar_tracking)` em toda a
view. Propor: aplicar em páginas lazy (apenas linhas visíveis). Escopo fora de
92 — anotar para Sprint 92d futura se virar gargalo.

---

## Tokens usados

- `hero_titulo_html("03", "Extrato", "...")`
- `icon_html("search", 16)` no input
- `icon_html("check-circle", 16, CORES["positivo"])` para [v]
- `icon_html("alert-triangle", 16, CORES["alerta"])` para [!]
- `breadcrumb_drilldown_html(filtros)` (helper novo 92c)
