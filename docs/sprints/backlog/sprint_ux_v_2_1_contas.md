---
id: UX-V-2.1
titulo: Página Contas com sparkline + barras de uso + separação Contas/Cartões
status: backlog
prioridade: alta
data_criacao: 2026-05-07
fase: PARIDADE_VISUAL
depende_de: [UX-V-02]
co_executavel_com: [UX-V-2.2, UX-V-2.3, UX-V-2.7]
esforco_estimado_horas: 4
origem: docs/auditorias/AUDITORIA_PARIDADE_VISUAL_2026-05-07.md (página 03)
mockup: novo-mockup/mockups/03-contas.html
---

# Sprint UX-V-2.1 — Página Contas paridade com mockup

## Contexto

Auditoria 2026-05-07 identificou divergência ALTA na página **Contas** vs `mockups/03-contas.html`:

- Mockup tem **sparkline** em cada card de conta corrente (3 cartões)
- Mockup tem **barra de uso %** em cartões de crédito (Nubank/C6 com 36%/24% usado)
- Mockup separa **CONTAS CORRENTES & INVESTIMENTO** vs **CARTÕES DE CRÉDITO** em 2 blocos distintos
- Mockup tem **ícone+sigla do banco** no canto superior esquerdo de cada card
- Mockup tem **dados meta estruturados** ("último OFX/sha8/sincronizado/txns 30d")

Dashboard atual mistura tudo em "CONTAS CORRENTES & INVESTIMENTO" sem sparkline e sem barras de uso.

Esta sprint usa os micro-componentes da UX-V-02 (`sparkline_html` + `bar_uso_html`) já entregues.

## Página afetada

`src/dashboard/paginas/contas.py` apenas.

## Objetivo

1. Importar `sparkline_html` e `bar_uso_html` de `componentes.ui`.
2. Separar visualmente em 2 seções: **CONTAS CORRENTES & INVESTIMENTO** e **CARTÕES DE CRÉDITO**.
3. Cada card de conta corrente tem sparkline (~80x24px) com saldo dos últimos 30 dias.
4. Cada cartão de crédito tem barra de uso (limite vs usado) com cor semântica (verde<60%, amarelo 60-90%, vermelho >90%).
5. Manter dados reais existentes; adicionar visualizações por cima.

## Validação ANTES (grep obrigatório — padrão `(k)`)

```bash
# Estrutura atual da página
wc -l src/dashboard/paginas/contas.py
grep -n "^def \|st\.markdown" src/dashboard/paginas/contas.py | head -10

# Dados disponíveis: extrato tem coluna 'data', 'valor', 'banco_origem'?
grep -n "banco_origem\|saldo_diario\|cartao\|limite" src/dashboard/dados.py | head -10

# Pré-requisito: micro-componentes V-02
.venv/bin/python -c "
from src.dashboard.componentes.ui import sparkline_html, bar_uso_html
print(sparkline_html([1.0, 2.0, 3.0, 2.5])[:60])
print(bar_uso_html(36, 100, label='36% usado')[:60])
"
# Esperado: HTML não vazio
```

Se contas.py não tem dados de cartão/limite, é achado-bloqueio — registrar e parar.

## Spec de implementação

### 1. Imports adicionar em `contas.py`

```python
from src.dashboard.componentes.ui import (
    callout_html,
    carregar_css_pagina,
    sparkline_html,
    bar_uso_html,
)
```

### 2. Função auxiliar para sparkline de saldo

```python
def _sparkline_saldo_30d(df_extrato: pd.DataFrame, banco: str) -> str:
    """Gera sparkline com saldo acumulado dos últimos 30 dias para um banco.
    
    Calcula saldo cumulativo agrupado por dia, últimos 30 dias.
    Retorna ``""`` se não há dados suficientes (ADR-10 graceful).
    """
    df_banco = df_extrato[df_extrato['banco_origem'] == banco].copy()
    if df_banco.empty or len(df_banco) < 2:
        return ""
    df_banco['data'] = pd.to_datetime(df_banco['data'])
    df_banco = df_banco.sort_values('data')
    saldo_diario = df_banco.groupby(df_banco['data'].dt.date)['valor'].sum().cumsum()
    if len(saldo_diario) < 2:
        return ""
    valores = saldo_diario.tail(30).tolist()
    return sparkline_html(valores, largura=120, altura=28)
```

### 3. Reestruturar renderização

```python
def renderizar(dados, mes_selecionado, pessoa, ctx=None):
    # ... topbar_actions, page_header existentes ...
    
    df = dados['extrato']
    # ... filtros existentes ...
    
    # Separar contas correntes vs cartões
    bancos_correntes = ['Itau', 'Santander', 'Bradesco', 'Inter', 'C6']  # heurística
    bancos_cartoes = ['Nubank', 'C6 Cartao']  # heurística
    
    # === BLOCO CONTAS CORRENTES ===
    st.markdown(
        '<h2 class="contas-secao-titulo">CONTAS CORRENTES &amp; INVESTIMENTO</h2>',
        unsafe_allow_html=True,
    )
    cols = st.columns(3)
    for i, banco in enumerate(bancos_correntes):
        df_banco = df[df['banco_origem'] == banco]
        if df_banco.empty:
            continue
        saldo = df_banco['valor'].sum()
        sparkline = _sparkline_saldo_30d(df, banco)
        with cols[i % 3]:
            st.markdown(
                minificar(f"""
                <div class="card conta-card">
                  <div class="conta-head">
                    <span class="conta-sigla">{banco[:2].upper()}</span>
                    <span class="conta-nome">{banco}</span>
                  </div>
                  <div class="conta-saldo">{formatar_moeda(saldo)}</div>
                  <div class="conta-sparkline">{sparkline}</div>
                  <div class="conta-meta">
                    <span>{len(df_banco)} txns 30d</span>
                  </div>
                </div>
                """),
                unsafe_allow_html=True,
            )
    
    # === BLOCO CARTÕES DE CRÉDITO ===
    st.markdown(
        '<h2 class="contas-secao-titulo">CARTÕES DE CRÉDITO</h2>',
        unsafe_allow_html=True,
    )
    cols_cartoes = st.columns(2)
    for i, banco in enumerate(bancos_cartoes):
        df_banco = df[df['banco_origem'] == banco]
        if df_banco.empty:
            continue
        usado = abs(df_banco[df_banco['valor'] < 0]['valor'].sum())
        # Limite: vir de mappings/contas_casal.yaml ou hardcoded fallback
        limites = {'Nubank': 18000, 'C6 Cartao': 12000}
        limite = limites.get(banco, 10000)
        bar = bar_uso_html(usado=usado, total=limite, label=f"{(usado/limite)*100:.0f}% usado")
        with cols_cartoes[i % 2]:
            st.markdown(
                minificar(f"""
                <div class="card cartao-card">
                  <div class="cartao-head">
                    <span class="cartao-sigla">{banco[:2].upper()}</span>
                    <span class="cartao-nome">{banco}</span>
                  </div>
                  <div class="cartao-fatura">FATURA: {formatar_moeda(usado)}</div>
                  {bar}
                  <div class="cartao-meta">limite: {formatar_moeda(limite)}</div>
                </div>
                """),
                unsafe_allow_html=True,
            )
```

### 4. CSS dedicado em `src/dashboard/css/paginas/contas.css`

Adicionar (criar se não existir):

```css
/* Página Contas — UX-V-2.1 paridade com mockup 03-contas.html */

.contas-secao-titulo {
    font-family: var(--ff-mono);
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.10em;
    color: var(--text-muted);
    margin: var(--sp-5) 0 var(--sp-3);
}

.conta-card,
.cartao-card {
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: var(--r-md);
    padding: var(--sp-4);
    display: flex;
    flex-direction: column;
    gap: var(--sp-2);
    height: 100%;
}

.conta-head, .cartao-head {
    display: flex;
    align-items: center;
    gap: var(--sp-2);
}

.conta-sigla, .cartao-sigla {
    width: 32px; height: 32px;
    display: grid; place-items: center;
    background: var(--accent-purple);
    color: var(--text-inverse);
    border-radius: var(--r-sm);
    font-family: var(--ff-mono);
    font-weight: 600;
    font-size: 12px;
}

.conta-nome, .cartao-nome {
    font-family: var(--ff-mono);
    font-size: 13px;
    color: var(--text-primary);
    font-weight: 500;
}

.conta-saldo, .cartao-fatura {
    font-family: var(--ff-mono);
    font-size: 24px;
    font-weight: 500;
    color: var(--text-primary);
    font-variant-numeric: tabular-nums;
}

.cartao-fatura {
    color: var(--accent-orange);
    font-size: 18px;
}

.conta-sparkline {
    margin-top: var(--sp-2);
}

.conta-meta, .cartao-meta {
    font-family: var(--ff-mono);
    font-size: 11px;
    color: var(--text-muted);
}
```

E carregar via `st.markdown(minificar(carregar_css_pagina("contas")), unsafe_allow_html=True)` no início da `renderizar`.

## Validação DEPOIS

```bash
# Imports OK
grep -E "sparkline_html|bar_uso_html" src/dashboard/paginas/contas.py | head -5

# CSS criado
test -f src/dashboard/css/paginas/contas.css && wc -l src/dashboard/css/paginas/contas.css

# Lint, smoke, cluster pytest
make lint
make smoke
.venv/bin/python -m pytest tests/test_dashboard_contas*.py -q | tail -3
```

## Proof-of-work runtime-real

```bash
# Restart dashboard
pkill -f "streamlit run" 2>/dev/null
setsid -f sh -c '.venv/bin/python -m streamlit run src/dashboard/app.py --server.port 8501 --server.headless true --browser.gatherUsageStats false > /tmp/dash.log 2>&1 &'
sleep 7

# Validação visual side-by-side via skill validacao-visual:
# - Dashboard: http://localhost:8501/?cluster=Finanças&tab=Contas
# - Mockup:    http://127.0.0.1:8766/mockups/03-contas.html
# Cada screenshot deve mostrar:
# 1. Bloco "CONTAS CORRENTES & INVESTIMENTO" com 3+ cards
# 2. Cada card: sigla+nome do banco | saldo | SPARKLINE visível | meta
# 3. Bloco "CARTÕES DE CRÉDITO" separado com 1-2 cards
# 4. Cada cartão: sigla+nome | FATURA valor | BARRA DE USO colorida | limite
```

## Critério de aceitação

1. `contas.py` importa `sparkline_html` e `bar_uso_html`.
2. Renderização separada em 2 seções (Correntes vs Cartões).
3. Sparkline visível em pelo menos 2 cards de conta corrente.
4. Barra de uso visível em pelo menos 1 cartão.
5. CSS `contas.css` criado e carregado.
6. Lint OK + smoke 10/10 + cluster pytest verde.
7. Validação visual side-by-side: estruturalmente próximo ao mockup.

## Não-objetivos

- NÃO criar componentes novos em `ui.py` (consumir os 6 da V-02).
- NÃO mexer em outras páginas.
- NÃO implementar interatividade (clicar no card abre extrato — escopo de drilldown).
- NÃO usar dados sintéticos — só dados reais do `dados['extrato']`. Se conta não tem dados, omitir card.

## Referência

- Mockup: `novo-mockup/mockups/03-contas.html`.
- Auditoria: `docs/auditorias/AUDITORIA_PARIDADE_VISUAL_2026-05-07.md` linha 03.
- Pré-requisito: UX-V-02 (`sparkline_html`, `bar_uso_html`).
- VALIDATOR_BRIEF padrões: `(a)` edit incremental, `(b)` acentuação PT-BR, `(k)` hipótese da spec não é dogma, `(u)` proof-of-work runtime real.

*"O dado real desenha o gráfico; o componente é só a moldura." — princípio V-2*
