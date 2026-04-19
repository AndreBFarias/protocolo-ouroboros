## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 34
  title: "Supervisor Auditor: 4 checagens pós-pipeline via Batches API"
  touches:
    - path: src/llm/auditor.py
      reason: "novo módulo com 4 auditorias disparadas via Batches API após make process"
    - path: src/dashboard/paginas/inteligencia.py
      reason: "página reaproveitada para listar proposições de auditoria ao lado das do Modo 1"
    - path: mappings/proposicoes/
      reason: "auditor grava YYYY-MM-DD_auditoria.yaml seguindo mesmo schema da Sprint 31"
  n_to_n_pairs:
    - [src/llm/auditor.py, src/llm/schemas.py]
    - [src/llm/auditor.py, src/llm/cost_tracker.py]
  forbidden:
    - mappings/categorias.yaml  # auditor PROPÕE, humano aprova
    - mappings/overrides.yaml   # idem
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: ".venv/bin/pytest tests/test_llm_auditor.py -x -q"
      timeout: 120
    - cmd: "./run.sh --auditor --dry-run"
      timeout: 60
  acceptance_criteria:
    - "4 verificações implementadas: classificações limiar médio, duplicatas suspeitas, tags IRPF contextuais, anomalias temporais"
    - "Saída em mappings/proposicoes/YYYY-MM-DD_auditoria.yaml no schema da Sprint 31"
    - "Dedup por hash(transacao_id + versao_auditor + tipo_check) evita reprocessar nos últimos 7 dias"
    - "Integração com Batches API: 50% de desconto no custo"
    - "Kill switch por ANTHROPIC_MONTHLY_BUDGET_USD funciona"
    - ">= 5 anomalias detectadas em 1 mês de uso real"
    - "Taxa de aprovação humana >= 60% nas proposições geradas"
    - "Custo mensal < $3"
    - "Acentuação PT-BR correta e zero emojis"
```

> Executar antes de começar: `make lint && ./run.sh --check`

---

# Sprint 34 -- Supervisor Auditor: 4 checagens pós-pipeline via Batches API

**Status:** PENDENTE
**Data:** 2026-04-18
**Prioridade:** ALTA
**Tipo:** Feature
**Dependências:** Sprint 31 (Infra LLM)
**Desbloqueia:** Sprint 35 (IRPF Regras YAML)
**Issue:** --
**Implementa:** ADR-08 (Supervisor-Aprovador) -- Modo 2 Auditor
**ADR:** ADR-08

---

## Como Executar

**Comandos principais:**
- `make lint`
- `./run.sh --auditor --dry-run` -- simula sem contatar provedor
- `./run.sh --auditor` -- dispara Batches API após `make process`
- `make dashboard` -- página "Inteligência Pendente" mostra proposições de auditoria

### O que NÃO fazer

- NÃO escrever direto em `mappings/categorias.yaml` ou `mappings/overrides.yaml`.
- NÃO reprocessar transações já auditadas nos últimos 7 dias (hash canônico).
- NÃO ignorar kill switch de orçamento.
- NÃO misturar auditoria com pipeline principal: é comando separado.

---

## Problema

A Sprint 31 criou o supervisor Modo 1 (categoriza transações marcadas como `Outros` ou `Questionável`). Mas classificações que entram com confiança >= 0.7 nunca mais são conferidas. Problemas escapam:

- Duplicatas sutis (mesmo fornecedor, valor ± 2%, data ± 3 dias) que os 3 níveis de dedup não pegam.
- Tags IRPF com falso positivo (armadilha "CONSULT" casando "consulta médica" como serviço profissional).
- Categorias que dobram mês a mês sem gerar flag.
- Classificações na faixa cinza (0.5 ≤ conf < 0.7) que mereciam segunda opinião.

Um auditor rodando em batch (latência alta aceitável = 50% de desconto na Batches API) fecha esse buraco.

---

## O que já existe (NÃO duplicar)

| Sistema | Arquivo | O que faz |
|---------|---------|-----------|
| Supervisor Modo 1 | `src/llm/supervisor.py` | Categorização via LLM (Sprint 31) |
| Schemas | `src/llm/schemas.py` | Pydantic `SugestaoRegra`, `SugestaoOverride`, `SugestaoTagIRPF`, `AuditoriaClassificacao` |
| Cache | `src/llm/cache.py` | SQLite por hash |
| Cost tracker | `src/llm/cost_tracker.py` | JSONL + kill switch |
| Dashboard | `src/dashboard/paginas/inteligencia.py` | Página lista proposições (Sprint 31) |

---

## Implementação

### Fase 1: módulo `auditor.py`

**Arquivo:** `src/llm/auditor.py`

Entrypoint `python -m src.llm.auditor [--dry-run]`:

1. Carrega XLSX consolidado.
2. Para cada uma das 4 verificações, coleta inputs e calcula hash de dedup.
3. Pula inputs já processados nos últimos 7 dias.
4. Monta batch request via Batches API (tolerante a latência).
5. Aguarda resultado, valida via Pydantic.
6. Grava `mappings/proposicoes/YYYY-MM-DD_auditoria.yaml`.
7. Registra custo em `llm_costs.jsonl` com tag `modo=auditor`.

### Fase 2: as 4 verificações

**`auditar_classificacoes_limiar_medio(df) -> list[AuditoriaClassificacao]`**

Seleciona transações com `0.5 <= confianca < 0.7`. Envia para LLM com prompt "revise classificação". Sugere nova categoria/classificação quando discordar.

**`detectar_duplicatas_suspeitas(df) -> list[SugestaoOverride]`**

Janela deslizante: pares `(data, local, valor)` com `mesmo_local AND abs(valor_diff)/valor < 0.02 AND abs(data_diff_days) <= 3` que passaram dos 3 níveis de dedup. LLM julga se é duplicata real (hash não pegou) ou gastos legítimos repetidos.

**`auditar_tags_irpf_contextuais(df) -> list[SugestaoTagIRPF]`**

Transações com tag IRPF atribuída via regex simples mas com descrição que sugere outra categoria. Exemplo crítico: regex "CONSULT" casou em "CONSULTA MEDICA DR X" → tag deve ser `dedutivel_medico`, não `servicos_profissionais`.

**`detectar_anomalias_temporais(df) -> list[dict]`**

Categorias que:
- Dobraram mês a mês (MoM).
- Sumiram por 2+ meses seguidos.
- Apareceram pela primeira vez no mês corrente.

Cada anomalia vira `SugestaoRegra` quando o LLM propõe padrão novo, ou apenas alerta informativo quando o dado não sustenta regra.

### Fase 3: dedup canônico

**Arquivo:** `src/llm/auditor.py`

```python
def hash_dedup(transacao_id: str, versao_auditor: str, tipo_check: str) -> str:
    return sha256(f"{transacao_id}|{versao_auditor}|{tipo_check}".encode()).hexdigest()
```

Persistir hashes processados em `data/output/auditor_processed.sqlite`. TTL 7 dias.

### Fase 4: Batches API

**Arquivo:** `src/llm/auditor.py`

Usar endpoint de batches do provedor: submete todos os prompts de uma vez, aguarda conclusão (até 24h), baixa resultados. Custo = 50% do preço normal.

Fallback: se batch expira (>24h), retry na próxima execução. Hash de dedup evita reprocessar entrada já resolvida.

### Fase 5: integração com dashboard

**Arquivo:** `src/dashboard/paginas/inteligencia.py`

Lê `mappings/proposicoes/*.yaml` (tanto do Modo 1 quanto do auditor). Mostra tag na UI indicando a origem (`supervisor_modo1` vs `auditor_duplicata` etc). Aprovação/rejeição segue mesmo fluxo da Sprint 31.

### Fase 6: kill switch

**Arquivo:** `src/llm/cost_tracker.py`

Respeitar `ANTHROPIC_MONTHLY_BUDGET_USD` (já existe). Se extrapolar no mês, auditor sai com warning e zero chamadas.

---

## Armadilhas Conhecidas

| Ref | Armadilha | Como evitar |
|-----|-----------|-------------|
| A34.1 | Batch expira >24h sem resposta | Hash de dedup garante retry idempotente; log warning e tentar na próxima execução |
| A34.2 | Mesma transação re-processada várias vezes | `auditor_processed.sqlite` com TTL 7 dias |
| A34.3 | Custo sobe descontroladamente em mês de alto volume | `cost_tracker.checar_orcamento()` barra antes do submit |
| A34.4 | Auditor escreve direto em `categorias.yaml` | Proibido no SPEC; todas as saídas vão para `proposicoes/` |
| A34.5 | Versão do auditor muda e reprocessa tudo | Controlar `versao_auditor` no hash; bump versão força reanálise consciente |
| A34.6 | Proposições auditoria sobrecarregam dashboard | Paginar página "Inteligência Pendente"; agrupar por tipo |

Referência: `docs/ARMADILHAS.md`

---

## Evidências Obrigatórias

- [ ] `make lint` passa sem erros
- [ ] `./run.sh --auditor --dry-run` imprime quantas entradas passariam por cada verificação
- [ ] `./run.sh --auditor` gera `mappings/proposicoes/YYYY-MM-DD_auditoria.yaml` com pelo menos 5 entradas em 1 mês real
- [ ] Taxa de aprovação humana >= 60% nas primeiras 20 proposições
- [ ] Custo mensal registrado < $3
- [ ] `data/output/auditor_processed.sqlite` cresce sem reprocessar entradas repetidas
- [ ] Kill switch bloqueia chamadas quando `ANTHROPIC_MONTHLY_BUDGET_USD` é ultrapassado

---

## Verificação end-to-end

```bash
make lint
./run.sh --auditor --dry-run
./run.sh --auditor
ls mappings/proposicoes/*_auditoria.yaml
tail -n 10 data/output/llm_costs.jsonl | grep auditor
make dashboard   # navegar até "Inteligência Pendente"
```

---

*"O ceticismo não é uma posição; é um método." -- Marcus Aurelius*
