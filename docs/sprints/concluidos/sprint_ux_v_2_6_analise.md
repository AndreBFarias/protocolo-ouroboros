---
id: UX-V-2.6
titulo: Página Análise com Insights Derivados + counters nas tabs + delta vs anterior
status: concluída
concluida_em: 2026-05-07
prioridade: alta
data_criacao: 2026-05-07
fase: PARIDADE_VISUAL
depende_de: [UX-V-02]
co_executavel_com: [UX-V-2.4, UX-V-2.5, UX-V-2.17]
esforco_estimado_horas: 4
origem: docs/auditorias/AUDITORIA_PARIDADE_VISUAL_2026-05-07.md (página 12)
mockup: novo-mockup/mockups/12-analise.html
---

# Sprint UX-V-2.6 — Análise paridade com mockup

## Contexto

Auditoria 2026-05-07 identificou divergência ALTA na página **Análise** (Avançada) vs `mockups/12-analise.html`:

- Mockup tem **counters nas tabs** ("Fluxo de caixa **3**", "Categorias **6**", "Padrões temporais **365D**")
- Mockup tem **% vs anterior** em KPIs ("+8% vs ano anterior")
- Mockup tem **Insights Derivados** lateral direita: 4 cards (Positivo / Atenção / Descoberta / Previsão) com narrativa curta
- Dashboard atual tem KPIs sem delta + Sankey, sem insights laterais

Esta sprint usa micro-componentes V-02 (`tab_counter_html` + `insight_card_html`) já entregues.

## Página afetada

`src/dashboard/paginas/analise_avancada.py` apenas.

## Objetivo

1. Importar `tab_counter_html` + `insight_card_html` de `componentes.ui`.
2. Adicionar counters nas tabs (Fluxo: contagem de categorias / Categorias: contagem de famílias / Padrões: dias do período).
3. Adicionar `% vs anterior` em cada KPI (calcular delta entre período atual e anterior do mesmo tamanho).
4. Adicionar bloco lateral **INSIGHTS DERIVADOS** com 3-4 cards (gerados deterministicamente das estatísticas — sem LLM, ADR-13).

## Validação ANTES (grep obrigatório — padrão `(k)`)

```bash
wc -l src/dashboard/paginas/analise_avancada.py
grep -n "^def \|st\.tabs\|tab\(\[" src/dashboard/paginas/analise_avancada.py | head -10

# Pré-requisito V-02
.venv/bin/python -c "
from src.dashboard.componentes.ui import tab_counter_html, insight_card_html
print('imports OK')
"
```

## Spec de implementação

### 1. Função delta vs anterior

```python
def _delta_periodo_anterior(df: pd.DataFrame, periodo_atual: str) -> dict:
    """Calcula valores do período anterior para comparação.
    
    Se periodo_atual='2026-04', anterior='2026-03'. Devolve dict com
    delta_entradas, delta_saidas, delta_saldo (em pp ou %).
    """
    from datetime import datetime
    try:
        ano, mes = map(int, periodo_atual.split('-'))
        if mes == 1:
            ant = f"{ano - 1}-12"
        else:
            ant = f"{ano}-{mes - 1:02d}"
    except (ValueError, AttributeError):
        return {}
    
    df_ant = df[df['mes_ref'] == ant]
    df_atual = df[df['mes_ref'] == periodo_atual]
    
    if df_ant.empty:
        return {}
    
    ent_ant = df_ant[df_ant['valor'] > 0]['valor'].sum()
    ent_atual = df_atual[df_atual['valor'] > 0]['valor'].sum()
    delta_ent = ((ent_atual - ent_ant) / ent_ant * 100) if ent_ant > 0 else 0
    
    return {"delta_entradas_pct": delta_ent}
```

### 2. Insights derivados (determinísticos)

```python
def _gerar_insights(df: pd.DataFrame) -> list[tuple[str, str, str]]:
    """Gera 3-4 insights derivados deterministicamente. Tuples (tipo, titulo, corpo).
    
    Sem LLM (ADR-13). Heurísticas:
    - Categoria que cresceu mais que 20% vs anterior -> Atenção
    - Recorrência detectada (mesma assinatura mensal) -> Descoberta
    - Saldo médio dos últimos 12m positivo crescente -> Positivo
    - Margem prevista próximo mês com base em médias -> Previsão
    """
    insights = []
    
    if df.empty or len(df) < 30:
        return insights
    
    # 1. Crescimento por categoria
    if 'mes_ref' in df.columns and 'categoria' in df.columns:
        meses = sorted(df['mes_ref'].dropna().unique())
        if len(meses) >= 2:
            mes_atual = meses[-1]
            mes_ant = meses[-2]
            for cat in df['categoria'].dropna().unique():
                v_atual = abs(df[(df['mes_ref'] == mes_atual) & (df['categoria'] == cat)]['valor'].sum())
                v_ant = abs(df[(df['mes_ref'] == mes_ant) & (df['categoria'] == cat)]['valor'].sum())
                if v_ant > 0:
                    delta = (v_atual - v_ant) / v_ant * 100
                    if delta > 20 and v_atual > 100:
                        insights.append((
                            "atencao",
                            f"{cat} aumentou {delta:.0f}%",
                            f"De R$ {v_ant:,.2f} ({mes_ant}) para R$ {v_atual:,.2f} ({mes_atual}). "
                            f"Sazonalidade ou novo padrão?"
                        ))
                        break  # só o primeiro
    
    # 2. Saldo crescente (Positivo)
    if 'mes_ref' in df.columns:
        saldos = df.groupby('mes_ref')['valor'].sum().tail(6)
        if len(saldos) >= 3 and saldos.iloc[-1] > saldos.iloc[0]:
            insights.append((
                "positivo",
                "Saldo crescente nos últimos meses",
                f"De R$ {saldos.iloc[0]:,.2f} ({saldos.index[0]}) para "
                f"R$ {saldos.iloc[-1]:,.2f} ({saldos.index[-1]})."
            ))
    
    # 3. Previsão simples (média)
    if len(saldos) >= 3:
        media = saldos.mean()
        insights.append((
            "previsao",
            "Margem prevista para próximo mês",
            f"Saldo médio ~R$ {media:,.2f} pelos últimos {len(saldos)} meses. "
            f"Aporte sugerido em CDB."
        ))
    
    return insights[:4]  # máximo 4
```

### 3. Render

```python
def renderizar(dados, mes_selecionado, pessoa, ctx=None):
    # ... topbar_actions, page_header existentes ...
    st.markdown(minificar(carregar_css_pagina("analise_avancada")), unsafe_allow_html=True)
    
    df = dados['extrato']
    delta = _delta_periodo_anterior(df, mes_selecionado)
    
    # Tabs com counters (custom HTML; st.tabs nativo não suporta)
    n_cats = df['categoria'].nunique() if 'categoria' in df.columns else 0
    n_meses = df['mes_ref'].nunique() if 'mes_ref' in df.columns else 0
    tabs_html = (
        tab_counter_html("Fluxo de caixa", 1, ativo=True)
        + tab_counter_html("Categorias", n_cats)
        + tab_counter_html("Padrões temporais", n_meses)
    )
    st.markdown(f'<div class="analise-tabs">{tabs_html}</div>', unsafe_allow_html=True)
    
    # KPIs com delta (mantém st.tabs nativo abaixo)
    # ... KPIs existentes -- ADICIONAR linha de delta abaixo do valor:
    # <span class="kpi-delta">+{delta_entradas:.0f}% vs anterior</span>
    
    # Layout: Sankey à esquerda, Insights à direita
    col_main, col_insights = st.columns([2, 1])
    with col_main:
        # ... Sankey/gráfico existente ...
        pass
    with col_insights:
        st.markdown('<h3 class="insights-titulo">INSIGHTS DERIVADOS</h3>', unsafe_allow_html=True)
        insights = _gerar_insights(df)
        if not insights:
            st.markdown(callout_html("info", "Sem insights -- precisa mais dados (>=30 transações)."), unsafe_allow_html=True)
        for tipo, titulo, corpo in insights:
            st.markdown(insight_card_html(tipo, titulo, corpo), unsafe_allow_html=True)
```

### 4. CSS — `src/dashboard/css/paginas/analise_avancada.css`

```css
/* Análise -- UX-V-2.6 */

.analise-tabs {
    display: flex; gap: var(--sp-3); align-items: center;
    margin-bottom: var(--sp-4);
    border-bottom: 1px solid var(--border-subtle);
    padding-bottom: 4px;
}

.kpi-delta {
    font-family: var(--ff-mono); font-size: 11px;
    color: var(--accent-green);
}
.kpi-delta.negativo { color: var(--accent-red); }

.insights-titulo {
    font-family: var(--ff-mono); font-size: 11px;
    text-transform: uppercase; letter-spacing: 0.10em;
    color: var(--text-secondary);
    margin: 0 0 var(--sp-3);
}
```

## Validação DEPOIS

```bash
test -f src/dashboard/css/paginas/analise_avancada.css
make lint && make smoke
.venv/bin/python -m pytest tests/test_analise*.py tests/test_dashboard_categorias*.py -q | tail -3
```

## Proof-of-work runtime-real

Validação visual side-by-side em `cluster=Análise&tab=Análise` vs `mockups/12-analise.html`. Screenshot deve mostrar:
1. Tabs canônicas com counters (Fluxo de caixa **N** · Categorias **N** · Padrões temporais **N**)
2. KPIs com delta `+X% vs anterior`
3. Bloco lateral INSIGHTS DERIVADOS com 3-4 cards coloridos (positivo/atenção/descoberta/previsão)

## Critério de aceitação

1. Counters nas 3 tabs renderizando com valores reais.
2. Delta vs anterior visível em KPIs.
3. INSIGHTS DERIVADOS lateral com 1+ insight gerado deterministicamente.
4. CSS criado.
5. Lint OK + smoke 10/10 + cluster pytest verde.

## Não-objetivos

- NÃO usar LLM/API para insights — gerar deterministicamente das estatísticas.
- NÃO mexer em Sankey ou gráficos existentes.
- NÃO criar componentes novos em ui.py.

## Referência

- Mockup: `novo-mockup/mockups/12-analise.html`.
- Pré-requisito: UX-V-02 (`tab_counter_html`, `insight_card_html`).
- ADR-13: supervisor artesanal sem API programática (insights determinísticos).

*"O dado fala; o insight escuta." — princípio V-2.6*
