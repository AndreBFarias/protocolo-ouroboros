# GLOSSARIO — Termos canônicos do projeto

> Sprint **DOC-VERDADE-01.E**. Resolve ambiguidade detectada em sessão de validação onde Opus fresh confundiu `categoria` (slot textual no XLSX) com `tipo` (enum estrito) e ainda com `categoria` (node tipo no grafo SQLite). 3 camadas, 3 contextos, mesmo nome em alguns casos — esta página dá o vocabulário comum.

## §1 — As 3 camadas que parecem iguais e não são

### Camada 1 — `categoria` (string livre na coluna do `extrato`)

**O que é**: slot textual humano na coluna `categoria` da aba `extrato` do `data/output/ouroboros_2026.xlsx`.

**Valores possíveis**: livre, mas vem de `mappings/categorias.yaml` ou de `mappings/overrides.yaml`. Exemplos reais:
- `Mercado`
- `Padaria`
- `Pagamento de Fatura`
- `Aluguel`
- `Farmácia`
- `Energia`
- `Outros` (fallback quando regex não casa)

**Quem preenche**: `src/transform/categorizer.py` aplicando regras regex em ordem (overrides → regex YAML → fallback `Outros`).

**Onde vê na vida real**: linha do extrato XLSX, dashboard Streamlit aba "Categorias", relatório mensal `.md`.

### Camada 2 — `tipo` (enum estrito na coluna do `extrato`)

**O que é**: slot **enum** na coluna `tipo` da mesma aba `extrato`. Define **como a transação entra nas métricas mensais**.

**Valores possíveis (apenas 4)**:
- `Despesa` — saída de dinheiro consumida (compra de mercado, gasolina, plano de saúde).
- `Receita` — entrada de dinheiro próprio (salário, bolsa, freelance).
- `Transferência Interna` — movimentação **entre contas próprias** do casal. **Não é gasto nem receita** — é dinheiro que muda de bolso.
- `Imposto` — pagamento a Receita Federal/Estado/Município (DAS, IPVA, IPTU). Tratado separadamente para tag IRPF.

**Quem preenche**: `src/transform/normalizer.py` (campo `_classificar_tipo`). Regras hierárquicas, com canonicalizer de transferência interna como camada de proteção.

**Pegadinha clássica**: pagamento de fatura entre contas próprias é `tipo=Transferência Interna`, **não** `tipo=Despesa`. Mesmo que pareça "saiu dinheiro do banco", o dinheiro entrou em outro banco do mesmo dono.

### Camada 3 — `categoria` (node tipo `categoria` no grafo SQLite)

**O que é**: entidade no grafo `data/output/grafo.sqlite` (ADR-14). Cada categoria do `extrato` que aparece em pelo menos uma transação ganha um node com `tipo='categoria'`.

**Atributos**:
- `nome_canonico`: nome em maiúscula (ex: `MERCADO`, `OUTROS`).
- `metadata`: dict opcional, podendo ter `tipo_categoria: despesa | receita | item` (ADR-14:31).

**Arestas que conecta**:
- `categoria_de`: `transacao` ou `item` → `categoria`.

**Onde vê**: query `SELECT * FROM node WHERE tipo='categoria'`. Atualmente o grafo de produção tem ~104 categorias distintas.

## §2 — Tabela comparativa rápida

| Aspecto | Camada 1 (`extrato.categoria`) | Camada 2 (`extrato.tipo`) | Camada 3 (node `categoria` no grafo) |
|---------|-------------------------------|---------------------------|--------------------------------------|
| Onde mora | Coluna do XLSX | Coluna do XLSX | Tabela `node` em SQLite |
| Cardinalidade | ~100 valores observados | 4 valores fixos | ~100 nodes (1 por valor distinto da Camada 1) |
| É enum? | Não — texto livre | **Sim** | Não — string identificadora |
| Quem produz | `categorizer.py` | `normalizer.py` | `ingestor_documento.py` + arestas no pipeline |
| Pode ter acento | Sim (`Energia`, `Saúde`) | Sim (`Transferência Interna`) | **Não** (`SAUDE`, `ENERGIA` — uppercase canonical) |
| Mutável em runtime | Sim, via override YAML | Não, regras fixas | Sim, via `INSERT OR IGNORE` em pipeline |

## §3 — Exemplos canônicos (transação → 3 camadas)

### Exemplo 1: compra de pão no mercado

| Campo | Valor |
|-------|-------|
| `extrato.categoria` (Camada 1) | `Padaria` |
| `extrato.tipo` (Camada 2) | `Despesa` |
| Node grafo (Camada 3) | `node(tipo='categoria', nome_canonico='PADARIA')` |
| Arestas | `transacao → PADARIA via categoria_de`; `transacao → MERCADO_X via contraparte` |

### Exemplo 2: pagamento da fatura do Nubank do André via PIX da conta Itaú

| Campo | Valor |
|-------|-------|
| `extrato.categoria` (Camada 1) | `Pagamento de Fatura` |
| `extrato.tipo` (Camada 2) | **`Transferência Interna`** (não `Despesa`!) |
| Node grafo (Camada 3) | `node(tipo='categoria', nome_canonico='PAGAMENTO DE FATURA')` |
| Arestas | `tx_saida ↔ tx_entrada via transferencia_par`; ambas categorizadas como `PAGAMENTO DE FATURA` |

A pegadinha aqui: a coluna `categoria` mostra `Pagamento de Fatura` (descritivo humano), mas a coluna `tipo` é `Transferência Interna` (semântica de fluxo de caixa). Ambos coexistem. Sprint A da validação tropeçou exatamente nessa diferença.

### Exemplo 3: pagamento de IPVA

| Campo | Valor |
|-------|-------|
| `extrato.categoria` (Camada 1) | `Mobilidade` (ou `Imposto Veículo` dependendo da regra) |
| `extrato.tipo` (Camada 2) | **`Imposto`** (não `Despesa`) |
| Node grafo (Camada 3) | `node(tipo='categoria', nome_canonico='MOBILIDADE')` + `node(tipo='tag_irpf', nome_canonico='imposto_pago')` |
| Arestas | `transacao → tag_irpf via irpf` |

`tipo=Imposto` permite que o pacote IRPF (futura sprint IRPF-01) capture todos os tributos pagos no ano sem precisar varrer `categoria` específicas.

## §4 — Regra prática para o supervisor

Quando alguém (dono ou outro Opus) disser "categoria":

1. Pergunte (ou descubra pelo contexto): **camada 1, 2 ou 3?**
2. Se for análise financeira humana ("quanto gastei em Mercado?") → **Camada 1**.
3. Se for métrica agregada do mês ("quanto foi receita vs despesa?") → **Camada 2**.
4. Se for cruzamento no grafo ("quais transações conectam ao mesmo fornecedor categorizado como Padaria?") → **Camada 3**.

Se diferenças entre as 3 camadas aparecerem em runtime (ex: `extrato.categoria='Pagamento de Fatura'` mas `extrato.tipo='Despesa'`), é **bug de classificação** — abrir sprint-filha.

## §5 — Onde isso é referenciado

- **`CLAUDE.md §Schema do XLSX`** lista as colunas `categoria` e `tipo` mas remete aqui para a diferença prática.
- **`mappings/categorias.yaml`** declara regras regex → categoria (Camada 1).
- **`docs/adr/ADR-14-grafo-sqlite-extensivel.md`** define schema do node `categoria` (Camada 3).
- **`src/transform/categorizer.py`** preenche Camada 1.
- **`src/transform/normalizer.py`** preenche Camada 2.
- **`src/graph/ingestor_documento.py`** ingere Camada 3.

## §6 — Outros termos canônicos (mini)

### `quem`

Coluna do `extrato` com **3 valores** (na verdade 4, contando vazio): `André`, `Vitória`, `Casal`, ou null. Inferido por `pessoa_detector.py` via:
1. Identificadores em `mappings/pessoas.yaml` (PII, gitignored).
2. Pasta de origem (`data/raw/andre/...` → André).
3. CPF/CNPJ no conteúdo do documento.

### `forma_pagamento`

Coluna do `extrato` com valores normalizados: `Pix`, `Débito`, `Crédito`, `Boleto`, `Transferência`. Vem de `_FORMAS_CANONICAS` em `src/dashboard/dados.py`.

### `mes_ref`

Coluna do `extrato` no formato `YYYY-MM`. Mês de referência da transação. Usado para todos os agregados mensais.

### `tag_irpf`

Coluna opcional do `extrato`. Quando preenchida, vem de `src/transform/irpf_tagger.py` casando regras em `mappings/irpf_regras.yaml`. Valores canônicos: `pagador`, `fonte_renda`, `despesa_dedutivel`, `deducao_legal`, `imposto_pago`.

---

*"Mesmo nome em contextos diferentes é ambiguidade silenciosa. Glossário é antídoto." — princípio do vocabulário comum*
