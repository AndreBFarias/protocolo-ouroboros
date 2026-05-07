---
id: UX-M-02.A-RESIDUAL
titulo: Residual de CSS local em busca.py e catalogacao.py (Onda M)
status: backlog
prioridade: media
data_criacao: 2026-05-06
fase: MODULARIZAÇÃO
depende_de: [UX-M-02.A, UX-M-02, UX-M-03]
esforco_estimado_horas: 3
origem: sprint-filha gerada durante execução de UX-M-02.A (achado-bloqueio padrão (k))
---

# Sprint UX-M-02.A-RESIDUAL — Migrar CSS local específico de Busca/Catalogação

## Contexto

Durante a execução de UX-M-02.A, a hipótese da spec ("regras de `_CSS_LOCAL_*`
JÁ EXISTEM em `components.css` -- duplicatas a remover") foi **REFUTADA por
grep** (padrão `(k)` -- hipótese da spec não é dogma).

Comparação literal entre as 9 classes definidas em `_CSS_LOCAL_BUSCA` e as
classes públicas de `components.css`: **zero overlap**. As classes
`.ouroboros-search-bar`, `.ouroboros-facet-card`, `.ouroboros-res-group`,
`.ouroboros-res-head`, `.ouroboros-res-row`, `.ouroboros-res-title`,
`.ouroboros-res-meta`, `.ouroboros-res-snippet`, `.ouroboros-busca-contagem`
são **genuinamente específicas** da página Busca Global.

Mesmo cenário em `_CSS_LOCAL_CATALOGACAO`: `.ouroboros-cat-toolbar` é
específica da Catalogação.

A restrição inviolável de UX-M-02.A proíbe (i) modificar `components.css`,
(ii) modificar `ui.py`, (iii) remover `_CSS_LOCAL_*` (quebraria visual sem
substituto). Logo, o critério de aceitação 1 ("`_CSS_LOCAL_BUSCA` e
`_CSS_LOCAL_CATALOGACAO` removidos") e os critérios 3-4 ("≥40% redução")
ficam **inalcançáveis sem nova decisão arquitetural**.

## Objetivo

Decidir e executar UMA das três opções a seguir, em sprint própria
(autorizada a tocar `components.css` / `ui.py`):

### Opção A — Promover classes para components.css

Mover as 10 classes (`.ouroboros-search-bar`, `.ouroboros-facet-card`,
`.ouroboros-res-*` x6, `.ouroboros-busca-contagem`, `.ouroboros-cat-toolbar`)
para `src/dashboard/css/components.css` sob bloco "BUSCA E CATALOGAÇÃO".
Atualizar `novo-mockup/_shared/components.css` espelho.

Prós: estilos passam a ser canônicos, qualquer página pode reutilizar.
Contras: classes `.ouroboros-*` poluem fronteira "components.css" se
nunca forem reusadas.

### Opção B — Criar componentes em ui.py

Criar `search_bar_html()`, `facet_card_html()`, `result_group_html()`,
`busca_contagem_html()`, `cat_toolbar_html()` em `ui.py`. Cada componente
emite o HTML completo + injeta o CSS necessário (via `<style>` inline
contido). `_CSS_LOCAL_*` desaparece das páginas.

Prós: API Python encapsula HTML + CSS. Páginas ficam mais limpas.
Contras: 5 funções novas em `ui.py`, possivelmente quebra limite 800L.

### Opção C — Manter `_CSS_LOCAL_*` formalmente como exceção

Documentar no rodapé de `ui.py` e em `VALIDATOR_BRIEF.md` que páginas
podem manter blocos CSS locais quando as classes são exclusivas àquela
página. Sprint UX-M-02.A é fechada com critério 1/3/4 marcados N/A.

Prós: zero edit, zero risco visual.
Contras: a fronteira "ui.py + components.css canônicos" fica com
exceção permanente -- o que UX-M-03 tentou eliminar.

## Recomendação

**Opção A** é a mais alinhada com a Onda M (canonização visual). Volume
pequeno (≈90 linhas CSS), risco baixo, valor canônico alto. Executar
em sprint UX-M-02.A-RESIDUAL com escopo: editar `components.css` +
`novo-mockup/_shared/components.css` (espelho) + remover `_CSS_LOCAL_*`
+ atualizar testes regressivos `test_busca_global.py` (se assertam
texto "_CSS_LOCAL_BUSCA").

## Validação ANTES (grep obrigatório)

```bash
# Quais classes existem em busca.py + catalogacao.py?
grep -oE '\.ouroboros-[a-z-]+' src/dashboard/paginas/busca.py | sort -u
grep -oE '\.ouroboros-[a-z-]+' src/dashboard/paginas/catalogacao.py | sort -u
# Esperado: 9 + 1 = 10 classes

# Nenhuma já existe em components.css?
for c in $(grep -oE '\.ouroboros-[a-z-]+' src/dashboard/paginas/busca.py src/dashboard/paginas/catalogacao.py | sort -u); do
    grep -c "$c" src/dashboard/css/components.css
done
# Esperado: zero

# Quem mais usa essas classes? (validar reuso futuro)
grep -rE '\.ouroboros-(search-bar|facet-card|res-|busca-contagem|cat-toolbar)' src/ novo-mockup/ docs/ 2>/dev/null
```

## Proof-of-work

```bash
# Pós-Opção A:
make lint && make smoke && pytest tests/test_busca_global.py tests/test_catalogacao_humanizado.py -q

# Validação visual: 7 páginas do cluster Documentos sem regressão.
# Comparar antes/depois com playwright + diff visual.

# Tamanho:
wc -l src/dashboard/paginas/busca.py src/dashboard/paginas/catalogacao.py
# Esperado: -141L em busca.py, -32L em catalogacao.py
```

## Critério de aceitação

1. `_CSS_LOCAL_BUSCA` e `_CSS_LOCAL_CATALOGACAO` removidos.
2. Classes promovidas para `components.css` + espelho `novo-mockup/_shared/`.
3. `busca.py` reduzido de 1212L para ≤ 1071L (≥141L).
4. `catalogacao.py` reduzido de 671L para ≤ 639L (≥32L).
5. Lint OK + smoke 10/10 + 19 testes passados (mesmo baseline UX-M-02.A).
6. Validação visual cluster Documentos sem regressão.

## Não-objetivos

- NÃO criar componentes Python novos em `ui.py` (Opção B descartada).
- NÃO mexer em outros clusters (B/C/D fazem).
- NÃO mudar lógica das páginas.

## Referência

- Sprint UX-M-02.A (concluída parcialmente, ver achado-bloqueio).
- VALIDATOR_BRIEF padrão `(k)` -- hipótese da spec não é dogma.
- VALIDATOR_BRIEF padrão `(l)` -- achado colateral vira sprint-filha.

*"O que não tem dono canônico, não tem futuro." -- princípio Onda M*
