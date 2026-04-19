## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 36
  title: "Métricas IA no Dashboard: termômetro de autossuficiência"
  touches:
    - path: src/dashboard/paginas/metricas_ia.py
      reason: "nova página com 5 métricas e série temporal 12 meses"
    - path: src/dashboard/app.py
      reason: "registrar rota para Metricas IA no menu lateral"
  n_to_n_pairs:
    - [src/dashboard/paginas/metricas_ia.py, src/dashboard/estilos.py]
  forbidden:
    - data/output/  # página é somente leitura; não escreve exceto exportação CSV a pedido
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: ".venv/bin/pytest tests/test_metricas_ia.py -x -q"
      timeout: 60
  acceptance_criteria:
    - "Dashboard carrega página Metricas IA em < 2s com 12 meses de dados"
    - "5 KPIs: % determinístico, custo LLM mês, regras aprovadas, proposições rejeitadas, tempo médio aprovação"
    - "Série temporal renderizada para cada KPI via criar_layout_plotly (Sprint 20)"
    - "Botão 'Exportar CSV' gera data/output/metricas_ia_YYYY-MM-DD.csv"
    - "Página não crasha quando llm_costs.jsonl não existe: mostra mensagem 'Supervisor não executado'"
    - "Cache de 10min para refletir novas execuções"
    - "% determinístico = transações do mês sem chamada LLM / total do mês"
    - "Acentuação PT-BR correta e zero emojis"
```

> Executar antes de começar: `make lint && ./run.sh --check`

---

# Sprint 36 -- Métricas IA no Dashboard: termômetro de autossuficiência

**Status:** PENDENTE
**Data:** 2026-04-18
**Prioridade:** MÉDIA
**Tipo:** Feature
**Dependências:** Sprint 20 (layout), Sprint 31 (Infra LLM), Sprint 33 (Narrativa), Sprint 34 (Auditor)
**Desbloqueia:** Fase 3 (grafo/busca)
**Issue:** --
**Implementa:** ADR-09 (Autossuficiência Progressiva) -- termômetro de dependência LLM
**ADR:** ADR-09

---

## Como Executar

**Comandos principais:**
- `make lint`
- `make dashboard` -- navegar até "Métricas IA"
- `.venv/bin/pytest tests/test_metricas_ia.py -v`

### O que NÃO fazer

- NÃO escrever em `data/output/` exceto o CSV de exportação a pedido do usuário.
- NÃO calcular % determinístico sobre total histórico (achata a série); usar transações do mês.
- NÃO crashar se `llm_costs.jsonl` ainda não existe; mostrar mensagem explicativa.
- NÃO usar cache de mais de 10min: métricas precisam refletir execuções recentes.

---

## Problema

Plano 30/60/90 §2.6 define termômetro explícito: "o sistema está ficando mais autossuficiente ou mais dependente do LLM?". Sem métrica visível, decisões de investimento ficam cegas.

A meta do loop Sprint 31 → Sprint 34 → aprovação humana é mover a cobertura determinística de 85% → 95% em 90 dias, reduzindo simultaneamente o custo LLM. Sem dashboard, não dá para saber se está indo no sentido certo.

---

## O que já existe (NÃO duplicar)

| Sistema | Arquivo | O que faz |
|---------|---------|-----------|
| Cost tracker | `src/llm/cost_tracker.py` | Append em `data/output/llm_costs.jsonl` por chamada |
| Proposições | `mappings/proposicoes/*.yaml` | Arquivos com status (aprovado/rejeitado/pendente) |
| Layout Plotly | `src/dashboard/estilos.py` | `criar_layout_plotly(titulo)` factory (Sprint 20) |
| Cards KPI | `src/dashboard/estilos.py` | `render_card_kpi(label, valor, delta)` (Sprint 20) |

---

## Implementação

### Fase 1: leitores de dados

**Arquivo:** `src/dashboard/paginas/metricas_ia.py`

```python
@st.cache_data(ttl=600)
def carregar_custos() -> pd.DataFrame:
    caminho = Path("data/output/llm_costs.jsonl")
    if not caminho.exists():
        return pd.DataFrame(columns=["ts", "modelo", "tokens_in", "tokens_out", "custo_usd", "modo"])
    return pd.read_json(caminho, lines=True)

@st.cache_data(ttl=600)
def carregar_proposicoes() -> pd.DataFrame:
    # percorre mappings/proposicoes/*.yaml, extrai status, data, tipo
    ...
```

### Fase 2: cálculo dos 5 KPIs

**Arquivo:** `src/dashboard/paginas/metricas_ia.py`

1. **% determinístico** -- `1 - (transacoes_com_chamada_llm_no_mes / transacoes_total_mes)`. Meta: 85% → 95%.
2. **Custo LLM mensal** -- `soma(custo_usd where mes_ref == mes_corrente)`. Meta: < $10/mês.
3. **Regras aprovadas no mês** -- count de `mappings/proposicoes/*.yaml` com `status=aprovado` e data no mês.
4. **Proposições rejeitadas** -- count de `status=rejeitado`. Alerta se muito baixo (André aprovando sem olhar).
5. **Tempo médio aprovação** -- diferença entre timestamp de criação da proposição e timestamp de aprovação/rejeição.

### Fase 3: série temporal 12 meses

**Arquivo:** `src/dashboard/paginas/metricas_ia.py`

Para cada KPI, gráfico Plotly de linha com 12 pontos (um por mês). Usar `criar_layout_plotly(titulo, altura=280)` da Sprint 20 para consistência visual.

### Fase 4: exportação CSV

**Arquivo:** `src/dashboard/paginas/metricas_ia.py`

Botão Streamlit `st.download_button` gera CSV com colunas `mes_ref, pct_deterministico, custo_usd, regras_aprovadas, proposicoes_rejeitadas, tempo_medio_aprovacao_horas`. Arquivo sugerido: `metricas_ia_YYYY-MM-DD.csv`.

### Fase 5: mensagens de estado

**Arquivo:** `src/dashboard/paginas/metricas_ia.py`

- Se `llm_costs.jsonl` vazio: bloco `st.info("Supervisor ainda não executado. Rode `./run.sh --supervisor` para popular métricas.")`.
- Se `proposicoes/` vazio: bloco informativo equivalente.
- Se `pct_rejeitado < 5%` em 30 dias e `pct_aprovado > 90%`: bloco `st.warning("Taxa de rejeição muito baixa. Confirme que está revisando cada proposição.")`.

### Fase 6: teste da função `% determinístico`

**Arquivo:** `tests/test_metricas_ia.py`

Fixture com 100 transações em um mês, 15 com chamada LLM registrada. `pct_deterministico == 0.85`. Caso de borda: mês sem transação → pct indeterminado, mostrar "--" na UI.

---

## Armadilhas Conhecidas

| Ref | Armadilha | Como evitar |
|-----|-----------|-------------|
| A36.1 | `llm_costs.jsonl` não existe e página crasha | `exists()` check + DataFrame vazio como fallback |
| A36.2 | Cache do Streamlit serve dado velho | `ttl=600` (10min); botão manual "Atualizar" opcional |
| A36.3 | % determinístico calculado sobre total histórico achata série | Usar denominador "transações do mês" |
| A36.4 | Série temporal sem dados suficientes (< 3 meses) gera gráfico esquisito | Render apenas com >= 3 pontos; senão exibir "dados insuficientes" |
| A36.5 | Exportar CSV em loop gera muitos arquivos em `data/output/` | Download via `st.download_button` não grava em disco do servidor |

Referência: `docs/ARMADILHAS.md`

---

## Evidências Obrigatórias

- [ ] `make lint` passa sem erros
- [ ] Página "Métricas IA" carrega em < 2s com 12 meses de dados reais
- [ ] 5 KPIs rendem valor correto contra fixture de teste
- [ ] Série temporal 12 meses exibe para cada KPI
- [ ] Botão "Exportar CSV" gera arquivo válido
- [ ] Página não crasha com `llm_costs.jsonl` ausente
- [ ] Teste unitário `test_metricas_ia.py` passa
- [ ] Alerta de "taxa de rejeição baixa" dispara corretamente

---

## Verificação end-to-end

```bash
make lint
.venv/bin/pytest tests/test_metricas_ia.py -v
make dashboard   # navegar até "Métricas IA"
# clicar em "Exportar CSV" e validar arquivo
ls data/output/metricas_ia_*.csv 2>/dev/null || echo "arquivo baixado pelo navegador"
```

---

*"Aquilo que não se mede não se pode melhorar." -- William Thomson Kelvin*
