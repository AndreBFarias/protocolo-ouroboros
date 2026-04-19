## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 51
  title: "Dashboard de Catalogação"
  touches:
    - path: src/dashboard/paginas/catalogacao.py
      reason: "página Streamlit mostrando documentos, itens, propostas, gaps"
    - path: src/dashboard/dados.py
      reason: "adiciona carregamento do grafo SQLite"
    - path: src/dashboard/app.py
      reason: "registra nova página no menu"
    - path: src/dashboard/paginas/conferencia.py
      reason: "página para revisão de propostas abertas (linking, classificação, categoria)"
  n_to_n_pairs: []
  forbidden:
    - src/llm/  # sem cliente programático
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: "make dashboard &"
      timeout: 30  # sobe e derruba
  acceptance_criteria:
    - "Página Catalogação mostra contagem de documentos por tipo/mês"
    - "Página Conferência lista propostas abertas agrupadas por tipo"
    - "Usuário consegue aprovar/rejeitar proposta via dashboard (escreve no arquivo)"
    - "Gráfico 'gastos por categoria de item' renderiza sem erro"
    - "Acentuação PT-BR correta"
```

> Executar antes de começar: `make lint && ./run.sh --check`

---

# Sprint 51 -- Dashboard de Catalogação

**Status:** PENDENTE
**Data:** 2026-04-19
**Prioridade:** ALTA
**Tipo:** Feature
**Dependências:** Sprints 42 (grafo), 43 (propostas), 50 (itens categorizados)
**Desbloqueia:** Visualização consolidada do catálogo
**Issue:** --
**ADR:** --

---

## Como Executar

- `make dashboard`
- Acessar `http://localhost:8501` → aba "Catalogação"

### O que NÃO fazer

- NÃO sobrescrever páginas existentes
- NÃO abrir conexões concorrentes ao SQLite (usa cache)
- NÃO expor dados sensíveis (CPF, diagnóstico médico)

---

## Problema

Após Fases BETA/GAMA/DELTA, todos os dados estão no grafo: documentos, itens, categorias, propostas. Falta uma interface que mostre:

- Quantos documentos chegaram no mês
- Itens mais comprados, gasto por categoria
- Propostas pendentes aguardando aprovação
- Gaps: meses com pouca catalogação, fornecedores sem entity resolution

## O que já existe (NÃO duplicar)

| Sistema | Arquivo | O que faz |
|---------|---------|-----------|
| Dashboard Streamlit | `src/dashboard/app.py` | App principal |
| Páginas existentes | `src/dashboard/paginas/` | `visao_geral`, `transacoes`, `metas`, `contas`, `irpf` |
| Carregamento XLSX | `src/dashboard/dados.py` | `carregar_dados()` cacheado |

## Implementação

### Fase 1: extensão do `dados.py`

```python
@st.cache_resource(ttl=300)
def carregar_grafo() -> sqlite3.Connection:
    conn = sqlite3.connect(CAMINHO_GRAFO, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn
```

### Fase 2: página Catalogação

`src/dashboard/paginas/catalogacao.py`:

Seções:
1. **KPIs** (cards): total docs, total itens, total gasto categorizado, % propostas abertas
2. **Documentos por tipo e mês** (bar chart): quantidade ao longo do tempo
3. **Top categorias de item** (treemap): gasto por categoria_item
4. **Top produtos** (tabela): produto_canonico, contagem, gasto total
5. **Gaps** (lista): meses com < 5 docs (baixa cobertura)

### Fase 3: página Conferência

`src/dashboard/paginas/conferencia.py`:

- Lista propostas em `docs/propostas/*/*.md` (não arquivadas)
- Agrupadas por tipo (`regra`, `classificacao`, `linking`, `resolver`)
- Cada proposta: mostra markdown renderizado + botões "Aprovar" e "Rejeitar"
- Aprovar: chama `scripts/supervisor_aprovar.sh` via subprocess
- Rejeitar: abre input para motivo, chama `supervisor_rejeitar.sh`

### Fase 4: integração no menu

`src/dashboard/app.py` adiciona entradas no sidebar:
- "Catalogação"
- "Conferência"

## Armadilhas Conhecidas

| Ref | Armadilha | Como evitar |
|-----|-----------|-------------|
| A51-1 | SQLite em modo thread compartilhado corrompe com writes | Apenas READ no dashboard; writes via subprocess (scripts) |
| A51-2 | `st.cache_resource` não invalida quando arquivo muda | TTL de 300s + botão "refresh" explícito |
| A51-3 | Propostas em branco ou malformadas quebram renderização | Try/except ao ler markdown + mostrar erro como card vermelho |
| A51-4 | Dados sensíveis de receita médica vazam no dashboard público | Página Conferência exige senha ambiente (`STREAMLIT_SECRET`) |
| A51-5 | Dashboard Streamlit com recarregamento automático de mutating subprocess cria loop | Aprovar/rejeitar só executa sob clique + `st.stop()` após |

## Evidências Obrigatórias

- [ ] `make lint` passa
- [ ] Dashboard sobe sem erro (`make dashboard`)
- [ ] Página Catalogação renderiza sem warning
- [ ] Aprovar proposta via UI move o arquivo e atualiza diário
- [ ] Screenshots ficam em `docs/screenshots/catalogacao/` (opcional)

## Verificação end-to-end

```bash
make dashboard &
DASHBOARD_PID=$!
sleep 5
curl -s http://localhost:8501 | grep -q "Ouroboros"
kill $DASHBOARD_PID
.venv/bin/pytest tests/test_dashboard_catalogacao.py -v  # se criado
```

## Conferência Artesanal Opus

**Arquivos originais a ler:** páginas Streamlit + queries que as alimentam.

**Checklist:**

1. KPIs batem com queries SQL feitas manualmente?
2. Rotas de aprovação/rejeição funcionam E-2-E?
3. Privacidade de dados sensíveis preservada (receitas, CPFs)?

**Relatório em `docs/propostas/sprint_51_conferencia.md`**: ajustes de layout, queries a corrigir.

**Critério**: dashboard usável por humano sem conhecer comando bash; aprovações realizáveis pela UI.

---

*"Interface é a mão que alcança o dado." -- princípio do designer*
