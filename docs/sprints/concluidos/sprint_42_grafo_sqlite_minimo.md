## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 42
  title: "Grafo SQLite Mínimo: backbone de cruzamentos"
  touches:
    - path: src/graph/__init__.py
      reason: "novo pacote do grafo"
    - path: src/graph/models.py
      reason: "dataclasses Node e Edge + helpers de serialização JSON"
    - path: src/graph/db.py
      reason: "conexão SQLite, criação de schema, upsert idempotente"
    - path: src/graph/schema.sql
      reason: "DDL declarativo das tabelas node e edge + índices"
    - path: src/graph/entity_resolution.py
      reason: "unificação de entidades via rapidfuzz; retorna sugestões de alias_de"
    - path: src/graph/migracao_inicial.py
      reason: "popula grafo a partir do XLSX existente (transações + contrapartes + categorias)"
    - path: src/graph/queries.py
      reason: "biblioteca de consultas canônicas (vida-de-transacao, itens-por-fornecedor, etc)"
    - path: mappings/tipos_node.yaml
      reason: "catálogo de tipos de nó permitidos"
    - path: mappings/tipos_edge.yaml
      reason: "catálogo de tipos de aresta permitidos"
    - path: src/pipeline.py
      reason: "após gerar_xlsx, chamar migracao_incremental do grafo"
    - path: pyproject.toml
      reason: "adiciona rapidfuzz; SQLAlchemy opcional (decisão interna)"
  n_to_n_pairs:
    - [src/graph/schema.sql, src/graph/db.py]
    - [mappings/tipos_node.yaml, src/graph/models.py]
    - [mappings/tipos_edge.yaml, src/graph/models.py]
  forbidden:
    - data/output/ouroboros_*.xlsx  # grafo NÃO sobrescreve o XLSX; coexiste
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: ".venv/bin/pytest tests/test_graph.py -x -q"
      timeout: 60
    - cmd: ".venv/bin/python -m src.graph.migracao_inicial"
      timeout: 300
  acceptance_criteria:
    - "data/output/grafo.sqlite existe após migração inicial"
    - "Grafo tem >= 6.136 nodes tipo=transacao (um por transação do XLSX)"
    - "Grafo tem >= 500 nodes tipo=fornecedor (contrapartes unificadas via rapidfuzz)"
    - "Grafo tem nodes tipo=periodo para cada YYYY-MM entre 2019-10 e 2026-04"
    - "queries.vida_de_transacao(id) retorna pelo menos 3 arestas (categoria, origem, periodo)"
    - "Rodar migração inicial duas vezes não duplica (idempotente)"
    - "Acentuação PT-BR correta"
    - "Zero emojis"
```

> Executar antes de começar: `make lint && ./run.sh --check`

---

# Sprint 42 -- Grafo SQLite Mínimo

**Status:** CONCLUÍDA
**Data:** 2026-04-19 (criada e implementada no mesmo dia)
**Prioridade:** CRÍTICA
**Tipo:** Infra
**Dependências:** Nenhuma (paralelizou com 41)
**Desbloqueia:** Sprints 43, 44-53 (extratores gravam no grafo; dashboard/busca/linking consomem)
**Issue:** --
**ADR:** ADR-12, ADR-14
**Conferência Artesanal Opus:** `docs/propostas/sprint_42_conferencia.md`
**Migração contra XLSX real:** 6086 transações + 1099 fornecedores canônicos (entity resolution unificou 17% de 1321 locais distintos) + 24506 arestas. Idempotente confirmado.

---

## Como Executar

**Comandos principais:**
- `.venv/bin/python -m src.graph.migracao_inicial`
- `.venv/bin/python -c "from src.graph import queries; print(queries.estatisticas())"`
- `make lint`
- `.venv/bin/pytest tests/test_graph.py`

### O que NÃO fazer

- NÃO quebrar o XLSX -- o grafo é derivado, coexiste
- NÃO usar ORM pesado sem justificar (SQLAlchemy core ok; ORM declarativo só se ganhar clareza)
- NÃO adicionar motores de linking complexos (Sprint 48)
- NÃO mexer em dashboard nesta sprint (Sprint 51)
- NÃO expor grafo em API (Local First, sem servidor)

---

## Problema

Hoje todos os cruzamentos são feitos ad-hoc no XLSX via pandas. Perguntas como "quanto paguei à NEOENERGIA em 2025?" precisam de join manual; "este cupom fiscal de R$ 50 bate com qual débito no Itaú?" não tem resposta automatizada; entity resolution (NEOENERGIA vs Neoenergia SA vs NEOEN S/A) é manual.

Sem um grafo, nada do roadmap de Fase DELTA/EPSILON sai do papel. Sem a migração do histórico, fica só promessa — precisa popular com os dados reais do XLSX.

## O que já existe (NÃO duplicar)

| Sistema | Arquivo | O que faz |
|---------|---------|-----------|
| XLSX com 8 abas | `data/output/ouroboros_2026.xlsx` | Fonte de verdade atual das transações (6.136 linhas) |
| Pipeline principal | `src/pipeline.py` | Orquestra ETL até gerar XLSX |
| Categorizer | `src/transform/categorizer.py` | Mapeia transação → categoria |
| IRPF tagger | `src/transform/irpf_tagger.py` | Extrai CNPJ/CPF contextual (já reutilizável) |
| Logger | `src/utils/logger.py` | Rotacionado por módulo |

## Implementação

### Fase 1: schema

`src/graph/schema.sql`:

```sql
CREATE TABLE IF NOT EXISTS node (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tipo TEXT NOT NULL,
  nome_canonico TEXT NOT NULL,
  aliases TEXT NOT NULL DEFAULT '[]',   -- JSON array
  metadata TEXT NOT NULL DEFAULT '{}',  -- JSON object
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (tipo, nome_canonico)
);

CREATE INDEX IF NOT EXISTS idx_node_tipo ON node(tipo);

CREATE TABLE IF NOT EXISTS edge (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  src_id INTEGER NOT NULL REFERENCES node(id) ON DELETE CASCADE,
  dst_id INTEGER NOT NULL REFERENCES node(id) ON DELETE CASCADE,
  tipo TEXT NOT NULL,
  peso REAL NOT NULL DEFAULT 1.0,
  evidencia TEXT NOT NULL DEFAULT '{}',  -- JSON object
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (src_id, dst_id, tipo)
);

CREATE INDEX IF NOT EXISTS idx_edge_src ON edge(src_id);
CREATE INDEX IF NOT EXISTS idx_edge_dst ON edge(dst_id);
CREATE INDEX IF NOT EXISTS idx_edge_tipo ON edge(tipo);
```

### Fase 2: `src/graph/models.py`

Dataclasses Node e Edge; helpers `from_row` / `to_row` com JSON encode/decode. Uso explícito de `TypedDict` para `metadata` de cada tipo.

### Fase 3: `src/graph/db.py`

```python
class GrafoDB:
    def __init__(self, caminho: Path): ...
    def criar_schema(self) -> None: ...
    def upsert_node(self, tipo: str, nome_canonico: str, metadata: dict, aliases: list[str] | None = None) -> int: ...
    def adicionar_edge(self, src_id: int, dst_id: int, tipo: str, peso: float = 1.0, evidencia: dict | None = None) -> None: ...
    def buscar_node(self, tipo: str, nome_canonico: str) -> Optional[Node]: ...
    def limpar(self) -> None: ...  # dev only
```

**Idempotência crítica**: `upsert_node` usa `INSERT ... ON CONFLICT(tipo, nome_canonico) DO UPDATE`. `adicionar_edge` usa `INSERT OR IGNORE`.

### Fase 4: `src/graph/entity_resolution.py`

```python
from rapidfuzz import process, fuzz

def resolver_fornecedor(nome_bruto: str, fornecedores_existentes: list[str], threshold: int = 85) -> tuple[str, int]:
    """Retorna (nome_canonico_escolhido, similaridade).
    Se similaridade < threshold, retorna (nome_bruto, 0) -- cadastra como novo.
    Se estiver entre threshold e 95, abre proposta em docs/propostas/resolver/.
    """
```

Regras determinísticas primeiro: remover sufixos `S/A`, `LTDA`, `ME`; upper case; remover pontuação. Só depois fuzzy.

### Fase 5: `src/graph/migracao_inicial.py`

```python
def executar() -> None:
    db = GrafoDB(caminho_padrao())
    db.criar_schema()
    xlsx = _localizar_xlsx_mais_recente()
    df = pd.read_excel(xlsx, sheet_name="extrato")
    _migrar_transacoes(db, df)
    _migrar_fornecedores(db, df)  # entity resolution
    _migrar_categorias(db, df)
    _migrar_periodos(db, df)
    _migrar_contas(db, df)
    _migrar_arestas(db, df)  # categoria_de, origem, ocorre_em, contraparte
    logger.info("Migração inicial: %s", db.estatisticas())
```

Passagem dupla: primeira cria todos os nodes, segunda cria todas as arestas. Evita dependência de ordem.

### Fase 6: `src/graph/queries.py`

Biblioteca de consultas nomeadas:

```python
def vida_de_transacao(id: int) -> list[dict]: ...
def itens_por_fornecedor(cnpj: str, ano: Optional[int] = None) -> list[dict]: ...
def timeline_de_entidade(nome_canonico: str) -> list[dict]: ...
def fornecedores_recorrentes(valor_minimo: float = 500.0) -> list[dict]: ...
def estatisticas() -> dict: ...  # contagem por tipo de node/edge
```

### Fase 7: integração no pipeline

`src/pipeline.py` após `gerar_xlsx`:

```python
from src.graph.migracao_inicial import executar as migrar_grafo
try:
    migrar_grafo()
except Exception as e:
    logger.warning("Migração do grafo falhou (não-bloqueante): %s", e)
```

Não-bloqueante: falha do grafo não derruba o pipeline. Grafo é recuperável via re-migração.

### Fase 8: testes

`tests/test_graph.py`:
- `test_criar_schema_idempotente`
- `test_upsert_node_unico_por_tipo_nome`
- `test_adicionar_edge_dedup_por_tripla`
- `test_resolver_fornecedor_case_similar_alto` (NEOENERGIA vs Neoenergia S/A)
- `test_resolver_fornecedor_nao_casa_diferente` (NEOENERGIA vs IFOOD)
- `test_vida_de_transacao_retorna_arestas_esperadas`
- `test_migracao_idempotente_dobrando_rodada`

## Armadilhas Conhecidas

| Ref | Armadilha | Como evitar |
|-----|-----------|-------------|
| A42-1 | SQLite sem `PRAGMA foreign_keys=ON` não valida FKs | Habilitar no `__init__` da conexão |
| A42-2 | JSON em coluna TEXT sem indexação vira queries O(n) | Normalizar campos quentes como colunas; aceitar O(n) pra queries frias |
| A42-3 | `rapidfuzz.process.extractOne` retorna None pra lista vazia | Sempre guardar comprimento da lista antes de chamar |
| A42-4 | Migrar em transaction única com 6.136 INSERTs explode memória | Chunk de 500 INSERTs com commit intermediário |
| A42-5 | Fornecedor com nome similar mas CNPJ diferente merge errado | Se metadata[cnpj] existe nos dois, só unifica se CNPJs iguais |
| A42-6 | Regenerar schema apaga dados manualmente inseridos (se houver) | `limpar()` só em contexto dev; pipeline nunca apaga |
| A42-7 | `UNIQUE (tipo, nome_canonico)` case-sensitive por default | Guardar sempre `upper().strip()` como `nome_canonico` |

Referência: `docs/ARMADILHAS.md`

## Evidências Obrigatórias

- [ ] `make lint` passa
- [ ] `python -m src.graph.migracao_inicial` roda sem erro
- [ ] `data/output/grafo.sqlite` existe após rodar
- [ ] `python -c "from src.graph import queries; print(queries.estatisticas())"` imprime pelo menos `{transacao: 6136, fornecedor: 500+, categoria: N, periodo: 82, conta: M}`
- [ ] `.venv/bin/pytest tests/test_graph.py -v` passa
- [ ] Pipeline full (`./run.sh --tudo`) conclui com grafo populado no final
- [ ] Rodando migração 2x, contagens não duplicam

## Verificação end-to-end

```bash
make lint
rm -f data/output/grafo.sqlite
.venv/bin/python -m src.graph.migracao_inicial
sqlite3 data/output/grafo.sqlite "SELECT tipo, COUNT(*) FROM node GROUP BY tipo;"
# esperado: transacao, fornecedor, categoria, periodo, conta, tag_irpf

.venv/bin/python -m src.graph.migracao_inicial  # segunda rodada
sqlite3 data/output/grafo.sqlite "SELECT COUNT(*) FROM node;"
# esperado: mesmo número da primeira rodada

.venv/bin/python -c "
from src.graph import queries
print('Estatisticas:', queries.estatisticas())
print('Top 10 fornecedores:', queries.fornecedores_recorrentes()[:10])
"

.venv/bin/pytest tests/test_graph.py -v
```

## Conferência Artesanal Opus

**Arquivos originais a ler:**

- `data/output/ouroboros_2026.xlsx` (aba `extrato`, amostra de 20 linhas)
- Output da query `SELECT * FROM node WHERE tipo = 'fornecedor' ORDER BY nome_canonico;`

**Checklist de conferência:**

1. Contrapartes que são a mesma entidade acabaram unificadas? (NEOENERGIA, "NEOENERGIA S/A", "Neoenergia" -> 1 node)
2. Contrapartes distintas que batem por fuzzy (ex: "Mercado São João" vs "Mercado São José") NÃO foram merged erroneamente?
3. Cada transação tem pelo menos aresta `origem` (→ conta) e `ocorre_em` (→ periodo)?
4. Transações com `tag_irpf` têm aresta `irpf` correspondente?
5. Contagem de nodes bate com a contagem esperada do XLSX?

**Relatório esperado em `docs/propostas/sprint_42_conferencia.md`**:

- Tabela "Top 20 fornecedores canônicos" com aliases absorvidos em cada um
- Lista de "merges suspeitos" (similaridade 85-95) para revisão manual
- Proposta de ajustes de `threshold` em `entity_resolution.py` ou regras de desambiguação em `mappings/desambiguar_fornecedores.yaml`

**Critério de aprovação**: >= 90% dos fornecedores estão canonizados; lista de merges suspeitos tem < 30 itens.

---

*"O grafo é o esqueleto; as arestas são o que lembra." -- princípio de cartógrafo*
