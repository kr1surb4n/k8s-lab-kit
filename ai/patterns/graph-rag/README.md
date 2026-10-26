# Graph RAG Pattern — Retrieval-Augmented Generation with Knowledge Graphs

**What**: RAG enhanced with knowledge graphs for multi-hop reasoning and entity relationships.

**When**: Complex queries requiring multi-step reasoning, entity disambiguation, citation tracing.

**API Contract**: `POST /v1/graph-rag/query` → `{answer, sources[], graph_path[], trace_id, latency_ms}`

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Client    │────▶│   Router    │────▶│  Hybrid     │────▶│   Graph     │
│  (query)    │     │ (intent)    │     │  Retriever  │     │  Expander   │
└─────────────┘     └─────────────┘     └──────┬──────┘     └──────┬──────┘
                                               ▼                  ▼
                                         ┌─────────────┐     ┌─────────────┐
                                         │   Vector    │     │   Apache    │
                                         │  Search     │     │    AGE      │
                                         │ (pgvector)  │     │ (PostgreSQL)│
                                         └──────┬──────┘     └──────┬──────┘
                                                ▼                  ▼
                                         ┌─────────────┐     ┌─────────────┐
                                         │   Reranker  │     │  Subgraph   │
                                         │ (cross-enc) │     │  Extractor  │
                                         └──────┬──────┘     └──────┬──────┘
                                                ▼                  ▼
                                         ┌─────────────────────────────────┐
                                         │      Generator + Graph Path     │
                                         │   (LLM + subgraph context)      │
                                         └─────────────────────────────────┘
                                                ▼
                                         ┌─────────────────────────────────┐
                                         │         Guardrail               │
                                         │  (citations, hallucination chk) │
                                         └─────────────────────────────────┘
                                                ▼
                                         ┌─────────────────────────────────┐
                                         │        Response                 │
                                         │ {answer, sources[], graph_path, │
                                         │  trace_id, latency_ms}          │
                                         └─────────────────────────────────┘
```

## Components

| Component | Technology | Config |
|-----------|------------|--------|
| Vector Embedding | `bge-m3-local` via Ollama (1024-dim) | batch=32, normalize=True |
| Vector Store | PGVector (PostgreSQL 16) | HNSW, m=16, ef=64 |
| BM25 | PostgreSQL tsvector | title^2 + body |
| Hybrid Fusion | RRF (k=60) | α=0.5 |
| Graph DB | Plain Postgres tables + recursive CTEs; Apache AGE optional | see the Phase 17 plan |
| Reranker | LLM listwise via `granite3.3-8b-local` (default); optional `BAAI/bge-reranker-v2-m3` | top-20 → top-5 |
| Generator | `granite3.3-8b-local` Q4_K_M (primary); `qwen3-8b-local` fallback | temp=0.2, num_ctx=8192 |
| Guardrail | Presidio + custom | PII, toxicity, format |

The component table is the Phase 17 target. The imported architecture diagram
and schema still show Apache AGE; the implementation uses plain Postgres tables
and recursive CTEs as the primary graph layer, with AGE as an optional adapter.

## Local model setup

The local model set is chosen and imported. See
[`models/README.md`](models/README.md) for the full matrix, import commands and
verification commands.

- Required: `bge-m3-local` (embeddings) and `granite3.3-8b-local` (generation).
- Optional: `qwen3-8b-local` (fallback), `phi-4-mini-local` (fast fallback),
  `nuextract-local` (structured extraction).
- Rerank: listwise LLM prompt with Granite first; add a cross-encoder only if
  the evaluation justifies it.

## Graph schema (plain Postgres)

The graph is stored in Postgres, not Apache AGE. See [`db/README.md`](db/README.md)
for the decision and the R18 comparison plan.

| Table | Purpose |
|---|---|
| `documents` | corpus documents with `sha256`, version, and source metadata |
| `chunks` | text spans with offsets, a generated `tsv`, and a content hash |
| `embeddings` | one 1024-dim `bge-m3` vector per chunk (HNSW, cosine) |
| `nodes` | entities, unique by `(name, type)` |
| `edges` | relations with `arity`; `arity >= 3` is a hyperedge |
| `edge_nodes` | edge members with a role and an ordered position |
| `provenance` | table + row + document + chunk + source hash + corpus version |

A hyperedge is one `edges` row plus its `edge_nodes` members. The
`edge_summary` view returns each edge with its ordered member names, so "which
three components jointly serve the page" is one query, not three pairwise joins.

The Phase 16 RAG pattern is untouched and remains the baseline.

## Corpus and evaluation

The Phase 17 corpus is 20 documents under [`corpus/`](corpus/README.md), with a
SHA-256 manifest and provenance for every document. The golden set in
[`eval/golden_qa.jsonl`](eval/golden_qa.jsonl) has 42 questions: 30 answerable,
10 relation-only, and 2 that must be refused. `make corpus-check` validates all
of it offline, including checking that every expected answer fact appears in the
cited documents.


## Data Flow

1. **Ingest**: `POST /v1/graph-rag/ingest` → chunk → embed → upsert to PGVector + extract entities/relations → upsert to AGE
2. **Query**: `POST /v1/graph-rag/query` → embed query → hybrid search (top-50) → graph expansion (2-hop) → rerank (top-5) → subgraph extraction → generate with graph context → guardrail → respond
3. **Trace**: Every step emits OTel spans with `trace_id` propagated through all services

## API

```bash
# Ingest documents with entities
curl -X POST http://graph-rag:8000/v1/graph-rag/ingest \
  -H "Content-Type: application/json" \
  -d '{"documents": [{"id": "doc-1", "title": "K8s Basics", "text": "...", "entities": [{"name": "Kubernetes", "type": "Technology"}, {"name": "Pod", "type": "Resource"}]}, ...]}'

# Query with graph expansion
curl -X POST http://graph-rag:8000/v1/graph-rag/query \
  -H "Content-Type: application/json" \
  -d '{"query": "How do Pods relate to Deployments?", "top_k": 5, "graph_hops": 2, "rerank": true}'

Response:
{
  "answer": "Deployments manage ReplicaSets which create Pods...",
  "sources": [...],
  "graph_path": [
    {"source": "Deployment", "relation": "MANAGES", "target": "ReplicaSet"},
    {"source": "ReplicaSet", "relation": "CREATES", "target": "Pod"}
  ],
  "trace_id": "00000000000000000000000000000001",
  "latency_ms": 450
}
```

## Kubernetes Deployment

```yaml
# Deployment with GPU + PostgreSQL/AGE sidecar
apiVersion: apps/v1
kind: Deployment
metadata:
  name: graph-rag-api
spec:
  replicas: 2
  template:
    spec:
      containers:
        - name: api
          image: boilerplate/graph-rag-api:1.0
          resources:
            requests:
              cpu: "1000m"
              memory: "4Gi"
              nvidia.com/gpu: "1"
            limits:
              memory: "8Gi"
              nvidia.com/gpu: "1"
        - name: postgres-age
          image: apache/age:1.5.0-pg16
          ports:
            - containerPort: 5432
          env:
            - name: POSTGRES_DB
              value: "graph_rag"
            - name: POSTGRES_USER
              value: "rag"
            - name: POSTGRES_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: graph-rag-secrets
                  key: postgres-password
          volumeMounts:
            - name: pgdata
              mountPath: /var/lib/postgresql/data
      volumes:
        - name: pgdata
          emptyDir: {}
```

## Evaluation

```bash
# Golden Q&A with graph path verification
make eval

# Metrics
- Recall@5: ≥ 0.85
- Graph Path Accuracy: ≥ 0.80
- Faithfulness (LLM-as-judge): ≥ 0.85
- Latency p50: ≤ 800ms, p99: ≤ 3000ms
```

## Failure Modes

| # | Symptom | Root Cause | Mitigation |
|---|---------|------------|------------|
| 1 | Low graph path accuracy | Entity extraction missing | Improve NER model; add manual curation |
| 2 | Graph expansion timeout | Too many hops / large subgraph | Limit hops to 2; add timeout |
| 3 | AGE extension missing | PG extension not loaded | Ensure `CREATE EXTENSION age` in init |
| 4 | Cypher injection | User input in Cypher | Parameterized queries only |
| 5 | Graph bloat | Too many entities/relations | TTL cleanup; entity dedup |

## Quick Start

```bash
cd ai/patterns/graph-rag
make corpus-check   # offline: corpus, manifest, golden set
make db-check       # docker: schema twice + hyperedge round-trip
make build          # docker build -t boilerplate/graph-rag-api:1.0 mockup
make deploy         # kubectl apply -k k8s
make eval           # runs golden Q&A + graph path evaluation
```

The `mockup/` app is still the imported keyword demo. Phase 17.3 replaces its
in-memory store with the schema above.


## References

- [Apache AGE Documentation](https://age.apache.org/)
- [PGVector Documentation](https://github.com/pgvector/pgvector)
- [RAG with Knowledge Graphs Paper](https://arxiv.org/abs/2402.04243)