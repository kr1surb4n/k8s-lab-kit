# Graph RAG failure modes — observed issues and mitigations

The implementation uses plain PostgreSQL tables, recursive CTEs, and pgvector.
Apache AGE is not installed; the earlier AGE/Cypher rows in this file described
a design that was not built.

| # | Symptom | Root cause | Detection | Mitigation |
|---|---------|------------|-----------|------------|
| 1 | `extraction failed ... Expecting ',' delimiter` | Local model output hit `num_predict` mid-JSON | Ingest log line; document stored with text but no graph | Ollama JSON schema, bounded arrays, 900-token budget, one shorter retry |
| 2 | `duplicate key ... edge_nodes_edge_id_position_key` | Same edge id reinserted with reversed member order | Ingest aborts on `UniqueViolation` | Directed pair edge ids; delete and reinsert members atomically. Fix: `892fa99` |
| 3 | A crash lost hours of ingest | psycopg savepoints stayed inside one outer transaction | Row counts do not grow during a long run | Commit once per document and per prune. Fix: `7e403fb` |
| 4 | Top-level notes missing | `fnmatch("note.md", "**/*.md")` is false | Compare source file count with `stats` | Leading `**/` also matches the source root. Fix: `a6fb773` |
| 5 | A large saved web page is skipped | `max_file_bytes` guard | `skip (too large)` in the log | Raise `max_file_bytes` for the notes source (currently 30 MB) and rerun |
| 6 | A PDF has almost no text | Image-only or scanned PDF; OCR is not installed | Very small chunk count for a large PDF | Keep the summary JSON text; add OCR in a later phase |
| 7 | Low graph-path accuracy | Local model relation names and entity phrasing differ from the golden labels; context is one hop | `graph_path_accuracy` in `make eval-local` | Treat it as a model-quality metric, not a lookup; improve prompts or curate labels |
| 8 | Polish keyword search is weak | `to_tsvector('english', ...)` has no Polish stemmer | Polish query with low lexical score | bge-m3 vector search carries the query; lexical results supplement it |
| 9 | Private excerpts reach a cloud model | Hermes sends MCP tool results to its configured model (`gpt-oss:120b-cloud` by default) | Model/provider in the Hermes transcript | Use `granite3.3-8b-local` or `qwen3-8b-local`; MCP strips absolute paths and truncates snippets |
| 10 | Notes could enter the evaluation database | A wrong `--db` or DSN | `stats` shows a private corpus in the eval DB | Separate database, volume, and port; CLI rejects private corpora in eval |
| 11 | Stale documents after edits | Content hash changed or a file disappeared | `skipped` count in ingest output | `--prune` deletes missing files; `--force` rebuilds changed ones |
| 12 | GPU out of memory | Too many models or a large context | `ollama ps`; Ollama error | One 8B model at a time, `num_ctx=4096`, 900 output tokens |
| 13 | `PostgreSQL text fields cannot contain NUL` | A PDF or HTML file contains `0x00` bytes | Ingest aborts on `DataError` | `normalize_text` strips NUL; per-document commit resumes at the failed file |
| 14 | A notes query returns no chunks while similar notes exist | HNSW filters `documents.corpus` after the index scan; top global neighbours can all be papers | Polish notes query returns `[]`; same query on an unfiltered scan returns rows | Force an exact vector scan at this index size. Revisit partial indexes or iterative HNSW above ~1M chunks |
| 15 | A relation question is answered with no graph context after the graph layer was emptied | The answer path never required a graph context, so it answered from chunk context alone | `graph_error: "graph_path_empty"` in the answer; run with `require_graph` to fail loudly | Enable the guard (`require_graph: true` or `ask --require-graph`); keep it on for relation questions |

## Destructive drills

Phase 17 acceptance drills run against the evaluation database and are always
restored afterwards (see [`examples/failure-drills.md`](../examples/failure-drills.md)):

- **Deleted cited document**: delete a document that a golden answer cites and
  check that the answer changes and the citation disappears. Metric moved:
  citation precision.
- **Empty graph layer**: empty `edge_nodes` and ask a relation question with
  `require_graph`. Expected: a loud refusal with `graph_error: "graph_path_empty"`.
  Metric moved: graph-path accuracy and refusal correctness.

## Local checks

```bash
make app-test                 # offline tests for the app, no GPU or database
make eval-local               # 42-question golden set against the eval DB
.venv/bin/python -m app.cli stats
curl -s localhost:8099/healthz | jq
```

The Kubernetes Prometheus alerts that used to be in this file were never
deployed for the local tool. Do not copy them into a cluster without metrics
exporters first.
