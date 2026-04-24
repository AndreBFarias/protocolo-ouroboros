## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 92a
  title: "UX fixes cirúrgicos -- 11 itens priorizados da Auditoria 92"
  depends_on:
    - sprint_id: 92
      artifact: "docs/ux/audit_2026-04-23.md"
  touches:
    - path: src/dashboard/componentes/grafo_pyvis.py
      reason: "item 1 P0 — labels humanos em nodes transacao + acentuar legend"
    - path: src/graph/queries.py
      reason: "item 1 P0 — label_humano especializado para transacao"
    - path: src/dashboard/paginas/categorias.py
      reason: "item 2 P0 — contraste do treemap por luminosidade"
    - path: src/dashboard/paginas/completude.py
      reason: "item 3 P0 — heatmap menos agressivo + toggle"
    - path: src/dashboard/paginas/pagamentos.py
      reason: "item 4 P0 — rename columns + strftime em data"
    - path: src/dashboard/paginas/visao_geral.py
      reason: "item 6 P1 — hero_titulo_html"
    - path: src/dashboard/paginas/extrato.py
      reason: "item 6 + item 8 — hero + paginação"
    - path: src/dashboard/paginas/contas.py
      reason: "item 6 — hero"
    - path: src/dashboard/paginas/projecoes.py
      reason: "item 6 + item 10 — hero + metric colorido"
    - path: src/dashboard/paginas/metas.py
      reason: "item 6 + item 9 — hero + progress inline"
    - path: src/dashboard/paginas/analise_avancada.py
      reason: "item 6 + item 12 — hero + hovertemplate Sankey"
    - path: src/dashboard/paginas/irpf.py
      reason: "item 6 — hero"
    - path: src/dashboard/paginas/catalogacao.py
      reason: "item 11 — rotulos_tipo_documento estender"
    - path: tests/test_dashboard_grafo.py
      reason: "teste regressivo label humano de transacao"
    - path: tests/test_dashboard_completude.py
      reason: "teste regressivo toggle de filtro"
  forbidden:
    - "Alterar estrutura de abas (Sprint 92b resolve)"
    - "Introduzir CSS vars globais (Sprint 92c resolve)"
    - "Criar callout_html/progress_inline_html genéricos (Sprint 92c)"
  tests:
    - cmd: ".venv/bin/pytest tests/ -q"
    - cmd: "make lint"
    - cmd: "make smoke"
  acceptance_criteria:
    - "Labels de nodes transacao no pyvis mostram '<data> R$ <valor> <fornecedor>' em vez de hash"
    - "Legenda do grafo usa 'transação' e 'período' com acento correto"
    - "Treemap de categorias usa textfont.color preto quando luminosidade do fundo > 0.6, branco caso contrário"
    - "Completude: heatmap usa paleta laranja-amarelo-verde (não vermelho saturado); toggle 'Mostrar só categorias com >=2 tx' presente"
    - "Pagamentos: tabela de boletos usa 'Data' 'Fornecedor' 'Valor' 'Vencimento' 'Status' 'Banco'; coluna data em formato 'YYYY-MM-DD'"
    - "9 abas (todas exceto Catalogação, Busca, Grafo) ganham hero_titulo_html"
    - "Extrato: paginação 25 linhas/página + header 'Mostrando X-Y de Z'"
    - "Metas: progress bar inline dentro do card"
    - "Projeções: st.metric colorido por sinal (delta_color ou custom)"
    - "Catalogação: ROTULOS_TIPO_DOCUMENTO inclui irpf_parcela, das_mei, comprovante_cpf"
    - "Análise: Sankey com hovertemplate 'R$ <valor>' nos links"
    - "Screenshots ANTES/DEPOIS em docs/screenshots/sprint_92a_2026-xx-xx/"
    - "make lint exit 0 + pytest >=1220 passed + smoke 8/8"
```

---

# Sprint 92a — fixes cirúrgicos UX

**Status:** BACKLOG (criada pela Sprint 92 audit)
**Prioridade:** P0 (4 blockers) + P1 (4 majors) + P2 (3 minors) = 11 itens
**Dependências:** Sprint 92 concluída (audit aprovado pelo supervisor)
**Origem:** `docs/ux/audit_2026-04-23.md` §5 itens 1-4, 6-12

## Itens por ordem de execução

### P0 — blockers (4 itens, ~6h)

1. **Labels humanos em nodes `transacao` no grafo** (~2h, touches `grafo_pyvis.py` + `queries.py` + teste)
   - Em `src/graph/queries.py::label_humano(node)`: quando `node.tipo == "transacao"`, montar label como `<data> R$ <valor> <local curto>` a partir de `node.metadata`.
   - Em `src/dashboard/componentes/grafo_pyvis.py`: ajustar `COR_POR_TIPO` para chaves acentuadas: `"transação"`, `"período"`.
   - **MAS:** chave do dict do grafo permanece `"transacao"` (N-para-N com schema). A acentuação é APENAS no label exibido ao usuário.
   - Teste: `test_label_humano_transacao_usa_data_valor_local` assert contra metadata sintético.

2. **Contraste do treemap** (~1h, touches `categorias.py`)
   - Função auxiliar `_cor_texto_por_fundo(hex) -> str` que calcula luminância relativa (WCAG) e retorna `#000` ou `#fff`.
   - Em `_treemap_categorias`, adicionar `textfont.color` por leaf com base em cor da classificação.
   - Teste unitário da função auxiliar com 3 fundos conhecidos.

3. **Completude menos agressivo** (~2h, touches `completude.py` + teste)
   - Mudar colorscale de `[negativo, alerta, positivo]` para `[alerta, info, positivo]` (laranja, amarelo, verde).
   - Adicionar `st.checkbox("Mostrar só categorias com >=2 transações", value=True)` antes do heatmap; filtrar `categorias_obrigatorias` antes de passar a `calcular_completude`.
   - Teste: `test_completude_toggle_reduz_categorias` assert com fixture.

4. **Rename Pagamentos** (~30min, touches `pagamentos.py`)
   - Em `_renderizar_boletos`, aplicar `boletos_fmt.rename(columns={"data": "Data", "fornecedor": "Fornecedor", "valor": "Valor", "vencimento": "Vencimento", "status": "Status", "banco_origem": "Banco"})`.
   - Antes do rename, converter coluna `data` para string `YYYY-MM-DD` (se for datetime) — mesmo tratamento que já é feito em `vencimento`.
   - Teste unitário simula DataFrame com ambos os campos datetime e valida strings.

### P1 — majors (4 itens, ~6h)

6. **`hero_titulo_html` em 9 páginas** (~3h)
   - Touches: `visao_geral.py`, `categorias.py`, `extrato.py`, `contas.py`, `pagamentos.py`, `projecoes.py`, `metas.py`, `analise_avancada.py`, `irpf.py`, `completude.py`.
   - Substituir `st.markdown("<p style=...>Completude Documental</p>")` por `st.markdown(hero_titulo_html("NN", "Título", "descrição em 1 linha"), unsafe_allow_html=True)`.
   - Numeração: 01-13 para as 13 abas (nem tudo numera hoje).

8. **Paginação Extrato** (~1h, touches `extrato.py`)
   - `st.dataframe` suporta `pagination=True` desde versão 1.31 — verificar versão no pyproject e usar config nativa.
   - Header "Mostrando X-Y de Z" acima da tabela, calculado via `len(df)` e `page_size=25`.
   - Teste já existe em `tests/test_dashboard_extrato.py` — apenas não regredir.

9. **Progress bar inline Metas** (~1h, touches `metas.py`)
   - Em `_card_meta`, em vez de `st.progress(pct)` após o card, embutir `<div style='height:4px; background: texto_sec; border-radius:2px;'><div style='width:{pct*100}%; height:100%; background: {cor}; border-radius:2px;'></div></div>` DENTRO do HTML do card.
   - Remover a chamada subsequente a `st.progress`.

10. **`st.metric` colorido Projeções** (~1h, touches `projecoes.py`)
    - Em `_renderizar_ritmos`, substituir `col.metric("Ritmo X", valor)` por HTML custom via `card_html` quando valor é numérico e conhecido, com cor por sinal (`positivo` se >0, `negativo` se <0, `texto_sec` se None).

### P2 — minors (3 itens, ~1h)

11. **Estender `ROTULOS_TIPO_DOCUMENTO`** (~15min, touches `catalogacao.py`)
    - Adicionar 3 chaves: `"irpf_parcela": "Parcela IRPF"`, `"das_mei": "DAS MEI"`, `"comprovante_cpf": "Comprovante CPF"`.

12. **Hovertemplate Sankey** (~30min, touches `analise_avancada.py`)
    - Em `_preparar_dados_sankey`, adicionar `hovertemplate="%{source.label} → %{target.label}<br>R$ %{value:,.2f}<extra></extra>"`.

13. **Legenda Doc? no Extrato** (~15min, touches `extrato.py`)
    - Abaixo da tabela: `st.caption("Legenda: 'OK' = documento vinculado no grafo; '!' = categoria obrigatória sem comprovante; vazio = sem tracking.")`.

## Proof-of-work

- `.venv/bin/pytest tests/ -q` >=1220 passed, zero regressão.
- `make lint` exit 0.
- `make smoke` 23/0 + 8/8.
- Screenshots ANTES/DEPOIS em `docs/screenshots/sprint_92a_2026-xx-xx/` para cada item P0 (4 screenshots mínimo).

## Armadilhas

- **N-para-N com schema do grafo:** chaves do dict `{"tipo": "transacao"}` NÃO mudam. Apenas o LABEL exibido ao usuário no pyvis recebe acento (`"transação"`). Se alguém "corrigir" a chave, quebra 500 linhas de código do grafo.
- **Paginação nativa do `st.dataframe` precisa Streamlit >= 1.31** — já é requisito via pyproject.toml (Sprint 73). Se CI aponta versão menor, dropar para solução manual.
- **Commit atômico por item.** Mesclar múltiplos itens num único commit dificulta bisect quando regressão aparece.

---

*"Todo polish cirúrgico é um voto de confiança no produto." -- princípio de iteração rápida*
