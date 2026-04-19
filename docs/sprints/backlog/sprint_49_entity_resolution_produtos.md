## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 49
  title: "Entity Resolution de Produtos (unificação de itens)"
  touches:
    - path: src/graph/er_produtos.py
      reason: "unifica descrições diferentes do mesmo produto; cria produto_canonico"
    - path: mappings/produtos_canonicos.yaml
      reason: "aliases conhecidos validados pelo supervisor"
    - path: src/pipeline.py
      reason: "chama ER de produtos após linking (Sprint 48)"
  n_to_n_pairs: []
  forbidden: []
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: ".venv/bin/pytest tests/test_er_produtos.py -x -q"
      timeout: 60
  acceptance_criteria:
    - "Desodorante Dove 150ml, Dove Deo 150g, DOVE ROLLON 150ML unificados em produto_canonico único"
    - "Produtos com similaridade 80-95 viram proposta para supervisor"
    - "Aresta mesmo_produto_que criada entre itens equivalentes"
    - "mappings/produtos_canonicos.yaml serve como override manual"
    - "Acentuação PT-BR correta"
```

> Executar antes de começar: `make lint && ./run.sh --check`

---

# Sprint 49 -- Entity Resolution de Produtos

**Status:** PENDENTE
**Data:** 2026-04-19
**Prioridade:** MEDIA
**Tipo:** Feature
**Dependências:** Sprints 42, 44, 45, 46 (itens já existem no grafo)
**Desbloqueia:** Análise por SKU, histórico de preço, alerta de variação
**Issue:** --
**ADR:** ADR-14

---

## Como Executar

- `./run.sh --tudo`
- `.venv/bin/pytest tests/test_er_produtos.py -v`

### O que NÃO fazer

- NÃO unificar produtos de categorias diferentes (shampoo vs condicionador têm nomes similares)
- NÃO usar APIs externas (NCM lookup online) -- offline only

---

## Problema

Mesmo produto aparece com nomes diferentes em NFs de fornecedores distintos:
- "DESODORANTE DOVE CLINICAL 150ML"
- "Dove Deodorant Rollon 150g"
- "DOVE DEO 150ml RO"

Sem unificação, análise "quanto gastei em desodorante Dove em 2026?" requer busca manual. Sprint 49 cria o `produto_canonico` como aresta/node que agrupa variações.

## O que já existe (NÃO duplicar)

| Sistema | Arquivo | O que faz |
|---------|---------|-----------|
| Entity resolution de fornecedor | `src/graph/entity_resolution.py` (Sprint 42) | Mesma ideia, outro domínio |
| rapidfuzz | lib | Fuzzy matching |
| NCM em itens | Metadata do node item | Pista de categoria ampla |

## Implementação

### Fase 1: normalização

```python
def normalizar_descricao(desc: str) -> str:
    desc = desc.upper()
    desc = re.sub(r"\b(DEO|DESOD|DESODORANTE)\b", "DESODORANTE", desc)
    desc = re.sub(r"\b(ML|GR|G|KG)\b", "ML", desc)  # normaliza medidas
    desc = re.sub(r"\s+", " ", desc).strip()
    desc = unicodedata.normalize("NFKD", desc).encode("ascii", "ignore").decode()
    return desc
```

Dicionário de sinônimos em `mappings/produtos_aliases.yaml`:

```yaml
sinonimos:
  desodorante: ["desod", "deo", "desodorante", "desodorant"]
  sabonete: ["sab", "sabonete", "bar soap"]
  amaciante: ["amaci", "amaciante", "softener"]
```

### Fase 2: clustering

```python
def unificar_produtos(db: GrafoDB, threshold: int = 92) -> dict:
    itens = db.listar_nodes(tipo="item")
    normalizados = {i.id: normalizar_descricao(i.nome_canonico) for i in itens}

    clusters = []
    for item_id, norm in normalizados.items():
        for cluster in clusters:
            score = fuzz.token_set_ratio(norm, cluster["canonico"])
            if score >= threshold:
                cluster["membros"].append((item_id, score))
                break
        else:
            clusters.append({"canonico": norm, "membros": [(item_id, 100)]})

    for cluster in clusters:
        if len(cluster["membros"]) >= 2:
            _criar_produto_canonico_e_arestas(db, cluster)
```

### Fase 3: produto canônico no grafo

Tipo novo de node: `produto_canonico`. Aresta `mesmo_produto_que`:

```python
produto_id = db.upsert_node("produto_canonico", cluster["canonico"],
                             metadata={"membros_count": len(cluster["membros"])})
for item_id, score in cluster["membros"]:
    db.adicionar_edge(item_id, produto_id, "mesmo_produto_que",
                      peso=score/100, evidencia={"fuzzy_score": score})
```

### Fase 4: override manual

`mappings/produtos_canonicos.yaml`:

```yaml
# Overrides manuais quando a heurística falha
canonicos:
  - canonico: "DESODORANTE DOVE 150ML"
    aliases:
      - "DESODORANTE DOVE CLINICAL 150ML"
      - "DOVE DEO ROLLON 150G"
      - "DOVE DEODORANT 150ML"
```

Override lido antes da heurística; casos já cobertos não entram em fuzzy.

### Fase 5: propostas para fronteira

Clusters com 80 <= score < 92: proposta em `docs/propostas/resolver/<slug>.md` para humano decidir.

### Fase 6: testes

- `test_unifica_tres_variacoes_dove`
- `test_nao_unifica_shampoo_com_condicionador_do_mesmo_fabricante`
- `test_override_manual_respeitado`
- `test_score_entre_80_92_vira_proposta`

## Armadilhas Conhecidas

| Ref | Armadilha | Como evitar |
|-----|-----------|-------------|
| A49-1 | "Leite 1L" e "Leite 2L" viram cluster (score alto) | Extrair volume da descrição e usar como feature separada |
| A49-2 | Marca diferente mesmo produto (genérico vs marca) | NÃO unificar -- são consumos distintos para análise |
| A49-3 | Token com erro OCR muda o cluster | Normalização robusta (sinonimos.yaml) ajuda mas não resolve tudo |
| A49-4 | Promoção com brinde: "DOVE 150ML + BARRA 60G" vira 1 item inflando a unificação | Detectar "+" na descrição e separar em 2 items (se possível) |

## Evidências Obrigatórias

- [ ] `make lint` passa
- [ ] Testes passam
- [ ] Clusters gerados coerentes (visual review de 10 samples)
- [ ] Overrides em YAML aplicados corretamente
- [ ] Propostas abertas para casos ambíguos

## Verificação end-to-end

```bash
./run.sh --tudo
sqlite3 data/output/grafo.sqlite "
SELECT pc.nome_canonico, COUNT(e.src_id) as membros
FROM node pc
JOIN edge e ON e.dst_id = pc.id AND e.tipo='mesmo_produto_que'
WHERE pc.tipo='produto_canonico'
GROUP BY pc.id
ORDER BY membros DESC LIMIT 20;
"
```

## Conferência Artesanal Opus

**Arquivos originais a ler:** nodes `item` no grafo + clusters resultantes.

**Checklist:**

1. Clusters fazem sentido? (humano concorda que são o mesmo produto)
2. Há falsos merges (produtos diferentes unificados)?
3. Produtos que deveriam unificar ficaram separados?

**Relatório em `docs/propostas/sprint_49_conferencia.md`**: aliases novos para `mappings/produtos_canonicos.yaml`; sinônimos novos para `mappings/produtos_aliases.yaml`.

**Critério**: > 70% dos clusters validados visualmente pelo supervisor; propostas cobrem o restante.

---

*"Nomear com precisão é o começo da sabedoria." -- Confúcio (parafraseado)*
