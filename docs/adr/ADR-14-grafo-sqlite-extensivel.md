# ADR-14: Schema Extensível do Grafo SQLite (extensão do ADR-12)

## Status: Aceita

## Contexto

O ADR-12 estabeleceu o grafo SQLite como backbone dos cruzamentos, com tipos iniciais `entidade`, `transacao`, `documento`, `evento` e relações `paga`, `referencia`, `alias_de`, `ocorre_em`.

A visão de 2026-04-19 exige catalogação granular de documentos com itens individuais (20 produtos de uma NF da Americanas, cada um com categoria própria). O schema do ADR-12 é a semente certa, mas precisa ser explicitado como suportar sem rework:

- Itens individuais de NF (produto, qtd, valor unitário, NCM, categoria)
- Fornecedores como entidades de primeira classe (CNPJ, nome canônico, aliases)
- Garantias ligadas a produtos específicos de uma NF
- Receitas médicas ligadas a medicamentos (que são itens de NF de farmácia)
- Arestas de linking heurístico com evidência e nível de confiança

## Decisão

Schema final do grafo, em duas tabelas:

**`node`** (id INTEGER PK, tipo TEXT, nome_canonico TEXT, aliases JSON, metadata JSON, created_at, updated_at)

Tipos iniciais (extensível via `mappings/tipos_node.yaml`):

| Tipo | nome_canonico | metadata típico |
|------|---------------|-----------------|
| `transacao` | hash da transação | `{data, valor, banco, forma_pagamento, quem}` |
| `documento` | id do documento (NF, cupom, recibo, contracheque) | `{tipo_documento, data_emissao, total, caminho_arquivo}` |
| `item` | descrição bruta do item | `{qtd, valor_unit, valor_total, ncm, categoria_item, documento_id}` |
| `fornecedor` | CNPJ ou nome canônico | `{cnpj, nome_fantasia, endereco, aliases}` |
| `categoria` | nome da categoria | `{tipo_categoria: despesa/receita/item}` |
| `conta` | banco + subtipo | `{banco_origem, titular, tipo: cc/cartao/poupanca}` |
| `prescricao` | id da receita médica | `{crm, medico, paciente, validade}` |
| `garantia` | número de série | `{produto, prazo_meses, inicio, fim, fornecedor}` |
| `periodo` | YYYY-MM ou YYYY | `{inicio, fim}` |
| `tag_irpf` | nome da tag | `{tipo: dedutivel, rendimento, imposto}` |

**`edge`** (id INTEGER PK, src_id, dst_id, tipo TEXT, peso REAL, evidencia JSON, created_at)

Tipos de aresta (extensível via `mappings/tipos_edge.yaml`):

| Tipo | src → dst | evidencia típica |
|------|-----------|------------------|
| `alias_de` | node → node | `{similaridade: 0.0-1.0, aprovador}` |
| `documento_de` | documento → `transacao` | `{diff_dias, diff_valor, heuristica}` |
| `contem_item` | documento → item | `{ordem_linha}` |
| `fornecido_por` | documento → fornecedor | `{cnpj_extraido}` |
| `categoria_de` | `transacao` \| item → categoria | `{regra_aplicada}` |
| `origem` | `transacao` → conta | `{arquivo_origem}` |
| `contraparte` | `transacao` → fornecedor \| entidade | `{tipo_relacao}` |
| `ocorre_em` | `transacao` \| documento → periodo | — |
| `prescreve` | prescricao → item \| fornecedor | `{posologia}` |
| `cobre` | garantia → item | `{data_ativacao}` |
| `irpf` | `transacao` \| item → tag_irpf | `{ano}` |
| `transferencia_par` | `transacao` → `transacao` | `{mesmo_valor: bool, diff_horas}` |

**Invariantes:**

1. `nome_canonico` é único por `tipo` (viola o invariante → re-trabalho de entity resolution).
2. `aliases` são sempre um subset de nomes que já apontam por `alias_de` para o node canônico.
3. Arestas nunca apagam `node` — só adicionam `edge` de `alias_de` ou `obsoleta`.
4. Toda `evidencia` de aresta heurística (similaridade, diff de data, fuzzy match) fica no JSON; auditável.

**Migrações:**

- `src/graph/migracao_inicial.py` (Sprint 42): popula grafo a partir do XLSX atual (transações → nodes, contrapartes → fornecedores stub, categorias existentes → nodes).
- Cada nova tipo-de-documento (Sprint 44-47b) adiciona seed nodes mas não altera schema.
- Schema versionado em `data/output/grafo.schema.sql` — regeneração deletando e recriando é seguro (grafo é derivado, não canônico).

**Queries de primeira classe:**

```sql
-- Vida de uma transação
SELECT e.tipo, n.nome_canonico, n.metadata
FROM edge e JOIN node n ON n.id = e.dst_id
WHERE e.src_id = :transacao_id;

-- Todos os itens comprados de um fornecedor no ano
SELECT i.nome_canonico, i.metadata->>'valor_total'
FROM node i
JOIN edge e1 ON e1.dst_id = i.id AND e1.tipo = 'contem_item'
JOIN edge e2 ON e2.src_id = e1.src_id AND e2.tipo = 'fornecido_por'
JOIN node f ON f.id = e2.dst_id AND f.nome_canonico = :cnpj
WHERE i.tipo = 'item';
```

## Consequências

**Positivas:**
- Schema aberto a novos tipos sem migração de tabela (é só cadastrar em YAML).
- Evidência explícita em cada aresta heurística — auditor (humano ou Claude) consegue revisar.
- `rapidfuzz` feito no Python, não no SQL — rápido e independente de extensões SQLite.
- Migração inicial idempotente: rodar duas vezes não duplica.
- Compatível com consulta NL da Sprint 52 (mapeamento pergunta → traversal SQL).

**Negativas:**
- JSON em colunas exige parse manual (não `text->>'key'` universalmente, depende da versão do SQLite).
- Queries complexas podem ficar lentas em > 1M arestas — aceitável para horizonte do projeto (< 100k esperado).
- Sem ORM (SQLAlchemy opcional; decisão adiada para Sprint 42).

## Relações com outras decisões

- Estende ADR-12 (grafo como backbone) sem conflitar.
- Compatível com ADR-07 (Local First) — SQLite único arquivo.
- Depende implicitamente de ADR-13 (supervisor artesanal) — `alias_de` ambíguos viram propostas para humano aprovar.

---

*"Um bom mapa é extensível, não rígido."* -- princípio de cartógrafo
