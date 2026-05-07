---
id: UX-M-02.A
titulo: Migração cluster Documentos para ui.py canônico
status: concluida_parcial
prioridade: alta
data_criacao: 2026-05-06
concluida_em: 2026-05-06
fase: MODULARIZAÇÃO
depende_de: [UX-M-02, UX-M-03]
co_executavel_com: [UX-M-02.B, UX-M-02.C, UX-M-02.D]
esforco_estimado_horas: 4
sprint_filha: UX-M-02.A-RESIDUAL
ressalva: |
  Critérios 1, 3 e 4 (remoção de _CSS_LOCAL_* e redução ≥40% das páginas)
  bloqueados por achado empírico (padrão (k)): as classes `.ouroboros-*`
  definidas em busca.py e catalogacao.py NÃO são duplicatas de
  components.css, são genuinamente específicas. Restrições invioláveis
  da sub-sprint proíbem promovê-las para components.css ou criar
  componentes em ui.py. Trabalho restante migrado para UX-M-02.A-RESIDUAL.
  Critérios 2, 5 e 6 entregues (imports de tema -> ui em 7 páginas;
  19/19 testes regressivos verdes; validação visual sem regressão).
---

# Sprint UX-M-02.A — Migração cluster Documentos

## Contexto

Após UX-M-02 entregar `ui.py` consolidado e UX-M-03 entregar `components.css` canônico, as páginas existentes continuam usando imports antigos (`from tema import callout_html`) e `_CSS_LOCAL_*` próprios. Esta sub-sprint migra as páginas do cluster **Documentos** para usar exclusivamente `ui.py` + classes canônicas.

## Páginas afetadas (cluster Documentos)

| Arquivo | Tem `_CSS_LOCAL_*`? | Ação |
|---|---|---|
| `src/dashboard/paginas/busca.py` | SIM (`_CSS_LOCAL_BUSCA`, ~141 linhas CSS) | Migrar |
| `src/dashboard/paginas/catalogacao.py` | SIM (`_CSS_LOCAL_CATALOGACAO`) | Migrar |
| `src/dashboard/paginas/completude.py` | NÃO (já modular pós-Onda T) | Validar imports |
| `src/dashboard/paginas/revisor.py` | NÃO | Validar imports |
| `src/dashboard/paginas/validacao_arquivos.py` | NÃO | Validar imports |
| `src/dashboard/paginas/extracao_tripla.py` | NÃO | Validar imports |
| `src/dashboard/paginas/grafo_obsidian.py` | NÃO | Validar imports |

**Foco principal: 2 páginas com CSS local (`busca.py`, `catalogacao.py`).**

## Objetivo

1. Substituir `_CSS_LOCAL_BUSCA` e `_CSS_LOCAL_CATALOGACAO` por imports de `ui.py` que carregam classes canônicas de `components.css` (M-03).
2. Trocar `from src.dashboard.tema import callout_html, chip_html, ...` por `from src.dashboard.componentes.ui import ...` em todas as 7 páginas do cluster.
3. Reduzir linhas das 2 páginas com CSS local em ≥40%.

## Validação ANTES (grep obrigatório)

```bash
# Volume de CSS local nas páginas-alvo
grep -c "_CSS_LOCAL\|<style>" src/dashboard/paginas/busca.py
# Esperado: ≥1 (CSS local presente)

grep -c "_CSS_LOCAL\|<style>" src/dashboard/paginas/catalogacao.py
# Esperado: ≥1

# Imports atuais
grep -E "from src.dashboard.tema import" src/dashboard/paginas/{busca,catalogacao,completude,revisor,validacao_arquivos,extracao_tripla,grafo_obsidian}.py
# Listar imports a trocar

# ui.py existe (M-02)?
test -f src/dashboard/componentes/ui.py && echo "M-02 OK"

# components.css existe (M-03)?
test -f src/dashboard/css/components.css && echo "M-03 OK"

# Baseline de tamanho
wc -l src/dashboard/paginas/busca.py src/dashboard/paginas/catalogacao.py
# Registrar para comparar no DEPOIS
```

## Spec de implementação

### Regra geral de migração (aplicar a cada página)

1. **Substituir bloco `_CSS_LOCAL_X`**:
   - Identificar regras CSS no bloco que JÁ EXISTEM em `components.css` (são duplicatas — remover).
   - Identificar regras CSS que são genuinamente específicas da página (são raras — manter ou propor classe nova em M-03).
   - Remover `st.markdown(_CSS_LOCAL_X, unsafe_allow_html=True)` do `renderizar()`.

2. **Trocar imports**:
   ```python
   # ANTES
   from src.dashboard.tema import (
       CORES, callout_html, chip_html, card_html
   )

   # DEPOIS
   from src.dashboard.tema import CORES  # constantes
   from src.dashboard.componentes.ui import callout_html, chip_html, card_html  # componentes
   ```

3. **Trocar HTML inline por componentes**:
   ```python
   # ANTES (em busca.py)
   st.markdown(
       '<div class="ouroboros-search-bar">...</div>',
       unsafe_allow_html=True,
   )

   # DEPOIS (usar componente canônico)
   from src.dashboard.componentes.ui import search_bar_html
   st.markdown(
       search_bar_html(placeholder="Buscar...", kbd_hint="/"),
       unsafe_allow_html=True,
   )
   ```

### Páginas sem CSS local (5 páginas)

`completude.py`, `revisor.py`, `validacao_arquivos.py`, `extracao_tripla.py`, `grafo_obsidian.py`:

- Apenas trocar imports de `tema` para `ui` quando aplicável.
- Validar visualmente sem regressão.

## Validação DEPOIS

```bash
# Sem CSS local nas 2 páginas migradas
grep -c "_CSS_LOCAL\|<style>" src/dashboard/paginas/busca.py
# Esperado: 0

grep -c "_CSS_LOCAL\|<style>" src/dashboard/paginas/catalogacao.py
# Esperado: 0

# Imports trocados em 7 páginas
grep -c "from src.dashboard.componentes.ui import" src/dashboard/paginas/busca.py
# Esperado: ≥1

# Tamanho reduzido
wc -l src/dashboard/paginas/busca.py
# Esperado: ≥40% menor que baseline

# Lint, smoke, tests
make lint && make smoke && pytest tests/test_busca_global.py tests/test_catalogacao_humanizado.py -q
```

## Proof-of-work

```bash
# Restart dashboard
pkill -f "streamlit run" 2>/dev/null || true
make dashboard &
sleep 5

# Validação visual playwright batch das 7 páginas:
# - Busca Global (cluster=Documentos&tab=Busca+Global)
# - Catalogação (cluster=Documentos&tab=Catalogação)
# - Completude (cluster=Documentos&tab=Completude)
# - Revisor (cluster=Documentos&tab=Revisor)
# - Validação por Arquivo (cluster=Documentos&tab=Validação+por+Arquivo)
# - Grafo + Obsidian (cluster=Documentos&tab=Grafo+%2B+Obsidian)

# Comparar com mockups canônicos:
# - novo-mockup/mockups/06-busca-global.html
# - novo-mockup/mockups/07-catalogacao.html
# - novo-mockup/mockups/08-completude.html
# - novo-mockup/mockups/09-revisor.html
# - novo-mockup/mockups/10-validacao.html
```

## Critério de aceitação

1. `_CSS_LOCAL_BUSCA` e `_CSS_LOCAL_CATALOGACAO` removidos.
2. 7 páginas do cluster Documentos importam componentes via `ui.py`.
3. Tamanho de `busca.py` reduzido ≥40% em linhas.
4. Tamanho de `catalogacao.py` reduzido ≥40% em linhas.
5. Lint OK + smoke 10/10 + testes regressivos verdes (test_busca_global, test_catalogacao_humanizado).
6. Validação visual: 7 páginas idênticas ao mockup canônico (sem regressão vs commit baseline).

## Não-objetivos

- NÃO migrar páginas de outros clusters (sub-sprints B/C/D fazem).
- NÃO mudar comportamento ou lógica das páginas — só CSS/imports.
- NÃO criar componentes novos — usar `ui.py` existente.

## Referência

- UX-M-02 (depende) — `ui.py` consolidado.
- UX-M-03 (depende) — `components.css` canônico.
- `novo-mockup/mockups/06-busca-global.html` — fonte visual.
- `novo-mockup/mockups/07-catalogacao.html` — fonte visual.

*"Migrar uma página é validar se ui.py é mesmo canônico." — princípio M-02.x*
