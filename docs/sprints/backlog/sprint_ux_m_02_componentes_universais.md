---
id: UX-M-02
titulo: Componentes universais HTML em ui_canonico.py
status: backlog
prioridade: alta
data_criacao: 2026-05-06
fase: MODULARIZAÇÃO
depende_de: [UX-M-01]
bloqueia: [UX-M-03]
---

# Sprint UX-M-02 — Componentes universais HTML

## Contexto

Cada página do dashboard reinventa seus próprios componentes HTML:
- 4 páginas têm `_page_header_html()` reescrito (busca, catalogacao, contas, projecoes).
- KPI cards têm 5+ classes diferentes (`.vg-t01-kpi`, `.kpi-card`, `.pat-card`, `.ouroboros-res-head`, etc.).
- Cards de grupo, tabelas, search bars, chips — tudo tem N variantes.

Resultado: ajustar um padrão visual exige tocar dezenas de arquivos. Modularidade zero.

## Objetivo

Criar `src/dashboard/componentes/ui_canonico.py` com **8 funções universais** que emitem HTML padronizado. Páginas existentes migram para usar essas funções (zero classes próprias, zero CSS local de elementos repetidos).

## Hipótese

8 padrões visuais cobrem ~90% do dashboard:
1. `page_header(titulo, subtitulo, sprint_id, badges)` — cabeçalho UPPERCASE com pílula UX-RD.
2. `kpi_card(label, valor, sub_label, accent)` — card de número grande com label minúsculo.
3. `section_header(titulo, contagem, acoes)` — cabeçalho de seção com subtitulo opcional.
4. `group_card(titulo, contagem, linhas, pill_label)` — moldura de grupo de resultados.
5. `data_row(titulo, meta, snippet)` — linha de resultado com snippet opcional.
6. `search_bar(placeholder, kbd_hint)` — moldura visual da busca.
7. `chip_group(items, callback)` — grupo de chips clicáveis.
8. `toolbar(buttons)` — barra horizontal de botões.

Verificar via grep antes de codar: contar quantas vezes cada padrão aparece em cada página.

## Validação ANTES (grep obrigatório)

```bash
# Confirmar volume real
grep -rn "_page_header_html\|page-header" src/dashboard/paginas/ | wc -l
grep -rn "kpi-card\|vg-t01-kpi\|pat-card" src/dashboard/paginas/ | wc -l
grep -rn "ouroboros-res-group\|cluster-card" src/dashboard/paginas/ | wc -l
```

## Spec de implementação

### Estrutura proposta de `ui_canonico.py`

```python
"""Componentes universais HTML para o dashboard Ouroboros.

Princípio: ZERO duplicação visual. Toda página usa as mesmas funções,
emitindo HTML padronizado. CSS dos componentes vive em
src/dashboard/css/components/ (ver UX-M-03).
"""
from __future__ import annotations

from src.dashboard.componentes.html_utils import minificar


def page_header(
    titulo: str,
    subtitulo: str = "",
    sprint_id: str = "",
    badges: list[tuple[str, str]] | None = None,
) -> str:
    """Cabeçalho canônico de página (UPPERCASE + sprint-tag + badges).

    Args:
        titulo: título humano (ex: "Busca Global"). Renderizado UPPERCASE.
        subtitulo: descrição da página (uma frase, sem \\n).
        sprint_id: ID da sprint (ex: "UX-RD-09"). Renderiza pílula.
        badges: lista de (label, valor) para pílulas extras (ex: contagens).

    Exemplo:
        >>> page_header("Catalogação", "Banco normalizado.",
        ...              sprint_id="UX-RD-09",
        ...              badges=[("Arquivos", "48")])
    """
    badges = badges or []
    badges_html = "".join(
        f'<span class="badge-info">{lbl} {val}</span>' for lbl, val in badges
    )
    return minificar(f"""
    <div class="page-header">
      <div>
        <h1 class="page-title">{titulo.upper()}</h1>
        <p class="page-subtitle">{subtitulo}</p>
      </div>
      <div class="page-meta">
        {f'<span class="sprint-tag">{sprint_id}</span>' if sprint_id else ''}
        {badges_html}
      </div>
    </div>
    """)


def kpi_card(label: str, valor: str, sub_label: str = "", accent: str = "purple") -> str:
    """KPI card canônico (label MAIÚSCULO + valor grande + sub-label).

    Args:
        label: rótulo curto MAIÚSCULO (ex: "ARQUIVOS CATALOGADOS").
        valor: número formatado (ex: "48", "R$ 776.571,59", "0%").
        sub_label: contexto secundário (ex: "11 tipos no grafo").
        accent: cor da borda esquerda (purple, cyan, green, yellow, red, orange, pink).
    """
    return minificar(f"""
    <div class="kpi-card kpi-card--{accent}">
      <div class="kpi-label">{label.upper()}</div>
      <div class="kpi-valor">{valor}</div>
      {f'<div class="kpi-sub">{sub_label}</div>' if sub_label else ''}
    </div>
    """)


def section_header(titulo: str, contagem: str = "", acoes_html: str = "") -> str:
    """Cabeçalho de seção (faixa horizontal com título + contagem + ações)."""
    return minificar(f"""
    <div class="section-header">
      <h2 class="section-title">{titulo.upper()}</h2>
      {f'<span class="section-count">{contagem}</span>' if contagem else ''}
      {f'<div class="section-actions">{acoes_html}</div>' if acoes_html else ''}
    </div>
    """)


def group_card(
    titulo: str,
    linhas_html: str,
    contagem: str = "",
    pill_label: str = "",
) -> str:
    """Moldura de grupo de resultados (header + linhas + footer opcional)."""
    return minificar(f"""
    <div class="group-card">
      <div class="group-card-head">
        {f'<div class="group-pill">{pill_label}</div>' if pill_label else ''}
        <h3 class="group-title">{titulo.upper()}</h3>
        {f'<span class="group-count">{contagem}</span>' if contagem else ''}
      </div>
      {linhas_html}
    </div>
    """)


def data_row(
    titulo_html: str,
    meta_dict: dict[str, str],
    snippet_html: str = "",
) -> str:
    """Linha de resultado com título + meta inline + snippet opcional."""
    meta_html = "".join(
        f'<span>{lbl}{": " if lbl and val else ""}{val}</span>'
        for lbl, val in meta_dict.items()
    )
    return minificar(f"""
    <div class="data-row">
      <div class="data-row-title">{titulo_html}</div>
      <div class="data-row-meta">{meta_html}</div>
      {f'<div class="data-row-snippet">{snippet_html}</div>' if snippet_html else ''}
    </div>
    """)


def search_bar(placeholder: str = "Buscar...", kbd_hint: str = "/") -> str:
    """Moldura visual da search bar (input real é st.text_input separado)."""
    return minificar(f"""
    <div class="search-bar">
      <span class="search-icon">⌕</span>
      <span class="search-placeholder">{placeholder}</span>
      <span class="search-kbd">{kbd_hint}</span>
    </div>
    """)


def chip_group_html(items: list[str]) -> str:
    """Grupo de chips visuais (callback via st.button separado)."""
    chips = "".join(f'<span class="chip">{item}</span>' for item in items)
    return minificar(f'<div class="chip-group">{chips}</div>')


def toolbar(buttons: list[dict[str, str]]) -> str:
    """Barra horizontal de botões (botões são st.button separados)."""
    btns = "".join(
        f'<button class="btn btn--{b.get("variant", "default")}">'
        f'{b["label"]}</button>'
        for b in buttons
    )
    return minificar(f'<div class="toolbar">{btns}</div>')
```

### Migração das páginas (sub-sprints)

UX-M-02 emite `ui_canonico.py` mas NÃO migra páginas. Migração vira sub-sprints:

- **UX-M-02.A** — Migrar cluster Documentos (5 páginas: busca, catalogacao, completude, revisor, validacao)
- **UX-M-02.B** — Migrar cluster Finanças (5 páginas: extrato, contas, pagamentos, projecoes, [+1])
- **UX-M-02.C** — Migrar cluster Análise (3 páginas: categorias, analise, irpf)
- **UX-M-02.D** — Migrar cluster Sistema/Inbox/Bem-estar (16 páginas)

Cada sub-sprint substitui chamadas locais (`_page_header_html`, classes próprias) por imports de `ui_canonico`.

## Proof-of-work

```bash
# Após criar ui_canonico.py:
python -c "from src.dashboard.componentes.ui_canonico import page_header; print(page_header('Teste', 'sub', 'UX-XX'))"
# Esperado: HTML minificado válido com <h1>TESTE</h1>

# Após migração de uma página piloto (ex: catalogacao):
make dashboard
# Validar visualmente: layout idêntico ao anterior, mas código da página
# REDUZIDO em ≥30% de linhas.
```

## Critério de aceitação

1. `ui_canonico.py` criado com 8 funções públicas.
2. Funções têm docstrings + exemplos.
3. HTML emitido é válido (parsea via lxml/html.parser sem erro).
4. Sub-sprints UX-M-02.A..D escritas e linkadas (mas não executadas nesta sprint).
5. Lint, smoke, tests verdes.

## Não-objetivos

- NÃO criar CSS dos componentes (isso é UX-M-03).
- NÃO migrar todas as páginas (isso vira sub-sprints separadas).

## Referência

- UX-M-01 (depende de) — tokens CSS centralizados.
- UX-M-03 (bloqueia) — CSS escopado por componente.

*"Um botão. Em um lugar. Para todas as páginas." — princípio da Onda M*
