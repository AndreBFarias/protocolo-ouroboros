# Roteiro Final do Redesign UX/RD — 14 sprints corretivas

> **Origem**: auditoria honesta `docs/auditorias/AUDITORIA_REDESIGN_2026-05-05.md` (seções 6, 7, 8).
> **Decisão arquitetural** (2026-05-05, dono): Decisão A confirmada — criar 5 páginas Bem-estar reais (Treinos, Marcos, Alarmes, Contadores, Tarefas). FIX-14 cobre as 5 páginas órfãs via deep-link interno.
> **Objetivo**: dashboard Streamlit `src/dashboard/` ficar **idêntico** aos 29 mockups em `novo-mockup/mockups/`.
> **Estado de partida** (2026-05-05): score consolidado 64/100. Produto-final esperado: ≥95/100.
> **Critério global de pronto**:
> - Todas as 29 telas com fidelidade ≥85% por dimensão (estrutura, tipografia, paleta, conteúdo, animação, gráfico).
> - Deep-link `?cluster=X&tab=Y` funcional para os 8 clusters × todas as abas declaradas + sub-rota `&secao=` para 5 órfãs Bem-estar.
> - `make lint` exit 0; `make smoke` 10/10; `pytest tests/ -q` baseline mantida ou crescida.
> - Zero TODO/FIXME inline; zero achado colateral pendurado.
> - Todos os .py novos com citação filosófica final (regra 10 do CLAUDE.md).

---

## Linha de montagem (DAG de dependências)

```
ONDA C1 -- Higiene crítica (paralela, ~1 dia total)
  FIX-01 (lint .md acentuação)        -- independente
  FIX-02 (bug Despesa R$ 0,00)        -- independente, isolado em extrato.py
  FIX-03 (kpi-grid minmax 220→180)    -- independente, 1 linha em tema_css.py
  FIX-04 (Material Symbols vazando)   -- independente, regra CSS
  FIX-05 (breadcrumb clicável)        -- independente, shell.py
  FIX-06 (h1 duplicado st.title)      -- independente, app.py:238

ONDA C2 -- Reconstrução estética (paralela, ~3 dias)
  FIX-07 (23 glyphs SVG portados)     -- independente
  FIX-08 (tipografia escala fina)     -- independente
  FIX-09 (Plotly modebar+Dracula)     -- independente

ONDA C3 -- Decisão A executada (~2 dias)
  FIX-10 (criar 5 páginas Bem-estar)  -- bloqueia FIX-11 e FIX-14

ONDA C4 -- Integração Bem-estar (~0,5 dia)
  FIX-11 (deep-link 12 abas)          -- depende de FIX-10

ONDA C5 -- Acabamento (paralela, ~1 dia)
  FIX-12 (acessibilidade WCAG)        -- independente
  FIX-14 (rota interna 5 órfãs)       -- depende de FIX-10 e FIX-11
  FIX-13 (citação filosófica em .py)  -- ÚLTIMA, toca tudo modificado pelas outras
```

**Tempo total estimado**: ~7-8 dias úteis com 1 IA executora + revisão humana entre ondas.
**Paralelizabilidade máxima**: C1 (6 sprints) + C2 (3 sprints) podem rodar em 9 worktrees paralelos.

---

## Tabela das 14 sprints

| ID | Nome | Onda | Esforço | Depende de | Bloqueia | Paths principais |
|---|---|--:|--:|---|---|---|
| FIX-01 | Lint acentuação 11 .md | C1 | 1h | -- | -- | docs/sprints/, novo-mockup/ |
| FIX-02 | Bug Despesa R$ 0,00 no Extrato | C1 | 2h | -- | -- | src/dashboard/paginas/extrato.py |
| FIX-03 | KPI grid minmax 220→180 | C1 | 30min | -- | -- | src/dashboard/tema_css.py |
| FIX-04 | Material Symbols vazando | C1 | 2h | -- | -- | src/dashboard/tema_css.py |
| FIX-05 | Breadcrumb clicável | C1 | 1h | -- | -- | src/dashboard/componentes/shell.py |
| FIX-06 | H1 duplicado (remover st.title) | C1 | 1h | -- | -- | src/dashboard/app.py |
| FIX-07 | 23 glyphs SVG portados | C2 | 1 dia | -- | -- | NOVO src/dashboard/componentes/glyphs.py |
| FIX-08 | Tipografia escala fina | C2 | 1 dia | -- | -- | .streamlit/config.toml + src/dashboard/tema_css.py |
| FIX-09 | Plotly modebar + Dracula | C2 | 1 dia | -- | -- | NOVO src/dashboard/tema_plotly.py + paginas |
| **FIX-10** | **Criar 5 páginas Bem-estar reais** | **C3** | **2 dias** | -- | FIX-11, FIX-14 | NOVO be_treinos.py, be_marcos.py, be_alarmes.py, be_contadores.py, be_tarefas.py + REFACTOR be_memorias.py, be_rotina.py + app.py |
| FIX-11 | Deep-link 12 abas Bem-estar | C4 | 4h | FIX-10 | -- | src/dashboard/app.py + drilldown.py |
| FIX-12 | Acessibilidade (skip + ARIA) | C5 | 4h | -- | -- | src/dashboard/componentes/shell.py + app.py |
| **FIX-14** | **Rota interna 5 órfãs (Memórias, Rotina, Cruzamentos, Privacidade, Editor TOML)** | **C5** | **6h** | FIX-10, FIX-11 | -- | src/dashboard/app.py + be_recap.py + be_memorias.py + be_rotina.py |
| FIX-13 | Citação filosófica em 60+ .py | C5 | 2h | TODAS | -- | TODOS arquivos .py modificados |

---

## Ordem de execução recomendada (1 IA, sequencial)

1. **Dia 1**: FIX-03, FIX-06, FIX-05, FIX-04 (todas XS, paralelas em worktrees ou seriais).
2. **Dia 1 final**: FIX-01, FIX-02 (XS, isoladas).
3. **Dia 2-4**: FIX-07, FIX-08, FIX-09 (M, paralelas em worktrees).
4. **Dia 5-6**: FIX-10 (criação das 5 páginas + extração de sub-conteúdos + refactor be_memorias/be_rotina).
5. **Dia 6 final (após FIX-10)**: FIX-11 (validar 12 deep-links).
6. **Dia 7**: FIX-12 (a11y) + FIX-14 (5 órfãs via deep-link interno) em paralelo.
7. **Dia 7 final**: FIX-13 (citação filosófica em todos os .py — DEVE ser última).

**Validador-sprint deve aprovar cada uma individualmente. Após FIX-13 (última), refaz auditoria completa via `docs/auditorias/AUDITORIA_REDESIGN_2026-05-12.md` para confirmar produto final.**

---

## Critério de paralelização (worktrees)

Cada sprint da Onda C1 e C2 pode rodar em worktree próprio sem conflito:

```bash
git worktree add ../ouroboros-fix-01 -b ux/rd-fix-01-lint-acentuacao ux/redesign-v1
git worktree add ../ouroboros-fix-02 -b ux/rd-fix-02-bug-despesa ux/redesign-v1
# ... e assim por diante
```

**Conflitos previstos**:
- FIX-08 (tipografia) e FIX-09 (Plotly) ambos tocam `tema_css.py` -- merge sequencial.
- FIX-12 (a11y) e FIX-05 (breadcrumb) ambos tocam `shell.py` -- merge sequencial.
- FIX-14 (5 órfãs) e FIX-10 (5 páginas novas) ambos tocam `app.py` e `be_memorias.py`/`be_rotina.py` -- FIX-14 deve aguardar FIX-10 mergeada.
- FIX-13 toca todos -- deve ser **ÚLTIMA** após merge das outras 13.

---

## Gauntlet integrador final (após FIX-13)

```bash
# 1. lint
make lint                        # exit 0 esperado

# 2. smoke aritmético
make smoke                       # 10/10 contratos OK

# 3. pytest baseline
.venv/bin/pytest tests/ -q       # >=2520 + ~30 novos = >=2550

# 4. auditoria visual completa
nohup .venv/bin/streamlit run src/dashboard/app.py --server.port 8765 --server.headless true &
sleep 6
nohup python3 -m http.server 8766 --bind 127.0.0.1 --directory novo-mockup &
sleep 2
.venv/bin/python /tmp/auditoria_redesign/cap_dashboard.py   # re-captura 28 telas
.venv/bin/python /tmp/auditoria_redesign/medir_estilos.py   # mede computed styles

# 5. validar deep-link 12 abas Bem-estar
.venv/bin/pytest tests/test_deeplink_bemestar.py -v

# 6. validar deep-link interno 5 órfãs
.venv/bin/pytest tests/test_deeplink_orfaos.py -v

# 7. validar h1 unico (1 visível por tela)
.venv/bin/pytest tests/test_h1_unico_por_tela.py -v
```

**Sprint Final (UX-RD-FECHAMENTO-01) re-roda auditoria** e move este ROTEIRO para `concluidos/` apenas se todos os critérios baterem.

---

## Estrutura final esperada (dashboard pós-FIX-14)

### Cluster Bem-estar (12 abas top-level + 5 órfãs via deep-link)

```
?cluster=Bem-estar&tab=Hoje         -> be_hoje.renderizar
?cluster=Bem-estar&tab=Humor        -> be_humor.renderizar
?cluster=Bem-estar&tab=Diário       -> be_diario.renderizar
?cluster=Bem-estar&tab=Eventos      -> be_eventos.renderizar
?cluster=Bem-estar&tab=Medidas      -> be_medidas.renderizar
?cluster=Bem-estar&tab=Treinos      -> be_treinos.renderizar         (NOVA, FIX-10)
?cluster=Bem-estar&tab=Marcos       -> be_marcos.renderizar          (NOVA, FIX-10)
?cluster=Bem-estar&tab=Alarmes      -> be_alarmes.renderizar         (NOVA, FIX-10)
?cluster=Bem-estar&tab=Contadores   -> be_contadores.renderizar      (NOVA, FIX-10)
?cluster=Bem-estar&tab=Ciclo        -> be_ciclo.renderizar
?cluster=Bem-estar&tab=Tarefas      -> be_tarefas.renderizar         (NOVA, FIX-10)
?cluster=Bem-estar&tab=Recap        -> be_recap.renderizar (com 5 cards-nav, FIX-14)

?cluster=Bem-estar&tab=Recap&secao=Memorias    -> be_memorias.renderizar    (FIX-14)
?cluster=Bem-estar&tab=Recap&secao=Rotina      -> be_rotina.renderizar      (FIX-14)
?cluster=Bem-estar&tab=Recap&secao=Cruzamentos -> be_cruzamentos.renderizar (FIX-14)
?cluster=Bem-estar&tab=Recap&secao=Privacidade -> be_privacidade.renderizar (FIX-14)
?cluster=Bem-estar&tab=Recap&secao=Editor-TOML -> be_editor_toml.renderizar (FIX-14)
```

**Cobertura mockup**: 12 abas top-level cobrem 12 das 12 telas do shell sidebar do mockup. Os 5 mockups adicionais (20-rotina, 23-memorias, 26-cruzamentos, 27-privacidade, 28-rotina-toml) ficam acessíveis via deep-link interno (FIX-14).

---

## Achados que NÃO entraram nas 14 (deferidos)

- Streamlit `st.popover` para autocomplete da Busca Global -- considerado adequado o atual `st.button` columns.
- Streamlit `st.toast` para feedback ETL -- escopo de sprint operacional futura.
- `::-webkit-scrollbar` custom -- limitação Streamlit (não suporta override consistente).
- Aporte mensal R$ 0,00 em Projeções -- requer alterar lógica financeira fora do escopo UI/UX.
- Decomposição dos 5 arquivos >800 linhas -- sprint UX-RD-DECOMP-01 dedicada, fora do roteiro de fidelidade visual.

---

*"O todo é mais que a soma das partes -- mas só se as partes encaixam." -- adaptado de Aristóteles*
