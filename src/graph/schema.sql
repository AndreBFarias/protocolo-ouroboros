-- =============================================================================
-- schema.sql -- DDL do grafo SQLite (Sprint 42, ADR-12 + ADR-14)
-- =============================================================================
-- Esquema 2-tabelas: node (entidades) + edge (relações).
-- Idempotente: pode rodar múltiplas vezes sem efeito colateral.
-- Foreign keys e índices habilitados; consulta-se o tipo via WHERE simples.
-- =============================================================================

CREATE TABLE IF NOT EXISTS node (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tipo TEXT NOT NULL,
  nome_canonico TEXT NOT NULL,
  aliases TEXT NOT NULL DEFAULT '[]',
  metadata TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (tipo, nome_canonico)
);

CREATE INDEX IF NOT EXISTS idx_node_tipo ON node(tipo);

CREATE TABLE IF NOT EXISTS edge (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  src_id INTEGER NOT NULL REFERENCES node(id) ON DELETE CASCADE,
  dst_id INTEGER NOT NULL REFERENCES node(id) ON DELETE CASCADE,
  tipo TEXT NOT NULL,
  peso REAL NOT NULL DEFAULT 1.0,
  evidencia TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (src_id, dst_id, tipo)
);

CREATE INDEX IF NOT EXISTS idx_edge_src ON edge(src_id);
CREATE INDEX IF NOT EXISTS idx_edge_dst ON edge(dst_id);
CREATE INDEX IF NOT EXISTS idx_edge_tipo ON edge(tipo);
