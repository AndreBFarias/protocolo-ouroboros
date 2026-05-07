---
id: UX-V-2.3
titulo: Página Completude com 4 KPIs no topo + heatmap por tipo de doc
status: backlog
prioridade: alta
data_criacao: 2026-05-07
fase: PARIDADE_VISUAL
depende_de: [UX-V-02]
co_executavel_com: [UX-V-2.1, UX-V-2.2, UX-V-2.7]
esforco_estimado_horas: 4
origem: docs/auditorias/AUDITORIA_PARIDADE_VISUAL_2026-05-07.md (página 08)
mockup: novo-mockup/mockups/08-completude.html
---

# Sprint UX-V-2.3 — Completude paridade com mockup

## Contexto

Auditoria 2026-05-07 identificou divergência ALTA na página **Completude** vs `mockups/08-completude.html`:

- Mockup tem **4 KPIs no topo** (Cobertura Global / Tipos Completos / Lacunas Críticas / Lacunas Médias)
- Mockup heatmap mostra **tipos de documento** (OFX bancos, Faturas cartão, Comprovantes Pix, NF serviços, Recibos) × meses
- Dashboard atual mostra **categorias de transação** (Aluguel, Condomínio, Energia, Farmácia, etc.) × meses
- Mockup tem **legenda** (completo/parcial/ausente) com cores e contagem

Dashboard atual NÃO tem KPIs no topo e usa eixo Y diferente.

## Página afetada

`src/dashboard/paginas/completude.py` apenas.

## Objetivo

1. Adicionar 4 KPIs no topo: Cobertura Global %, Tipos Completos N/T, Lacunas Críticas N, Lacunas Médias N.
2. Heatmap pode manter eixos atuais (categorias × meses) — não inventar dados — MAS adicionar:
   - Legenda completo (verde) / parcial (amarelo) / ausente (vermelho) com contagens
   - Sprint-tag UX-V-2.3
3. Cobertura calculada com base em transações com `documento_vinculado` (campo do XLSX/grafo).

## Validação ANTES (grep obrigatório — padrão `(k)`)

```bash
wc -l src/dashboard/paginas/completude.py
grep -n "^def \|st\.markdown\|heatmap" src/dashboard/paginas/completude.py | head -10

# Hipótese: cobertura por tipo de doc requer dados que talvez não existam
grep -rn "documento_vinculado\|tipos_documento\|cobertura_global\|lacunas" src/dashboard/dados.py src/graph/queries.py 2>/dev/null | head -10
```

Se cobertura por tipo de documento não está disponível em DataFrames atuais, **manter heatmap por categoria atual mas adicionar 4 KPIs derivados de transações vs documentos vinculados** (achado-bloqueio aceitável).

## Spec de implementação

### 1. KPIs derivados (grep mostra precedente)

```python
def _calcular_kpis_completude(df: pd.DataFrame, df_docs: pd.DataFrame | None = None) -> dict:
    """Calcula 4 KPIs canônicos da Completude.
    
    Cobertura = % de transações com documento vinculado.
    Tipos completos = quantos tipos de doc têm cobertura >= 90%.
    Lacunas críticas = transações em categorias obrigatórias sem doc.
    Lacunas médias = lacunas em categorias não-obrigatórias.
    """
    if df.empty:
        return {"cobertura": 0.0, "tipos_completos": 0, "tipos_total": 0,
                "lacunas_criticas": 0, "lacunas_medias": 0}
    
    # Cobertura: usar coluna 'documento_vinculado' se existe, ou fallback
    if 'documento_vinculado' in df.columns:
        com_doc = df['documento_vinculado'].notna().sum()
    else:
        com_doc = 0
    total = len(df)
    cobertura = (com_doc / total * 100) if total > 0 else 0.0
    
    # Tipos completos: contar tipos de doc com cobertura >= 90% (heurística)
    tipos_total = df['categoria'].nunique() if 'categoria' in df.columns else 0
    tipos_completos = 0  # placeholder; cálculo real depende de mappings
    
    # Lacunas críticas: categorias obrigatórias sem documento vinculado
    obrigatorias = {'Aluguel', 'Energia', 'Saúde', 'Impostos', 'Educação'}
    if 'categoria' in df.columns and 'documento_vinculado' in df.columns:
        sem_doc = df[df['documento_vinculado'].isna()]
        lacunas_criticas = sem_doc[sem_doc['categoria'].isin(obrigatorias)].shape[0]
        lacunas_medias = sem_doc[~sem_doc['categoria'].isin(obrigatorias)].shape[0]
    else:
        lacunas_criticas = lacunas_medias = total - com_doc
    
    return {
        "cobertura": cobertura,
        "tipos_completos": tipos_completos,
        "tipos_total": tipos_total,
        "lacunas_criticas": lacunas_criticas,
        "lacunas_medias": lacunas_medias,
    }
```

### 2. KPIs HTML (4 cards)

```python
def _kpis_html(kpis: dict) -> str:
    return minificar(f"""
    <div class="kpi-grid">
      <div class="kpi">
        <span class="kpi-label">COBERTURA GLOBAL · 12M</span>
        <span class="kpi-value" style="color: var(--accent-purple);">{kpis['cobertura']:.0f}%</span>
        <span class="kpi-sub">meta · 90%</span>
      </div>
      <div class="kpi">
        <span class="kpi-label">TIPOS COMPLETOS</span>
        <span class="kpi-value">{kpis['tipos_completos']} / {kpis['tipos_total']}</span>
        <span class="kpi-sub">≥90% cobertos</span>
      </div>
      <div class="kpi">
        <span class="kpi-label">LACUNAS CRÍTICAS</span>
        <span class="kpi-value" style="color: var(--accent-red);">{kpis['lacunas_criticas']}</span>
        <span class="kpi-sub">obrigatórias sem doc</span>
      </div>
      <div class="kpi">
        <span class="kpi-label">LACUNAS MÉDIAS</span>
        <span class="kpi-value" style="color: var(--accent-orange);">{kpis['lacunas_medias']}</span>
        <span class="kpi-sub">tolerável · sem bloquear</span>
      </div>
    </div>
    """)
```

### 3. Renderizar (manter heatmap, adicionar KPIs antes)

```python
def renderizar(dados, mes_selecionado, pessoa, ctx=None):
    # ... topbar_actions, page_header existentes ...
    
    df = dados['extrato']
    kpis = _calcular_kpis_completude(df)
    st.markdown(_kpis_html(kpis), unsafe_allow_html=True)
    
    # ... heatmap existente (manter) ...
    
    # Legenda no rodapé do heatmap
    st.markdown(minificar("""
    <div class="completude-legenda">
      <span><span class="leg-cor" style="background: var(--accent-green);"></span> completo (≥80%)</span>
      <span><span class="leg-cor" style="background: var(--accent-yellow);"></span> parcial (40-80%)</span>
      <span><span class="leg-cor" style="background: var(--accent-red);"></span> ausente (&lt;40%)</span>
    </div>
    """), unsafe_allow_html=True)
```

### 4. CSS — Reusa `.kpi-grid` e `.kpi` canônicos (já existem em components.css UX-M-03)

Adicionar SÓ legenda em `src/dashboard/css/paginas/completude.css`:

```css
/* Legenda do heatmap -- UX-V-2.3 */
.completude-legenda {
    display: flex; gap: var(--sp-4); align-items: center;
    margin-top: var(--sp-3);
    font-family: var(--ff-mono); font-size: 11px;
    color: var(--text-secondary);
}
.completude-legenda .leg-cor {
    display: inline-block; width: 12px; height: 12px;
    border-radius: var(--r-xs); margin-right: 4px;
    vertical-align: middle;
}
```

## Validação DEPOIS

```bash
test -f src/dashboard/css/paginas/completude.css || echo "criar"
make lint && make smoke
.venv/bin/python -m pytest tests/test_*completude*.py -q 2>&1 | tail -3
```

## Proof-of-work runtime-real

Validação visual side-by-side em `cluster=Documentos&tab=Completude` vs `mockups/08-completude.html`. Cada screenshot deve mostrar:
1. **4 KPIs no topo** (Cobertura Global / Tipos Completos / Lacunas Críticas / Lacunas Médias) com valores reais
2. Heatmap renderizando
3. Legenda no rodapé com 3 cores

## Critério de aceitação

1. 4 KPIs renderizando com valores reais (não inventados — derivados de `df['documento_vinculado']` se existir, fallback graceful).
2. Legenda no rodapé com 3 cores.
3. CSS `completude.css` criado (mesmo se for só a legenda).
4. Lint OK + smoke 10/10 + cluster pytest verde.

## Não-objetivos

- NÃO mudar eixos do heatmap (mantém categorias × meses por enquanto; reorientar para tipos de doc é débito futuro).
- NÃO inventar dados de cobertura por tipo (sem fonte canônica = 0).
- NÃO mexer em outras páginas.

## Referência

- Mockup: `novo-mockup/mockups/08-completude.html`.
- Auditoria: linha 08.
- VALIDATOR_BRIEF: `(a)/(b)/(k)/(o)/(u)`.

*"O que não se mede, não se completa." — princípio V-2.3*
