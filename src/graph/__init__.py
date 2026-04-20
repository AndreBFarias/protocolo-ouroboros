"""Grafo SQLite mínimo: backbone de cruzamentos do projeto (Sprint 42).

Schema 2-tabelas (node + edge) declarado em ADR-14. Tipos de nó canônicos:
transacao, documento, item, fornecedor, categoria, conta, periodo, tag_irpf,
prescricao, garantia, apolice, seguradora.

Sub-módulos:
- models: dataclasses Node e Edge
- db: GrafoDB com upsert idempotente
- entity_resolution: rapidfuzz para unificar fornecedores
- queries: biblioteca de consultas canônicas
- migracao_inicial: popula grafo a partir do XLSX existente
"""

# "O grafo é o esqueleto; as arestas são o que lembra." -- princípio de cartógrafo
