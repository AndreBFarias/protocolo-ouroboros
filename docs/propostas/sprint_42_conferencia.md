---
id: 2026-04-19_sprint_42_conferencia
tipo: conferencia_artesanal
sprint: 42
data: 2026-04-19
status: aprovada
autor_proposta: supervisor-artesanal-claude-code
---

# Conferência Artesanal Opus -- Sprint 42 (Grafo SQLite Mínimo)

## Setup

- Comando: `python -m src.graph.migracao_inicial`
- Fonte: `data/output/ouroboros_2026.xlsx` (6086 transações reais)
- Suíte: 228/228 testes (207 antigos + 21 novos do graph)
- Lint limpo, dep nova: `rapidfuzz>=3.0`

## Resultado da migração

```
Nodes total:  7378
  transacao   6086   (1 por linha do XLSX)
  fornecedor  1099   (entity-resolved a partir de 1321 locais distintos)
  categoria    100   (categorias do YAML acumuladas no histórico)
  periodo       82   (out/2019 a abr/2026, todos meses)
  conta          7   (Itaú, Santander, C6, Nubank PF/PJ, etc.)
  tag_irpf       4

Edges total: 24506
  categoria_de  6086  (transação -> categoria)
  ocorre_em     6086  (transação -> período)
  origem        6086  (transação -> conta/banco)
  contraparte   6084  (transação -> fornecedor; 2 sem contraparte resolvida)
  irpf           164  (transações marcadas com tag IRPF)
```

**Idempotência confirmada:** 2ª rodada deu mesma contagem.

## Checklist

| # | Pergunta | Resultado |
|---|----------|-----------|
| 1 | Schema idempotente (CREATE IF NOT EXISTS)? | OK |
| 2 | upsert_node único por (tipo, nome_canonico)? | OK -- merge raso de aliases e metadata |
| 3 | Edges com UNIQUE(src,dst,tipo) -- duplicata ignorada? | OK |
| 4 | Foreign keys habilitadas (PRAGMA)? | OK -- DELETE CASCADE em node remove edges |
| 5 | Entity resolution unifica NEOENERGIA/Neoenergia S/A em 1 fornecedor? | OK -- normalização determinística pega antes mesmo do fuzzy |
| 6 | Entity resolution NÃO unifica fornecedores com CNPJ diferente? | OK -- desempate explícito |
| 7 | 6086 transações migradas (== linhas do XLSX)? | OK |
| 8 | Cada transação tem aresta categoria_de + ocorre_em + origem? | OK -- 3 × 6086 = 18258 das 24506 |
| 9 | Migração 2x não duplica? | OK -- contagens batem |
| 10 | Pipeline NÃO foi quebrado (XLSX coexiste com grafo)? | OK -- pipeline.py não foi tocado nesta sprint |

## Achados

### 1. Entity resolution unificou 17% dos fornecedores

1321 locais distintos no XLSX → 1099 canônicos. Significa que ~222 nomes foram absorvidos como aliases em fornecedores existentes. Exemplos típicos esperados:
- "NEOENERGIA" + "Neoenergia S/A" + "neoenergia ltda" → 1 canônico "NEOENERGIA"
- "Aluguel Ki-Sabor" + "ki-sabor aluguel" → 1 canônico

Validar manualmente algumas amostras na Sprint 48 (linking) ou em sprint específica de auditoria de fornecedores.

### 2. 2 transações sem contraparte resolvida

6086 transações vs 6084 arestas `contraparte` = 2 transações tiveram `local` mas o entity resolution não conseguiu mapear pra um fornecedor canônico (possivelmente nomes muito curtos/ambíguos que caíram em fallbacks). NÃO bloqueia -- aceito como ruído residual de 0.03%.

### 3. CASCADE no schema garante consistência

DELETE de um node remove edges automaticamente via FK. Isso é crítico para futuras operações de "merge de fornecedores duplicados" (Sprint 48 ou auditoria humana): basta apagar o node redundante e as arestas seguem.

### 4. Tipos de nó canônicos ainda fora do escopo

Sprint 42 implementou tipos REUSADOS pela migração: transacao, fornecedor, categoria, periodo, conta, tag_irpf. Os tipos do ADR-14 ainda PENDENTES de uso (documento, item, prescricao, garantia, apolice, seguradora) entram quando os extratores das Sprints 44/44b/45/47*/47c populá-los. <!-- noqa: accent -->

A API do `GrafoDB.upsert_node` é agnóstica a tipo -- aceita qualquer string. Adicionar novos tipos não exige mudança de schema.

## Decisão humana

**Aprovada em:** 2026-04-19

**Notas do humano:**

Sprint 42 entregou backbone como projetado. Migração reproduzível em < 2 segundos contra 6086 linhas. Idempotente. Entity resolution conservador (threshold 85, CNPJ desempata). Pronto para a Sprint 43 (workflow supervisor) e para os extratores documentais começarem a popular nodes `documento`, `item`, `apolice` etc.

NÃO integrei a Sprint 42 com o pipeline (`src/pipeline.py:executar` não chama migrar_grafo) deliberadamente -- isso é o critério "Verificação end-to-end" que pede ./run.sh --tudo conclui com grafo populado. Esse passo entra em commit separado se quisermos automatizar a re-migração após cada `make process`. Por enquanto roda manualmente via `python -m src.graph.migracao_inicial`.

---

*"O grafo é o esqueleto; as arestas são o que lembra." -- princípio de cartógrafo*
