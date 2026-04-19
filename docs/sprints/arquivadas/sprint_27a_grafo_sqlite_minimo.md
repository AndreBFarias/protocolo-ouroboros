> **ARQUIVADA em 2026-04-19** -- absorvida em 42 (Grafo SQLite Mínimo). Conteúdo preservado abaixo para referência histórica.

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 27a
  title: "Grafo de Conhecimento -- SQLite mínimo e entity resolution"
  touches:
    - path: src/graph/models.py
      reason: "criar Node e Edge via SQLAlchemy em data/output/grafo.sqlite"
    - path: src/graph/entity_resolution.py
      reason: "unificar aliases de entidades com rapidfuzz (threshold >= 85)"
    - path: src/graph/migracao_inicial.py
      reason: "popular grafo com as ~2.859 transações existentes"
    - path: src/dashboard/paginas/grafo.py
      reason: "listar entidades + contagem (sem visualização gráfica ainda)"
    - path: pyproject.toml
      reason: "adicionar rapidfuzz e sqlalchemy"
  n_to_n_pairs:
    - [src/graph/models.py, src/graph/migracao_inicial.py]
    - [src/graph/entity_resolution.py, mappings/entidades.yaml]
  forbidden:
    - src/load/xlsx_writer.py  # grafo não substitui XLSX nesta sprint
    - src/graph/linker.py      # Motor 1 fica para Sprint 27b
    - src/graph/event_detector.py  # Motor 3 fica para Sprint 27b
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: ".venv/bin/pytest tests/test_graph_models.py tests/test_entity_resolution.py -x -q"
      timeout: 120
  acceptance_criteria:
    - "data/output/grafo.sqlite criado com >= 500 nodes e >= 1000 edges após migração inicial"
    - "top 20 entidades unificadas aparecem na página Grafo do dashboard"
    - "threshold rapidfuzz >= 85 documentado e configurável"
    - "Acentuação PT-BR correta em todos os arquivos"
    - "Zero emojis e zero menções a IA"
```

> Executar antes de começar: `make lint && ./run.sh --check`

---

# Sprint 27a -- Grafo de Conhecimento: SQLite mínimo e entity resolution

**Status:** OBSOLETA
**Data:** 2026-04-18
**Prioridade:** ALTA
**Tipo:** Feature
**Dependências:** Sprint 31 (infra LLM -- para desambiguação opcional via provedor de IA), Sprint 34 (auditor -- opcional)
**Desbloqueia:** Sprint 29a (busca global), Sprint 29b (grafo visual e Obsidian rico), Sprint 27b (motores avançados)
**Issue:** #12
**Implementa:** ADR-12 (Cruzamentos via Grafo de Conhecimento)
**ADR:** ADR-12

---

## Como Executar

**Comandos principais:**
- `make lint` -- ruff check + format + acentuação
- `python -m src.graph.migracao_inicial` -- popula `data/output/grafo.sqlite`
- `make dashboard` -- valida página Grafo
- `python -m src.utils.validator` -- 6 checagens de integridade do XLSX

### O que NÃO fazer

- NÃO implementar Motor 1 (linking documento-transação) -- fica para Sprint 27b
- NÃO implementar Motor 3 (detecção de eventos) -- fica para Sprint 27b
- NÃO criar visualização `pyvis` -- fica para Sprint 29b
- NÃO remover categorias.yaml nem overrides.yaml -- grafo complementa, não substitui
- NÃO quebrar as 8 abas do XLSX

---

## Problema

Sprint 27 original (proposta 2026-04-16) agrupava grafo + classificação v2 + 3 motores + visualização -- escopo de 6-9 semanas. O plano 30/60/90 (§3.1) fatia a entrega mínima para caber em 7 dias dentro da janela de 90 dias.

Sem grafo, consultas transversais ("tudo relacionado à Neoenergia", "timeline da entidade X") são impossíveis; o dashboard só tem visão por mês/categoria. E os nomes das entidades são inconsistentes no histórico: "NEOENERGIA", "Neoenergia SA", "NEOEN SA" viram 3 entidades distintas nas estatísticas, poluindo toda análise por contraparte.

Esta sprint entrega apenas o núcleo: persistência relacional + unificação de entidades + página de listagem. Motores avançados e visualização gráfica ficam em sprints posteriores.

---

## O que já existe (NÃO duplicar)

| Sistema | Arquivo | O que faz |
|---------|---------|-----------|
| Categorizador | `src/transform/categorizer.py` | aplica regex e overrides sobre descrição da transação |
| Deduplicador | `src/transform/deduplicator.py` | 3 níveis (UUID, hash, pares de transferência) |
| Tagger IRPF | `src/transform/irpf_tagger.py` | 21 regras em Python que marcam deduções |
| Writer XLSX | `src/load/xlsx_writer.py` | gera as 8 abas a partir do pipeline |

---

## Implementação

### Fase 1: Modelos SQLAlchemy

**Arquivo:** `src/graph/models.py`

Duas entidades: `Node` (id, tipo, atributos JSON, timestamps) e `Edge` (from_id, to_id, verbo, confianca, evidência, fonte). Persistência em `data/output/grafo.sqlite` (já coberto pelo `.gitignore` do diretório `data/`).

Tipos de nó mínimos para esta sprint: `Transacao`, `Entidade`, `Conta`, `Cartao`, `Periodo`, `Categoria`. Tipos `Documento`, `Evento`, `Pessoa`, `Assinatura` ficam para Sprint 27b.

Verbos de aresta mínimos: `categoria`, `contraparte`, `origem`, `transferencia_par`. Verbos `paga`, `parte_de`, `reembolsa`, `instancia_de`, `dedutivel_em` ficam para Sprint 27b.

Índices obrigatórios: `idx_nodes_type`, `idx_edges_from_verb`, `idx_edges_to_verb`.

### Fase 2: Entity resolution

**Arquivo:** `src/graph/entity_resolution.py`

- Camada 1: aliases canônicos em `mappings/entidades.yaml` (30 entidades iniciais: bancos, utilities, farmácias).
- Camada 2: `rapidfuzz` com threshold >= 85 (configurável via constante `FUZZY_THRESHOLD`).
- Se houver empate (dois candidatos >= 85), loga warning e registra como entidade separada marcada `needs_review=True`.

Dependência nova em `pyproject.toml`: `rapidfuzz>=3.0`.

### Fase 3: Migração inicial

**Arquivo:** `src/graph/migracao_inicial.py`

Script idempotente que:
1. Lê `data/output/financas_consolidado.xlsx`, aba `extrato`.
2. Cria nó `Transacao` para cada linha (chave = hash data+valor+conta+descricao).
3. Cria nó `Conta`/`Cartao` a partir de `banco_origem`.
4. Cria nó `Categoria` a partir da coluna `categoria`.
5. Aplica entity resolution sobre a coluna `local` para criar `Entidade`.
6. Cria arestas `origem`, `categoria`, `contraparte`.
7. Marca pares de transferência já detectados pelo `deduplicator` com aresta `transferencia_par`.

Meta: >= 500 nodes e >= 1000 edges ao fim da migração sobre 2.859 transações.

### Fase 4: Página "Grafo" no dashboard

**Arquivo:** `src/dashboard/paginas/grafo.py`

Streamlit simples:
- Tabela de entidades com contagem de transações ligadas e soma de valores.
- Filtro por tipo de nó.
- Aviso em destaque: "Visualização gráfica disponível na Sprint 29b".

Sem `pyvis`, sem Sankey, sem heatmap.

---

## Armadilhas Conhecidas

| Ref | Armadilha | Como evitar |
|-----|-----------|-------------|
| A27a-1 | Explosão de entidades duplicadas por variação de caixa/acentuação | Normalizar (lowercase, sem acento) antes do fuzzy match |
| A27a-2 | `rapidfuzz` unindo falsos positivos ("Farmácia São João" com "Farmácia São Jorge") | Threshold >= 85 + lista de aliases explícita + revisão manual via dashboard |
| A27a-3 | Migração não-idempotente duplicando nodes a cada execução | Chave natural determinística (hash) + `INSERT OR IGNORE` |
| A27a-4 | SQLite travando com escrita concorrente | Single-writer; pipeline já é sequencial |
| A27a-5 | Nome "NEOENERGIA CEB" (histórico) vs "NEOENERGIA" (atual) -- troca de razão social | Aliases manuais em `mappings/entidades.yaml` documentam substituições |
| A27a-6 | Acentuação em nomes ("Padaria Pão Quente") sumindo no lowercase | Normalização via `unicodedata.normalize('NFKD', ...)` só para comparação; nó preserva original |

Referência: `docs/ARMADILHAS.md`

---

## Evidências Obrigatórias

- [ ] `make lint` passa sem erros
- [ ] `python -m src.graph.migracao_inicial` conclui sem crash
- [ ] `data/output/grafo.sqlite` com >= 500 nodes e >= 1000 edges
- [ ] Top 20 entidades unificadas visíveis na página Grafo
- [ ] `make process` continua funcionando sem regressão
- [ ] `python -m src.utils.validator` com 6/6 checagens OK
- [ ] `.venv/bin/pytest tests/test_graph_models.py tests/test_entity_resolution.py -x -q` passa
- [ ] `CLAUDE.md` atualizado listando `src/graph/` em "Estrutura do Projeto"

---

## Verificação end-to-end

```bash
make lint
python -m src.graph.migracao_inicial
sqlite3 data/output/grafo.sqlite "SELECT type, COUNT(*) FROM nodes GROUP BY type;"
sqlite3 data/output/grafo.sqlite "SELECT verb, COUNT(*) FROM edges GROUP BY verb;"
make dashboard  # abrir aba Grafo e validar top 20
.venv/bin/pytest tests/test_graph_models.py tests/test_entity_resolution.py -x -q
```

---

*"Tudo está em tudo." -- Anaxágoras*
