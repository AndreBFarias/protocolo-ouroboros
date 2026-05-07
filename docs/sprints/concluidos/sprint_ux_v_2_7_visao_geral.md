---
id: UX-V-2.7
titulo: Página Visão Geral com 6 cards de cluster + Atividade Recente com ícones
status: concluída
concluida_em: 2026-05-07  # noqa: accent
prioridade: alta
data_criacao: 2026-05-07
fase: PARIDADE_VISUAL
depende_de: [UX-V-02]
co_executavel_com: [UX-V-2.1, UX-V-2.2, UX-V-2.3]
esforco_estimado_horas: 3
origem: docs/auditorias/AUDITORIA_PARIDADE_VISUAL_2026-05-07.md (página 01)
mockup: novo-mockup/mockups/01-visao-geral.html
---

# Sprint UX-V-2.7 — Visão Geral paridade com mockup

## Contexto

Auditoria 2026-05-07 identificou divergência ALTA na **Visão Geral** vs `mockups/01-visao-geral.html`:

- Mockup tem **6 cards** dos clusters (Inbox, Finanças, Documentos, Análise, Metas, Sistema) em grid 3x2
- Dashboard atual mostra **3 cards visíveis** (Inbox, Finanças, Documentos) — faltam Análise, Metas, Sistema
- Mockup tem **Atividade Recente com ícones coloridos** por tipo (registro / opus / sprint / skill / pipeline / adr)
- Dashboard atual mostra Atividade Recente apenas em texto sem ícones

## Página afetada

`src/dashboard/paginas/visao_geral.py` apenas.

## Objetivo

1. Renderizar 6 cards de cluster (3x2 grid) com count + descrição.
2. Atividade Recente com ícones SVG canônicos (do `componentes/glyphs.py` UX-V-05) prefixando cada linha por tipo.
3. Manter hero, KPIs e Sprint Atual existentes.

## Validação ANTES (grep obrigatório — padrão `(k)`)

```bash
wc -l src/dashboard/paginas/visao_geral.py
grep -n "^def \|st\.markdown\|cluster\|Atividade" src/dashboard/paginas/visao_geral.py | head -15

# Glyphs SVG disponíveis
test -f src/dashboard/componentes/glyphs.py && grep -c "^GLYPHS\b\|^def glyph" src/dashboard/componentes/glyphs.py
test -f src/dashboard/componentes/glyphs_canonicos.py && cat src/dashboard/componentes/glyphs_canonicos.py | head -10
```

## Spec de implementação

### 1. Garantir 6 cards de cluster

```python
CLUSTERS_CANONICOS = [
    ("Inbox", "INBOX", "Entrada de dados. Drop por sha8.", "/?cluster=Inbox"),
    ("Finanças", "FINANÇAS", "Extrato, contas, pagamentos, projeções.", "/?cluster=Finanças"),
    ("Documentos", "DOCUMENTOS", "Busca, catálogo, completude, revisor, validação.", "/?cluster=Documentos"),
    ("Análise", "ANÁLISE", "Categorias, multi-perspectiva, IRPF.", "/?cluster=Análise"),
    ("Metas", "METAS", "Financeiras + operacionais (skills D7).", "/?cluster=Metas"),
    ("Sistema", "SISTEMA", "Skills D7, runs, ADRs, configuração.", "/?cluster=Sistema"),
]


def _cards_cluster_html(dados: dict) -> str:
    """6 cards em grid 3x2 com info de cada cluster."""
    df = dados.get('extrato', pd.DataFrame())
    docs_count = ... # ler do grafo
    
    cards = []
    for chave, label, desc, link in CLUSTERS_CANONICOS:
        if chave == "Inbox":
            metric = f"<a href='?cluster=Inbox'>aguardando</a>"
        elif chave == "Finanças":
            n_contas = df['banco_origem'].nunique() if not df.empty else 0
            n_txns = len(df)
            metric = f"<strong>{n_contas} contas</strong> · <strong>{n_txns}</strong> txns"
        elif chave == "Documentos":
            metric = f"<strong>{docs_count} arquivos</strong>"
        elif chave == "Análise":
            n_cats = df['categoria'].nunique() if not df.empty else 0
            metric = f"<strong>{n_cats} categorias</strong>"
        elif chave == "Metas":
            metric = "—"
        else:  # Sistema
            metric = "skills · runs · ADRs"
        
        cards.append(f"""
        <div class="cluster-card">
          <a href="{link}" class="cluster-card-link">
            <h3 class="cluster-card-titulo">{label}</h3>
            <p class="cluster-card-desc">{desc}</p>
            <p class="cluster-card-metric">{metric}</p>
          </a>
        </div>
        """)
    
    return minificar(
        '<div class="cluster-grid">' + "".join(cards) + '</div>'
    )
```

### 2. Atividade Recente com ícones

```python
TIPO_ICONE = {
    "registro": "upload",
    "extracao": "diff",
    "sprint": "validar",
    "skill": "atencao",
    "pipeline": "refresh",
    "adr": "lista",
}


def _atividade_recente_html(eventos: list[dict]) -> str:
    """Lista Atividade Recente com ícone SVG por tipo."""
    if not eventos:
        return '<p class="atividade-vazio">Sem atividade recente.</p>'
    
    from src.dashboard.componentes.glyphs import GLYPHS
    
    linhas = []
    for ev in eventos[:10]:
        tipo = ev.get("tipo", "registro")
        icone = GLYPHS.get(TIPO_ICONE.get(tipo, "lista"), "")
        ts = ev.get("ts", "")
        descricao = ev.get("descricao", "")
        linhas.append(f"""
        <div class="atividade-linha">
          <span class="atividade-ts">{ts}</span>
          <span class="atividade-icone">{icone}</span>
          <span class="atividade-desc">{descricao}</span>
        </div>
        """)
    return minificar('<div class="atividade-lista">' + "".join(linhas) + '</div>')
```

### 3. Renderização

```python
def renderizar(dados, mes_selecionado, pessoa, ctx=None):
    # ... topbar_actions, page_header, hero existentes ...
    st.markdown(minificar(carregar_css_pagina("visao_geral")), unsafe_allow_html=True)
    
    # ... KPIs existentes ...
    
    col_clusters, col_atividade = st.columns([2, 1])
    with col_clusters:
        st.markdown('<h2 class="secao-titulo">OS 5 CLUSTERS</h2>', unsafe_allow_html=True)
        st.markdown(_cards_cluster_html(dados), unsafe_allow_html=True)
    with col_atividade:
        st.markdown('<h2 class="secao-titulo">ATIVIDADE RECENTE</h2>', unsafe_allow_html=True)
        eventos = _carregar_eventos_recentes()  # ler de docs/HISTORICO_SESSOES.md ou git log
        st.markdown(_atividade_recente_html(eventos), unsafe_allow_html=True)
    
    # ... Sprint Atual existente ...
```

### 4. CSS — `src/dashboard/css/paginas/visao_geral.css`

```css
/* Página Visão Geral -- UX-V-2.7 paridade mockup 01-visao-geral.html */

.secao-titulo {
    font-family: var(--ff-mono); font-size: 11px;
    text-transform: uppercase; letter-spacing: 0.10em;
    color: var(--text-muted);
    margin: var(--sp-4) 0 var(--sp-2);
}

.cluster-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: var(--sp-3);
}

.cluster-card {
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: var(--r-md);
    padding: var(--sp-4);
    transition: border-color 0.15s, transform 0.15s;
}
.cluster-card:hover {
    border-color: var(--accent-purple);
    transform: translateY(-1px);
}
.cluster-card-link {
    text-decoration: none; color: inherit; display: block;
}
.cluster-card-titulo {
    font-family: var(--ff-mono); font-size: 14px;
    color: var(--text-primary); font-weight: 500;
    margin: 0 0 var(--sp-1);
}
.cluster-card-desc {
    font-size: 12px; color: var(--text-secondary);
    margin: 0 0 var(--sp-2);
}
.cluster-card-metric {
    font-family: var(--ff-mono); font-size: 11px;
    color: var(--text-muted);
    margin: 0;
}
.cluster-card-metric strong {
    color: var(--text-primary);
    font-variant-numeric: tabular-nums;
}

/* Atividade Recente */
.atividade-lista {
    display: flex; flex-direction: column; gap: var(--sp-2);
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: var(--r-md);
    padding: var(--sp-3);
}
.atividade-linha {
    display: grid;
    grid-template-columns: auto 18px 1fr;
    gap: var(--sp-2);
    align-items: center;
    padding: 4px 0;
    border-bottom: 1px solid var(--border-subtle);
}
.atividade-linha:last-child { border-bottom: none; }
.atividade-ts {
    font-family: var(--ff-mono); font-size: 10px;
    color: var(--text-muted);
}
.atividade-icone {
    color: var(--accent-purple);
    display: grid; place-items: center;
}
.atividade-icone svg { width: 14px; height: 14px; }
.atividade-desc {
    font-size: 12px; color: var(--text-secondary);
}
.atividade-vazio {
    font-family: var(--ff-mono); font-size: 12px;
    color: var(--text-muted); padding: var(--sp-3);
}
```

## Validação DEPOIS

```bash
test -f src/dashboard/css/paginas/visao_geral.css
make lint && make smoke
.venv/bin/python -m pytest tests/test_visao_geral*.py -q 2>&1 | tail -3
```

## Proof-of-work runtime-real

Validação visual side-by-side em `cluster=Home&tab=Visão+Geral` vs `mockups/01-visao-geral.html`. Screenshot deve mostrar:
1. Hero card com texto canônico
2. KPIs (manter atuais)
3. **6 cards de cluster** em grid 3x2 (Inbox, Finanças, Documentos, Análise, Metas, Sistema)
4. **Atividade Recente** lateral com ícones SVG por linha
5. Sprint Atual abaixo (manter)

## Critério de aceitação

1. 6 cards de cluster renderizando (todos os 6, mesmo que alguns metric="—").
2. Atividade Recente com ícones SVG canônicos (não emoji, não placeholder).
3. CSS `visao_geral.css` criado.
4. Lint OK + smoke 10/10 + pytest verde.

## Não-objetivos

- NÃO inventar dados de "Atividade" — usar git log ou eventos do projeto reais. Se vazio, mostrar fallback "Sem atividade recente."
- NÃO mexer em hero, KPIs ou Sprint Atual existentes.
- NÃO criar componente novo em `ui.py` — usar HTML inline da própria página.

## Referência

- Mockup: `novo-mockup/mockups/01-visao-geral.html`.
- Auditoria: linha 01.
- Glyphs: `src/dashboard/componentes/glyphs.py` (52 SVGs UX-RD-FIX-07).

*"A visão geral é o índice do sistema." — princípio V-2.7*
