## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 48
  title: "Linking Documento ↔ Transação bancária"
  touches:
    - path: src/graph/linking.py
      reason: "motor heurístico que cria arestas documento_de entre documento e transação"
    - path: mappings/linking_config.yaml
      reason: "thresholds ajustáveis por tipo de documento"
    - path: src/pipeline.py
      reason: "chama linking após extratores de documento"
  n_to_n_pairs: []
  forbidden: []
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: ".venv/bin/pytest tests/test_linking.py -x -q"
      timeout: 120
  acceptance_criteria:
    - "Para 10 NFs conhecidas, 8+ foram linkadas automaticamente a transações corretas"
    - "Falsos positivos (link errado) < 5% em amostra de 50 documentos"
    - "Conflitos (mais de 1 transação candidata) viram proposta em docs/propostas/linking/"
    - "Aresta documento_de tem evidencia JSON com diff_dias, diff_valor e heuristica"
    - "Acentuação PT-BR correta"
```

> Executar antes de começar: `make lint && ./run.sh --check`

---

# Sprint 48 -- Linking Documento ↔ Transação

**Status:** CONCLUÍDA
**Data:** 2026-04-19
**Prioridade:** ALTA
**Tipo:** Feature
**Dependências:** Sprints 42 (grafo), 44-47b (documentos ingeridos)
**Desbloqueia:** Dashboard doc-cêntrico, relatórios granulares por item
**Issue:** --
**ADR:** ADR-14

---

## Como Executar

- `./run.sh --tudo`
- `.venv/bin/pytest tests/test_linking.py -v`

### O que NÃO fazer

- NÃO linkar por data apenas -- sempre combinar data + valor + fornecedor
- NÃO sobrescrever linking humano aprovado (respeita `evidencia.aprovador`)
- NÃO inventar transação quando não existe -- ausência é informação

---

## Problema

Hoje o grafo tem nodes `documento` (NFs, cupons, recibos) e nodes `transacao` (débitos, créditos), mas nenhuma aresta os conectando. Sem linking, não se responde: "esta NF bate com qual transação bancária?" -- a principal pergunta do usuário.

## O que já existe (NÃO duplicar)

| Sistema | Arquivo | O que faz |
|---------|---------|-----------|
| Grafo | `src/graph/db.py` | upsert_node, adicionar_edge |
| Entity resolution | `src/graph/entity_resolution.py` | Fornecedor normalizado |
| Transações no grafo | `src/graph/migracao_inicial.py` | Nodes transação já existem |

## Implementação

### Fase 1: heurística base

`src/graph/linking.py`:

```python
def candidatas_para_documento(db: GrafoDB, documento_id: int) -> list[tuple[int, dict]]:
    """Retorna lista (transacao_id, evidencia) de candidatas ordenadas por confiança."""
    doc = db.buscar_node_by_id(documento_id)
    data = date.fromisoformat(doc.metadata["data_emissao"])
    total = float(doc.metadata["total"])
    cnpj = doc.metadata.get("cnpj_emissor")

    candidatas = []
    for delta in range(-3, 4):
        data_q = data + timedelta(days=delta)
        rows = db.conn.execute("""
            SELECT id, metadata FROM node
            WHERE tipo='transacao'
              AND JSON_EXTRACT(metadata, '$.data') = ?
              AND ABS(JSON_EXTRACT(metadata, '$.valor') - ?) <= 1.0
        """, (data_q.isoformat(), total)).fetchall()
        for row in rows:
            meta = json.loads(row["metadata"])
            score = _calcular_score(meta, delta, total, cnpj)
            candidatas.append((row["id"], {
                "diff_dias": delta,
                "diff_valor": abs(meta["valor"] - total),
                "score": score,
                "heuristica": "data_valor_fornecedor",
            }))

    return sorted(candidatas, key=lambda x: x[1]["score"], reverse=True)


def _calcular_score(transacao_meta: dict, delta_dias: int, valor_doc: float, cnpj_doc: str | None) -> float:
    score = 1.0
    score -= abs(delta_dias) * 0.1
    score -= abs(transacao_meta["valor"] - valor_doc) / max(valor_doc, 1) * 0.5
    if cnpj_doc and cnpj_doc in transacao_meta.get("local", ""):
        score += 0.3
    return score
```

### Fase 2: aplicar linking

```python
def linkar_documentos(db: GrafoDB) -> dict:
    stats = {"linkados": 0, "conflitos": 0, "sem_candidato": 0}
    docs_sem_aresta = db.conn.execute("""
        SELECT id FROM node WHERE tipo='documento'
        AND id NOT IN (SELECT src_id FROM edge WHERE tipo='documento_de')
    """).fetchall()

    for (doc_id,) in docs_sem_aresta:
        candidatas = candidatas_para_documento(db, doc_id)
        if not candidatas:
            stats["sem_candidato"] += 1
            continue

        melhor = candidatas[0]
        if melhor[1]["score"] >= 0.9:
            db.adicionar_edge(doc_id, melhor[0], "documento_de",
                              peso=melhor[1]["score"],
                              evidencia=melhor[1])
            stats["linkados"] += 1
        elif len(candidatas) > 1 and candidatas[1][1]["score"] > melhor[1]["score"] - 0.1:
            _abrir_proposta_conflito(doc_id, candidatas[:3])
            stats["conflitos"] += 1
        else:
            _abrir_proposta_baixa_confianca(doc_id, melhor)
            stats["conflitos"] += 1

    return stats
```

### Fase 3: propostas

Conflitos e baixa confiança viram arquivos em `docs/propostas/linking/<doc_id>.md` com template `docs/templates/PROPOSTA_LINKING.md`. Claude Code lê o arquivo original + as candidatas, decide com humano.

### Fase 4: testes

Fixtures: grafo seed com 5 documentos e 20 transações; 3 matchings corretos garantidos, 1 conflito proposital, 1 sem candidato.

## Armadilhas Conhecidas

| Ref | Armadilha | Como evitar |
|-----|-----------|-------------|
| A48-1 | Parcelado em 3x: NF R$ 300 vs transação R$ 100 x3 | Detectar parcelamento olhando descrição da transação ("1/3"); documenta mas não linka se ambíguo |
| A48-2 | Pix instantâneo: data da NF = data da transação (delta=0); muitos candidatos | Aumentar peso do fornecedor no score quando delta=0 |
| A48-3 | Compra com desconto na fatura: valor difere de NF | Tolerância ±R$ 1 não cobre; deixar para proposta |
| A48-4 | Várias NFs do mesmo valor na mesma data | Top-2 com score próximo sempre vira proposta |
| A48-5 | Transação já linkada a outro documento | Permitir múltiplos documentos→1 transação (parcelamento); mas detectar soma de docs > transação |

## Evidências Obrigatórias

- [ ] `make lint` passa
- [ ] >= 8/10 NFs conhecidas linkadas automaticamente
- [ ] Falsos positivos < 5%
- [ ] Propostas criadas quando houver ambiguidade
- [ ] Testes passam

## Verificação end-to-end

```bash
./run.sh --tudo
sqlite3 data/output/grafo.sqlite "SELECT COUNT(*) FROM edge WHERE tipo='documento_de';"
ls docs/propostas/linking/
.venv/bin/pytest tests/test_linking.py -v
```

## Conferência Artesanal Opus

**Arquivos originais a ler:** 10 NFs e as transações candidatas (via SQL + PDF/imagem).

**Checklist:**

1. Para cada linking criado: a transação realmente corresponde?
2. Casos em `_proposta/` têm contexto suficiente para humano decidir?
3. Scores fazem sentido (alto para match óbvio, baixo para ambíguo)?

**Relatório em `docs/propostas/sprint_48_conferencia.md`**: tabela com linking proposto vs correto e ajustes sugeridos em thresholds.

**Critério**: ≥ 80% de precisão em amostra de 10 NFs, todos os conflitos viraram proposta (não foram linkados silenciosamente).

---

*"Ligar é responsabilidade -- ligar errado é confundir a memória." -- princípio do arquivista*
