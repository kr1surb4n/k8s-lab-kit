# RAG Pattern — Retrieval-Augmented Generation

**What**: Answer questions over a document corpus using retrieval + generation.

**When**: Internal knowledge base, code search, customer support, onboarding.

**API Contract**: `POST /v1/rag/query` → `{answer, sources[], trace_id, latency_ms}`

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Client    │────▶│   Router    │────▶│  Retriever  │────▶│  Generator  │
│  (query)    │     │ (intent)    │     │ (hybrid:    │     │ (LLM +      │
└─────────────┘     └─────────────┘     │  BM25 +     │     │  context)   │
                                         │  vector)    │     └─────────────┘
                                         └──────┬──────┘           │
                                                ▼                 ▼
                                         ┌─────────────┐     ┌─────────────┐
                                         │   Reranker  │     │  Guardrail  │
                                         │ (cross-enc) │     │ (PII, tox,  │
                                         └─────────────┘     │  halluc.)   │
                                                               └─────────────┘
```

## Components

| Component | Technology | Config |
|-----------|------------|--------|
| Embedding | `BAAI/bge-small-en-v1.5` (384-dim) | batch=32, normalize=True |
| Vector Store | PGVector (PostgreSQL) | HNSW, m=16, ef=64 |
| BM25 | Tantivy / PostgreSQL tsvector | title^2 + body |
| Hybrid Fusion | RRF (k=60) | α=0.5 |
| Reranker | `BAAI/bge-reranker-base` | top-50 → top-5 |
| Generator | `mistralai/Mistral-7B-Instruct-v0.3` | 4-bit GPTQ, temp=0.3 |
| Guardrail | Presidio + custom rules | PII, toxicity, format |

## Data Flow

1. **Ingest**: `POST /v1/rag/ingest` → chunk (512 tokens, 50 overlap) → embed → upsert to PGVector
2. **Query**: `POST /v1/rag/query` → embed query → hybrid search (top-50) → rerank (top-5) → generate → guardrail → respond
3. **Trace**: Every step emits OTel spans with `trace_id` propagated through all services

## API

```bash
# Ingest documents
curl -X POST http://rag:8000/v1/rag/ingest \
  -H "Content-Type: application/json" \
  -d '{"documents": [{"id": "doc-1", "title": "K8s Basics", "text": "..."}, ...]}'

# Query
curl -X POST http://rag:8000/v1/rag/query \
  -H "Content-Type: application/json" \
  -d '{"query": "How do I scale a deployment?", "top_k": 5, "rerank": true}'

Response:
{
  "answer": "Use kubectl scale deploy/myapp --replicas=3...",
  "sources": [
    {"doc_id": "doc-5", "title": "Scaling", "score": 0.92, "snippet": "kubectl scale..."},
    {"doc_id": "doc-2", "title": "Deployments", "score": 0.87, "snippet": "replicas field..."}
  ],
  "trace_id": "00000000000000000000000000000001",
  "latency_ms": 234
}
```

## Kubernetes Deployment

```yaml
# Deployment with HPA (CPU + custom metric: queue_depth)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rag-api
spec:
  replicas: 2
  selector:
    matchLabels:
      app.kubernetes.io/name: rag-api
  template:
    spec:
      containers:
        - name: api
          image: boilerplate/rag-api:1.0
          ports:
            - containerPort: 8000
          env:
            - name: PGVECTOR_DSN
              valueFrom:
                secretKeyRef:
                  name: rag-secrets
                  key: pgvector-dsn
            - name: MODEL_PATH
              value: /models/mistral-7b-instruct-gptq
            - name: EMBEDDING_MODEL
              value: BAAI/bge-small-en-v1.5
            - name: RERANKER_MODEL
              value: BAAI/bge-reranker-base
          resources:
            requests:
              cpu: "500m"
              memory: "2Gi"
              nvidia.com/gpu: "1"
            limits:
              memory: "4Gi"
              nvidia.com/gpu: "1"
          readinessProbe:
            httpGet:
              path: /healthz
              port: 8000
            initialDelaySeconds: 30
            periodSeconds: 10
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: rag-api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: rag-api
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Pods
      pods:
        metric:
          name: rag_queue_depth
        target:
          type: AverageValue
          averageValue: "10"
```

## Evaluation

```bash
# Golden Q&A dataset
make eval

# Metrics
- Recall@5: ≥ 0.85
- Recall@10: ≥ 0.92
- MRR: ≥ 0.75
- Faithfulness (LLM-as-judge): ≥ 0.85
- Answer relevance: ≥ 0.80
- Latency p50: ≤ 500ms, p99: ≤ 2000ms
```

### Recorded baseline

`eval/results.json` is the Phase 16 mockup run over the 10 golden questions
(2026-10-25). It is committed so later changes can be compared against it.

| Metric | Value |
|---|---|
| Questions | 10 |
| Recall@5 (mean) | 1.00 |
| Faithfulness (mean) | 1.00 — placeholder, not an LLM judge yet |
| Latency p50 | 1 ms |
| Latency p99 | 12 ms |
| Latency within 2 s | 100% |

The numbers come from the mockup, whose generator is deterministic; they say the
harness and contracts work, not that the prompts are good. Phase 17 replaces the
placeholder faithfulness score with a real judgement.

## Failure Modes

| Symptom | Cause | Fix |
|---------|-------|-----|
| Low recall | Embedding model mismatch | Re-embed with same model |
| Hallucination | Weak retrieval | Increase top-k, improve reranker |
| High latency | GPU memory pressure | Reduce batch, enable flash-attn |
| OOM | Model too large for GPU | Quantize to 4-bit, offload layers |
| Stale answers | Corpus not updated | Automate re-ingest pipeline |

## Security

- All endpoints require JWT (issued by auth proxy)
- PII detection on input/output (Presidio)
- Rate limit: 60 req/min per tenant
- Audit log: request/response + trace_id to Loki

## Quick Start

```bash
# Build
docker build -t boilerplate/rag-api:1.0 ai/patterns/rag

# Deploy
kubectl apply -k ai/patterns/rag/k8s

# Test
curl -X POST http://rag.k8s-lab.svc.cluster.local/v1/rag/query \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"query": "How do I scale a deployment?"}'

# Evaluate
make -C ai/patterns/rag eval
```