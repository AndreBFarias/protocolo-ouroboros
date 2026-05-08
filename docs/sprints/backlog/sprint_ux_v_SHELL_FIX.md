---
id: UX-V-SHELL-FIX
titulo: Shell global — largura 100%, sidebar Buscar, alinhamento lupa, popover filtros
status: backlog
prioridade: alta
data_criacao: 2026-05-08
fase: PARIDADE_VISUAL
depende_de: []
esforco_estimado_horas: 3
origem: docs/auditorias/AUDITORIA_PARIDADE_VISUAL_2026-05-08.md M9 (achados imediatos do dono)
mockup: novo-mockup/mockups/00-shell-navegacao.html
afeta: TODAS as páginas
---

# Sprint UX-V-SHELL-FIX — 4 fixes do shell global

## Contexto

Inspeção visual ao vivo 2026-05-08 com o dono revelou 4 débitos do shell que afetam todas as páginas. UX-V-01 (filtro global chip-bar) e Onda M (modularização CSS) declararam fechamento mas estes débitos persistem:

**M9.1 — Layout não usa 100% da largura do monitor**: barras pretas/cinzas nas laterais; app ocupa ~1568px central enquanto monitor pode ir além.

**M9.2 — Largura da sidebar corta input "Buscar"**: placeholder "Buscar" truncado, atalho `/` colado na borda.

**M9.3 — Lupa SVG desalinhada**: glyph "Q" da lupa fora do baseline do texto.

**M9.4 — Filtros globais (chip-bar) com polish ruim**: popover Streamlit-nativo desproporcional ao chip; padding interno errado.

## Objetivo

1. **M9.1**: aplicar `.main .block-container { max-width: 100% !important; padding-left: var(--sp-4); padding-right: var(--sp-4); }` em CSS global em `tema_css.py`.
2. **M9.2**: ajustar `width` da sidebar Streamlit (CSS `[data-testid="stSidebar"] { min-width: 280px; max-width: 320px; }`); garantir input + atalho cabem.
3. **M9.3**: padronizar SVG lupa com `vertical-align: middle` ou `display: inline-flex; align-items: center` em `_components.css` da search-bar.
4. **M9.4**: revisar dimensões do popover de filtros globais (`width` proporcional ao chip, `padding` interno menor, borda visível).

## Validação ANTES (grep)

```bash
grep -n "block-container\|max-width\|stSidebar\|popover\|lupa\|search-bar" src/dashboard/tema_css.py src/dashboard/css/ -r | head -20
```

## Não-objetivos

- NÃO mudar tokens canônicos (cores, raios, fontes).
- NÃO afetar layout específico de páginas.
- NÃO reescrever a chip-bar (V-01 já fez); só ajuste de popover.

## Proof-of-work

```bash
make lint && make smoke
.venv/bin/pytest tests/ -q  # baseline mantida
```

Captura visual em 5 páginas (Visão Geral, Pagamentos, Catalogação, Bem-estar Hoje, Editor TOML) deve mostrar:
1. Layout ocupando 100% width (sem barras laterais pretas).
2. Sidebar com input "Buscar" + atalho `/` visíveis sem truncate.
3. Lupa alinhada com baseline do texto.
4. Popover de filtro proporcional ao chip.

## Critério de aceitação

1. Layout 100% width em viewport >=1280px.
2. Sidebar input "Buscar..." sem truncate.
3. Lupa alinhada visualmente.
4. Popover dos 4 chips proporcional.
5. Lint + smoke + baseline pytest 1.620+.

## Referência

- Auditoria: `AUDITORIA_PARIDADE_VISUAL_2026-05-08.md` M9.
- VALIDATOR_BRIEF: `(w)` (anti-padrão JS global afetando todas páginas).

*"Shell ruim contamina todas as páginas." — princípio V-SHELL-FIX*
