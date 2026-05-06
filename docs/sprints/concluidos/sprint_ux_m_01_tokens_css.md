---
id: UX-M-01
titulo: Tokens CSS centralizados em um único arquivo
status: concluida
concluida_em: 2026-05-06
prioridade: alta
data_criacao: 2026-05-06
data_revisao: 2026-05-06
fase: MODULARIZAÇÃO
depende_de: []
bloqueia: [UX-M-02, UX-M-03]
co_executavel_com: [UX-M-04]
esforco_estimado_horas: 3-5
esforco_real_horas: ~30min
---

# Sprint UX-M-01 — Tokens CSS centralizados

## Contexto

Sessão de auditoria visual em 2026-05-06 expôs que o dashboard tem **CSS local em 17 páginas** (`_CSS_LOCAL_BUSCA`, `_CSS_LOCAL_CONTAS`, etc.) com 50-300 linhas inline cada. Cores, fontes, espaçamentos e bordas são repetidos em sintaxe `var(--accent-purple, var(--color-destaque))` (com fallback) em centenas de pontos.

Cada ajuste de design exige tocar dezenas de arquivos. Modelo insustentável — dono caracterizou como "trabalho de corno eterno" em 2026-05-06.

**Achado da auditoria 2026-05-06:** a fonte canônica de tokens **JÁ EXISTE** em `novo-mockup/_shared/tokens.css` (138 linhas, 50+ tokens). O mockup é a fonte de verdade do redesign. Sprint UX-RD-02 já trouxe esses tokens para `tema_css.py` mas em formato hard-coded dentro de Python, não como arquivo CSS separado.

## Objetivo

**Extrair** os tokens CSS de `tema_css.py` para um arquivo único `src/dashboard/css/tokens.css` (cópia 1:1 de `novo-mockup/_shared/tokens.css`). `tema_css.py` carrega esse arquivo via `Path.read_text()` no início do `css_global()`. `tema.py` continua exportando constantes Python (`CORES`, `SPACING`, etc.) como **espelho** dos tokens CSS — manter sincronizado por convenção (comment header obrigatório).

## Hipótese

**A**: tokens vivem em CSS estático único; Python lê via I/O.
**Anti-A** (descartada): manter tokens hard-coded em string Python como hoje.

Razão A: arquivo CSS é editável por designer/humano sem entender Python; é fonte canônica para validação cruzada com mockup; reduz `tema_css.py` em ~150 linhas.

## Validação ANTES (grep obrigatório)

```bash
# Confirmar volume real do problema
grep -rn "var(--.*,\s*var(--" src/dashboard/ | wc -l
# Esperado: > 100 ocorrências (fallbacks duplicados)

# Confirmar tamanho atual de tema_css.py
wc -l src/dashboard/tema_css.py
# Esperado: ~1675 linhas

# Confirmar fonte canônica do mockup
wc -l novo-mockup/_shared/tokens.css
# Esperado: 138 linhas

# Listar todos os tokens citados em fallback
grep -rho "var(--[a-z0-9-]*" src/dashboard/ | sort -u | wc -l
# Esperado: 30-60 tokens canônicos
```

## Spec de implementação

### 1. Criar `src/dashboard/css/tokens.css` (arquivo novo)

**Conteúdo: cópia 1:1 de `novo-mockup/_shared/tokens.css`** (NÃO criar tokens novos — usar fonte canônica).

```bash
mkdir -p src/dashboard/css
cp novo-mockup/_shared/tokens.css src/dashboard/css/tokens.css
```

Adicionar header no topo do arquivo destino:

```css
/* Tokens CSS canônicos do dashboard Ouroboros.
 * Fonte: novo-mockup/_shared/tokens.css (mantida 1:1).
 * Espelho Python: src/dashboard/tema.py (CORES, SPACING, FONTE_*).
 * Sprint UX-M-01 — Onda M (modularização).
 *
 * REGRA: ao editar QUALQUER token aqui, atualizar o espelho em tema.py
 * na mesma sprint. Inconsistência = bug visual silencioso.
 */
```

### 2. Refatorar `src/dashboard/tema_css.py`

- Adicionar no topo:

```python
from pathlib import Path

_RAIZ_DASHBOARD = Path(__file__).resolve().parent
_TOKENS_CSS = (_RAIZ_DASHBOARD / "css" / "tokens.css").read_text(encoding="utf-8")
```

- Remover bloco `:root` do redesign que estava hard-coded em `_root_redesign()` (substituir o conteúdo da função para retornar `_TOKENS_CSS`).
- **Manter** bloco `:root` legado `_root_legado()` como está (14 páginas + 81 testes dependem; migração futura, fora desta sprint).

### 3. Refatorar `src/dashboard/tema.py`

- Adicionar comment header acima do dict `CORES`:

```python
# ─────────────────────────────────────────────────────────────────────
# CORES — espelho de src/dashboard/css/tokens.css (UX-M-01).
# Manter sincronizado: editar AQUI e em tokens.css na MESMA sprint.
# Inconsistência = bug visual silencioso (CSS usa um valor, Python outro).
# ─────────────────────────────────────────────────────────────────────
```

- Adicionar mesmo comment acima de `SPACING` e `FONTE_*`.
- **NÃO** mudar valores nem assinaturas (compat com 14 páginas legadas + testes).

### 4. Substituir fallbacks `var(--moderno, var(--legado))` em CSS local das páginas

Sed automatizado:

```bash
# Trocar var(--moderno, var(--legado)) por var(--moderno) em arquivos Python
find src/dashboard/paginas/ -name "*.py" -exec sed -i \
  's/var(--\([a-z0-9-]*\), var(--[a-z0-9-]*)/var(--\1)/g' {} \;
```

Verificação manual após sed: confirmar nenhum fallback restante via grep (esperado: 0 ocorrências).

## Estratégia tema.py vs tokens.css

| Aspecto | tokens.css | tema.py |
|---|---|---|
| Tipo | CSS estático | Constantes Python |
| Fonte de verdade | SIM (canônico) | Espelho |
| Editável por humano sem Python? | SIM | Não (precisa entender módulo) |
| Usado por | CSS injetado em runtime | Código Python (formatação valores, lógica) |
| Manutenção | Edit + sync tema.py mesma sprint | Edit + sync tokens.css mesma sprint |

**Não-objetivo:** unificar tokens.css e tema.py em runtime via parser. Sincronia é responsabilidade humana, validada por testes (lazy: nenhum teste hoje, criar é fora de escopo).

## Impedimentos conhecidos

1. **Streamlit não suporta `@import url(...)` em `<style>` injetado** — testado em sprints anteriores, regras `@import` são ignoradas pelo CSS-in-JS interno. Solução: ler `tokens.css` via `Path.read_text()` e CONCATENAR ao CSS no `css_global()`. Já é o padrão do projeto.

2. **Caracter encoding** — `tokens.css` deve ser UTF-8 puro (sem BOM). Sprint pode falhar se editor adicionar BOM no Windows.

3. **`tokens.css` vs `tema_css.py._root_legado()`**: o CSS legado (`--color-fundo`, `--spacing-*`, `--font-*`) NÃO é coberto por esta sprint. Migrar legado é débito separado em ondas futuras (ver não-objetivos).

## Validação DEPOIS

```bash
# Sem fallbacks remanescentes
grep -rn "var(--.*,\s*var(--" src/dashboard/ | wc -l
# Esperado: 0

# tokens.css existe e tem mesmo tamanho do mockup
diff -q src/dashboard/css/tokens.css novo-mockup/_shared/tokens.css | head -1
# Esperado: vazio (ou apenas diff em comment header)

# tema_css.py reduziu (≥100 linhas a menos)
wc -l src/dashboard/tema_css.py
# Esperado: ~1500 linhas (era ~1675)

# Lint, smoke, tests
make lint && make smoke && pytest tests/ -q
```

## Proof-of-work

```bash
# Restart dashboard
pkill -f "streamlit run" 2>/dev/null || true
make dashboard &
sleep 5

# Verificar que CSS canônico está sendo emitido
curl -s http://127.0.0.1:8765 | grep -c "accent-purple: #bd93f9"
# Esperado: ≥1 (token presente no HTML servido)

# Validação visual via playwright (5 páginas-amostra)
# - Visão Geral: hero deve manter cor purple #bd93f9
# - Busca Global: borda do search-bar mantém purple
# - Catalogação: KPIs mantêm cores semânticas
# - Contas: cards de banco com cor de banco preservada
# - Projeções: linhas do gráfico nas cores Dracula
```

## Critério de aceitação

1. `src/dashboard/css/tokens.css` existe e é cópia 1:1 de `novo-mockup/_shared/tokens.css` (exceto header comment).
2. `tema_css.py` carrega `tokens.css` UMA vez via `Path.read_text()`.
3. Zero fallbacks `var(--, var(--))` em `src/dashboard/`.
4. `tema.py` tem comment header sobre espelho de `tokens.css` em CORES, SPACING, FONTE_*.
5. `tema_css.py` reduziu ≥100 linhas.
6. Lint, smoke, tests verdes.
7. Validação visual: 5 páginas-amostra sem regressão.

## Não-objetivos (escopo fechado)

- NÃO migrar bloco `:root` legado (`--color-*`, `--spacing-*`, `--font-*`) — débito separado.
- NÃO criar tokens novos — só copiar do mockup.
- NÃO remover CSS local das páginas (isso é UX-M-02 + UX-M-03).
- NÃO criar componentes universais HTML (isso é UX-M-02).
- NÃO mexer em `instalar_fix_sidebar_padding` (isso é UX-M-04).
- NÃO criar testes de sincronia tokens.css ↔ tema.py — sprint futura.

## Referência

- `novo-mockup/_shared/tokens.css` — fonte canônica.
- `src/dashboard/tema.py` — espelho Python.
- `src/dashboard/tema_css.py::_root_redesign()` — bloco a refatorar.
- UX-M-02 (bloqueia) — componentes universais.
- UX-M-03 (bloqueia) — CSS escopado.

## Dúvidas que NÃO precisam ser perguntadas (já respondidas)

- "Devo criar tokens novos?" Não — copiar do mockup.
- "E o `:root` legado?" Não-objetivo, fica como está.
- "Streamlit suporta `@import`?" Não — usar `Path.read_text() + concat`.
- "Quem é fonte de verdade, CSS ou Python?" CSS. Python é espelho.

*"O design começa com o token, não com o pixel." — princípio da Onda M*
