---
id: UX-V-2.14
titulo: Página Cruzamentos com builder dinâmico (3 dropdowns + scatter + perguntas pré-prontas)
status: concluída
concluida_em: 2026-05-07
prioridade: alta
data_criacao: 2026-05-07
fase: PARIDADE_VISUAL
depende_de: [UX-V-02]
co_executavel_com: [UX-V-2.8, UX-V-2.10, UX-V-2.16]
esforco_estimado_horas: 10
origem: docs/auditorias/AUDITORIA_PARIDADE_VISUAL_2026-05-07.md (página 26)
mockup: novo-mockup/mockups/26-cruzamentos.html
decisao_dono_2026_05_07: Builder + 3 padrões default como perguntas pré-prontas (mais rico que mockup)
---

# Sprint UX-V-2.14 -- Cruzamentos como builder dinâmico

## Contexto

Auditoria identificou divergência ESTRUTURAL ALTA: dashboard atual tem 3 expanders fixos (Humor × Eventos / Humor × Medidas / Treinos × Humor) com 1 gráfico vazio cada. Mockup é builder dinâmico (3 dropdowns Métrica × Cruzar com × Filtro/Janela + scatter + perguntas pré-prontas + insights).

Decisão dono em 2026-05-07: **Builder dinâmico + 3 padrões default como perguntas pré-prontas clicáveis** (preserva os 3 cruzamentos atuais como atalhos).

## Página afetada

`src/dashboard/paginas/be_cruzamentos.py` apenas.

## Objetivo

1. **Builder dinâmico**: 3 dropdowns no topo (Métrica / Cruzar com / Janela).
2. **Resultado**: scatter plot quando ambos dropdowns válidos.
3. **Perguntas pré-prontas**: 8 sugestões clicáveis lateral (mockup tem; dashboard atual tem 3 expanders).
4. **Insights desta query**: 1-3 cards gerados deterministicamente da correlação calculada.

## Validação ANTES

```bash
wc -l src/dashboard/paginas/be_cruzamentos.py
grep -n "^def \|expander\|scatter\|builder" src/dashboard/paginas/be_cruzamentos.py | head -10
```

## Spec de implementação

```python
def _builder_html(metrica: str, cruza: str, janela: str) -> str:
    """Estado atual do builder em texto canônico."""
    return minificar(f"""
    <div class="builder-bloco">
      <span class="builder-rotulo">cruzando</span>
      <strong>{metrica}</strong>
      <span class="builder-x">×</span>
      <strong>{cruza}</strong>
      <span class="builder-em">em</span>
      <strong>{janela}</strong>
    </div>
    """)


def _scatter_correlacao(df_metrica: pd.Series, df_cruza: pd.Series) -> tuple[float, str]:
    """Pearson correlation. Retorna (r, classificação_texto)."""
    if len(df_metrica) < 3 or len(df_cruza) < 3:
        return 0.0, "amostra insuficiente"
    r = df_metrica.corr(df_cruza)
    if abs(r) > 0.7:
        cls = "forte"
    elif abs(r) > 0.4:
        cls = "moderada"
    elif abs(r) > 0.2:
        cls = "fraca"
    else:
        cls = "negligível"
    return float(r), cls


PERGUNTAS_PRE_PRONTAS = [
    ("viagens nos fazem bem?", "humor", "evento", "180d"),
    ("reuniões aumentam ansiedade?", "ansiedade", "evento_trabalho", "90d"),
    ("rolezinhos ajudam o casal?", "humor", "rolezinho", "90d"),
    ("ciclo afeta meu humor (B)?", "humor_b", "ciclo_fase", "90d"),
    ("sono ruim → briga?", "briga", "sono_horas", "90d"),
    ("caminhada vespertina → foco?", "foco", "caminhada", "60d"),
    ("treinos elevam humor?", "humor", "treino", "60d"),
    ("dias de chuva → ansiedade?", "ansiedade", "chuva", "90d"),
]


def _perguntas_html() -> str:
    items = []
    for texto, m, c, j in PERGUNTAS_PRE_PRONTAS:
        items.append(f"""
        <div class="pergunta-card" data-metrica="{m}" data-cruza="{c}" data-janela="{j}">
          <span class="pergunta-texto">{texto}</span>
          <span class="pergunta-meta">{m} × {c} · {j}</span>
        </div>
        """)
    return minificar(
        '<div class="perguntas-bloco">'
        '<h3 class="perguntas-titulo">PERGUNTAS PRÉ-PRONTAS · CLIQUE PARA RODAR</h3>'
        + '<div class="perguntas-grid">' + "".join(items) + '</div>'
        + '</div>'
    )
```

Render layout 2-col: builder + scatter à esquerda, perguntas + insights à direita.

## CSS dedicado em `src/dashboard/css/paginas/be_cruzamentos.css`

```css
.builder-bloco {
    background: var(--bg-surface); border: 1px solid var(--accent-purple);
    border-radius: var(--r-md); padding: var(--sp-3);
    font-family: var(--ff-mono); font-size: 13px;
    display: flex; align-items: center; gap: var(--sp-2);
}
.builder-x, .builder-em {
    color: var(--text-muted); font-size: 12px;
}
.builder-rotulo {
    color: var(--text-muted); text-transform: uppercase;
    font-size: 11px; letter-spacing: 0.10em;
}

.perguntas-bloco {
    background: var(--bg-surface); border: 1px solid var(--border-subtle);
    border-radius: var(--r-md); padding: var(--sp-4);
}
.perguntas-titulo {
    font-family: var(--ff-mono); font-size: 11px;
    text-transform: uppercase; letter-spacing: 0.10em;
    color: var(--text-muted); margin: 0 0 var(--sp-3);
}
.perguntas-grid { display: grid; grid-template-columns: 1fr 1fr; gap: var(--sp-2); }
.pergunta-card {
    background: var(--bg-inset); border: 1px solid var(--border-subtle);
    border-radius: var(--r-sm); padding: var(--sp-2) var(--sp-3);
    cursor: pointer;
}
.pergunta-card:hover { border-color: var(--accent-purple); }
.pergunta-texto {
    display: block; font-size: 12px; color: var(--text-primary);
}
.pergunta-meta {
    display: block; font-family: var(--ff-mono); font-size: 10px;
    color: var(--text-muted); margin-top: 2px;
}
```

## Validação DEPOIS

```bash
make lint && make smoke
.venv/bin/python -m pytest tests/test_be_cruzamentos*.py -q
```

## Proof-of-work runtime-real

Validação visual em `cluster=Bem-estar&tab=Cruzamentos`. Mostrar:
1. Builder com 3 dropdowns (Métrica / Cruzar com / Janela) + texto canônico
2. Scatter plot quando ambos selecionados (ou placeholder)
3. 8 perguntas pré-prontas em grid 4×2
4. Insights laterais com correlação calculada

## Critério de aceitação

1. Builder dinâmico funciona (3 dropdowns).
2. Perguntas pré-prontas em grid 4×2.
3. Scatter ou placeholder.
4. CSS criado.
5. Lint OK + cluster pytest verde.

## Não-objetivos

- NÃO implementar persistência de queries salvas (visual only).
- NÃO mexer em outras páginas Bem-estar.

## Referência

- Mockup: `novo-mockup/mockups/26-cruzamentos.html`.
- Decisão dono 2026-05-07: builder + perguntas pré-prontas.
- VALIDATOR_BRIEF: `(a)/(b)/(k)/(u)`.

*"Pergunta clara, dado fala." -- princípio V-2.14*
