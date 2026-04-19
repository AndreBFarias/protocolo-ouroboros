## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 50
  title: "Categorização de Itens via YAML"
  touches:
    - path: mappings/categorias_item.yaml
      reason: "regras regex por categoria de produto (higiene, doces, bebidas, limpeza, eletrônicos, etc.)"
    - path: src/transform/item_categorizer.py
      reason: "categorizer dedicado para itens de NF (espelha src/transform/categorizer.py)"
    - path: src/pipeline.py
      reason: "chama item_categorizer após ER de produtos (Sprint 49)"
  n_to_n_pairs:
    - [mappings/categorias_item.yaml, src/transform/item_categorizer.py]
  forbidden:
    - mappings/categorias.yaml  # categorias de transação continuam separadas das de item
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: ".venv/bin/pytest tests/test_item_categorizer.py -x -q"
      timeout: 60
  acceptance_criteria:
    - "mappings/categorias_item.yaml tem pelo menos 80 regras cobrindo 15+ categorias de produto"
    - "Itens não cobertos por regra ficam com categoria_item=Outros + Questionável, e frequentes (>=3 ocorrências) geram proposta de regra nova"
    - "Grafo: aresta categoria_de entre item e categoria"
    - "Cada item_canonico tem exatamente 1 categoria (override > regex > fallback)"
    - "Acentuação PT-BR correta"
```

> Executar antes de começar: `make lint && ./run.sh --check`

---

# Sprint 50 -- Categorização de Itens via YAML

**Status:** PENDENTE
**Data:** 2026-04-19
**Prioridade:** ALTA
**Tipo:** Feature
**Dependências:** Sprints 44-49 (itens extraídos e unificados)
**Desbloqueia:** Análise "quanto gasto em doces vs higiene?", Sprint 51 dashboard
**Issue:** --
**ADR:** ADR-11 (classificação em camadas)

---

## Como Executar

- `./run.sh --tudo`
- `.venv/bin/pytest tests/test_item_categorizer.py -v`

### O que NÃO fazer

- NÃO fundir mappings/categorias.yaml com categorias_item.yaml -- domínios diferentes
- NÃO depender de NCM para tudo -- código é pista, não verdade
- NÃO inferir categoria de item usando só o nome do fornecedor (farmácia pode vender doces)

---

## Problema

Itens estão extraídos (Sprint 44-47b) e unificados (Sprint 49), mas sem categoria. Análise "quanto gastei em doces no mês?" fica impossível sem categorizar produto a produto.

## O que já existe (NÃO duplicar)

| Sistema | Arquivo | O que faz |
|---------|---------|-----------|
| Categorizer de transação | `src/transform/categorizer.py` | Padrão regex+override+fallback; espelhar |
| Categorias de transação | `mappings/categorias.yaml` | 111 regras -- estrutura referência |
| Overrides manuais | `mappings/overrides.yaml` | Padrão de override |

## Implementação

### Fase 1: `mappings/categorias_item.yaml`

Estrutura espelhando categorias.yaml:

```yaml
regras:
  higiene_pessoal:
    regex: "SABONETE|SHAMPOO|CONDICIONADOR|DESODORANTE|ABSORVENTE|FIO DENTAL|PASTA DENT"
    categoria_item: "Higiene"
    classificacao: "Obrigatório"

  doces:
    regex: "CHOCOLATE|BOMBOM|BALA|PIRULITO|BISCOITO RECHEAD|COOKIE|BROWNIE"
    categoria_item: "Doces"
    classificacao: "Supérfluo"

  bebidas_alcoolicas:
    regex: "CERVEJA|VINHO|CACHAÇA|WHISKY|VODKA|GIN"
    categoria_item: "Bebida Alcoólica"
    classificacao: "Supérfluo"

  bebidas_soft:
    regex: "REFRIGERANTE|COCA|GUARANA|SUCO DE CAIXINHA|ENERGETICO"
    categoria_item: "Bebida"
    classificacao: "Questionável"

  laticinios:
    regex: "LEITE\\b|IOGURTE|QUEIJO|MANTEIGA|REQUEIJAO"
    categoria_item: "Laticínios"
    classificacao: "Obrigatório"

  limpeza:
    regex: "SABAO|DETERGENTE|AGUA SANITARIA|AMACIANTE|LIMPA"
    categoria_item: "Limpeza"
    classificacao: "Obrigatório"

  medicamentos:
    regex: "\\bCOMP\\b|DIPIRONA|PARACETAMOL|OMEPRAZOL|VITAMINA"
    categoria_item: "Medicamento"
    classificacao: "Obrigatório"

  eletronicos:
    regex: "CABO|CARREGADOR|FONE|TECLADO|MOUSE|HEADSET"
    categoria_item: "Eletrônicos"
    classificacao: "Supérfluo"

  jogos_midia:
    regex: "JOGO|STEAM|BLURAY|DVD|XBOX|PLAYSTATION"
    categoria_item: "Jogos e Mídia"
    classificacao: "Supérfluo"

  # ... pelo menos 80 regras cobrindo 15+ categorias
```

### Fase 2: categorizer

```python
class ItemCategorizer:
    def __init__(self, caminho_regras: Path = None): ...
    def categorizar(self, item: dict) -> dict:
        """Mutates item com categoria_item e classificacao."""
        ...
    def categorizar_lote(self, itens: list[dict]) -> list[dict]: ...
```

Espelha `Categorizer` mas usa `mappings/categorias_item.yaml`. Fallback: `Outros` + `Questionável` (mesma lógica Sprint 40).

### Fase 3: persistência no grafo

```python
for item in itens:
    cat_id = db.upsert_node("categoria_item", item["categoria_item"],
                             metadata={"classificacao": item["classificacao"]})
    db.adicionar_edge(item["node_id"], cat_id, "categoria_de",
                      evidencia={"regra_aplicada": item["regra_nome"]})
```

### Fase 4: detectar padrões novos

Após lote, conta itens com `categoria_item=Outros` que aparecem ≥3x. Gera proposta em `docs/propostas/categoria_item/<slug>.md`:

```markdown
## Padrão recorrente sem regra

Itens com categoria "Outros" e ≥3 ocorrências:

| Descrição | Ocorrências | Sugestão |
|-----------|-------------|----------|
| BARRA CEREAL NATURE | 5 | categoria=Alimentação Saudável? |
| RACAO PREMIER | 3 | categoria=Pet? |
```

### Fase 5: testes

```python
def test_categoriza_chocolate_como_doces()
def test_sabonete_dove_categoriza_como_higiene()
def test_desconhecido_cai_em_outros_questionavel()
def test_override_manual_prevalece_sobre_regex()
```

## Armadilhas Conhecidas

| Ref | Armadilha | Como evitar |
|-----|-----------|-------------|
| A50-1 | Regex "\bLEITE\b" casa "LEITE MOCA" (leite condensado -- doces) | Ordem de regras importa; específica antes de genérica |
| A50-2 | Categoria "Medicamento" precisa cruzar com prescrição (Sprint 47a) | Aresta adicional `prescreve_cobre` liga quando coincidir |
| A50-3 | NCM pode sinalizar categoria errada (NCM de alimento não diferencia doce vs saudável) | NCM é pista, não verdade; regex vence |
| A50-4 | Item que é serviço (conserto, entrega) vira "Outros" | Adicionar categoria explícita "Serviço" com regex específico |
| A50-5 | Item em combo ("KIT SHAMPOO + COND") confunde regex | Override manual quando detectar combo |

## Evidências Obrigatórias

- [ ] `make lint` passa
- [ ] >= 80 regras em `mappings/categorias_item.yaml` cobrindo ≥ 15 categorias
- [ ] Testes passam com ≥ 10 cenários
- [ ] ≥ 70% dos itens do grafo categorizados (fora de "Outros")
- [ ] Propostas abertas para padrões recorrentes

## Verificação end-to-end

```bash
./run.sh --tudo
sqlite3 data/output/grafo.sqlite "
SELECT c.nome_canonico, COUNT(e.src_id) as itens
FROM node c
JOIN edge e ON e.dst_id = c.id AND e.tipo='categoria_de'
WHERE c.tipo='categoria_item'
GROUP BY c.id ORDER BY itens DESC;
"
```

## Conferência Artesanal Opus

**Arquivos originais a ler:** lista de itens com categoria atribuída (query SQL) + 20 amostras aleatórias.

**Checklist:**

1. Cada item recebeu categoria coerente com o nome?
2. Classificação (Obrigatório/Questionável/Supérfluo) faz sentido para o contexto do usuário?
3. Itens em "Outros" têm padrão que justifica regra nova?

**Relatório em `docs/propostas/sprint_50_conferencia.md`**: regras novas propostas + ajustes em classificação.

**Critério**: ≥ 70% de itens categorizados automaticamente; propostas cobrem o cauda longa.

---

*"Conhecer pelo nome é o primeiro passo da economia." -- princípio do orçamento*
