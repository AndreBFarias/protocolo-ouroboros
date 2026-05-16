---
id: INFRA-DEDUP-DAS-PARCSN-DUPLICADO
titulo: "DAS PARCSN duplicado no grafo (doc 7664 e 7671 mesma realidade)"
status: backlog
concluida_em: null
prioridade: P2
data_criacao: 2026-05-16
fase: QUALIDADE
epico: 3
depende_de: []
esforco_estimado_horas: 1
origem: "achado colateral do executor `a51d3c56` (LINK-AUDIT-01) 2026-05-15. Doc 7664 e doc 7671 têm vencimento idêntico (2025-03-31) e total idêntico (R$ 321,35) com CNPJ Receita Federal. São DAS duplicados (mesma realidade) que linkam à mesma transação 5686. Provável ingestão dupla via 2 paths diferentes."
---

# Sprint INFRA-DEDUP-DAS-PARCSN-DUPLICADO

## Contexto

DAS PARCSN é declaração de imposto. Cada competência mensal gera 1
documento único. Doc 7664 e 7671 são clones — mesma data, mesmo valor,
mesmo emissor. Linkando ambos à transação 5686 cria ambiguidade no grafo.

Causa raiz provável: extrator `das_parcsn_pdf` foi rodado 2× sobre o
mesmo arquivo (uma vez via inbox, outra via re-extração) e o
`upsert_node` não dedupou porque algo na chave canônica (sha256 ou
nome) diverge.

## Hipótese e validação ANTES

```bash
sqlite3 data/output/grafo.sqlite "
SELECT id, nome_canonico, json_extract(metadata, '\$.arquivo_origem'), json_extract(metadata, '\$.sha256')
FROM node
WHERE id IN (7664, 7671)
"
# Esperado: 2 linhas; comparar arquivo_origem e sha256 para entender divergência

sqlite3 data/output/grafo.sqlite "
SELECT src_id, dst_id, tipo FROM edge WHERE dst_id=5686 AND tipo='documento_de'
"
# Esperado: 2 arestas para a mesma transação
```

## Objetivo

1. Diagnosticar: quais campos divergem entre 7664 e 7671 (paths, sha256, data_emissao).
2. Decidir: manter 7664 (primeiro) ou 7671. Critério: mais metadata completo.
3. Script `scripts/merge_documentos_duplicados.py` que:
   - Lê 2 nodes documento com mesmo (tipo_documento, data_emissao, total, cnpj_emitente).
   - Decide vencedor (mais metadata, ou primeiro criado).
   - Transfere arestas do perdedor para o vencedor.
   - Deleta perdedor.
4. Aplicar para 7664 vs 7671.
5. Salvar log em `data/output/dedup_documentos_log.json`.

## Não-objetivos

- Não modificar `upsert_node` ou `ingestor_documento.py` (sprint dedicada para prevenção futura).
- Não rodar dedup em outros tipos sem auditoria.

## Proof-of-work runtime-real

```bash
.venv/bin/python scripts/merge_documentos_duplicados.py --dry-run
# Esperado: lista 7664 e 7671 como candidatos

.venv/bin/python scripts/merge_documentos_duplicados.py --apply
sqlite3 data/output/grafo.sqlite "SELECT COUNT(*) FROM node WHERE tipo='documento'"
# Esperado: 51 (era 52)
```

## Acceptance

- 1 documento DAS duplicado fundido (7664 ou 7671 deletado).
- Aresta `documento_de` única para tx 5686.
- Pytest > 3080. Smoke 10/10. Lint exit 0.

## Padrões aplicáveis

- (m) Branch reversível — script registra log para rollback.

---

*"Mesma realidade, mesmo nó. Dois nós são um nó perdido." — princípio do entity resolution*
