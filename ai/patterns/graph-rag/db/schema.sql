-- Graph RAG schema — Postgres 16 + pgvector.
--
-- This file is idempotent: `make migrate` can run it any number of times.
-- It is the primary graph layer: plain tables plus recursive CTEs. Apache AGE
-- is not used (see db/README.md for the decision and the evidence).
--
-- One row per corpus document, one row per chunk, one embedding per chunk.
-- A relation is an edge row plus its members in edge_nodes. A pairwise edge has
-- two members; a hyperedge has three or more. Arity is stored, not inferred, so
-- a broken hyperedge is visible instead of silently becoming a pair.

CREATE EXTENSION IF NOT EXISTS vector;

-- Track which schema files have run.
CREATE TABLE IF NOT EXISTS schema_migrations (
    version    text PRIMARY KEY,
    applied_at timestamptz NOT NULL DEFAULT now()
);

-- The corpus documents and their provenance snapshot.
CREATE TABLE IF NOT EXISTS documents (
    id             text PRIMARY KEY,
    corpus         text NOT NULL DEFAULT 'lab',
    corpus_version text NOT NULL,
    title          text NOT NULL,
    section        text NOT NULL,
    path           text NOT NULL,
    sha256         text NOT NULL,
    source         jsonb NOT NULL DEFAULT '{}'::jsonb,
    inserted_at    timestamptz NOT NULL DEFAULT now(),
    updated_at     timestamptz NOT NULL DEFAULT now()
);

-- Existing databases created before the corpus column need the additive change.
ALTER TABLE documents ADD COLUMN IF NOT EXISTS corpus text NOT NULL DEFAULT 'lab';
CREATE INDEX IF NOT EXISTS documents_corpus_idx ON documents (corpus);
CREATE UNIQUE INDEX IF NOT EXISTS documents_corpus_path_uidx ON documents (corpus, path);

-- Chunks keep their offsets so a citation can point at a real span.
CREATE TABLE IF NOT EXISTS chunks (
    id              text PRIMARY KEY,
    document_id     text NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    ordinal         integer NOT NULL CHECK (ordinal >= 0),
    text            text NOT NULL,
    start_offset    integer NOT NULL CHECK (start_offset >= 0),
    end_offset      integer NOT NULL CHECK (end_offset > start_offset),
    content_sha256  text NOT NULL,
    page_start      integer,
    page_end        integer,
    tsv             tsvector GENERATED ALWAYS AS (to_tsvector('english', text)) STORED,
    UNIQUE (document_id, ordinal)
);

-- Existing databases need the page columns; notes and Markdown leave them null.
ALTER TABLE chunks ADD COLUMN IF NOT EXISTS page_start integer;
ALTER TABLE chunks ADD COLUMN IF NOT EXISTS page_end integer;

-- One embedding row per chunk. The dimension is fixed by the chosen model.
CREATE TABLE IF NOT EXISTS embeddings (
    chunk_id   text PRIMARY KEY REFERENCES chunks(id) ON DELETE CASCADE,
    model      text NOT NULL,
    dim        integer NOT NULL CHECK (dim = 1024),
    vector     vector(1024) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- Entities mentioned by the corpus.
CREATE TABLE IF NOT EXISTS nodes (
    id          text PRIMARY KEY,
    name        text NOT NULL,
    type        text NOT NULL DEFAULT 'Entity',
    description text,
    UNIQUE (name, type)
);

-- Relations, pairwise or hyperedges, with the document they came from.
CREATE TABLE IF NOT EXISTS edges (
    id          text PRIMARY KEY,
    kind        text NOT NULL,
    arity       integer NOT NULL CHECK (arity >= 2),
    confidence  real NOT NULL DEFAULT 1.0 CHECK (confidence >= 0 AND confidence <= 1),
    document_id text REFERENCES documents(id) ON DELETE CASCADE,
    chunk_id    text REFERENCES chunks(id) ON DELETE SET NULL,
    created_at  timestamptz NOT NULL DEFAULT now()
);

-- Edge membership. `role` keeps "source"/"target"/"member" explicit, and
-- `position` keeps the order for hyperedges whose meaning depends on it.
CREATE TABLE IF NOT EXISTS edge_nodes (
    edge_id  text NOT NULL REFERENCES edges(id) ON DELETE CASCADE,
    node_id  text NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    role     text NOT NULL DEFAULT 'member',
    position integer NOT NULL DEFAULT 0,
    PRIMARY KEY (edge_id, node_id, role),
    UNIQUE (edge_id, position)
);

-- Why every row exists: table, row id, document, chunk, source hash, version.
CREATE TABLE IF NOT EXISTS provenance (
    id             bigserial PRIMARY KEY,
    entity_table   text NOT NULL,
    entity_id      text NOT NULL,
    document_id    text NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_id       text REFERENCES chunks(id) ON DELETE CASCADE,
    source_path    text NOT NULL,
    section        text NOT NULL,
    doc_sha256     text NOT NULL,
    corpus_version text NOT NULL,
    created_at     timestamptz NOT NULL DEFAULT now(),
    UNIQUE (entity_table, entity_id, document_id)
);
CREATE INDEX IF NOT EXISTS provenance_entity_idx ON provenance (entity_table, entity_id);

-- Vector index: cosine distance, the metric bge-m3 vectors are normalized for.
CREATE INDEX IF NOT EXISTS embeddings_vector_hnsw
    ON embeddings USING hnsw (vector vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Lexical index. This is tsvector ranking, not real BM25; db/README.md says so.
CREATE INDEX IF NOT EXISTS chunks_tsv_idx ON chunks USING gin (tsv);

-- Both sides of the membership join must be fast for graph expansion.
CREATE INDEX IF NOT EXISTS edge_nodes_node_idx ON edge_nodes (node_id);
CREATE INDEX IF NOT EXISTS edge_nodes_edge_idx ON edge_nodes (edge_id);
CREATE INDEX IF NOT EXISTS edges_kind_idx ON edges (kind);
CREATE INDEX IF NOT EXISTS edges_document_idx ON edges (document_id);
CREATE INDEX IF NOT EXISTS chunks_document_idx ON chunks (document_id);
CREATE INDEX IF NOT EXISTS documents_sha256_idx ON documents (sha256);

-- One row per edge with its ordered members, which keeps hyperedge queries short.
CREATE OR REPLACE VIEW edge_summary AS
SELECT e.id,
       e.kind,
       e.arity,
       e.document_id,
       array_agg(n.name ORDER BY en.position) AS members
FROM edges e
JOIN edge_nodes en ON en.edge_id = e.id
JOIN nodes n ON n.id = en.node_id
GROUP BY e.id, e.kind, e.arity, e.document_id;

COMMENT ON TABLE embeddings IS 'One 1024-dim bge-m3 vector per chunk';
COMMENT ON TABLE edges IS 'A relation; arity >= 3 means a hyperedge';
COMMENT ON VIEW edge_summary IS 'Edges with their ordered member names';

INSERT INTO schema_migrations (version) VALUES ('0001_graph_rag')
ON CONFLICT (version) DO NOTHING;
