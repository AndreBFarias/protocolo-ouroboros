# ADR-19 — Dashboard interativo: clique leva ao fato, não à página

**Status:** PROPOSTO
**Data:** 2026-04-21

## Contexto

Auditoria 2026-04-21 e visão do Andre: "o dash inteiro tem que ser interativo". Hoje o dashboard é uma galeria de gráficos: bonito, mas inerte. Ver um ponto anômalo no gráfico de tendências não permite navegar até a transação. Ver "Natação R$ 101,60" não abre o boleto. Ver "Farmácia R$ 688" não lista os comprovantes.

## Decisão

**Todo elemento visual clicável do dashboard tem uma ação de drill-down bem definida, que leva a UM dos três destinos:**

1. **Aba Extrato filtrada** (destino padrão para dados agregados)
2. **Modal de detalhe da transação** (destino para ponto individual)
3. **Documento original** (destino quando há vínculo no grafo)

### Mapa canônico de cliques

| Origem | Ação ao clicar |
|---|---|
| Ponto em gráfico de tendência (Visão Geral, Projeções, Categorias) | Navega → Extrato filtrado pelo mês/categoria do ponto |
| Quadrado do treemap (Gastos por Categoria) | Extrato filtrado pela categoria |
| Linha da tabela "Top 10 Categorias" | Extrato filtrado pela categoria |
| Barra de bar chart (Top Fornecedores, Top Itens) | Extrato filtrado pelo fornecedor |
| Nó do grafo (fornecedor/documento/item) | Extrato filtrado por aquela entidade |
| Aresta do grafo | Modal com preview das transações que compõem a aresta |
| Linha do Extrato | Modal de detalhe com: categoria, classificação, tag IRPF, documento vinculado (preview), botão "Upload comprovante" |
| Ícone de documento na Catalogação | Abre preview do PDF/JPG em modal |
| Card KPI "Maior gasto" | Extrato filtrado pela categoria do maior gasto |

### Mecânica técnica

Streamlit não tem `onClick` nativo em Plotly, mas suporta dois caminhos:

1. **`st.plotly_events()`** (via `streamlit-plotly-events`): retorna dicionário do ponto clicado; usamos `st.session_state["filtro_dest"]` + `st.rerun()` para atualizar aba Extrato.
2. **`st.query_params`** (nativo, estável): setamos `?filtro=fornecedor:Neoenergia` ao clicar, recarregamos página; aba Extrato lê query params e filtra.

Escolha: **`st.query_params`** como padrão (nativo, zero dependência extra, compartilhável via URL). `st.plotly_events` só se necessário para gráficos onde query param não cabe.

### Modal de detalhe

Streamlit 1.31+ tem `st.dialog`. Modal da transação contém:

- Cabeçalho: data, valor, local, categoria, classificação, tag IRPF
- Seção "Documento vinculado": preview iframe do PDF ou imagem, link pro original em `data/raw/originais/`
- Se vazio: "Sem comprovante — jogue na inbox: `~/Controle de Bordo/Inbox/`"
- Seção "Transações relacionadas": outras com mesmo fornecedor/categoria no mês
- Botão "Abrir nota no Obsidian" (chama `obsidian://` URL scheme)

## Consequências

### Positivas
- Dashboard vira navegação real, não slide.
- Toda pergunta "o que gerou esse número?" vira 1 clique.
- URL compartilhável com filtros (debugging + handoff).

### Custos
- Sprint 73 reescreve integração de 4 gráficos principais.
- Streamlit-plotly-events ou custom solution.
- Testar em 3 viewports (depois da Sprint 62 que já estabeleceu responsividade).

## Sprints desbloqueadas

- **Sprint 73** — Interatividade do dashboard (clique → filtro)
- **Sprint 74** — Modal de detalhe da transação (com documento vinculado)
- **Sprint 78** — Grafo clicável (nó → extrato filtrado)

---

*"Gráfico bonito que não responde é museu." — princípio"*
