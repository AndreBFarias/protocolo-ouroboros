---
id: UX-M-01
titulo: Tokens CSS centralizados em um único arquivo
status: backlog
prioridade: alta
data_criacao: 2026-05-06
fase: MODULARIZAÇÃO
depende_de: []
bloqueia: [UX-M-02, UX-M-03, UX-M-04]
---

# Sprint UX-M-01 — Tokens CSS centralizados

## Contexto

Sessão de auditoria visual em 2026-05-06 expôs que o dashboard tem **CSS local em 17 páginas** (`_CSS_LOCAL_BUSCA`, `_CSS_LOCAL_CONTAS`, etc.) com 50-300 linhas inline cada. Cores, fontes, espaçamentos e bordas são repetidos em sintaxe `var(--accent-purple, var(--color-destaque))` (com fallback) em centenas de pontos.

Cada ajuste de design exige tocar dezenas de arquivos. Modelo insustentável — dono caracterizou como "trabalho de corno eterno" em 2026-05-06.

## Objetivo

Centralizar **TODOS** os tokens de design em um único arquivo `src/dashboard/css/tokens.css` carregado UMA vez via `tema_css.py`. Eliminar fallbacks `var(--moderno, var(--legado))` — usar só variável canônica única por token.

## Hipótese

Tokens repetidos hoje em pelo menos 3 lugares:
1. `tema.py` constantes Python (`CORES`, `SPACING`, `FONTE_*`)
2. `tema_css.py` regras CSS no `:root`
3. CSS local de cada página (com fallbacks)

Se centralizarmos os 3 em um `tokens.css` único e fizermos `tema.py` ler dele (ou expor as constantes Python que espelhem), eliminamos a tripla.

## Validação ANTES (grep obrigatório)

```bash
# Confirmar volume real do problema
grep -rn "var(--.*,\s*var(--" src/dashboard/ | wc -l
# Esperado: > 100 ocorrências (fallbacks duplicados)

# Confirmar quantos CSS locais existem
grep -rln "_CSS_LOCAL\|_CSS_INLINE" src/dashboard/paginas/ | wc -l
# Esperado: ~17

# Listar todos os tokens citados em fallback
grep -rho "var(--[a-z-]*" src/dashboard/ | sort -u | wc -l
# Esperado: ~30-50 tokens canônicos
```

## Spec de implementação

### 1. Criar `src/dashboard/css/tokens.css` (arquivo novo)

Estrutura:

```css
/* Cores Dracula canônicas */
:root {
  --bg-base: #0e0f15;
  --bg-surface: #1a1d28;
  --bg-inset: #252835;
  --text-primary: #f8f8f2;
  --text-secondary: #b8b8c5;
  --text-muted: #6b7080;
  --accent-purple: #bd93f9;
  --accent-cyan: #8be9fd;
  --accent-green: #50fa7b;
  --accent-yellow: #f1fa8c;
  --accent-red: #ff5555;
  --accent-orange: #ffb86c;
  --accent-pink: #ff79c6;
  --border-subtle: rgba(98, 114, 164, 0.25);

  /* Fontes */
  --ff-mono: 'JetBrains Mono', 'Fira Code', monospace;
  --ff-sans: 'Inter', system-ui, sans-serif;

  /* Tamanhos */
  --fs-display: 40px;
  --fs-h1: 28px;
  --fs-h2: 20px;
  --fs-h3: 16px;
  --fs-body: 14px;
  --fs-label: 11px;
  --fs-mono: 12px;

  /* Espaçamentos */
  --sp-1: 4px;
  --sp-2: 8px;
  --sp-3: 12px;
  --sp-4: 16px;
  --sp-5: 20px;
  --sp-6: 24px;
  --sp-7: 32px;
  --sp-8: 40px;

  /* Bordas */
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
}
```

### 2. Refatorar `src/dashboard/tema_css.py`

- Carregar `tokens.css` no início via `(_RAIZ / "css" / "tokens.css").read_text()`.
- Remover seção `:root` antiga do CSS injetado.
- Remover fallbacks `var(--novo, var(--legado))` — manter só variável canônica.

### 3. Refatorar `src/dashboard/tema.py`

- `CORES` continua dict Python para compat com código que lê em runtime.
- Constantes alinhadas 1:1 com tokens CSS (mesmo nome, mesmo valor).
- Adicionar comment header "Espelho de tokens.css — manter sincronizado".

### 4. Substituir fallbacks em CSS local das páginas

Script automatizado:
```bash
# Trocar var(--moderno, var(--legado)) por var(--moderno) em todos os arquivos
find src/dashboard/paginas/ -name "*.py" -exec sed -i \
  's/var(--\([a-z-]*\), var(--[a-z-]*)/var(--\1)/g' {} \;
```

Verificação manual após sed: confirmar nenhum fallback restante via grep.

## Validação DEPOIS

```bash
# Sem fallbacks remanescentes
grep -rn "var(--.*,\s*var(--" src/dashboard/ | wc -l
# Esperado: 0

# Tokens carregam de UM lugar só
grep -rn "var(--accent-purple)" src/dashboard/ | head -3
# Esperado: várias referências, nenhuma com fallback

# Smoke 10/10
make smoke

# Lint 0
make lint

# Testes baseline ou crescida
pytest tests/ -q
```

## Proof-of-work

```bash
make dashboard
# Abrir http://127.0.0.1:8765/?cluster=Home&tab=Visão+Geral
# Validar visualmente: layout idêntico ao estado anterior (cores Dracula
# preservadas, sem regressão visual).
```

## Critério de aceitação

1. `tokens.css` existe e contém todos os tokens canônicos (≥30 variáveis).
2. `tema_css.py` carrega `tokens.css` UMA vez.
3. Zero fallbacks `var(--, var(--))` no projeto.
4. `tema.py` constantes Python espelham tokens CSS 1:1.
5. Lint, smoke, tests verdes.
6. Validação visual: 5 páginas-amostra sem regressão (Visão Geral, Busca Global, Catalogação, Contas, Projeções).

## Não-objetivos (escopo fechado)

- NÃO remover CSS local das páginas (isso é UX-M-03).
- NÃO criar componentes universais HTML (isso é UX-M-02).
- NÃO mexer em `instalar_fix_sidebar_padding` (isso é UX-M-04).

## Referência

- `docs/sprints/backlog/sprint_ux_m_02_componentes_universais.md`
- `docs/sprints/backlog/sprint_ux_m_03_css_escopado.md`
- `docs/sprints/backlog/sprint_ux_m_04_shell_consolidado.md`

*"O design começa com o token, não com o pixel." — princípio da Onda M*
