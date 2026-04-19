## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 29a
  title: "UX Navegável -- busca global, abrir PDF e timeline de entidade"
  touches:
    - path: src/dashboard/paginas/busca.py
      reason: "campo único de busca textual + por entidade"
    - path: src/dashboard/paginas/pergunte.py
      reason: "consulta em linguagem natural com SQL read-only gerado por provedor de IA"
    - path: src/dashboard/paginas/entidade.py
      reason: "timeline de transações de uma entidade"
    - path: src/search/parser.py
      reason: "parser de query -- detecta tipo de input"
    - path: src/search/executor.py
      reason: "executor sobre grafo SQLite"
  n_to_n_pairs:
    - [src/search/parser.py, src/search/executor.py]
    - [src/dashboard/paginas/pergunte.py, src/llm/nl_query.py]
  forbidden:
    - src/graph/models.py  # só consome; não altera schema
    - mappings/*.yaml      # só lê
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: ".venv/bin/pytest tests/test_search_parser.py tests/test_nl_query_safety.py -x -q"
      timeout: 120
  acceptance_criteria:
    - "busca por 'neoenergia' retorna >= 30 resultados em < 3s"
    - "'Pergunte' responde 'quanto gastei com farmácia em Q1 2026?' com SQL + evidência"
    - "timeline renderiza para 3 entidades com >= 20 transações cada"
    - "toda query NL é SELECT, timeout 10s, log obrigatório"
    - "Acentuação PT-BR correta"
    - "Zero emojis e zero menções a IA"
```

> Executar antes de começar: `make lint && ./run.sh --check`

---

# Sprint 29a -- UX Navegável: busca global, abrir PDF e timeline de entidade

**Status:** PENDENTE
**Data:** 2026-04-18
**Prioridade:** ALTA
**Tipo:** Feature
**Dependências:** Sprint 27a (grafo mínimo), Sprint 31 (infra de provedor de IA)
**Desbloqueia:** Sprint 29b (grafo visual e Obsidian rico)
**Issue:** #14
**ADR:** ADR-08

---

## Como Executar

**Comandos principais:**
- `make lint`
- `make dashboard` -- validar as 3 páginas novas
- `./run.sh --check` -- health check
- `.venv/bin/pytest tests/test_search_parser.py tests/test_nl_query_safety.py -x -q`

### O que NÃO fazer

- NÃO gerar SQL por concatenação de string -- usar SQLAlchemy com parâmetros
- NÃO permitir UPDATE/DELETE/INSERT na consulta NL -- whitelist SELECT
- NÃO ultrapassar 10s de execução por query
- NÃO exibir números que o provedor gerou sozinho -- toda resposta cita transação de origem
- NÃO criar visualização `pyvis` -- Sprint 29b

---

## Problema

Sprint 29 original juntava busca + timeline + grafo visual + Obsidian rico + "Vida de um Boleto" num escopo de 6-8 semanas. O plano 30/60/90 separa:

- **29a (Fase 3, §3.2 + §3.3 + §3.4)**: entregáveis prioritários que já destravam uso diário -- busca, consulta NL, timeline.
- **29b (pós-90d)**: visualização `pyvis`, "Vida de um Boleto" e Obsidian enriquecido, que dependem do grafo completo (Sprint 27b) e Sprint 20 redesign.

Sem essas 3 páginas, o grafo da Sprint 27a fica invisível. Com elas, o usuário já consulta "neoenergia março 2026" e recebe a fatura + pagamento com evidência em segundos.

---

## O que já existe (NÃO duplicar)

| Sistema | Arquivo | O que faz |
|---------|---------|-----------|
| Grafo SQLite | `src/graph/models.py` | `Node`, `Edge` persistidos (Sprint 27a) |
| Entity resolution | `src/graph/entity_resolution.py` | aliases canônicos (Sprint 27a) |
| Provedor de IA | `src/llm/provider.py` | interface abstrata (Sprint 31) |
| Cache provedor | `src/llm/cache.py` | resposta por hash (Sprint 31) |
| Dashboard base | `src/dashboard/app.py` | 8 páginas existentes |
| XLSX | `src/load/xlsx_writer.py` | fonte para fallback de busca |

---

## Implementação

### Fase 1: Busca global

**Arquivo:** `src/dashboard/paginas/busca.py` + `src/search/parser.py` + `src/search/executor.py`

- Campo `st.text_input` no topo. Shortcut `/` foca o campo (JS).
- Parser detecta tipo: valor (regex `R$ 450` ou `450-500`), período (`março 2026`, `2025`), código (linha digitável), palavra-chave.
- Executor consulta `extrato.local`, `obs`, `categoria`, `tag_irpf` e entidades do grafo (Sprint 27a).
- Resultado em tabela com coluna final "Abrir PDF original". Botão só aparece se existir rastro (`banco_origem` + `mes_ref` -> `data/raw/{pessoa}/{banco}/` tem o arquivo).

### Fase 2: Consulta NL "Pergunte ao sistema"

**Arquivo:** `src/dashboard/paginas/pergunte.py` + `src/llm/nl_query.py`

Orquestração:
1. Usuário digita pergunta em português.
2. Provedor de IA recebe **schema fechado** (colunas do grafo + XLSX) no system prompt.
3. Provedor devolve SQL **read-only** + explicação curta.
4. `nl_query.py` valida:
   - Só `SELECT` no início (whitelist via AST do `sqlparse`)
   - Sem `;` encadeado, sem `PRAGMA`, sem `ATTACH`
   - Timeout de 10s via `signal.alarm`
5. Executa via SQLAlchemy com parâmetros.
6. Resultado volta para o provedor, que formata em linguagem natural **citando transação/entidade específica** (zero alucinação de números).

Toda query gerada fica logada em `data/output/nl_queries.jsonl` (pergunta, SQL, resultado, custo).

Custo estimado: ~$0.01/query com prompt caching.

### Fase 3: Timeline de entidade

**Arquivo:** `src/dashboard/paginas/entidade.py`

- URL: `?slug=neoenergia`.
- Cabeçalho: nome canônico, total 12m, média mensal, último pagamento.
- Gráfico de linha: valor mensal ao longo do tempo.
- Tabela cronológica: data, valor, conta, link "Abrir PDF" (se houver).
- Alertas automáticos simples: "aumento > 15% vs mês anterior" (sem provedor de IA nesta sprint).

Clique em entidade na página Grafo (Sprint 27a) leva para esta timeline.

---

## Armadilhas Conhecidas

| Ref | Armadilha | Como evitar |
|-----|-----------|-------------|
| A29a-1 | SQL injection via NL query | SQLAlchemy parametrizado; AST whitelist; sem `os.system` |
| A29a-2 | Provedor alucinando números | Resposta obrigatoriamente cita transação de origem (regex valida) |
| A29a-3 | Query travando o dashboard | Timeout 10s obrigatório; `signal.alarm` |
| A29a-4 | PDF path com caracteres especiais no `file://` | `urllib.parse.quote` + validar `Path.exists()` antes de exibir botão |
| A29a-5 | Buscar "casal" retorna milhares de linhas | Paginação obrigatória (50 por página) |
| A29a-6 | Cache do provedor servindo resposta antiga com dados que mudaram | TTL curto (24h) para consulta NL; nunca cachear números absolutos |
| A29a-7 | Acento quebrando busca ("farmácia" vs "farmacia") | Normalizar ambos os lados com NFKD |

Referência: `docs/ARMADILHAS.md`

---

## Evidências Obrigatórias

- [ ] `make lint` passa
- [ ] Busca por `neoenergia` retorna >= 30 resultados em < 3s
- [ ] `Pergunte` responde "quanto gastei com farmácia em Q1 2026?" com SQL + evidência
- [ ] Timeline renderiza para 3 entidades (ex.: Neoenergia, Itaú, Santander)
- [ ] Botão "Abrir PDF" funciona em pelo menos 20 transações
- [ ] `.venv/bin/pytest tests/test_search_parser.py tests/test_nl_query_safety.py -x -q` passa
- [ ] Zero query não-SELECT executada (log confirma)
- [ ] `data/output/nl_queries.jsonl` com custo acumulado < $1 em teste

---

## Verificação end-to-end

```bash
make lint
make dashboard  # validar páginas Busca, Pergunte, Entidade
.venv/bin/pytest tests/test_search_parser.py tests/test_nl_query_safety.py -x -q
python -c "import json; print(sum(l['custo_usd'] for l in map(json.loads, open('data/output/nl_queries.jsonl'))))"
```

---

*"A simplicidade é a sofisticação suprema." -- Leonardo da Vinci*
