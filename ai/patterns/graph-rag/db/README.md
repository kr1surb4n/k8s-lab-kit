# Storage — Postgres 16 + pgvector

The graph layer is plain Postgres tables plus recursive CTEs. There is no
separate graph database and no Apache AGE extension in Phase 17.

| Item | Value |
|---|---|
| Image | `pgvector/pgvector:pg16` |
| Postgres | 16.15 (Debian) |
| pgvector | 0.8.7 |
| Vector metric | cosine (`vector_cosine_ops`), 1024 dimensions |
| Local port | `5433` (override with `GRAPHRAG_DB_PORT`) |
| Volume | `graph_rag_graphrag-pgdata` (named volume, survives `make db-down`) |

## Why no Apache AGE

The Phase 17 plan (`analysis/07-what-to-do.md` §3) already chose plain tables
and recursive CTEs as the primary graph layer, with AGE as an optional adapter.
Two facts make that the right default here:

- The official `pgvector/pgvector` image ships Postgres and pgvector, not AGE.
  The official AGE images ship AGE, not pgvector. No official image is known to
  ship both; combining them means maintaining a custom build of two extensions
  against one Postgres version.
- Every query in 17.4 is a breadth-first walk from a seed node: "relations for
  these nodes", "members of this hyperedge", "path from A to B up to two hops".
  Those are `JOIN`s and `WITH RECURSIVE`, not Cypher.

R18 in `analysis/03-research.md` still asks whether AGE's Cypher subset is worth
it. This schema is the artefact for that test: load the same data into both and
compare. Until then, no AGE dependency, no custom image, one backup.

## Tables

| Table | Purpose |
|---|---|
| `documents` | one row per corpus document, including `sha256` and `source` JSON |
| `chunks` | text spans with `start_offset` / `end_offset` and a generated `tsv` |
| `embeddings` | one 1024-dim vector per chunk, with the model name |
| `nodes` | entities, unique by `(name, type)` |
| `edges` | a relation, `arity >= 2`; `arity >= 3` is a hyperedge |
| `edge_nodes` | members of an edge with `role` and ordered `position` |
| `provenance` | table + row id + document + chunk + source hash + corpus version |
| `schema_migrations` | which schema versions have been applied |

`edge_summary` is a view that returns each edge with its ordered member names.
It exists to keep graph queries and the eval readable.

The hyperedge model is the one proposed in R19: one `edges` row plus N
`edge_nodes` rows. `smoke.sql` inserts "smoke-nginx, smoke-php and smoke-host
jointly serve" as **one** edge with three members and asserts that the view
returns exactly those three in order. It runs in a transaction and rolls back.

## Lexical search is not BM25

The `chunks.tsv` column and its GIN index give Postgres full-text search with
`ts_rank_cd`. That is **not** BM25: Postgres does not apply BM25's document-length
normalisation or IDF weighting by default. The plan says "BM25", so this is a
deliberate, visible deviation:

- The schema names the component "lexical", not "BM25".
- If the Phase 17 evaluation shows lexical recall is the weak part, the options
  are a BM25 extension (`pg_search`), a small BM25 index in the service, or RRF
  with more vectors. The schema does not need to change for any of them.

## Commands

```bash
make db-up       # start the container and wait for pg_isready
make migrate     # apply db/schema.sql (safe to repeat)
make db-check    # apply twice, diff the dumps, run the hyperedge check
make db-shell    # psql as graphrag
make db-down     # stop the container; the volume stays
```

`docker compose down -v` deletes the data. That is the only command that does,
besides dropping the volume by hand.

## Idempotency evidence

Run on 2026-10-26 against the local container:

```console
$ make db-check
schema ok: 8 tables, migrate is idempotent, hyperedge round-trip ok
```

The check compares `pg_dump --schema-only` after the first and the second
`make migrate`. The only nondeterministic line in a `pg_dump` 16.15 dump is the
random `\restrict` token, which the check filters out before diffing.

## Credentials

`compose.yaml` defaults to `graphrag/graphrag-dev-only` because this is a local
development database. Override `GRAPHRAG_DB_PASSWORD` and
`GRAPHRAG_DB_PORT` in the environment; never copy the default into a cluster
manifest. The k8s Secret in `k8s/secret.yaml` still holds placeholders and is
not used by this phase yet.
