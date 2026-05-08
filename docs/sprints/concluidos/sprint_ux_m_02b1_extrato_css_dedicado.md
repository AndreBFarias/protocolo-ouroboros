---
id: UX-M-02.B.1
titulo: Extrair `_estilos_locais_html` de extrato.py para CSS dedicado
status: concluída
prioridade: media
data_criacao: 2026-05-06
concluida_em: 2026-05-06
fase: MODULARIZAÇÃO
depende_de: [UX-M-02.B]
sprint_pai: UX-M-02.B
esforco_estimado_horas: 2
commit: 9309ff8
---

## Fechamento (retroativo — padrão `(v)`)

Sprint executada no commit `9309ff8` ("fix(ux-m-residual): zero debito -- 6 CSS extraidos + plotly undefined") em 2026-05-06, junto com 5 outras páginas (busca, catalogacao, categorias, inbox, skills_d7) e fix do `tema_plotly` (title.font undefined).

Resultado para extrato.py:
- 1381 → 1046 linhas (−335L = −24,3%) — supera meta ≥325L (≥23%).
- `src/dashboard/css/paginas/extrato.css` criado (331L).
- `_estilos_locais_html()` removida; carregamento via `carregar_css_pagina("extrato")` (linha 543).
- 0 resíduos `_CSS_LOCAL_*` ou `<style>` inline em `extrato.py`.

Validação rodada em 2026-05-08 (worktree `agent-ad7a77d89a6c9f34d`):
- `make lint` exit 0.
- `make smoke` exit 0 (23 checagens, 0 erros).
- `pytest tests/test_extrato_redesign.py tests/test_dashboard_extrato_paginacao.py tests/test_dashboard_filtros_extrato.py -q` → 33 passed.

Atributos `style="..."` decorativos pontuais em `extrato.py` (cor dinâmica, percentuais calculados) ficam preservados conforme não-objetivo da spec ("NÃO refatorar lógica Python de extrato.py — somente CSS").

# Sprint UX-M-02.B.1 — Extrair CSS local de extrato.py

## Origem

Sprint-filha derivada de UX-M-02.B (achado colateral, padrão `(l)`).

Durante a migração de imports do cluster Finanças, identificou-se que a função `_estilos_locais_html()` em `src/dashboard/paginas/extrato.py` (linhas 500-844, ~345 linhas) contém classes CSS específicas (`.t02-kpi*`, `.t02-filt-bar`, `.t02-chip`, `.extrato-saldo-*`, `.t02-cat-bar`, `.t02-dot`, `.extrato-mini-kpi`) que:

1. NÃO duplicam classes canônicas em `src/dashboard/css/components.css` (descartado padrão M-03 trivial).
2. São específicas do mockup `novo-mockup/mockups/02-extrato.html` (variações de KPI, filtros, breakdown de categorias).
3. Inflam `extrato.py` para 1378 linhas (acima do ideal de 800L do padrão `(h)`).

## Objetivo

Extrair `_estilos_locais_html()` de `extrato.py` para arquivo CSS dedicado, carregado on-demand quando a página Extrato renderiza.

## Opções de implementação

### Opção A — CSS dedicado por página (preferida)

1. Criar `src/dashboard/css/paginas/extrato.css` contendo o CSS literal de `_estilos_locais_html`.
2. Em `tema_css.py`, adicionar registro on-demand: ao renderizar página `extrato`, injetar `<link rel="stylesheet" href=".../extrato.css">` ou `<style>{conteúdo}</style>` via `minificar`.
3. Remover `_estilos_locais_html()` de `extrato.py` e a chamada `st.markdown(_estilos_locais_html(), unsafe_allow_html=True)` na linha 875.

### Opção B — Promover classes específicas para `components.css`

1. Renomear `.t02-*` para nomenclatura canônica (`.kpi-grid-fixed-4`, `.filt-bar-inline`, etc).
2. Adicionar em `components.css` (afeta todas páginas — risco de drift visual).

**Recomendação**: Opção A (escopo isolado, baixo risco).

## Validação ANTES (grep obrigatório — padrão `(k)`)

```bash
wc -l src/dashboard/paginas/extrato.py
# Esperado: 1378

grep -n "_estilos_locais_html\|<style>" src/dashboard/paginas/extrato.py
# Esperado: 3 matches (def, chamada, <style> dentro)

ls src/dashboard/css/paginas/ 2>/dev/null
# Esperado: NÃO existe (criar nesta sprint)
```

## Validação DEPOIS

```bash
wc -l src/dashboard/paginas/extrato.py
# Esperado: ≤1050 (≥328L removidas)

ls src/dashboard/css/paginas/extrato.css
# Esperado: existe

grep -c "_estilos_locais_html\|<style>" src/dashboard/paginas/extrato.py
# Esperado: 0

make lint && make smoke && pytest tests/test_extrato_redesign.py tests/test_dashboard_extrato_paginacao.py tests/test_dashboard_filtros_extrato.py -q
# Esperado: lint OK, smoke 10/10, testes verdes

# Validação visual playwright: diff visual entre antes/depois deve ser zero
# (CSS idêntico, só mudou origem do carregamento).
```

## Critério de aceitação

1. `extrato.py` reduzido em ≥325L (≥23%).
2. `src/dashboard/css/paginas/extrato.css` criado contendo as classes específicas.
3. Lint OK + smoke 10/10 + testes regressivos verdes.
4. Validação visual: página Extrato pixel-perfect comparada ao baseline.

## Não-objetivos

- NÃO mexer em `components.css` (escopo M-03, congelado).
- NÃO migrar outras páginas do cluster (já cobertas em M-02.B).
- NÃO refatorar lógica Python de `extrato.py` (somente CSS).

## Referência

- Sprint-pai: UX-M-02.B (concluída 2026-05-06 com ressalvas).
- Padrões aplicáveis: `(a)` edit incremental, `(h)` limite 800L, `(l)` achado vira sprint-filha, `(s)` validação ANTES com grep.

*"CSS específico de página tem casa específica." — princípio M-02.B.1*
