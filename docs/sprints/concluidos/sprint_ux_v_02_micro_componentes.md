---
id: UX-V-02
titulo: Micro-componentes visuais canônicos em ui.py + components.css
status: concluída
prioridade: altissima
data_criacao: 2026-05-07
concluida_em: 2026-05-07
fase: PARIDADE_VISUAL
depende_de: [UX-M-02, UX-M-03]
bloqueia: [UX-V-2.*]
co_executavel_com: [UX-V-01, UX-V-03, UX-V-04, UX-V-05]
esforco_estimado_horas: 5
origem: docs/auditorias/AUDITORIA_PARIDADE_VISUAL_2026-05-07.md (P2)
commit: e04a2a1410d51f854966f320152b7feb7b37f6cf
---

# Sprint UX-V-02 — Micro-componentes visuais canônicos

## Contexto

Auditoria 2026-05-07 (P2) listou 14 micro-elementos visuais que aparecem em mockups canônicos mas NÃO existem como componentes reutilizáveis no dashboard. Esta sprint adiciona 6 deles (os mais transversais) à fronteira pública `ui.py` + classes em `components.css`. As outras 8 ficam para sprints específicas de página.

Motivação: páginas da Onda V-2 vão consumir esses componentes ao migrar (Contas usa sparkline, Metas usa donut + barra-progresso + 3-colunas-prazo-ritmo-falta, Análise usa tab-counter + insight-card, etc.). Sem essa fundação, V-2 vira N reescritas duplicadas.

## Páginas afetadas

Nenhuma diretamente — esta sprint só ENTREGA os componentes em `ui.py` + `components.css`. Migração das páginas é responsabilidade das sprints V-2.x.

Alvos da migração futura (apenas referência, não escopo desta sprint):
- `sparkline_html` → Contas (cards de banco), Medidas (6 cards corporais)
- `bar_uso_html` → Contas (cartões), Categorias (rules hits)
- `donut_inline_html` + `prazo_ritmo_falta_html` → Metas
- `tab_counter_html` → Análise, Memórias
- `insight_card_html` → Análise, Cruzamentos

## Objetivo

1. Criar 6 funções HTML em `src/dashboard/componentes/ui.py`:
   - `sparkline_html(valores: list[float], cor: str | None = None) -> str`
   - `bar_uso_html(usado: float, total: float, *, label: str = "", cor: str | None = None) -> str`
   - `donut_inline_html(percentual: float, *, tamanho: int = 60, cor: str | None = None) -> str`
   - `prazo_ritmo_falta_html(prazo: str, ritmo: str, falta: str) -> str`
   - `tab_counter_html(label: str, count: int, *, ativo: bool = False) -> str`
   - `insight_card_html(tipo: str, titulo: str, corpo: str) -> str` — tipo ∈ {"positivo","atencao","descoberta","previsao"}
2. Adicionar classes correspondentes em `src/dashboard/css/components.css`:
   - `.sparkline`, `.sparkline-line`, `.sparkline-fill`
   - `.bar-uso`, `.bar-uso-fill`, `.bar-uso-label`
   - `.donut-mini`, `.donut-mini-track`, `.donut-mini-fill`, `.donut-mini-pct`
   - `.prazo-ritmo-falta`, `.prf-celula`, `.prf-rotulo`, `.prf-valor`
   - `.tab-counter`, `.tab-counter-num`, `.tab-counter-ativo`
   - `.insight-card`, `.insight-card-tipo`, `.insight-card-titulo`, `.insight-card-corpo`, e variantes `.insight-positivo`, `.insight-atencao`, `.insight-descoberta`, `.insight-previsao`
3. Adicionar testes unitários em `tests/test_ui_micro_componentes.py` validando que cada função retorna HTML não vazio + classes esperadas + minificação aplicada.

## Validação ANTES (grep obrigatório — padrão `(k)`)

```bash
# Hipótese da spec: nenhuma das 6 funções existe ainda
grep -rn "def sparkline_html\|def bar_uso_html\|def donut_inline_html\|def prazo_ritmo_falta\|def tab_counter\|def insight_card" src/dashboard/ --include="*.py"
# Esperado: 0 matches

# Hipótese: classes correspondentes não existem ainda em components.css
grep -nE "^\.sparkline|^\.bar-uso|^\.donut-mini|^\.prazo-ritmo|^\.tab-counter|^\.insight-card" src/dashboard/css/components.css
# Esperado: 0 matches

# ui.py base
grep -c "^def " src/dashboard/componentes/ui.py
# Esperado: 14 (pós Onda M)

# Tamanho atual de ui.py para comparar pós-edit
wc -l src/dashboard/componentes/ui.py
```

Se algum match aparecer, é precedente — adaptar (estender vs criar do zero).

## Spec de implementação

### 1. `sparkline_html`

SVG inline minimalista, 80×24px default. Usa polyline. Sem libs externas.

```python
def sparkline_html(
    valores: list[float],
    *,
    cor: str | None = None,
    largura: int = 80,
    altura: int = 24,
) -> str:
    """Sparkline SVG inline.

    Args:
        valores: série numérica (≥2 pontos). Lista vazia retorna string vazia.
        cor: hex/var token. Default ``var(--accent-purple)``.
        largura, altura: dimensões do SVG.

    Retorna ``<span class="sparkline">...</span>`` minificado.
    """
    if not valores or len(valores) < 2:
        return ""
    cor_efetiva = cor or "var(--accent-purple)"
    minimo, maximo = min(valores), max(valores)
    intervalo = (maximo - minimo) or 1.0
    n = len(valores)
    pontos = " ".join(
        f"{(i / (n - 1)) * largura:.2f},{altura - ((v - minimo) / intervalo) * altura:.2f}"
        for i, v in enumerate(valores)
    )
    return minificar(
        f"""
        <span class="sparkline">
          <svg viewBox="0 0 {largura} {altura}" width="{largura}" height="{altura}">
            <polyline class="sparkline-line"
              fill="none" stroke="{cor_efetiva}" stroke-width="1.5"
              points="{pontos}" />
          </svg>
        </span>
        """
    )
```

### 2. `bar_uso_html`

Barra horizontal de uso (usado/total) com label opcional. Cor varia por % (verde <60, amarelo 60-90, vermelho >90).

```python
def bar_uso_html(
    usado: float,
    total: float,
    *,
    label: str = "",
    cor: str | None = None,
) -> str:
    """Barra de uso percentual usado/total.

    Args:
        usado: valor consumido (numerador).
        total: capacidade total (denominador). 0 retorna string vazia.
        label: texto pequeno acima da barra (ex.: "36% usado").
        cor: override; default escolhe por %% (≥90% red, ≥60% orange, else green).

    Retorna ``<div class="bar-uso">...</div>`` minificado.
    """
    if total <= 0:
        return ""
    pct = max(0.0, min(100.0, (usado / total) * 100.0))
    if cor is None:
        if pct >= 90:
            cor = "var(--accent-red)"
        elif pct >= 60:
            cor = "var(--accent-orange)"
        else:
            cor = "var(--accent-green)"
    label_html = f'<span class="bar-uso-label">{label}</span>' if label else ""
    return minificar(
        f"""
        <div class="bar-uso" data-pct="{pct:.1f}">
          {label_html}
          <div class="bar-uso-track">
            <span class="bar-uso-fill" style="width:{pct:.2f}%; background:{cor};"></span>
          </div>
        </div>
        """
    )
```

### 3. `donut_inline_html`

SVG donut compacto (default 60px). Mostra percentual no centro.

```python
def donut_inline_html(
    percentual: float,
    *,
    tamanho: int = 60,
    cor: str | None = None,
) -> str:
    """Donut SVG inline com %% no centro.

    Args:
        percentual: 0..100 (clamped).
        tamanho: pixels (quadrado).
        cor: stroke do arco; default por %% (mesma escala bar_uso_html).

    Retorna ``<span class="donut-mini">...</span>`` minificado.
    """
    pct = max(0.0, min(100.0, percentual))
    if cor is None:
        if pct >= 100:
            cor = "var(--accent-green)"
        elif pct >= 70:
            cor = "var(--accent-yellow)"
        elif pct >= 30:
            cor = "var(--accent-purple)"
        else:
            cor = "var(--accent-red)"
    raio = (tamanho - 8) / 2  # margem 4px
    centro = tamanho / 2
    circ = 2 * 3.14159 * raio
    offset = circ * (1 - pct / 100)
    return minificar(
        f"""
        <span class="donut-mini" style="width:{tamanho}px;height:{tamanho}px;">
          <svg viewBox="0 0 {tamanho} {tamanho}">
            <circle class="donut-mini-track"
              cx="{centro}" cy="{centro}" r="{raio:.2f}"
              fill="none" stroke="var(--bg-elevated)" stroke-width="4" />
            <circle class="donut-mini-fill"
              cx="{centro}" cy="{centro}" r="{raio:.2f}"
              fill="none" stroke="{cor}" stroke-width="4"
              stroke-dasharray="{circ:.2f}" stroke-dashoffset="{offset:.2f}"
              transform="rotate(-90 {centro} {centro})" />
          </svg>
          <span class="donut-mini-pct">{pct:.0f}%</span>
        </span>
        """
    )
```

### 4. `prazo_ritmo_falta_html`

Layout 3-colunas usado em cards de meta (mockup 13-metas.html).

```python
def prazo_ritmo_falta_html(prazo: str, ritmo: str, falta: str) -> str:
    """3 colunas (PRAZO / RITMO / FALTA) usadas em cards de meta.

    Args:
        prazo: texto curto (ex.: "SET/2026").
        ritmo: texto curto (ex.: "+R$ 2.500/MÊS").
        falta: texto curto (ex.: "5 MESES").
    """
    return minificar(
        f"""
        <div class="prazo-ritmo-falta">
          <div class="prf-celula">
            <span class="prf-rotulo">PRAZO</span>
            <span class="prf-valor">{prazo}</span>
          </div>
          <div class="prf-celula">
            <span class="prf-rotulo">RITMO</span>
            <span class="prf-valor">{ritmo}</span>
          </div>
          <div class="prf-celula">
            <span class="prf-rotulo">FALTA</span>
            <span class="prf-valor">{falta}</span>
          </div>
        </div>
        """
    )
```

### 5. `tab_counter_html`

Contador inline em tabs (ex.: "Fluxo de caixa **3**", "Categorias **6**").

```python
def tab_counter_html(label: str, count: int, *, ativo: bool = False) -> str:
    """Tab com counter (ex.: 'Fluxo de caixa  3').

    Renderiza span com label + número estilizado. NÃO renderiza
    comportamento de tab (responsabilidade da página); apenas o HTML do
    rótulo + counter, embarcável em ``st.tabs([...])`` via custom CSS ou
    em radio horizontal.

    Args:
        label: texto da tab.
        count: número exibido pequeno após o label.
        ativo: se True aplica classe `.tab-counter-ativo` (cor accent).
    """
    classe = "tab-counter tab-counter-ativo" if ativo else "tab-counter"
    return minificar(
        f"""
        <span class="{classe}">
          {label}
          <span class="tab-counter-num">{count}</span>
        </span>
        """
    )
```

### 6. `insight_card_html`

Card lateral de insight (mockup 12-analise.html). 4 tipos canônicos.

```python
_INSIGHT_TIPOS_VALIDOS = {"positivo", "atencao", "descoberta", "previsao"}

def insight_card_html(tipo: str, titulo: str, corpo: str) -> str:
    """Card de insight derivado lateral.

    Args:
        tipo: ``"positivo"|"atencao"|"descoberta"|"previsao"``. Outro
            valor cai em ``"descoberta"`` (default) — não levanta erro
            (princípio de degradação graciosa, ADR-10).
        titulo: heading curto (≤60 chars idealmente).
        corpo: parágrafo (HTML safe esperado; chamador escapa se vier
            de input não-confiável).
    """
    if tipo not in _INSIGHT_TIPOS_VALIDOS:
        tipo = "descoberta"
    return minificar(
        f"""
        <div class="insight-card insight-{tipo}">
          <span class="insight-card-tipo">{tipo.upper()}</span>
          <h4 class="insight-card-titulo">{titulo}</h4>
          <p class="insight-card-corpo">{corpo}</p>
        </div>
        """
    )
```

### 7. CSS canônico em `components.css`

Adicionar ao final de `src/dashboard/css/components.css` (não substituir nada existente):

```css
/* ===== Micro-componentes UX-V-02 ===== */

/* Sparkline */
.sparkline { display: inline-block; vertical-align: middle; line-height: 0; }
.sparkline-line { stroke-linecap: round; stroke-linejoin: round; }

/* Barra de uso */
.bar-uso { display: flex; flex-direction: column; gap: 2px; }
.bar-uso-label {
    font-family: var(--ff-mono); font-size: 10px;
    color: var(--text-muted);
    text-transform: uppercase; letter-spacing: 0.06em;
}
.bar-uso-track {
    height: 6px; background: var(--bg-inset);
    border-radius: var(--r-full); overflow: hidden;
}
.bar-uso-fill {
    display: block; height: 100%;
    border-radius: var(--r-full);
    transition: width 0.3s ease-out;
}

/* Donut mini */
.donut-mini {
    position: relative;
    display: inline-grid;
    place-items: center;
    vertical-align: middle;
}
.donut-mini svg { position: absolute; inset: 0; }
.donut-mini-track { opacity: 0.4; }
.donut-mini-pct {
    position: relative; z-index: 1;
    font-family: var(--ff-mono);
    font-size: 13px; font-weight: 500;
    color: var(--text-primary);
    font-variant-numeric: tabular-nums;
}

/* Prazo / Ritmo / Falta (cards de meta) */
.prazo-ritmo-falta {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: var(--sp-3);
    padding: var(--sp-3) 0 0;
    border-top: 1px solid var(--border-subtle);
    margin-top: var(--sp-3);
}
.prf-celula { display: flex; flex-direction: column; gap: 2px; }
.prf-rotulo {
    font-family: var(--ff-mono); font-size: 10px;
    text-transform: uppercase; letter-spacing: 0.10em;
    color: var(--text-muted);
}
.prf-valor {
    font-family: var(--ff-mono); font-size: 12px;
    color: var(--text-primary);
    font-variant-numeric: tabular-nums;
}

/* Tab counter */
.tab-counter {
    display: inline-flex; align-items: center; gap: 6px;
    padding: 4px 10px; border-radius: var(--r-sm);
    font-family: var(--ff-mono); font-size: 12px;
    color: var(--text-secondary);
    cursor: pointer; user-select: none;
    border-bottom: 2px solid transparent;
}
.tab-counter-num {
    font-size: 10px; font-weight: 600;
    color: var(--text-muted);
    background: var(--bg-inset);
    padding: 1px 6px; border-radius: var(--r-full);
}
.tab-counter-ativo {
    color: var(--accent-purple);
    border-bottom-color: var(--accent-purple);
}
.tab-counter-ativo .tab-counter-num {
    color: var(--accent-purple);
    background: rgba(189, 147, 249, 0.15);
}

/* Insight card */
.insight-card {
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-left: 3px solid var(--accent-purple);
    border-radius: var(--r-md);
    padding: var(--sp-3) var(--sp-4);
    margin-bottom: var(--sp-3);
}
.insight-card-tipo {
    display: inline-block;
    font-family: var(--ff-mono); font-size: 10px;
    text-transform: uppercase; letter-spacing: 0.10em;
    color: var(--text-muted);
    margin-bottom: 6px;
}
.insight-card-titulo {
    font-size: 14px; font-weight: 500;
    color: var(--text-primary);
    margin: 0 0 6px;
}
.insight-card-corpo {
    font-family: var(--ff-mono); font-size: 12px;
    color: var(--text-secondary);
    margin: 0; line-height: 1.5;
}

.insight-positivo { border-left-color: var(--accent-green); }
.insight-positivo .insight-card-tipo { color: var(--accent-green); }

.insight-atencao { border-left-color: var(--accent-orange); }
.insight-atencao .insight-card-tipo { color: var(--accent-orange); }

.insight-descoberta { border-left-color: var(--accent-purple); }
.insight-descoberta .insight-card-tipo { color: var(--accent-purple); }

.insight-previsao { border-left-color: var(--accent-cyan); }
.insight-previsao .insight-card-tipo { color: var(--accent-cyan); }
```

### 8. Testes unitários

Criar `tests/test_ui_micro_componentes.py`:

```python
"""Testa as 6 funções HTML adicionadas em UX-V-02.

Não renderiza no Streamlit; valida apenas que retornam HTML não vazio
com classes esperadas e que minificar() foi aplicado (ausência de
indentação >=4 espaços).
"""
from __future__ import annotations

import re

import pytest

from src.dashboard.componentes.ui import (
    bar_uso_html,
    donut_inline_html,
    insight_card_html,
    prazo_ritmo_falta_html,
    sparkline_html,
    tab_counter_html,
)


def _sem_indentacao_python(html: str) -> bool:
    """Validação UX-RD-04: nenhuma linha com >=4 espaços iniciais."""
    return all(not linha.startswith("    ") for linha in html.splitlines())


def test_sparkline_lista_vazia_retorna_string_vazia() -> None:
    assert sparkline_html([]) == ""
    assert sparkline_html([1.0]) == ""


def test_sparkline_render_basico() -> None:
    html = sparkline_html([1.0, 2.0, 3.0, 2.5])
    assert 'class="sparkline"' in html
    assert "<polyline" in html
    assert _sem_indentacao_python(html)


def test_bar_uso_total_zero_retorna_vazio() -> None:
    assert bar_uso_html(usado=0, total=0) == ""


def test_bar_uso_render_com_label_e_cor_por_pct() -> None:
    html = bar_uso_html(usado=95, total=100, label="quase cheio")
    assert 'data-pct="95.0"' in html
    assert "var(--accent-red)" in html
    assert "quase cheio" in html


def test_donut_clampa_percentual_e_render() -> None:
    assert "100%" in donut_inline_html(150)
    assert "0%" in donut_inline_html(-10)
    html = donut_inline_html(71)
    assert "71%" in html
    assert "var(--accent-yellow)" in html


def test_prazo_ritmo_falta_estrutura_canonica() -> None:
    html = prazo_ritmo_falta_html("SET/2026", "+R$ 2.500/MES", "5 MESES")
    assert html.count('class="prf-celula"') == 3
    assert "SET/2026" in html
    assert "5 MESES" in html


def test_tab_counter_ativo_aplica_classe() -> None:
    inativo = tab_counter_html("Fluxo", 3)
    ativo = tab_counter_html("Fluxo", 3, ativo=True)
    assert "tab-counter-ativo" not in inativo
    assert "tab-counter-ativo" in ativo


def test_insight_card_tipo_invalido_cai_em_descoberta() -> None:
    html = insight_card_html("invalido", "T", "C")
    assert "insight-descoberta" in html


@pytest.mark.parametrize("tipo", ["positivo", "atencao", "descoberta", "previsao"])
def test_insight_card_tipos_validos(tipo: str) -> None:
    html = insight_card_html(tipo, "Título", "Corpo")
    assert f"insight-{tipo}" in html
    assert tipo.upper() in html


def test_todos_micro_componentes_minificados() -> None:
    """Lição UX-RD-04: HTML inline não pode ter indentação Python crua."""
    amostras = [
        sparkline_html([1, 2, 3]),
        bar_uso_html(50, 100, label="meio"),
        donut_inline_html(50),
        prazo_ritmo_falta_html("a", "b", "c"),
        tab_counter_html("x", 1),
        insight_card_html("positivo", "t", "c"),
    ]
    for html in amostras:
        assert _sem_indentacao_python(html), f"indentação perigosa: {html[:80]}"


# "A medida do componente é seu uso, não sua existência." -- principio (V-02)
```

## Validação DEPOIS

```bash
# 6 funções existem
grep -cE "^def (sparkline_html|bar_uso_html|donut_inline_html|prazo_ritmo_falta_html|tab_counter_html|insight_card_html)" src/dashboard/componentes/ui.py
# Esperado: 6

# Adicionadas em __all__
grep -E "sparkline_html|bar_uso_html|donut_inline_html|prazo_ritmo_falta|tab_counter|insight_card" src/dashboard/componentes/ui.py | grep -c "\""
# Esperado: ≥6 (cada nome em __all__)

# Classes em components.css
grep -cE "^\.(sparkline|bar-uso|donut-mini|prazo-ritmo-falta|tab-counter|insight-card)" src/dashboard/css/components.css
# Esperado: ≥6 (uma por componente principal)

# Testes
.venv/bin/python -m pytest tests/test_ui_micro_componentes.py -v 2>&1 | tail -15
# Esperado: 11 passed (8 funções + 4 paramétricos do insight)

# Lint + smoke + suite
make lint
make smoke
.venv/bin/python -m pytest tests/ -q 2>&1 | tail -3
# Esperado: 2570+ passed, baseline mantida
```

## Proof-of-work runtime-real

```bash
# Smoke import
.venv/bin/python -c "
from src.dashboard.componentes.ui import (
    sparkline_html, bar_uso_html, donut_inline_html,
    prazo_ritmo_falta_html, tab_counter_html, insight_card_html,
)
print('all 6 importable')
print(sparkline_html([1,2,3,4,5])[:80])
print(bar_uso_html(36, 100, label='36% usado')[:80])
print(donut_inline_html(71)[:80])
"
# Esperado: 'all 6 importable' + 3 saídas HTML não vazias
```

Validação visual fica para sprints V-2.x que consumirem os componentes — esta sprint apenas entrega a fronteira.

## Critério de aceitação

1. 6 funções adicionadas a `ui.py` + `__all__`.
2. CSS canônico para 6 componentes adicionado em `components.css`.
3. `tests/test_ui_micro_componentes.py` com ≥11 testes verdes.
4. `make lint && make smoke` OK.
5. `pytest tests/ -q` baseline mantida (≥2570 passed).
6. Imports cross-module funcionam (smoke import OK).

## Não-objetivos

- NÃO migrar páginas existentes para usar os novos componentes — escopo de V-2.x.
- NÃO criar componentes adicionais além dos 6 listados — outros 8 micro-elementos da auditoria (P2) ficam para sprints específicas.
- NÃO mexer em componentes existentes (`callout_html`, `kpi_card`, etc.).

## Referência

- Auditoria 2026-05-07 P2 (`docs/auditorias/AUDITORIA_PARIDADE_VISUAL_2026-05-07.md`).
- Mockups consumidores: 03-contas, 04-pagamentos, 12-analise, 13-metas, 24-medidas. <!-- noqa: accent -->
- VALIDATOR_BRIEF padrões: `(a)` edit incremental, `(b)` acentuação PT-BR, `(g)` citação filósofo, `(h)` limite 800L, `(u)` proof-of-work runtime real.

*"A medida do componente é seu uso, não sua existência." — princípio V-02*
