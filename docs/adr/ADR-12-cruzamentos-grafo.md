# ADR-12: Cruzamentos via Grafo de Conhecimento

## Status: Aceita

## Contexto

O usuário pediu explicitamente: *"fazer os cruzamentos todos que preciso"*. Na prática isso significa responder perguntas como:
- "NEOENERGIA", "Neoenergia SA" e "NEOEN S/A" são a mesma entidade? Quanto paguei a ela em 2026?
- Este boleto PDF bate com qual transação no extrato Itaú?
- Qual a timeline completa de interações com a farmácia X (transações + faturas + devoluções)?
- Que entidades recebem pagamentos recorrentes acima de R$ 500?

O XLSX plano (8 abas tabulares) não resolve isso. As alternativas foram:
- **Pandas joins ad-hoc**: funciona para queries pontuais mas não escala; cada pergunta vira código novo.
- **Banco relacional clássico (SQLite puro com tabelas normalizadas)**: resolve junções mas força modelagem rígida — entidades, documentos e eventos têm formas diferentes.
- **Grafo de conhecimento (Node + Edge)**: modelo flexível para entidades heterogêneas e relações arbitrárias; entity resolution é operação de primeira classe; consultas NL mapeiam naturalmente para traversals.

## Decisão

Implementar grafo de conhecimento como backbone dos cruzamentos:

1. **Armazenamento:** SQLite em `data/output/grafo.sqlite` (honra ADR-07 Local First). Nada de Neo4j/servidor externo.
2. **Schema mínimo:**
   - `Node(id, tipo, nome_canonico, aliases JSON, metadata JSON)` — tipos iniciais: `entidade`, `transacao`, `documento`, `evento`.
   - `Edge(src_id, dst_id, tipo, peso, evidencia JSON)` — tipos iniciais: `paga`, `referencia`, `alias_de`, `ocorre_em`.
3. **Entity resolution:** `rapidfuzz` determinístico como primeira linha. Casos de borda (similaridade < 0.85 ou ambíguos) viram proposições do supervisor via ADR-08 — humano aprova o merge.
4. **Migração inicial:** script popula o grafo a partir das 2.859 transações existentes. Unificação de entidades por nome canônico + aliases. Idempotente.
5. **Fase 3 entrega apenas nodes/edges e unificação.** Motor de linking doc-transação e detecção de eventos ficam na Sprint 27b. Visualização interativa (`pyvis`) fica pós-90d.
6. **Consumidores primários:** busca global, timeline de entidade e consulta NL ("pergunte ao Ouroboros") leem o grafo em vez do XLSX.

## Consequências

**Positivas:**
- Cruzamentos arbitrários viram queries SQL/traversal em vez de código novo
- Entity resolution centraliza um problema que hoje está implícito em regex
- Consultas NL (Sprint 28 Modo 3) têm um schema fechado para gerar SQL seguro
- Mantém Local First: SQLite é arquivo no disco
- Base para análises futuras (redes de dependência, detecção de anomalias relacionais)

**Negativas:**
- Nova fonte de verdade parcial: XLSX continua sendo saída oficial; grafo é projeção analítica
- Sincronização XLSX ↔ grafo exige cuidado (grafo é regenerado após `make process`, não editado à mão)
- Schema pode precisar evoluir (JSON metadata ajuda, mas migrações virão)
- SQLite não escala para milhões de transações — aceitável dado o volume doméstico

---

*"Os nós da rede são mais importantes que os nós individuais." -- Albert-László Barabási*
