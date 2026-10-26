# Graph RAG — Database Access & Usage Tutorial

This guide covers: (1) what's in the PostgreSQL databases, (2) how to connect from various tools, and (3) how to use the Graph RAG system for indexing and querying.

---

## 1. Database Overview

### Two Databases, Two Purposes

| Database | Port | Volume | Corpora | Purpose |
|----------|------|--------|---------|---------|
| `graphrag` (eval) | 5433 | `graphrag-pgdata` | `lab` | 20-doc evaluation fixture with 42 golden questions |
| `graphrag_private` | 5434 | `graphrag-private-pgdata` | `notes`, `papers` | Your personal knowledge base |

### Current Contents (as of 2026-10-26)

**Eval Database (`graphrag`)**
```
Documents: 20 (lab corpus)
Chunks: 20
Embeddings: 20 (1024-dim bge-m3)
Nodes: 358
Edges: 218
Edge nodes: 480
```

**Private Database (`graphrag_private`)**
```
Documents: 1,040 (notes: 179, papers: 861)
Chunks: 26,353
Embeddings: 26,353
Nodes: 6,305
Edges: 8,225
Edge nodes: 21,114
```

---

## 2. Starting the Databases

```bash
cd /home/kris/00___Castle/07__WorkShops/k8s/ai/patterns/graph-rag

# Start eval database (port 5433)
make db-up

# Start private database (port 5434) — separate profile
make private-db-up

# Apply schema (idempotent, safe to re-run)
make migrate
make private-migrate
```

### Verify They're Running
```bash
docker compose ps
# Should show: graph-rag-postgres (healthy), graph-rag-postgres-private (healthy)
```

---

## 3. Connecting to the Databases

### 3.1 Command Line (psql)

```bash
# Eval database
psql "postgresql://graphrag:graphrag-dev-only@localhost:5433/graphrag"

# Private database
psql "postgresql://graphrag:graphrag-private-dev-only@localhost:5434/graphrag_private"

# Or via make targets (shorter)
make db-shell          # eval
make private-db-shell  # private
```

### 3.2 GUI Tools (DBeaver, DataGrip, pgAdmin, pgweb)

| Field | Eval Database | Private Database |
|-------|---------------|------------------|
| **Host** | localhost | localhost |
| **Port** | 5433 | 5434 |
| **Database** | graphrag | graphrag_private |
| **Username** | graphrag | graphrag |
| **Password** | graphrag-dev-only | graphrag-private-dev-only |
| **SSL Mode** | disable / prefer | disable / prefer |

**DBeaver example:**
1. New Connection → PostgreSQL
2. Fill in the fields above
3. Test Connection → Finish
4. Expand `graphrag` → `public` → `Tables` to see: `chunks`, `documents`, `edges`, `nodes`, `edge_nodes`, `embeddings`, `provenance`, `schema_migrations`

### 3.3 Python (psycopg)

```python
import psycopg

# Eval database
conn = psycopg.connect(
    "postgresql://graphrag:graphrag-dev-only@localhost:5433/graphrag"
)

# Private database
conn = psycopg.connect(
    "postgresql://graphrag:graphrag-private-dev-only@localhost:5434/graphrag_private"
)

# Example query
with conn.cursor() as cur:
    cur.execute("SELECT corpus, count(*) FROM documents GROUP BY corpus;")
    print(cur.fetchall())
```

### 3.4 Quick Exploration Queries

```sql
-- Show all corpora and document counts
SELECT corpus, count(*) as docs FROM documents GROUP BY corpus;

-- Row counts per table
SELECT 'chunks' as t, count(*) FROM chunks
UNION ALL SELECT 'embeddings', count(*) FROM embeddings
UNION ALL SELECT 'nodes', count(*) FROM nodes
UNION ALL SELECT 'edges', count(*) FROM edges
UNION ALL SELECT 'edge_nodes', count(*) FROM edge_nodes;

-- View a sample document
SELECT id, title, corpus, left(text, 200) FROM documents LIMIT 5;

-- View chunks with text
SELECT chunk_id, doc_id, left(text, 300) FROM chunks LIMIT 10;

-- View graph edges (via edge_summary view)
SELECT * FROM edge_summary LIMIT 20;

-- View hyperedges (arity >= 3)
SELECT e.id, e.kind, e.arity,
       string_agg(n.name || '(' || en.role || ')', ', ' ORDER BY en.position) as members
FROM edges e
JOIN edge_nodes en ON en.edge_id = e.id
JOIN nodes n ON n.id = en.node_id
WHERE e.arity >= 3
GROUP BY e.id, e.kind, e.arity
ORDER BY e.id
LIMIT 10;
```

---

## 4. Using the Graph RAG System

### 4.1 Prerequisites

```bash
cd /home/kris/00___Castle/07__WorkShOps/k8s/ai/patterns/graph-rag

# Create venv and install dependencies (one-time)
make venv

# Ensure Ollama is running with required models
ollama serve &
ollama pull bge-m3-local        # embeddings
ollama pull granite3.3-8b-local # generation
ollama pull qwen3-8b-local      # fallback generation
```

### 4.2 Configuration (Private, Not Committed)

```bash
mkdir -p ~/.config/graphrag
cp app/config.example.yaml ~/.config/graphrag/config.yaml
chmod 600 ~/.config/graphrag/config.yaml

# Edit with your paths
$EDITOR ~/.config/graphrag/config.yaml
```

**Key config sections:**
```yaml
# Private config example
databases:
  eval: postgresql://graphrag:graphrag-dev-only@localhost:5433/graphrag
  private: postgresql://graphrag:graphrag-private-dev-only@localhost:5434/graphrag_private

sources:
  notes:
    kind: files
    path: ~/Documents
    include: ["**/*.md", "**/*.txt", "**/*.pdf", "**/*.docx"]
    max_file_bytes: 30000000

  papers:
    kind: papers
    path: ~/papers
    pdf_dir: processed-pdfs
    summaries_dir: analysis_results_per_file
```

---

## 5. Indexing (Ingestion)

### 5.1 Evaluation Corpus (Lab) — Deterministic, No GPU Needed

```bash
# Offline stub run (fast, no GPU, for CI/tests)
.venv/bin/python -m app.cli ingest lab --db eval --stub

# Real run with local models (needs GPU, takes ~30s)
.venv/bin/python -m app.cli ingest lab --db eval
```

### 5.2 Private Notes — Local LLM Extraction

```bash
# Incremental: only new/changed files processed
.venv/bin/python -m app.cli ingest notes

# Force rebuild all
.venv/bin/python -m app.cli ingest notes --force

# Prune deleted files
.venv/bin/python -m app.cli ingest notes --prune

# Limit to first N files (for testing)
.venv/bin/python -m app.cli ingest notes --limit 10
```

### 5.3 Research Papers — Embeddings + Tag-Based Graph

```bash
# Full paper library (634 PDFs + 227 summaries)
.venv/bin/python -m app.cli ingest papers

# With OCR for scanned PDFs (needs tesseract CLI)
.venv/bin/python -m app.cli ingest papers --ocr --force

# Trial run on 1 paper
.venv/bin/python -m app.cli ingest papers --limit 1 --ocr --force
```

### 5.4 Ingestion Options

| Flag | Purpose |
|------|---------|
| `--db eval\|private` | Target database (auto-selected by corpus) |
| `--stub` | Use deterministic stub embedder (no GPU) |
| `--force` | Re-index even unchanged files |
| `--prune` | Delete documents whose source files disappeared |
| `--limit N` | Process only first N documents |
| `--ocr` | Enable OCR for low-text PDF pages |
| `--extract auto\|llm\|tags\|stub\|none` | Extraction mode |

---

## 6. Querying the System

### 6.1 CLI — Search (Retrieval Only)

```bash
# Search eval corpus
.venv/bin/python -m app.cli search "How is a Service connected to Pods?" \
  --corpus lab --db eval --k 5

# Search private notes + papers
.venv/bin/python -m app.cli search "Kubernetes scheduling" \
  --corpus notes,papers --k 10

# Two-hop graph expansion (follow shared entities)
.venv/bin/python -m app.cli search "How is a Service connected to Pods?" \
  --corpus lab --db eval --graph-hops 2

# Rerank with local LLM (adds ~7s latency)
.venv/bin/python -m app.cli search "How is a Service connected to Pods?" \
  --corpus lab --db eval --rerank

# JSON output for scripting
.venv/bin/python -m app.cli search "..." --json
```

### 6.2 CLI — Ask (Full Answer with Citations)

```bash
# Ask a question against eval corpus
.venv/bin/python -m app.cli ask "Which object owns the Pods in the Deployment chain?" \
  --corpus lab --db eval

# Ask against private notes
.venv/bin/python -m app.cli ask "What do my notes say about Kubernetes networking?" \
  --corpus notes

# Require graph context (fails loudly if no graph edges)
.venv/bin/python -m app.cli ask "What connects A to B?" \
  --corpus lab --db eval --require-graph

# JSON output
.venv/bin/python -m app.cli ask "..." --json
```

### 6.3 Response Format (Ask)

```json
{
  "answer": "A Deployment owns a ReplicaSet which creates Pods... [doc-01#c0000]",
  "citations": [
    {
      "doc_id": "doc-01",
      "chunk_id": "doc-01#c0000",
      "title": "Kubernetes Objects",
      "path": "doc-01-objects.md",
      "page_start": null,
      "page_end": null,
      "span": [0, 500]
    }
  ],
  "graph_path": [
    {"source": "Deployment", "relation": "OWNS", "target": "ReplicaSet", "document_id": "doc-01", "hop": 1},
    {"source": "ReplicaSet", "relation": "CREATES", "target": "Pod", "document_id": "doc-01", "hop": 1}
  ],
  "scores": {"top_vector": 0.89, "top_rrf": 0.016},
  "trace_id": "a1b2c3d4...",
  "model_version": "granite3.3-8b-local",
  "latency_ms": 2340,
  "refused": false,
  "graph_hops": 1,
  "rerank": false
}
```

---

## 7. HTTP API (for Hermes / External Clients)

### 7.1 Start the Server

```bash
.venv/bin/python -m app.cli serve --host 127.0.0.1 --port 8099
```

### 7.2 Endpoints

```bash
# Health check
curl -s http://127.0.0.1:8099/healthz | jq

# List corpora with stats
curl -s http://127.0.0.1:8099/v1/corpora | jq

# Search
curl -s http://127.0.0.1:8099/v1/search \
  -H 'content-type: application/json' \
  -d '{"query":"How is a Service connected to Pods?","corpus":"lab","k":5,"graph_hops":2}' | jq

# Ask (full answer with citations)
curl -s http://127.0.0.1:8099/v1/ask \
  -H 'content-type: application/json' \
  -d '{"question":"Which object owns the Pods?","corpus":"lab","top_k":8}' | jq
```

### 7.3 Request/Response Models

**Search Request:**
```json
{
  "query": "string (1-2000 chars)",
  "corpus": "notes,papers|lab (default: notes,papers)",
  "k": 8,
  "graph_hops": 1,
  "rerank": false,
  "stub": false
}
```

**Ask Request:**
```json
{
  "question": "string (1-4000 chars)",
  "corpus": "notes,papers|lab",
  "top_k": 12,
  "graph_hops": 1,
  "rerank": false,
  "stub": false
}
```

---

## 8. MCP Server (for Hermes)

### 8.1 Run the Server

```bash
.venv/bin/python -m app.mcp_server
```

### 8.2 Register in Hermes (`~/.hermes/config.yaml`)

```yaml
mcp_servers:
  graphrag:
    command: /home/kris/00___Castle/07__WorkShops/k8s/ai/patterns/graph-rag/.venv/bin/python
    args: ["-m", "app.mcp_server"]
    env:
      PYTHONPATH: /home/kris/00___Castle/07__WorkShops/k8s/ai/patterns/graph-rag
      GRAPHRAG_CONFIG: /home/kris/.config/graphrag/config.yaml
    timeout: 120
    connect_timeout: 60
```

### 8.3 Hermes Tools Available

| Tool | Parameters | Description |
|------|------------|-------------|
| `search_knowledge` | `query, corpus?, k?` | Retrieve chunks + graph path |
| `ask_knowledge` | `question, corpus?, top_k?` | Full answer with citations |
| `list_corpora` | — | Document/chunk/edge counts |

> ⚠️ **Use a local Hermes model** (`granite3.3-8b-local` or `qwen3-8b-local`). Hermes defaults to `gpt-oss:120b-cloud` which would send your private snippets to the cloud.

---

## 9. Evaluation

### 9.1 Run Golden Set Evaluation

```bash
# Full evaluation against lab corpus (needs running DB + Ollama)
make eval-local

# With two-hop graph expansion
.venv/bin/python eval/local_eval.py --graph-hops 2

# With reranking
.venv/bin/python eval/local_eval.py --rerank

# Save detailed results
.venv/bin/python eval/local_eval.py --json-out eval/local-results.json
```

### 9.2 Current Baseline (2026-10-26)

| Metric | Value |
|--------|-------|
| Recall@k | 1.00 |
| Citation precision | 0.75 |
| Graph-path accuracy | 0.7875 |
| Strict answer-fact match | 0.825 |
| Refusal correctness | 1.00 |
| Latency p50 / p95 | 2,364 ms / 3,266 ms |

### 9.3 Offline Tests (No DB/GPU)

```bash
# 55 unit tests
cd ai/patterns/graph-rag && .venv/bin/python -m unittest discover -s app/tests -v

# Or from repo root
make app-test
```

---

## 10. Persistence & Backup

### 10.1 Data Persistence

- **Named Docker volumes**: `graphrag-pgdata`, `graphrag-private-pgdata`
- Survive: `docker compose down`, `make db-down`, container restarts
- Only deleted by: `docker compose down -v` or `docker volume rm`

### 10.2 Backup

```bash
# Eval database backup
docker compose exec -T postgres pg_dump -U graphrag graphrag \
  | grep -v -E '^\(un\)?restrict ' > backup-eval-$(date +%F).sql

# Private database backup
docker compose --profile private exec -T postgres-private pg_dump -U graphrag graphrag_private \
  | grep -v -E '^\(un\)?restrict ' > backup-private-$(date +%F).sql
```

### 10.3 Restore

```bash
# Drop and recreate schema
docker compose exec -T postgres psql -U graphrag -d graphrag \
  -c 'DROP SCHEMA public CASCADE; CREATE SCHEMA public;'

# Restore
docker compose exec -T postgres psql -U graphrag graphrag < backup-eval-2026-10-26.sql
```

---

## 11. Troubleshooting

| Issue | Solution |
|-------|----------|
| `connection refused` | `make db-up` / `make private-db-up`; wait for `pg_isready` |
| `permission denied` | Check password in DSN matches `compose.yaml` env vars |
| `no module named 'psycopg'` | `make venv` or `uv pip install -r app/requirements.txt` |
| Ollama: `connection refused` | `ollama serve` in separate terminal |
| Ollama: `model not found` | `ollama pull bge-m3-local` etc. |
| Slow queries | Ensure `vector_top_k` / `lexical_top_k` not too high; check HNSW index |
| PDF yields no text | Enable `--ocr` (needs `tesseract` CLI) |
| Private corpora in eval DB | CLI guards prevent this; check `--db` flag |

---

## 12. Quick Reference Card

```bash
# === STARTUP ===
cd ai/patterns/graph-rag
make venv                    # one-time
make db-up migrate           # eval DB
make private-db-up private-migrate  # private DB

# === INDEXING ===
.venv/bin/python -m app.cli ingest lab --db eval --stub   # fast test
.venv/bin/python -m app.cli ingest lab --db eval          # real
.venv/bin/python -m app.cli ingest notes                   # private notes
.venv/bin/python -m app.cli ingest papers                  # papers
.venv/bin/python -m app.cli ingest papers --ocr --force   # scanned PDFs

# === QUERY ===
.venv/bin/python -m app.cli search "..." --corpus lab --db eval --k 5
.venv/bin/python -m app.cli ask "..." --corpus notes --db private
.venv/bin/python -m app.cli ask "..." --require-graph      # fail if no graph

# === API ===
.venv/bin/python -m app.cli serve --port 8099
curl -s localhost:8099/v1/ask -d '{"question":"...","corpus":"lab"}' -H 'content-type: application/json'

# === EVAL ===
make eval-local
.venv/bin/python eval/local_eval.py --graph-hops 2 --rerank --json-out /tmp/results.json

# === CLEANUP ===
make db-down                    # stops eval DB (data persists)
make private-db-down            # stops private DB (data persists)
```

---

## 13. Key Files Reference

| File | Purpose |
|------|---------|
| `ai/patterns/graph-rag/app/README.md` | Full app documentation |
| `ai/patterns/graph-rag/app/config.example.yaml` | Config template |
| `~/.config/graphrag/config.yaml` | Your private config (git-ignored) |
| `ai/patterns/graph-rag/compose.yaml` | Docker Compose for both DBs |
| `ai/patterns/graph-rag/db/schema.sql` | Database schema |
| `ai/patterns/graph-rag/eval/golden_qa.jsonl` | 42 golden questions |
| `ai/patterns/graph-rag/eval/local_eval.py` | Evaluation runner |
| `ai/patterns/graph-rag/examples/` | 6 optional feature guides |

---

*Generated: 2026-10-26 | Repo: https://github.com/kr1surb4n/k8s-lab-kit*