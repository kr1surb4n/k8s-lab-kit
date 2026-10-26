# Local Graph RAG application

This is the runnable Phase 17 application. It indexes the synthetic lab corpus
for evaluation and, separately, local notes and research papers for daily use.
The private index is never mixed with the evaluation database.

## Two databases

| Database | Port | Volume | Corpora | Purpose |
|---|---|---|---|---|
| `graphrag` | 5433 | `graphrag-pgdata` | `lab` | 20-document evaluation fixture |
| `graphrag_private` | 5434 | `graphrag-private-pgdata` | `notes`, `papers` | personal knowledge base |

Both databases use the same [`db/schema.sql`](../db/schema.sql). The
`documents.corpus` column separates sources inside a database, and chunks have
optional page numbers for PDF citations.

## Setup

```bash
cd ai/patterns/graph-rag
make venv                 # Python venv + dependencies
make db-up migrate        # evaluation database on 5433
make private-db-up private-migrate   # private database on 5434
```

Create the private configuration outside the repository:

```bash
mkdir -p ~/.config/graphrag
cp app/config.example.yaml ~/.config/graphrag/config.yaml
chmod 600 ~/.config/graphrag/config.yaml
$EDITOR ~/.config/graphrag/config.yaml
```

The config holds personal paths and database URLs. It is git-ignored and must
never be committed. `GRAPHRAG_CONFIG` can point at a different file.

## Indexing

```bash
# Evaluation corpus: deterministic offline run, no GPU needed.
.venv/bin/python -m app.cli ingest lab --db eval --stub

# Real evaluation run: bge-m3 embeddings + Granite relation extraction.
.venv/bin/python -m app.cli ingest lab --db eval

# Private notes: local LLM extraction from the first ~3000 characters.
.venv/bin/python -m app.cli ingest notes

# Papers: embeddings from the full PDF plus summary, graph from the summary tags.
.venv/bin/python -m app.cli ingest papers
```

Notes and papers are accepted only by the private database; the CLI refuses to
put them in the eval database. Re-running an ingest is incremental: unchanged
documents are skipped by content hash. Add `--force` to rebuild, `--prune` to
delete documents whose files disappeared, and `--limit N` for a trial run.

PDF text is cached under `~/.cache/graphrag/pdf-text/` and keyed by path, size,
and modification time, so re-runs do not re-extract 600 PDFs.

### Extraction modes

`--extract auto` (the default) picks the cheapest useful mode per corpus:

| Mode | Used for | What it does |
|---|---|---|
| `llm` | lab, notes | Granite returns entities, UPPER_SNAKE relations, and at most one hyperedge from the document opening |
| `tags` | papers | Paper title and summary tags become `HAS_TOPIC` edges; three or more tags form a `COVERS_TOPICS` hyperedge |
| `stub` | offline tests | Markdown emphasis/backticks become entities; no relations |
| `none` | debugging | text and embeddings only |

Paper summaries already carry high-quality tags from the paper-processing
project, so using them avoids roughly 600 LLM calls while still giving the
graph useful topic nodes shared across papers. Notes have no such metadata, so
they use the local LLM.

## Querying

```bash
.venv/bin/python -m app.cli search "graph neural network datasets" --k 5
.venv/bin/python -m app.cli ask "Which papers discuss layout analysis?"

# The evaluation corpus is in the eval database.
.venv/bin/python -m app.cli ask "How do Deployments relate to Pods?" --corpus lab
```

`ask` refuses with `The corpus does not contain enough information to answer
this question.` when retrieval is weak, and only cites chunk ids that were
actually retrieved. Each response carries a `trace_id`, model version, prompt
version, latency, cosine and RRF scores, and graph edges attached to the
retrieved documents.

## HTTP API

```bash
.venv/bin/python -m app.cli serve --host 127.0.0.1 --port 8099
```

| Endpoint | Purpose |
|---|---|
| `GET /healthz` | database and Ollama health |
| `GET /v1/corpora` | document, chunk, embedding, edge counts |
| `POST /v1/search` | `{query, corpus, k}` → chunks and graph path |
| `POST /v1/ask` | `{question, corpus, top_k}` → answer and citations |

`corpus` is `notes`, `papers`, `notes,papers`, or `lab`. The lab corpus is
routed to the eval database; everything else stays on the private database.
There is no authentication. Bind to `127.0.0.1` and do not expose the port.

## MCP for Hermes

Run the server directly to test it:

```bash
.venv/bin/python -m app.mcp_server
```

Register it in `~/.hermes/config.yaml`:

```yaml
mcp_servers:
  graphrag:
    command: /absolute/path/to/graph-rag/.venv/bin/python
    args: ["-m", "app.mcp_server"]
    env:
      PYTHONPATH: /absolute/path/to/graph-rag
      GRAPHRAG_CONFIG: /home/you/.config/graphrag/config.yaml
    timeout: 120
    connect_timeout: 60
```

Hermes then exposes three tools:

- `search_knowledge(query, corpus, k)`
- `ask_knowledge(question, corpus)`
- `list_corpora()`

Verify with `hermes mcp test graphrag`.

**Use a local Hermes model for these tools.** This server makes no cloud calls,
but the agent that consumes its results does. Hermes is currently configured
with `gpt-oss:120b-cloud` by default; switch it to `granite3.3-8b-local` or
`qwen3-8b-local` before asking private questions, or the retrieved note and
paper excerpts will be sent to the cloud provider. The MCP tools strip absolute
paths, but they necessarily return local text snippets to the agent.

## Privacy

- Everything is local: Ollama at `localhost:11434`, Postgres on localhost, no
  cloud API calls in the app.
- The private database, volume, config, PDF cache, and logs stay outside git.
- Query text is written to the local process log with its trace id. Do not ship
  those logs to a remote collector.
- The HTTP API and MCP server have no authentication; treat them as local-only.

## Known limits

- Lexical search uses Postgres `english` stemming. bge-m3 handles Polish
  queries semantically, but Polish keyword matching is weaker than English.
- Relation extraction reads the first ~3000 characters of a note. Very long
  notes get a representative opening, not a full-document graph.
- Papers without a summary JSON are indexed from their PDF text but get no tag
  graph. Summaries without a PDF are still indexed from title, summary, and
  tags.
- Image-only PDFs produce little or no text; OCR is not part of this phase.
- Graph context is one hop: edges attached to the top retrieved documents. It
  does not yet walk shared topic nodes into other documents.
- The API loads configuration at import time. Restart it after editing
  `config.yaml`.
