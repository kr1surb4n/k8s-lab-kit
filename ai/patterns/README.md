# AI Patterns Catalogue

A curated collection of reusable AI/ML patterns for Kubernetes. Each pattern is a self-contained
module with: contract (API), mockup (demo), k8s manifests, failure modes, and eval.

## Structure

```
ai/patterns/
├── rag/              # Retrieval-Augmented Generation (working baseline)
├── graph-rag/        # RAG + knowledge graph (imported scaffold, see its PROVENANCE.md)
├── router/           # Semantic/model routing
├── agent/            # Tool-using agents
├── eval/             # Evaluation harness
├── guardrail/        # Input/output safety
├── rerank/           # Cross-encoder re-ranking
├── context/          # Long-context management
├── embedding/        # Embedding pipelines
├── vector-store/     # Vector DB operations
└── prompt-engineering/ # Prompt templates, few-shot
```

## Pattern Template

Each pattern follows this structure:

```
<pattern-name>/
├── README.md          # What it does, when to use, API contract
├── mockup/            # Minimal runnable demo (Python/Go)
├── k8s/               # Kubernetes manifests (Deployment, Service, HPA)
├── contracts/         # OpenAPI/AsyncAPI schemas
├── eval/              # Golden Q&A, metrics, latency budgets
├── failure-modes/     # Known failures + mitigations
└── Makefile           # build, test, deploy, eval
```

## Quick Start

```bash
# Build and deploy a pattern
cd ai/patterns/rag
make build          # builds Docker image
make deploy         # applies k8s manifests to k8s-lab namespace
make eval           # runs evaluation suite
make clean          # removes resources
```

## Patterns Index

| Pattern | Use Case | Complexity | Depends On |
|---------|----------|------------|------------|
| `rag` | Q&A over docs, code search | Medium | vector-store, embedding, rerank |
| `graph-rag` | Multi-hop Q&A with entity relations | High | rag, vector-store |
| `router` | Cost/quality routing | Low | eval |
| `agent` | Multi-step tool use | High | router, eval, guardrail |
| `eval` | Automated quality gates | Medium | - |
| `guardrail` | PII, toxicity, hallucination | Medium | eval |
| `rerank` | Precision boost for retrieval | Medium | embedding, vector-store |
| `context` | Long-document handling | Medium | embedding |
| `embedding` | Vector generation pipeline | Low | vector-store |
| `vector-store` | PGVector/Redis/Milvus ops | Low | - |
| `prompt-engineering` | Reusable prompt library | Low | - |

## Contracts

All patterns expose a consistent HTTP API:

```yaml
# Example: /generate (RAG, Agent, Router)
POST /v1/generate
Content-Type: application/json

{
  "query": "string",
  "context": {"key": "value"},
  "params": {"temperature": 0.7, "max_tokens": 512}
}

Response:
{
  "answer": "string",
  "sources": [{"doc_id": "string", "score": "float"}],
  "trace_id": "string",          # for OTel tracing
  "latency_ms": "int"
}
```

## Observability

Every pattern emits:
- **Metrics**: `requests_total`, `latency_seconds`, `tokens_in/out`, `error_rate`
- **Traces**: OTel spans for each step (retrieve, rerank, generate, guardrail)
- **Logs**: JSON structured with `trace_id`, `span_id`, `level`, `msg`

## Safety

All patterns include:
- Input validation (length, encoding, PII detection)
- Output filtering (toxicity, hallucination check, format enforcement)
- Rate limiting (per-tenant, per-endpoint)
- Audit logging (request/response with trace_id)

## Next: Implement RAG Pattern

The RAG pattern is the foundation. Start with:
1. `ai/patterns/rag/README.md` - contract + architecture
2. `ai/patterns/rag/mockup/` - minimal FastAPI demo
3. `ai/patterns/rag/k8s/` - Deployment + HPA + ConfigMap
4. `ai/patterns/rag/eval/` - golden Q&A + recall@k metrics