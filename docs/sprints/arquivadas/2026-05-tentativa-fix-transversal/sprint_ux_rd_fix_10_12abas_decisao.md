---
concluida_em: 2026-05-05
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: UX-RD-FIX-10
  title: "Criar 5 páginas Bem-estar faltantes (Treinos, Marcos, Alarmes, Contadores, Tarefas)"
  prioridade: P0
  estimativa: 2 dias (16h)
  onda: C3
  origem: "AUDITORIA_REDESIGN_2026-05-05.md §3.2 (5 abas-fantasma) e §6.3 (top problema #3). Decisão A confirmada pelo dono em 2026-05-05."
  depende_de: []
  bloqueia: [UX-RD-FIX-11, UX-RD-FIX-14]
  touches:
    - path: src/dashboard/paginas/be_treinos.py
      reason: "NOVO -- página real para aba Treinos. Extrai sub-aba 'Treinos' de be_memorias.py (heatmap 91d treinos lido de <vault>/.ouroboros/cache/treinos.json ou <vault>/treinos/<pessoa>/*.md)"
    - path: src/dashboard/paginas/be_marcos.py
      reason: "NOVO -- página real para aba Marcos. Extrai sub-aba 'Marcos' de be_memorias.py (lista cronológica DESC dos marcos)"
    - path: src/dashboard/paginas/be_alarmes.py
      reason: "NOVO -- página real para aba Alarmes. Extrai seção 'Alarmes' de be_rotina.py (lista de alarmes ativos lida de rotina.toml com toggle on/off)"
    - path: src/dashboard/paginas/be_contadores.py
      reason: "NOVO -- página real para aba Contadores. Extrai seção 'Contadores' de be_rotina.py (streaks/dias-desde com progresso visual)"
    - path: src/dashboard/paginas/be_tarefas.py
      reason: "NOVO -- página real para aba Tarefas. Extrai seção 'Tarefas' de be_rotina.py (TODO operacional com checkbox + prioridade)"
    - path: src/dashboard/app.py
      reason: "linhas 41-49: import das 5 novas páginas. Linhas 624-637: dispatcher 1:1 (cada with tab_be_X chama be_X.renderizar). Linhas 638-643: REMOVER os 3 expanders Cruzamentos/Privacidade/Editor TOML dentro de Recap (passam para FIX-14)"
    - path: src/dashboard/paginas/be_memorias.py
      reason: "REFACTOR -- após extrair Treinos e Marcos, esta página vira página-índice de Memórias com cards apontando para Treinos, Marcos, Fotos. Será reaproveitada por FIX-14"
    - path: src/dashboard/paginas/be_rotina.py
      reason: "REFACTOR -- após extrair Alarmes, Contadores, Tarefas, esta página vira página-índice com cards. Será reaproveitada por FIX-14"
    - path: tests/test_be_paginas_novas.py
      reason: "NOVO -- 15+ testes: cada uma das 5 páginas tem renderizar(dados, periodo, pessoa, ctx); empty state graceful; HTML minificado; cores tokens (sem hex hardcoded); sem regressão em be_memorias/be_rotina"
    - path: tests/test_be_12abas_consistente.py
      reason: "NOVO -- garante 12 abas declaradas == 12 chamadas distintas .renderizar() no dispatcher (zero duplicação)"
  forbidden:
    - "Continuar com 5 abas-fantasma (Treinos+Marcos -> be_memorias; Alarmes+Contadores+Tarefas -> be_rotina) -- a essência da sprint é eliminar isso"
    - "Manter expanders escondendo Cruzamentos/Privacidade/Editor TOML em Recap (linhas 639-643). REMOVER aqui; FIX-14 cuida delas"
    - "Criar páginas vazias com apenas st.write('TODO'). Cada página renderiza conteúdo real do mockup correspondente"
    - "Reescrever be_memorias.py e be_rotina.py do zero. REFACTOR preserva código existente: extrai sub-conteúdo + transforma a página em index/agregadora"
  hipotese:
    - "be_memorias.py:1-40 declara 3 sub-abas (Treinos, Fotos, Marcos) e be_rotina.py:1-40 declara 3 seções (Alarmes, Tarefas, Contadores). O código já existe; FIX-10 EXTRAI cada sub-conteúdo para módulo próprio. Após FIX-10: 5 páginas novas (be_treinos, be_marcos, be_alarmes, be_contadores, be_tarefas) + be_memorias e be_rotina viram páginas-índice (FIX-14 cuida da rota delas)."
  tests:
    - cmd: ".venv/bin/pytest tests/test_be_paginas_novas.py -v"
      esperado: "15+ PASSED"
    - cmd: ".venv/bin/pytest tests/test_be_12abas_consistente.py -v"
      esperado: "PASSED -- 12 abas, 12 chamadas distintas"
    - cmd: "grep -c 'be_memorias.renderizar\\|be_rotina.renderizar' src/dashboard/app.py"
      esperado: "0 (nenhuma chamada direta no dispatcher das 12 abas; FIX-14 vai reabilitar via outra rota)"
  acceptance_criteria:
    - "5 arquivos novos existem em src/dashboard/paginas/: be_treinos.py, be_marcos.py, be_alarmes.py, be_contadores.py, be_tarefas.py"
    - "Cada uma exporta `def renderizar(dados, periodo, pessoa, ctx) -> None` com contrato idêntico às demais be_*.py"
    - "Cada uma tem cabeçalho mono UPPERCASE: 'BEM-ESTAR · TREINOS', 'BEM-ESTAR · MARCOS', 'BEM-ESTAR · ALARMES', etc., com badge UX-RD-FIX-10 + sprint-tag"
    - "Cada uma renderiza pelo menos: 1 KPI principal + 1 visualização canônica (heatmap/lista/timeline/gauge) + filtros (Pessoa, Período onde fizer sentido) + empty state quando vault vazio"
    - "Treinos: heatmap 91d treinos colorido por sessão registrada (paleta neutra como be_memorias atual)"
    - "Marcos: lista cronológica DESC dos marcos do vault, mockup 23 sub-aba Marcos como referência visual"
    - "Alarmes: lista de alarmes ativos lida de <vault>/.ouroboros/rotina.toml seção [alarmes] com toggle visual on/off"
    - "Contadores: streaks/dias-desde de cada contador declarado em rotina.toml seção [contadores] com barra de progresso"
    - "Tarefas: TODO operacional com checkbox + prioridade (alta/média/baixa codificada via cor; alta=accent-red, média=accent-yellow, baixa=text-muted)"
    - "app.py dispatcher tem 1:1: tab_be_treinos -> be_treinos.renderizar; tab_be_marcos -> be_marcos.renderizar; tab_be_alarmes -> be_alarmes.renderizar; tab_be_contadores -> be_contadores.renderizar; tab_be_tarefas -> be_tarefas.renderizar"
    - "Expanders Cruzamentos/Privacidade/Editor TOML REMOVIDOS de Recap (app.py:639-643). FIX-14 reabilita via outra rota"
    - "be_memorias.py vira página-índice (mostra cards apontando para Treinos, Marcos, Fotos como sub-rotas) -- preparada para FIX-14"
    - "be_rotina.py vira página-índice (mostra cards apontando para Alarmes, Contadores, Tarefas) -- preparada para FIX-14"
    - "Pytest baseline mantido (>=2520 + 15 novos = >=2535)"
    - "make smoke 10/10; make lint exit 0"
  proof_of_work_esperado: |
    # 1. confirmar arquivos novos
    ls -la src/dashboard/paginas/be_treinos.py src/dashboard/paginas/be_marcos.py src/dashboard/paginas/be_alarmes.py src/dashboard/paginas/be_contadores.py src/dashboard/paginas/be_tarefas.py

    # 2. confirmar dispatcher 1:1
    grep -c "be_treinos.renderizar\|be_marcos.renderizar\|be_alarmes.renderizar\|be_contadores.renderizar\|be_tarefas.renderizar" src/dashboard/app.py
    # esperado: 5 (uma chamada por nova página)
    grep -c "be_memorias.renderizar\|be_rotina.renderizar" src/dashboard/app.py
    # esperado: 0 (foram substituídas no dispatcher das 12 abas; FIX-14 reabilita por outra rota)

    # 3. dashboard ao vivo: 12 abas, cada uma com seu próprio h1
    nohup .venv/bin/streamlit run src/dashboard/app.py --server.port 8530 --server.headless true &
    sleep 6
    .venv/bin/python -c "
    from playwright.sync_api import sync_playwright
    import urllib.parse
    abas = ['Hoje','Humor','Diário','Eventos','Medidas','Treinos','Marcos','Alarmes','Contadores','Ciclo','Tarefas','Recap']
    h1_esperado = {'Treinos':'BEM-ESTAR · TREINOS','Marcos':'BEM-ESTAR · MARCOS','Alarmes':'BEM-ESTAR · ALARMES','Contadores':'BEM-ESTAR · CONTADORES','Tarefas':'BEM-ESTAR · TAREFAS'}
    with sync_playwright() as p:
        b = p.chromium.launch(); page = b.new_context().new_page()
        falhas = []
        for aba in abas:
            url = f'http://127.0.0.1:8530/?cluster=Bem-estar&tab={urllib.parse.quote(aba)}'
            page.goto(url); page.wait_for_timeout(4500)
            h1s = page.evaluate('Array.from(document.querySelectorAll(\"h1\")).filter(h => h.getBoundingClientRect().width > 0).map(h => h.textContent.trim())')
            print(f'tab={aba}: h1={h1s}')
            esp = h1_esperado.get(aba)
            if esp and not any(esp in h for h in h1s):
                falhas.append((aba, h1s))
        if falhas: print(f'FALHAS: {falhas}'); exit(1)
        print('OK 12 abas com h1 correspondente')
        b.close()
    "
```

---

# Sprint UX-RD-FIX-10 — Criar 5 páginas Bem-estar faltantes (Decisão A)

**Status:** BACKLOG — Onda C3 (decisão arquitetural confirmada).

**Decisão tomada pelo dono em 2026-05-05**: criar páginas reais (decisão A), não renomear abas (decisão B).

## 1. Contexto

Auditoria 2026-05-05 §3.2 mostrou que `app.py:625-637` faz **5 abas chamarem 2 páginas**:

```python
with tab_be_treinos:     be_memorias.renderizar(...)   # Treinos -> Memórias
with tab_be_marcos:      be_memorias.renderizar(...)   # Marcos -> Memórias
with tab_be_alarmes:     be_rotina.renderizar(...)     # Alarmes -> Rotina
with tab_be_contadores:  be_rotina.renderizar(...)     # Contadores -> Rotina
with tab_be_tarefas:     be_rotina.renderizar(...)     # Tarefas -> Rotina
```

O comentário no código admite: *"preservar o invariante N=12 abas em ABAS_POR_CLUSTER"* (`app.py:622`). Isto é fraude de UI.

**Decisão A**: criar 5 páginas reais, dispatcher 1:1, eliminar a fraude.

A boa notícia é que `be_memorias.py` e `be_rotina.py` já contêm o código necessário em sub-aba/seção — esta sprint **EXTRAI** cada sub-conteúdo para um módulo próprio. Não é criação from-scratch.

## 2. Mapeamento mockup → código

| Aba | Origem mockup | Origem código (atual) | Destino |
|---|---|---|---|
| Treinos | `mockups/23-memorias.html` sub-aba **Treinos** | `paginas/be_memorias.py` função `_renderizar_treinos()` (extrair) | `paginas/be_treinos.py` |
| Marcos | `mockups/23-memorias.html` sub-aba **Marcos** | `paginas/be_memorias.py` função `_renderizar_marcos()` (extrair) | `paginas/be_marcos.py` |
| Alarmes | `mockups/20-rotina.html` seção `.alarme-row` | `paginas/be_rotina.py` função `_renderizar_alarmes()` (extrair) | `paginas/be_alarmes.py` |
| Contadores | `mockups/20-rotina.html` seção `.contador-row` | `paginas/be_rotina.py` função `_renderizar_contadores()` (extrair) | `paginas/be_contadores.py` |
| Tarefas | `mockups/20-rotina.html` seção `.tarefa-row` | `paginas/be_rotina.py` função `_renderizar_tarefas()` (extrair) | `paginas/be_tarefas.py` |

## 3. Hipótese verificável (Fase ANTES)

```bash
# 1) confirma o problema
grep -c "be_memorias.renderizar\|be_rotina.renderizar" src/dashboard/app.py
# esperado: 5+ ocorrências (5 abas chamando 2 páginas)

# 2) confirma sub-funções existem em be_memorias e be_rotina
grep -nE "^def _renderizar_(treinos|marcos|alarmes|contadores|tarefas|fotos)" src/dashboard/paginas/be_memorias.py src/dashboard/paginas/be_rotina.py
# esperado: 5+ ocorrências (1 por sub-conteúdo)

# 3) listar mockups de origem
wc -l novo-mockup/mockups/23-memorias.html novo-mockup/mockups/20-rotina.html
```

## 4. Tarefas

### 4.1 Criar `src/dashboard/paginas/be_treinos.py`

Template:

```python
"""Cluster Bem-estar -- página "Treinos" (UX-RD-FIX-10).

Heatmap 91 dias colorido por sessão de treino registrada. Lê de
``<vault>/.ouroboros/cache/treinos.json`` (gerado por
``mobile_cache.treinos`` ao varrer ``<vault>/treinos/<pessoa>/*.md``).

Mockup-fonte: ``novo-mockup/mockups/23-memorias.html`` sub-aba **Treinos**.

Lições UX-RD aplicadas:

* HTML emitido via :func:`minificar` (UX-RD-04).
* Cores via ``CORES`` em :mod:`src.dashboard.tema` -- nunca hex literal.
* Fallback graceful: cache ausente vira mensagem clara.
* Contrato uniforme ``renderizar(dados, periodo, pessoa, ctx)``.
"""

from __future__ import annotations
import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import streamlit as st

from src.dashboard.componentes.html_utils import minificar
from src.dashboard.tema import CORES
from src.mobile_cache.varrer_vault import descobrir_vault_root

PERIODO_HEATMAP_DIAS: int = 91


def _carregar_treinos(vault_root: Path | None) -> list[dict[str, Any]]:
    if vault_root is None:
        return []
    arquivo = vault_root / ".ouroboros" / "cache" / "treinos.json"
    if not arquivo.exists():
        return []
    try:
        return json.loads(arquivo.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _gerar_heatmap_html(treinos: list[dict[str, Any]]) -> str:
    """Espelha o padrão de be_memorias._renderizar_heatmap_treinos antes da extração."""
    # ... copiar literal de be_memorias.py linhas X-Y (ajustar imports)
    # ... mesma estética: 13 colunas (semanas) × 7 linhas (dias)
    pass


def renderizar(dados, periodo, pessoa, ctx) -> None:
    """Renderiza página Treinos no cluster Bem-estar."""
    st.markdown(minificar('''
        <header class="page-header">
          <div>
            <h1 class="page-title">BEM-ESTAR · TREINOS</h1>
            <p class="page-subtitle">Heatmap dos últimos 91 dias por sessão registrada no vault.</p>
          </div>
          <div class="page-meta">
            <span class="sprint-tag">UX-RD-FIX-10</span>
          </div>
        </header>
    '''), unsafe_allow_html=True)

    vault_root = descobrir_vault_root()
    treinos = _carregar_treinos(vault_root)

    if not treinos:
        st.markdown(minificar('''
            <div class="skill-instr">
              <h4>NENHUM TREINO REGISTRADO AINDA</h4>
              <p>Crie arquivos em <code>&lt;vault&gt;/treinos/&lt;pessoa&gt;/&lt;data&gt;.md</code> com frontmatter <code>tipo: treino</code>.</p>
            </div>
        '''), unsafe_allow_html=True)
        return

    # KPI total + heatmap + lista recente
    col_kpi, col_heat = st.columns([1, 3])
    with col_kpi:
        st.markdown(minificar(f'''
            <div class="kpi">
              <div class="kpi-label">Sessões 91d</div>
              <div class="kpi-value">{len(treinos)}</div>
            </div>
        '''), unsafe_allow_html=True)
    with col_heat:
        st.markdown(_gerar_heatmap_html(treinos), unsafe_allow_html=True)


# "<citação filosófica final aplicada por FIX-13>"
```

### 4.2 Criar `src/dashboard/paginas/be_marcos.py`

Template completo (copy-paste após FIX-13 adicionar citação):

```python
"""Cluster Bem-estar -- página "Marcos" (UX-RD-FIX-10).

Lista cronológica DESC dos marcos do vault. Cada marco é um arquivo
em ``<vault>/marcos/<pessoa>/<data>.md`` com frontmatter:
    tipo: marco
    categoria: rotina | conquista | lembranca
    titulo: <texto>
    tags: [...]

Mockup-fonte: ``novo-mockup/mockups/23-memorias.html`` sub-aba Marcos.

Lições UX-RD aplicadas: minificar() + tokens CORES + fallback graceful + contrato uniforme.
"""

from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

from src.dashboard.componentes.html_utils import minificar
from src.dashboard.tema import CORES
from src.mobile_cache.varrer_vault import descobrir_vault_root

CORES_CATEGORIA: dict[str, str] = {
    "rotina":    CORES.get("neutro", "var(--accent-cyan)"),
    "conquista": CORES.get("positivo", "var(--accent-green)"),
    "lembranca": CORES.get("alerta", "var(--accent-yellow)"),
}


def _carregar_marcos(vault_root: Path | None) -> list[dict[str, Any]]:
    if vault_root is None:
        return []
    arquivo = vault_root / ".ouroboros" / "cache" / "marcos.json"
    if not arquivo.exists():
        return []
    try:
        marcos = json.loads(arquivo.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    # ordem cronológica DESC
    return sorted(marcos, key=lambda m: m.get("data", ""), reverse=True)


def _gerar_lista_html(marcos: list[dict[str, Any]]) -> str:
    if not marcos:
        return ""
    linhas = []
    for m in marcos:
        cat = m.get("categoria", "rotina").lower()
        cor = CORES_CATEGORIA.get(cat, CORES_CATEGORIA["rotina"])
        data = m.get("data", "")
        titulo = (m.get("titulo") or m.get("title") or "").strip()
        tags = " · ".join(m.get("tags", [])) if m.get("tags") else ""
        linhas.append(f'''
            <article class="card" style="border-left: 3px solid {cor}; margin-bottom: var(--sp-3);">
              <div class="card-head">
                <span class="card-title">{cat.upper()}</span>
                <span class="mono" style="color: var(--text-muted)">{data}</span>
              </div>
              <p style="margin: 0; font-size: var(--fs-14)">{titulo}</p>
              {f'<p style="margin: var(--sp-1) 0 0; color: var(--text-muted); font-size: var(--fs-12)">{tags}</p>' if tags else ''}
            </article>
        ''')
    return "".join(linhas)


def renderizar(dados, periodo, pessoa, ctx) -> None:
    """Renderiza página Marcos no cluster Bem-estar."""
    st.markdown(minificar('''
        <header class="page-header">
          <div>
            <h1 class="page-title">BEM-ESTAR · MARCOS</h1>
            <p class="page-subtitle">Lista cronológica DESC dos marcos registrados no vault.</p>
          </div>
          <div class="page-meta">
            <span class="sprint-tag">UX-RD-FIX-10</span>
          </div>
        </header>
    '''), unsafe_allow_html=True)

    vault_root = descobrir_vault_root()
    marcos = _carregar_marcos(vault_root)

    col_kpi, col_lista = st.columns([1, 4])
    with col_kpi:
        st.markdown(minificar(f'''
            <div class="kpi">
              <div class="kpi-label">Total marcos</div>
              <div class="kpi-value">{len(marcos)}</div>
            </div>
        '''), unsafe_allow_html=True)

    with col_lista:
        if marcos:
            st.markdown(minificar(_gerar_lista_html(marcos)), unsafe_allow_html=True)
        else:
            st.markdown(minificar('''
                <div class="skill-instr">
                  <h4>NENHUM MARCO REGISTRADO</h4>
                  <p>Crie arquivos em <code>&lt;vault&gt;/marcos/&lt;pessoa&gt;/&lt;data&gt;.md</code> com frontmatter <code>tipo: marco</code>.</p>
                </div>
            '''), unsafe_allow_html=True)


# "<citação filosófica final aplicada por FIX-13>"
```

### 4.3 Criar `src/dashboard/paginas/be_alarmes.py`

Mesmo padrão de be_marcos.py, com 4 mudanças-chave:

1. Carregamento via `tomllib`:
   ```python
   import tomllib
   def _carregar_rotina_toml(vault_root: Path | None) -> dict:
       if vault_root is None: return {}
       toml_path = vault_root / ".ouroboros" / "rotina.toml"
       if not toml_path.exists():
           toml_path = Path.home() / ".ouroboros" / "rotina.toml"
       if not toml_path.exists(): return {}
       try:
           return tomllib.loads(toml_path.read_text(encoding="utf-8"))
       except (tomllib.TOMLDecodeError, OSError):
           return {}
   ```

2. Filtra `rotina.get("alarmes", [])` -- cada item esperado:
   ```toml
   [[alarmes]]
   hora = "06:30"
   titulo = "Acordar"
   dias = ["seg","ter","qua","qui","sex"]
   ativo = true
   ```

3. Renderização: linha por alarme com `.alarme-row` (classe canônica de mockup 20-rotina.html), seguindo grid `grid-template-columns: 80px 1fr auto`. Toggle on/off VISUAL (não funcional nesta sprint -- apenas reflete `ativo: true|false`).

4. KPI: `len([a for a in alarmes if a.get("ativo")])` ativos / `len(alarmes)` totais.

5. Empty state: link para Editor TOML em sub-rota `?cluster=Bem-estar&tab=Recap&secao=Editor-TOML` (FIX-14).

### 4.4 Criar `src/dashboard/paginas/be_contadores.py`

Mesmo padrão; 3 diferenças:

1. Carrega `rotina.get("contadores", [])`:
   ```toml
   [[contadores]]
   titulo = "Streak academia"
   tipo = "streak"        # ou "dias_desde"
   valor_atual = 12
   meta = 30
   ```

2. Cor da barra: `streak` progredindo = `var(--accent-green)`; `dias_desde` (de algo bom = streak; de algo ruim = `var(--accent-red)`).

3. Visual: card com classe `.contador-row` (componente do mockup 20-rotina.html), barra de progresso `(valor_atual / meta) × 100%`. Para `dias_desde`, mostra dias absoluto sem barra.

4. KPI: maior `valor_atual` entre os de tipo `streak`.

### 4.5 Criar `src/dashboard/paginas/be_tarefas.py`

Mesmo padrão; 3 diferenças:

1. Carrega `<vault>/tarefas/<pessoa>/*.md` ou `rotina.get("tarefas", [])`:
   ```toml
   [[tarefas]]
   titulo = "Renovar CNH"
   prioridade = "alta"     # alta | media | baixa
   feita = false
   prazo = "2026-06-15"
   ```

2. Ordena por: `feita` (não-feitas primeiro) → `prioridade` (alta primeiro).

3. CSS:
   ```python
   CSS_PRIORIDADE = {
       "alta":  "var(--accent-red)",
       "media": "var(--accent-yellow)",
       "baixa": "var(--text-muted)",
   }
   # tarefa.feita: opacity 0.55 + text-decoration: line-through
   ```

4. KPI: `pendentes / total` (ex.: "8 / 12").

5. Visual: `.tarefa-row` (classe do mockup 20-rotina.html), grid `grid-template-columns: 24px 1fr auto`, com checkbox **read-only**.

### 4.6 Atualizar `src/dashboard/app.py`

#### 4.6.1 Imports (linha 41-49 ou onde estão os imports be_*)

Adicionar:

```python
from src.dashboard.paginas import (
    ...,  # imports já existentes
    be_treinos,
    be_marcos,
    be_alarmes,
    be_contadores,
    be_tarefas,
)
```

#### 4.6.2 Dispatcher (linhas ~624-637)

**ANTES**:

```python
with tab_be_treinos:    be_memorias.renderizar(dados, periodo, pessoa, ctx)
with tab_be_marcos:     be_memorias.renderizar(dados, periodo, pessoa, ctx)
with tab_be_alarmes:    be_rotina.renderizar(dados, periodo, pessoa, ctx)
with tab_be_contadores: be_rotina.renderizar(dados, periodo, pessoa, ctx)
with tab_be_ciclo:      be_ciclo.renderizar(dados, periodo, pessoa, ctx)
with tab_be_tarefas:    be_rotina.renderizar(dados, periodo, pessoa, ctx)
with tab_be_recap:      be_recap.renderizar(dados, periodo, pessoa, ctx)
    with st.expander("Cruzamentos", expanded=False):
        be_cruzamentos.renderizar(dados, periodo, pessoa, ctx)
    with st.expander("Privacidade A ↔ B", expanded=False):
        be_privacidade.renderizar(dados, periodo, pessoa, ctx)
    with st.expander("Editor TOML (rotina)", expanded=False):
        be_editor_toml.renderizar(dados, periodo, pessoa, ctx)
```

**DEPOIS**:

```python
with tab_be_treinos:    be_treinos.renderizar(dados, periodo, pessoa, ctx)
with tab_be_marcos:     be_marcos.renderizar(dados, periodo, pessoa, ctx)
with tab_be_alarmes:    be_alarmes.renderizar(dados, periodo, pessoa, ctx)
with tab_be_contadores: be_contadores.renderizar(dados, periodo, pessoa, ctx)
with tab_be_ciclo:      be_ciclo.renderizar(dados, periodo, pessoa, ctx)
with tab_be_tarefas:    be_tarefas.renderizar(dados, periodo, pessoa, ctx)
with tab_be_recap:      be_recap.renderizar(dados, periodo, pessoa, ctx)
# Cruzamentos, Privacidade, Editor TOML: removidos daqui.
# FIX-14 reabilita via deep-link interno (?cluster=Bem-estar&aba=Recap&secao=Cruzamentos)
```

### 4.7 Refactor `be_memorias.py` e `be_rotina.py`

Após extrair, transformar cada uma em **página-índice**:

`be_memorias.py` novo `renderizar()`:

```python
def renderizar(dados, periodo, pessoa, ctx) -> None:
    """Página-índice de Memórias: cards apontando para Treinos, Marcos, Fotos."""
    st.markdown(minificar('''
        <header class="page-header">
          <h1 class="page-title">MEMÓRIAS</h1>
          <p class="page-subtitle">Treinos, marcos e fotos do período. Escolha uma sub-rota.</p>
        </header>
        <div class="kpi-grid">
          <a class="kpi card interactive" href="?cluster=Bem-estar&tab=Treinos">
            <div class="kpi-label">SUB-PÁGINA</div>
            <div class="kpi-value" style="font-size: var(--fs-20)">Treinos</div>
          </a>
          <a class="kpi card interactive" href="?cluster=Bem-estar&tab=Marcos">
            <div class="kpi-label">SUB-PÁGINA</div>
            <div class="kpi-value" style="font-size: var(--fs-20)">Marcos</div>
          </a>
          <a class="kpi card interactive" href="?cluster=Bem-estar&aba=Recap&secao=Memorias-Fotos">
            <div class="kpi-label">SUB-PÁGINA</div>
            <div class="kpi-value" style="font-size: var(--fs-20)">Fotos</div>
          </a>
        </div>
    '''), unsafe_allow_html=True)
```

Análogo para `be_rotina.py` apontando para Alarmes, Contadores, Tarefas.

**Esta página-índice NÃO é renderizada pelo dispatcher das 12 abas atuais** (foi removido). FIX-14 vai reabilitar via deep-link `?cluster=Bem-estar&secao=Memorias` que renderiza esta página dentro de Recap (ou rota dedicada).

### 4.8 Criar `tests/test_be_paginas_novas.py`

```python
import pytest
from unittest.mock import MagicMock

@pytest.mark.parametrize("modulo_nome,h1_esperado", [
    ("be_treinos",    "BEM-ESTAR · TREINOS"),
    ("be_marcos",     "BEM-ESTAR · MARCOS"),
    ("be_alarmes",    "BEM-ESTAR · ALARMES"),
    ("be_contadores", "BEM-ESTAR · CONTADORES"),
    ("be_tarefas",    "BEM-ESTAR · TAREFAS"),
])
def test_pagina_renderiza_com_vault_vazio(modulo_nome, h1_esperado, monkeypatch, capsys):
    """Cada nova página renderiza graceful quando vault não tem dados."""
    import importlib
    monkeypatch.setattr("src.mobile_cache.varrer_vault.descobrir_vault_root", lambda: None)
    modulo = importlib.import_module(f"src.dashboard.paginas.{modulo_nome}")
    # mock streamlit
    mocked_st = MagicMock()
    monkeypatch.setattr(modulo, "st", mocked_st)
    modulo.renderizar({}, "30d", "Todos", {})
    # capturar HTML emitido
    chamadas = [c.args[0] for c in mocked_st.markdown.call_args_list if c.args]
    todas = "\n".join(chamadas)
    assert h1_esperado in todas, f"h1 {h1_esperado} não emitido"

def test_assinatura_renderizar_uniforme():
    """Todas as 5 novas páginas devem ter a mesma assinatura `renderizar(dados, periodo, pessoa, ctx)`."""
    import inspect, importlib
    for nome in ["be_treinos","be_marcos","be_alarmes","be_contadores","be_tarefas"]:
        m = importlib.import_module(f"src.dashboard.paginas.{nome}")
        sig = inspect.signature(m.renderizar)
        params = list(sig.parameters)
        assert params == ["dados","periodo","pessoa","ctx"], f"{nome}.renderizar tem assinatura errada: {params}"

def test_paginas_novas_nao_usam_hex_hardcoded():
    """Nenhuma nova página tem #RRGGBB literal fora de fallback var(--token, #cor)."""
    import re
    from pathlib import Path
    padrao_hex = re.compile(r"#[0-9a-fA-F]{6}\b")
    for nome in ["be_treinos","be_marcos","be_alarmes","be_contadores","be_tarefas"]:
        p = Path(f"src/dashboard/paginas/{nome}.py")
        texto = p.read_text(encoding="utf-8")
        # encontrar hex que NÃO está dentro de var(--token, #cor)
        for m in padrao_hex.finditer(texto):
            inicio = max(0, m.start() - 20)
            contexto = texto[inicio:m.end() + 1]
            assert "var(--" in contexto, f"{nome}: hex literal {m.group()} fora de var() em {contexto!r}"
```

### 4.9 Criar `tests/test_be_12abas_consistente.py`

```python
import re
from pathlib import Path

def test_abas_por_cluster_bem_estar_tem_12():
    from src.dashboard.app import ABAS_POR_CLUSTER
    assert len(ABAS_POR_CLUSTER["Bem-estar"]) == 12

def test_dispatcher_chama_12_paginas_distintas():
    """Cada with tab_be_X chama UMA página be_X.renderizar; zero duplicação."""
    texto = Path("src/dashboard/app.py").read_text(encoding="utf-8")
    chamadas = re.findall(r'\bbe_(\w+)\.renderizar\(', texto)
    from collections import Counter
    counts = Counter(chamadas)
    fantasma = {m: n for m, n in counts.items() if n > 1}
    assert not fantasma, f'abas-fantasma detectadas (página chamada >1x): {fantasma}'

def test_5_paginas_novas_referenciadas_no_dispatcher():
    texto = Path("src/dashboard/app.py").read_text(encoding="utf-8")
    for nome in ["be_treinos","be_marcos","be_alarmes","be_contadores","be_tarefas"]:
        assert f"{nome}.renderizar(" in texto, f"{nome} não chamado no dispatcher"

def test_be_memorias_e_be_rotina_nao_estao_no_dispatcher_principal():
    """Após decisão A: be_memorias e be_rotina não são chamadas no dispatcher de 12 abas. FIX-14 reabilita via outra rota."""
    texto = Path("src/dashboard/app.py").read_text(encoding="utf-8")
    # buscar dentro do bloco do dispatcher Bem-estar (se ainda chamadas, FIX-14 não roda)
    assert "be_memorias.renderizar(" not in texto, "be_memorias.renderizar() ainda no dispatcher; remover (FIX-14 cuida)"
    assert "be_rotina.renderizar(" not in texto, "be_rotina.renderizar() ainda no dispatcher; remover (FIX-14 cuida)"
```

## 5. Anti-débito

- **Achado colateral conhecido**: as 5 páginas órfãs (be_memorias, be_rotina, be_cruzamentos, be_privacidade, be_editor_toml) **continuam sem rota top-level** após FIX-10. **FIX-14** (nova sprint que esta gera) cuida disso.
- **NÃO** reescrever o conteúdo de be_memorias e be_rotina do zero. Refactor preservando código existente; só transforma em página-índice.
- Se na extração descobrir que `_renderizar_treinos` (ou similar) tem dependências de helpers que estavam dentro de be_memorias.py: extrair os helpers para `componentes/be_helpers.py` ou duplicar no novo arquivo (DRY pode esperar uma sprint de refactor).
- Se um teste de tests/ pré-existente (test_be_memorias.py, test_be_rotina.py) quebrar porque be_memorias virou página-índice: atualizar o teste para a nova função (página-índice cards) -- registrar achado em **FIX-10.B**.

## 6. Validação visual

```bash
nohup .venv/bin/streamlit run src/dashboard/app.py --server.port 8530 --server.headless true &
sleep 6
mkdir -p .playwright-mcp/auditoria/fix-10
.venv/bin/python -c "
from playwright.sync_api import sync_playwright
import urllib.parse
with sync_playwright() as p:
    b = p.chromium.launch(); page = b.new_context(viewport={'width':1440,'height':900}).new_page()
    for aba in ['Treinos','Marcos','Alarmes','Contadores','Tarefas']:
        url = f'http://127.0.0.1:8530/?cluster=Bem-estar&tab={urllib.parse.quote(aba)}'
        page.goto(url); page.wait_for_timeout(4500)
        page.screenshot(path=f'.playwright-mcp/auditoria/fix-10/be_{aba.lower()}.png', full_page=True)
        print(f'salvo {aba}')
    b.close()
"
```

Validador humano confere: cada PNG mostra h1 correto + KPI principal + visualização canônica + filtros, sem reaproveitar conteúdo de outra aba.

## 7. Gauntlet

```bash
make lint                                                    # exit 0
make smoke                                                   # 10/10
.venv/bin/pytest tests/test_be_paginas_novas.py -v           # 5+ PASSED
.venv/bin/pytest tests/test_be_12abas_consistente.py -v      # 4 PASSED
.venv/bin/pytest tests/ -q --tb=no                           # baseline >=2520 + 9 = >=2529
ls src/dashboard/paginas/be_*.py | wc -l                     # 12 (7 atuais + 5 novas)
```

---

*"Toda separação cria duas formas mais nítidas." -- adaptado de Bachelard*
