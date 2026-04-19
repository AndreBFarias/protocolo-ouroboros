## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 52
  title: "Busca Global Documento-Cêntrica + Timeline"
  touches:
    - path: src/dashboard/paginas/busca.py
      reason: "página Streamlit com input único que busca em transações, documentos, itens, fornecedores"
    - path: src/graph/busca.py
      reason: "backend da busca: parse da query + execução no grafo + ranking"
  n_to_n_pairs: []
  forbidden:
    - data/output/ouroboros_*.xlsx  # busca usa grafo, não XLSX
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: ".venv/bin/pytest tests/test_busca.py -x -q"
      timeout: 60
  acceptance_criteria:
    - "Busca por CNPJ retorna fornecedor + documentos + transações relacionadas"
    - "Busca por termo retorna itens, categorias, transações com descrição matching"
    - "Timeline de entidade mostra cronologia (data × documento × valor × categoria)"
    - "Tempo de resposta < 500ms em query típica"
    - "Acentuação PT-BR correta"
```

> Executar antes de começar: `make lint && ./run.sh --check`

---

# Sprint 52 -- Busca Global Doc-Cêntrica

**Status:** PENDENTE
**Data:** 2026-04-19
**Prioridade:** ALTA
**Tipo:** Feature
**Dependências:** Sprints 42 (grafo), 48 (linking), 51 (dashboard)
**Desbloqueia:** Navegação rica, consulta NL futura
**Issue:** --
**ADR:** ADR-12

---

## Como Executar

- `make dashboard` → Busca
- `.venv/bin/pytest tests/test_busca.py`

### O que NÃO fazer

- NÃO implementar busca full-text com índice (SQLite FTS5 é opcional, decide interno)
- NÃO fazer consulta NL via LLM nesta sprint -- só busca estruturada

---

## Problema

Usuário precisa responder: "Quanto gastei com NEOENERGIA em 2025?", "Quais NFs da Americanas?", "Timeline do produto X?" Hoje resposta exige SQL manual; não escalável.

## O que já existe (NÃO duplicar)

| Sistema | Arquivo | O que faz |
|---------|---------|-----------|
| Grafo | `src/graph/queries.py` | Queries canônicas (vida_de_transacao, fornecedores_recorrentes) |
| Dashboard | `src/dashboard/app.py` | Infra Streamlit |
| rapidfuzz | lib | Já usado em entity resolution |

## Implementação

### Fase 1: parser de query

```python
def parsear_query(q: str) -> dict:
    """Detecta tipo: cnpj | cpf | data | intervalo | termo_livre."""
    if re.match(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}", q):
        return {"tipo": "cnpj", "valor": _normalizar_cnpj(q)}
    if re.match(r"\d{3}\.\d{3}\.\d{3}-\d{2}", q):
        return {"tipo": "cpf", "valor": q}
    if re.match(r"\d{4}-\d{2}(-\d{2})?", q):
        return {"tipo": "data", "valor": q}
    return {"tipo": "termo", "valor": q}
```

### Fase 2: executor

```python
def buscar(q: dict) -> dict:
    """Retorna {fornecedores, documentos, transacoes, itens} rankeados."""
    if q["tipo"] == "cnpj":
        forn = _buscar_fornecedor(q["valor"])
        if forn:
            return {
                "fornecedores": [forn],
                "documentos": _documentos_de(forn["id"]),
                "transacoes": _transacoes_de(forn["id"]),
                "itens": _itens_de(forn["id"]),
            }
    if q["tipo"] == "termo":
        return {
            "fornecedores": _fuzzy_fornecedores(q["valor"]),
            "itens": _fuzzy_itens(q["valor"]),
            "transacoes": _texto_transacoes(q["valor"]),
        }
    return {}
```

### Fase 3: timeline

```python
def timeline_entidade(nome_canonico: str) -> list[dict]:
    """
    Ordena cronologicamente todos os eventos relacionados à entidade:
    transações, documentos, itens, arestas novas.
    """
    ...
```

Render em Streamlit com `st.timeline` ou lista vertical com ícones.

### Fase 4: UI

```
[ 🔍 Buscar: _______________ ]

Fornecedores encontrados
  ▪ NEOENERGIA S.A. (CNPJ 00.394.460/0058-87) -- 48 documentos, R$ 12.340

Documentos
  📄 Fatura 2025-03.pdf -- R$ 487,23
  📄 Fatura 2025-02.pdf -- R$ 512,11
  ...

Transações
  💰 2025-03-08 Débito R$ 487,23 "NEOENERGIA DF"
  ...

Timeline [ver]
```

### Fase 5: testes

- `test_busca_por_cnpj_retorna_fornecedor_e_docs`
- `test_busca_por_termo_fuzzy_casa_sinonimo`
- `test_timeline_ordena_cronologicamente`
- `test_performance_query_tipica_menor_500ms`

## Armadilhas Conhecidas

| Ref | Armadilha | Como evitar |
|-----|-----------|-------------|
| A52-1 | CNPJ digitado sem pontuação | Normalizar antes de comparar |
| A52-2 | Acentos na busca livre diferem de acento no node | Comparar sempre depois de `unicodedata.normalize("NFKD", ...)` |
| A52-3 | Timeline com milhares de eventos trava Streamlit | Paginar (50 por página) |
| A52-4 | Entity resolution imperfeita separa resultados do mesmo fornecedor | Unir aliases na resposta |

## Evidências Obrigatórias

- [ ] Testes passam
- [ ] Busca por CNPJ existente retorna resultados corretos
- [ ] Timeline renderiza cronologicamente
- [ ] Performance < 500ms em amostras típicas

## Verificação end-to-end

```bash
make dashboard &
sleep 3
# abrir http://localhost:8501 → Busca → digitar "NEOENERGIA"
.venv/bin/pytest tests/test_busca.py -v
```

## Conferência Artesanal Opus

**Arquivos originais a ler:** queries executadas no grafo + UI renderizada.

**Checklist:**

1. Resultados batem com consulta SQL manual?
2. Ranking faz sentido (mais recente ou mais relevante primeiro)?
3. Timeline inclui todos os eventos conhecidos?

**Relatório em `docs/propostas/sprint_52_conferencia.md`**: ajustes de ranking, campos novos na busca.

**Critério**: 5 queries realistas do usuário retornam resultado correto em < 500ms.

---

*"Buscar é perguntar com precisão." -- Sócrates (parafraseado)*
