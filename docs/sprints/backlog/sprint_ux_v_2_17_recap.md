---
id: UX-V-2.17
titulo: Página Recap com Comparativo vs 30D anteriores + Destaques do mês
status: backlog
prioridade: media
data_criacao: 2026-05-07
fase: PARIDADE_VISUAL
depende_de: [UX-V-02]
co_executavel_com: [UX-V-2.4, UX-V-2.5, UX-V-2.6]
esforco_estimado_horas: 4
origem: docs/auditorias/AUDITORIA_PARIDADE_VISUAL_2026-05-07.md (página 21)
mockup: novo-mockup/mockups/21-recap.html
adr_aplicavel: ADR-13 (supervisor artesanal sem API)
---

# Sprint UX-V-2.17 — Recap paridade adaptada (ADR-13 vence narrativa LLM)

## Contexto

Auditoria 2026-05-07 identificou divergência arquitetural na página **Recap** vs `mockups/21-recap.html`:

- Mockup propõe **NARRATIVA por LLM** (Claude Sonnet via API) — proibido por ADR-13.
- Mockup tem **Comparativo vs 30D anteriores** (tabela rica com humor médio, ansiedade, foco, crises, aderência, tarefas, etc.) — implementável determinística.
- Mockup tem **DESTAQUES DO MÊS** com 5 cards coloridos por categoria (vitória/social/descoberta/conquista/risco).

Decisão do dono em 2026-05-07: **Recap fica determinístico** (Comparativo + Destaques estruturados). Narrativa LLM vira skill manual `/gerar-recap` (Opus interativo grava `docs/recaps/<mes>.md`, dashboard exibe quando existe).

## Página afetada

`src/dashboard/paginas/be_recap.py` apenas.

## Objetivo

1. Adicionar bloco **COMPARATIVO · vs 30D anteriores** (tabela com 5-8 métricas: humor médio, registros, eventos, treinos, peso variação) com delta + sinal.
2. Adicionar bloco **DESTAQUES DO MÊS** (até 5 cards) gerados deterministicamente:
   - Streaks (ex: "47 dias sem fumar")
   - Marcos (ex: "1ª centena")
   - Padrões descobertos (ex: "caminhada → ansiedade ↓")
   - Eventos importantes (ex: "Viagem a Trancoso")
3. Adicionar bloco opcional **NARRATIVA · gerada manualmente** que lê `docs/recaps/<YYYY-MM>.md` se existir; senão renderiza CTA "Use `/gerar-recap` para registrar narrativa do mês".

## Validação ANTES (grep obrigatório — padrão `(k)`)

```bash
wc -l src/dashboard/paginas/be_recap.py
grep -n "^def \|st\.markdown\|comparativo\|destaque" src/dashboard/paginas/be_recap.py | head -10

# Origem dos dados de bem-estar
ls .ouroboros/cache/*.json 2>/dev/null | head -5
grep -rn "humor-heatmap\|diario-emocional\|eventos.json" src/dashboard/dados.py 2>/dev/null | head -5

# docs/recaps/ existe?
ls docs/recaps/ 2>/dev/null || echo "criar diretorio se necessario"
```

## Spec de implementação

### 1. Comparativo vs 30D anteriores

```python
def _comparativo_html(metricas_atual: dict, metricas_ant: dict) -> str:
    """Tabela rica de comparação. Cada linha mostra metrica + valor + delta sinalizado.
    
    Args:
        metricas_atual: ``{"humor_medio": 4.0, "registros": 1, "eventos": 1, ...}``
        metricas_ant:   mesmo shape, dos 30 dias anteriores.
    """
    linhas = []
    chaves_legiveis = {
        "humor_medio": "humor médio",
        "registros": "registros · 30d",
        "eventos": "eventos",
        "treinos": "treinos",
        "peso_var": "peso (variação kg)",
        "ansiedade_media": "ansiedade média",
        "tarefas_concluidas": "tarefas concluídas",
        "noites_curtas": "noites &lt; 6h sono",
    }
    for k, label in chaves_legiveis.items():
        atual = metricas_atual.get(k)
        ant = metricas_ant.get(k)
        if atual is None or ant is None:
            continue
        delta = atual - ant
        if delta > 0.01:
            sinal = f"<span class=\"delta-pos\">↗ +{delta:+.2f}</span>"
        elif delta < -0.01:
            sinal = f"<span class=\"delta-neg\">↘ {delta:+.2f}</span>"
        else:
            sinal = "<span class=\"delta-zero\">= mesmo</span>"
        linhas.append(f"""
        <div class="comparativo-linha">
          <span class="comp-label">{label}</span>
          <span class="comp-valor">{atual:.2f}</span>
          {sinal}
        </div>
        """)
    return minificar(
        '<div class="comparativo-bloco">'
        '<h3 class="comp-titulo">COMPARATIVO · VS 30D ANTERIORES</h3>'
        + "".join(linhas) +
        '</div>'
    )
```

### 2. Destaques do mês (gerados das fontes do vault)

```python
def _gerar_destaques(caches: dict) -> list[dict]:
    """Gera até 5 destaques do mês deterministicamente.
    
    Heurísticas:
    - Maior streak ativo de qualquer contador (ex: dias sem fumar)
    - Marcos atingidos no mês
    - Eventos mais frequentes (top 3)
    - Padrão emocional (ex: "humor melhorou nos últimos 7 dias")
    """
    destaques = []
    
    # Contadores -> streaks
    contadores = caches.get('contadores', [])
    for c in contadores:
        streak = c.get('streak_dias')
        if streak and streak >= 7:
            destaques.append({
                "tipo": "vitoria",
                "rotulo": f"{streak} dias {c.get('nome', '?')}",
                "data": c.get('desde', ''),
            })
    
    # Eventos
    eventos = caches.get('eventos', [])
    if eventos:
        viagens = [e for e in eventos if 'viagem' in str(e.get('categoria', '')).lower()]
        if viagens:
            destaques.append({
                "tipo": "social",
                "rotulo": f"Viagem · {viagens[0].get('lugar', '?')}",
                "data": viagens[0].get('data', ''),
            })
    
    # Marcos
    marcos = caches.get('marcos', [])
    for m in marcos[:2]:
        destaques.append({
            "tipo": "conquista",
            "rotulo": m.get('nome', '?'),
            "data": m.get('data', ''),
        })
    
    return destaques[:5]


def _destaques_html(destaques: list[dict]) -> str:
    if not destaques:
        return '<p class="destaques-vazio">Sem destaques no período.</p>'
    
    cards = []
    for d in destaques:
        cards.append(f"""
        <div class="destaque-card destaque-{d['tipo']}">
          <span class="destaque-rotulo">{d['rotulo']}</span>
          <span class="destaque-data">{d.get('data', '')}</span>
        </div>
        """)
    return minificar(
        '<div class="destaques-bloco">'
        '<h3 class="destaques-titulo">DESTAQUES DO MÊS · {n}</h3>'.format(n=len(destaques))
        + '<div class="destaques-grid">' + "".join(cards) + '</div>'
        + '</div>'
    )
```

### 3. Narrativa manual

```python
def _narrativa_manual_html(periodo: str) -> str:
    """Lê docs/recaps/<YYYY-MM>.md se existir.
    
    Se não existir, renderiza CTA explicando como gerar via skill /gerar-recap.
    Conformidade ADR-13: zero API; conteúdo gerado por Opus interativo (humano).
    """
    from pathlib import Path
    raiz = Path(__file__).resolve().parents[3]
    recap_path = raiz / "docs" / "recaps" / f"{periodo}.md"
    
    if recap_path.exists():
        try:
            md = recap_path.read_text(encoding='utf-8')
            return f'<div class="narrativa-bloco"><div class="narrativa-corpo">{md}</div></div>'
        except OSError:
            pass
    
    return minificar(f"""
    <div class="narrativa-bloco narrativa-vazia">
      <h3 class="narrativa-titulo">NARRATIVA · {periodo}</h3>
      <p>
        Nenhuma narrativa gerada para este período. Use a skill canônica
        <code>/gerar-recap {periodo}</code> no Claude Code interativo (Opus
        principal) para registrar a narrativa do mês em
        <code>docs/recaps/{periodo}.md</code>. ADR-13: nenhum LLM via API
        é chamado pelo dashboard.
      </p>
    </div>
    """)
```

### 4. Render

```python
def renderizar(dados, mes_selecionado, pessoa, ctx=None):
    # ... topbar_actions, page_header existentes ...
    st.markdown(minificar(carregar_css_pagina("be_recap")), unsafe_allow_html=True)
    
    # Carrega métricas atuais e anteriores
    metricas_atual = _calcular_metricas(dados, periodo=mes_selecionado)
    metricas_ant = _calcular_metricas(dados, periodo=_periodo_anterior(mes_selecionado))
    caches = _carregar_caches_vault()
    
    col_narr, col_comp = st.columns([2, 1])
    with col_narr:
        st.markdown(_narrativa_manual_html(mes_selecionado), unsafe_allow_html=True)
        st.markdown(_destaques_html(_gerar_destaques(caches)), unsafe_allow_html=True)
    with col_comp:
        st.markdown(_comparativo_html(metricas_atual, metricas_ant), unsafe_allow_html=True)
```

### 5. CSS — `src/dashboard/css/paginas/be_recap.css` (estender existente)

```css
/* Recap V-2.17 -- Comparativo + Destaques + Narrativa manual */

.comparativo-bloco {
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: var(--r-md);
    padding: var(--sp-4);
}

.comp-titulo, .destaques-titulo, .narrativa-titulo {
    font-family: var(--ff-mono); font-size: 11px;
    text-transform: uppercase; letter-spacing: 0.10em;
    color: var(--text-muted);
    margin: 0 0 var(--sp-3);
}

.comparativo-linha {
    display: grid;
    grid-template-columns: 1fr auto auto;
    gap: var(--sp-3);
    align-items: baseline;
    padding: 4px 0;
    border-bottom: 1px dashed var(--border-subtle);
}
.comparativo-linha:last-child { border-bottom: none; }

.comp-label { font-size: 12px; color: var(--text-secondary); }
.comp-valor {
    font-family: var(--ff-mono); font-size: 13px;
    color: var(--text-primary);
    font-variant-numeric: tabular-nums;
}
.delta-pos { color: var(--accent-green); font-family: var(--ff-mono); font-size: 11px; }
.delta-neg { color: var(--accent-red); font-family: var(--ff-mono); font-size: 11px; }
.delta-zero { color: var(--text-muted); font-family: var(--ff-mono); font-size: 11px; }

.destaques-bloco {
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: var(--r-md);
    padding: var(--sp-4);
    margin-top: var(--sp-3);
}
.destaques-grid {
    display: flex; flex-direction: column; gap: var(--sp-2);
}
.destaque-card {
    display: flex; justify-content: space-between; align-items: center;
    padding: var(--sp-2) var(--sp-3);
    border-radius: var(--r-sm);
    border-left: 3px solid var(--accent-purple);
    background: var(--bg-inset);
}
.destaque-card.destaque-vitoria { border-left-color: var(--accent-green); }
.destaque-card.destaque-social { border-left-color: var(--accent-cyan); }
.destaque-card.destaque-conquista { border-left-color: var(--accent-yellow); }
.destaque-card.destaque-risco { border-left-color: var(--accent-red); }
.destaque-rotulo {
    font-size: 12px; color: var(--text-primary);
}
.destaque-data {
    font-family: var(--ff-mono); font-size: 10px;
    color: var(--text-muted);
}

.narrativa-bloco {
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: var(--r-md);
    padding: var(--sp-4);
    margin-bottom: var(--sp-3);
}
.narrativa-corpo {
    font-size: 13px;
    color: var(--text-primary);
    line-height: 1.6;
}
.narrativa-vazia {
    border-style: dashed;
    color: var(--text-muted);
}
```

## Validação DEPOIS

```bash
mkdir -p docs/recaps  # garantir que diretório existe
test -f src/dashboard/css/paginas/be_recap.css
make lint && make smoke
.venv/bin/python -m pytest tests/test_be_recap*.py -q 2>&1 | tail -3
```

## Proof-of-work runtime-real

Validação visual side-by-side em `cluster=Bem-estar&tab=Recap` vs `mockups/21-recap.html`. Screenshot deve mostrar:
1. Bloco NARRATIVA (vazio com CTA OU populado se existe `docs/recaps/<mes>.md`)
2. Bloco DESTAQUES DO MÊS com 1-5 cards coloridos
3. Bloco lateral COMPARATIVO · vs 30D ANTERIORES com 5-8 métricas + delta sinalizado

## Critério de aceitação

1. Comparativo renderizando com 5+ métricas + delta sinalizado.
2. Destaques renderizando com 1+ card (ou fallback "Sem destaques").
3. Narrativa renderizando CTA quando ausente.
4. CSS criado.
5. Diretório `docs/recaps/` criado (mesmo vazio).
6. Lint OK + smoke 10/10 + cluster pytest verde.

## Não-objetivos

- NÃO chamar API de LLM (ADR-13 vence).
- NÃO inventar métricas — usar caches reais do vault.
- NÃO criar componentes novos em ui.py.
- NÃO implementar a skill `/gerar-recap` nesta sprint (escopo separado).

## Referência

- Mockup: `novo-mockup/mockups/21-recap.html`.
- ADR-13 (supervisor artesanal sem API).
- Auditoria: linha 21.
- Decisão dono 2026-05-07: ADR-13 vence narrativa LLM.

*"Recap é memória estruturada, não palavra inventada." — princípio V-2.17*
