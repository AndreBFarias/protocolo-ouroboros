# Wireframe — Grafo Visual + Obsidian (pós-92a)

**Contexto:** aba com o pior UX atual (ver §2.12 do audit). Labels hash,
acentuação quebrada, layout amontoado. Esta é a página onde o supervisor Claude
Code deveria ver "o grafo financeiro do casal" como uma teia conectada — hoje
parece um amontoado técnico.

**Viewport alvo:** 1600×1000.

---

## Layout — 12 colunas, full-page grafo

```
+-------------------------------------------------------------------------+
| SIDEBAR                     | AREA PRINCIPAL                            |
|                             |                                           |
|                             | [HERO] 12 — Grafo visual + Obsidian       |
|                             | "Subgrafo interativo. Clique num nó."     |
|                             |                                           |
|                             | === ZONA A — GRAFO FULL-PAGE ===========  |
|                             | +----------------------------+-----------+|
|                             | |                            | Filtros   ||
|                             | |       (grafo pyvis)        |           ||
|                             | |                            | Tipos:    ||
|                             | |      o-- Neoenergia        | [x] forn. ||
|                             | |      |                     | [x] doc.  ||
|                             | |    MESES 2026              | [x] categ.||
|                             | |      |                     | [x] tx.   ||
|                             | |    o-- Boleto NAT SESC    | [x] item  ||
|                             | |      |                     |           ||
|                             | |  o-- 2026-03-19 R$ 104    | Órfãos:   ||
|                             | |   (Transação, label legível)| [ ]       ||
|                             | |                            |           ||
|                             | |  (distribuição força-direcionada,      ||
|                             | |   nós ocupam tela inteira, edges       ||
|                             | |   com labels minimais, não repetidos)  ||
|                             | +----------------------------+-----------+|
|                             | Legenda:                                  |
|                             | [o] transação  [o] documento [o] fornec. |
|                             | [o] categoria  [o] item [o] período      |
|                             |                                           |
|                             | === ZONA B — SUBGRAFO 1-HOP =========     |
|                             | Fornecedor: [Neoenergia                v] |
|                             | (scatter plotly com 1-hop vizinhos)       |
|                             |                                           |
|                             | === ZONA C — OBSIDIAN MOC ===========     |
|                             | [MOC 2026-04.md (baixar)]                 |
|                             | +--- preview do markdown ---+             |
|                             | | ## Pessoal/Casal/Financeiro|             |
|                             | | ...                        |             |
|                             | +----------------------------+             |
|                             |                                           |
|                             | === ZONA D — FLUXO ============            |
|                             | Receita por fonte | Despesa por cat | Top |
|                             | (3 bar charts lado a lado — OK hoje)      |
+-------------------------------------------------------------------------+
```

---

## Mudanças vs atual (aba_12_grafo_obsidian.png)

### CRÍTICO — correções de correspondência com mundo real (H2)

- **Labels dos nós `transacao` devem ser humanos.** Hoje mostram hashes hex.
  Proposta: `<data> · R$ <valor> · <fornecedor truncado 20ch>`, ex:
  `2026-03-19 · R$ 103,93 · SESC`. O `nome_canonico` de transação permanece
  sintético (chave do grafo) mas o label exibido no pyvis vira humano.
- **Legenda com acentos:** `"transação"` não `"transacao"`, `"período"` não
  `"periodo"`. <!-- noqa: accent (exemplo textual de bug a corrigir) --> CRÍTICO — viola CLAUDE.md regra #1.
- **"contraparte" label de edge:** aparecer UMA vez por tipo de aresta (como
  badge de legenda), não uma vez por edge. pyvis suporta `edge.label = ""` +
  legenda separada.

### Estrutural — layout

- **Força-direcionada (barnes-hut) em vez de hierárquico.** A configuração
  atual amontoa nós à esquerda. `options = {physics: {barnesHut: {gravitationalConstant: -8000, springConstant: 0.04}}}`.
- **Viewport ocupa toda a coluna principal** (12 cols - 3 para filtros = 9
  cols para grafo). Hoje parece ter ~6 cols.

### Secundário — UX dos filtros

- **Chips de tipos com toggle visual** em vez de multiselect Streamlit padrão
  (que força "x" clicável). Mais fluido: clica no chip, ativa/desativa.
- **Legenda por tipo** abaixo do grafo (em vez de lateral) — viewport é mais
  largo que alto.
- **Limite de nós:** slider 100-2000, default 500. Hoje OK.

---

## Estados

### Estado grafo vazio

Hoje exibe warning "Grafo SQLite não encontrado" (OK, manter).

### Estado nenhum nó visível após filtros

Hoje exibe info "Nenhum nó para os filtros atuais..." (OK, manter).

### Estado muitos nós (>2000)

Proposta: quando `limite` do slider em 2000 e `len(nodes) > limite`, mostrar
caption amarelo "Mostrando 2000 de N nós — amplie filtro para ver mais".

---

## Anti-patterns que NÃO adotar

- **Labels sempre visíveis em 500+ nós** → texto sobreposto ilegível. Hoje
  ocorre. Proposta: labels aparecem em hover + para nós grau > 5 sempre
  visíveis.
- **Edge labels sempre visíveis** → ruído. Labels de edge ficam em hover.
- **Zoom/pan desabilitados** → usuário perde controle. Manter interatividade
  nativa do pyvis.

---

## Dependência técnica — pyvis

Sprint 78 resolveu o setup básico (instalação, graceful degradation). Esta
Sprint 92a precisa:

- Investigar por que `_label_humano` fallback para "node-{id}" está
  sendo acionado para nodes `transacao`. Provável: `nome_canonico` sintético
  (`hash_transacao_canonico`) passa pelo fallback errado.
- Garantir que `label_humano(node_transacao)` receba data+valor+fornecedor
  direto do `metadata` do grafo (ADR-20 já persiste esses campos).

---

## Tokens usados

- `hero_titulo_html("12", "Grafo visual + Obsidian", "...")`
- `chip_html(tipo, cor=COR_POR_TIPO[tipo], clicavel=True)` — helper novo 92c
- `icon_html("zoom-in", 16, CORES["destaque"])` em label "Clique num nó"
- `COR_POR_TIPO` com acentos corrigidos (grafo_pyvis.py)
