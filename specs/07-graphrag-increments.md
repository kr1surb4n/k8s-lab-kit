# Spec: Phase 17 Graph RAG Optional Increments — COMPLETED

## Problem Statement
Implement six optional Phase 17 Graph RAG increments as separate runnable examples. Each increment is an independent commit with code, tests, documentation.

## Status: ✅ DONE (6 commits)

| # | Increment | Commit | Example Doc | Key Files |
|---|---|---|---|---|
| 1 | Two-hop graph expansion | `62fa4c6` | `examples/two-hop-graph-expansion.md` | `retrieval.py` (graph_context), `config.py` (graph_hops), `cli.py` (--graph-hops), `api.py` (graph_hops), `test_retrieval.py` |
| 2 | Local listwise reranker | `ff378cb` | `examples/reranker.md` | `rerank.py` (rerank_chunks), `retrieval.py` (rerank), `config.py` (rerank*), `cli.py` (--rerank), `test_rerank.py` |
| 3 | OCR for image-only PDFs | `ef1e3c9` | `examples/ocr-image-pdfs.md` | `sources.py` (read_pdf ocr*), `config.py` (ocr*), `cli.py` (--ocr), `test_ocr.py` |
| 4 | OpenTelemetry spans | `ffe299a` | `examples/opentelemetry-spans.md` | `telemetry.py`, `retrieval.py` (span), `config.py` (otel*), `test_telemetry.py` |
| 5 | Destructive failure drills | `00cad08` | `examples/failure-drills.md` | `retrieval.py` (require_graph), `config.py` (require_graph), `cli.py` (--require-graph), `api.py` (require_graph), `test_retrieval.py` |
| 6 | Kubernetes packaging | `a12424f` | `examples/kubernetes-packaging.md` | `k8s/` (deployment, service, configmap, secret, rbac, hpa, networkpolicy, kustomization) |

## Implementation Summary

### Common Patterns Across All Increments
- **Config-driven**: Settings in `config.py` / `config.example.yaml` with env override
- **CLI flags**: `--flag` for per-run override
- **API fields**: Same field names in request models
- **Tests**: Offline unit tests in `app/tests/test_*.py` (no DB/GPU needed)
- **Documentation**: `examples/<name>.md` with run commands, config, verification, limitations
- **Index**: `examples/README.md` lists all with default state

### Private Models Only
All increments use local Ollama models:
- Embeddings: `bge-m3-local` (1024-dim)
- Generation: `granite3.3-8b-local` (primary), `qwen3-8b-local` (fallback)
- Reranking: listwise prompt on generation model (no cross-encoder library)
- No cloud API calls in any increment

### Failure Drills Specifics
- Target **eval database only** (ports 5433/5434)
- Two drills: delete cited document, empty `edge_nodes`
- Restore via `pg_dump`/`pg_restore` or `make db-down && make db-up migrate ingest-lab`
- Metrics tracked: citation precision, graph-path accuracy, refusal correctness

### Kubernetes Packaging Specifics
- Kustomize base in `ai/patterns/graph-rag/k8s/`
- Non-root, readOnlyRootFs, dropped caps, resource requests/limits
- Secrets via `Secret` (placeholders), ConfigMap for settings
- NetworkPolicy: default-deny egress, allow DNS + OTel collector
- HPA on CPU, memory, custom queue metric
- Validated offline: `kubectl kustomize k8s | kubectl apply --dry-run=client`
- No minikube required for validation

## Test Results
```
$ make test
38 passed, 0 failed, 0 skipped

$ cd ai/patterns/graph-rag && .venv/bin/python -m unittest discover -s app/tests
Ran 55 tests in 0.7s
OK
```

## Archive
Saved to `~/.config/opencode/answers.md` with title "Phase 17 optional increments complete"

## Next Steps
See `specs/05-hardened-manifests.md` for propagating Kubernetes controls to production grade.
See `specs/08-shared-service-hardening.md` for auth/TLS/isolation/audit/rate-limits/secrets/packaging/privacy review.