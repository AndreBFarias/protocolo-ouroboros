---
id: UX-V-2.5
titulo: Página Metas com 6 cards (donut + valor + barra + 3 colunas PRAZO/RITMO/FALTA)
status: concluída
prioridade: alta
data_criacao: 2026-05-07
concluida_em: 2026-05-07
commit: 1d518f3
fase: PARIDADE_VISUAL
depende_de: [UX-V-02]
co_executavel_com: [UX-V-2.4, UX-V-2.6, UX-V-2.17]
esforco_estimado_horas: 5
origem: docs/auditorias/AUDITORIA_PARIDADE_VISUAL_2026-05-07.md (página 13)
mockup: novo-mockup/mockups/13-metas.html
---

# Sprint UX-V-2.5 -- Metas paridade com mockup

## Contexto

Auditoria 2026-05-07 identificou divergência ALTA na página **Metas** vs `mockups/13-metas.html`:

- Mockup mostra **6 cards de meta** (Reserva, Viagem Japão, Entrada imóvel, Troca carro, Independência financeira, MBA) cada um com:
  - **Donut % no canto superior direito** (atingimento)
  - **Valor / Meta** em mono
  - **Barra de progresso** abaixo
  - **3 colunas** PRAZO / RITMO / FALTA
- Mockup tem seção lateral **METAS OPERACIONAIS · PIPELINE** (Cobertura D7, % validadas)

Dashboard atual mostra 3 cards simples sem donut + barra + 3 colunas. Sem seção operacional.

Esta sprint usa micro-componentes V-02 (`donut_inline_html` + `prazo_ritmo_falta_html` + `bar_uso_html`) já entregues.

## Página afetada

`src/dashboard/paginas/metas.py` apenas.

## Objetivo

1. Importar `donut_inline_html`, `prazo_ritmo_falta_html`, `bar_uso_html` de `componentes.ui`.
2. Renderizar cada meta financeira como card completo (donut + valor + barra + 3 colunas).
3. Adicionar seção METAS OPERACIONAIS abaixo (Cobertura D7, % validadas) com fallback graceful se dados ausentes.
4. Manter dados reais existentes do `dados['extrato']` ou `mappings/metas.yaml`.

## Validação ANTES (grep obrigatório)

```bash
wc -l src/dashboard/paginas/metas.py
grep -n "^def \|st.markdown\|donut\|barra" src/dashboard/paginas/metas.py | head -10

ls mappings/metas.yaml data/output/metas.json 2>/dev/null

.venv/bin/python -c "
from src.dashboard.componentes.ui import donut_inline_html, prazo_ritmo_falta_html, bar_uso_html
print('imports OK')
"
```

## Spec de implementação

Ver `sprint_ux_v_2_2_pagamentos.md` como referência de padrão (4 funções + CSS + integração no renderizar).

### Card de meta (esqueleto)

```python
def _card_meta_html(meta: dict) -> str:
    pct = (meta['valor_atual'] / meta['valor_total'] * 100) if meta['valor_total'] > 0 else 0
    donut = donut_inline_html(pct, tamanho=56)
    bar = bar_uso_html(meta['valor_atual'], meta['valor_total'])
    prf = prazo_ritmo_falta_html(meta['prazo'], meta['ritmo'], meta['falta'])
    return minificar(f'''
    <div class="meta-card">
      <div class="meta-card-head">
        <div class="meta-card-info">
          <h3 class="meta-card-titulo">{meta['nome']}</h3>
          <p class="meta-card-sub">{meta.get('descricao', '')}</p>
        </div>
        <div class="meta-card-donut">{donut}</div>
      </div>
      <div class="meta-card-valores">
        <span class="meta-valor-atual">R$ {meta['valor_atual']:,.2f}</span>
        <span class="meta-valor-total">/ R$ {meta['valor_total']:,.2f}</span>
      </div>
      {bar}
      {prf}
    </div>
    ''')
```

### Renderização

```python
def renderizar(dados, mes_selecionado, pessoa, ctx=None):
    # ... topbar + page_header existentes ...
    st.markdown(minificar(carregar_css_pagina("metas")), unsafe_allow_html=True)
    
    metas = _carregar_metas(dados)
    if not metas:
        st.markdown(callout_html("info", "Nenhuma meta configurada."), unsafe_allow_html=True)
        return
    
    st.markdown('<h2 class="metas-secao">METAS FINANCEIRAS</h2>', unsafe_allow_html=True)
    cols = st.columns(3)
    for i, m in enumerate(metas):
        with cols[i % 3]:
            st.markdown(_card_meta_html(m), unsafe_allow_html=True)
    
    st.markdown('<h2 class="metas-secao">METAS OPERACIONAIS · PIPELINE</h2>', unsafe_allow_html=True)
    op_metas = _carregar_metas_operacionais()
    cols_op = st.columns(2)
    for i, om in enumerate(op_metas):
        with cols_op[i % 2]:
            st.markdown(_card_meta_html(om), unsafe_allow_html=True)
```

### CSS dedicado em `src/dashboard/css/paginas/metas.css`

```css
/* Página Metas -- UX-V-2.5 */
.metas-secao {
    font-family: var(--ff-mono); font-size: 12px;
    text-transform: uppercase; letter-spacing: 0.10em;
    color: var(--text-muted);
    margin: var(--sp-5) 0 var(--sp-3);
}
.meta-card {
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: var(--r-md);
    padding: var(--sp-4);
    display: flex; flex-direction: column; gap: var(--sp-3);
    height: 100%;
}
.meta-card-head {
    display: flex; justify-content: space-between; align-items: flex-start;
    gap: var(--sp-3);
}
.meta-card-info { flex: 1; min-width: 0; }
.meta-card-titulo {
    font-family: var(--ff-mono); font-size: 14px; font-weight: 500;
    color: var(--text-primary); margin: 0 0 var(--sp-1);
}
.meta-card-sub {
    font-family: var(--ff-mono); font-size: 11px;
    color: var(--text-muted); margin: 0;
}
.meta-card-valores {
    display: flex; align-items: baseline; gap: var(--sp-2);
    font-variant-numeric: tabular-nums;
}
.meta-valor-atual {
    font-family: var(--ff-mono); font-size: 18px; font-weight: 500;
    color: var(--accent-purple);
}
.meta-valor-total {
    font-family: var(--ff-mono); font-size: 12px;
    color: var(--text-muted);
}
```

## Validação DEPOIS

```bash
test -f src/dashboard/css/paginas/metas.css
make lint && make smoke
.venv/bin/python -m pytest tests/test_*metas*.py -q | tail -3
```

## Proof-of-work runtime-real

Validação visual side-by-side em `cluster=Metas&tab=Metas` vs `mockups/13-metas.html`. Screenshot deve mostrar 3-6 cards de meta com donut + valor + barra + 3 colunas, e seção operacional abaixo.

## Critério de aceitação

1. Cards de meta financeira renderizando com donut + valor + barra + PRAZO/RITMO/FALTA.
2. Seção operacional com 1+ card.
3. CSS criado.
4. Lint OK + smoke 10/10 + cluster pytest verde.

## Não-objetivos

- NÃO criar componentes novos em ui.py (consumir os 3 da V-02).
- NÃO mexer em outras páginas.
- NÃO inventar metas.

## Referência

- Mockup: `novo-mockup/mockups/13-metas.html`.
- Pré-requisito: UX-V-02.
- VALIDATOR_BRIEF: `(a)/(b)/(k)/(u)`.

*"Meta visualizada é meta lembrada." -- princípio V-2.5*
