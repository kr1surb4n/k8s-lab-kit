# Graph RAG Failure Modes — known issues and mitigations

| # | Symptom | Root Cause | Detection | Mitigation | Priority |
|---|---------|------------|-----------|------------|----------|
| 1 | Low graph path accuracy | Entity extraction missing / NER errors | Evaluation Graph Path Acc < 0.80 | Improve NER model; add manual curation; validate entities at ingest | P0 |
| 2 | Graph expansion timeout | Too many hops / large subgraph | `graph_expand_latency_seconds` p99 > 5s | Limit hops to 2; add timeout; limit subgraph size | P1 |
| 3 | AGE extension missing | PG extension not loaded | `CREATE EXTENSION age` fails; `SELECT * FROM ag_catalog.age_version()` fails | Ensure `CREATE EXTENSION age` in init script; add readiness check | P0 |
| 4 | Cypher injection | User input in Cypher queries | Security audit finds injection | Parameterized queries only; validate/sanitize all inputs | P0 |
| 5 | Graph bloat | Too many entities/relations over time | `SELECT count(*) FROM ag_catalog.ag_label` grows unbounded | TTL cleanup; entity dedup; archive old graphs | P2 |
| 6 | Low graph path accuracy | Weak entity extraction / missing relations | Evaluation Graph Path Acc < 0.80 | Improve NER; add relation extraction; validate at ingest | P0 |
| 7 | Hybrid search imbalance | One retriever dominates (BM25 vs vector) | RRF weights not working; inspect `fusion_scores` histogram | Tune RRF k parameter; add weight config; log per-retriever contribution | P2 |
| 8 | Reranker timeout | Cross-encoder too slow for top-50 | `rerank_latency_seconds` p99 > 500ms | Reduce rerank candidates to top-20; use smaller reranker model; async rerank | P2 |
| 7 | Generator repeats/loops | Temperature too high; no repetition penalty | Answer contains repeated phrases; `repetition_penalty` not set | Set `repetition_penalty=1.1`, `temperature=0.3`, `top_p=0.9` | P1 |
| 8 | Context window overflow | Retrieved chunks + graph context too long | Truncation warnings in logs; answer cuts off | Enforce chunk size ≤ 512 tokens; limit total context to 3000 tokens | P1 |
| 8 | Multi-tenant data leakage | Tenant A sees Tenant B docs/graph | Audit log shows cross-tenant `doc_id` in sources/graph_path | Enforce tenant_id filter in vector query AND Cypher; add row-level security | P0 |
| 9 | PII leakage in graph | Entity extraction captures PII | Audit log shows SSN/email in graph entities | Tighten Presidio rules; add custom regex; filter entities at ingest | P0 |
| 10 | GPU OOM | Model + graph context > VRAM | Pod `OOMKilled`; `nvidia-smi` shows 100% mem | Quantize to 4-bit GPTQ; reduce max_tokens; enable flash-attention | P0 |

## Monitoring Alerts

```yaml
# PrometheusRule for Graph RAG
- alert: GraphRAGLowGraphPathAccuracy
  expr: graph_rag_graph_path_accuracy < 0.80
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "Graph RAG graph path accuracy below 80%"

- alert: GraphRAGHighLatency
  expr: histogram_quantile(0.99, graph_rag_latency_seconds) > 3
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Graph RAG p99 latency above 3s"

- alert: GraphRAGLowRecall
  expr: graph_rag_recall_at_5 < 0.85
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "Graph RAG recall@5 below 85%"

- alert: GraphRAGGPUOOM
  expr: kube_pod_container_status_terminated_reason{pod=~"graph-rag-api.*",reason="OOMKilled"} > 0
  for: 1m
  labels:
    severity: critical
  annotations:
    summary: "Graph RAG pod OOMKilled"

- alert: AGEExtensionMissing
  expr: up{job="postgres-age"} == 0
  for: 1m
  labels:
    severity: critical
  annotations:
    summary: "Apache AGE PostgreSQL extension not available"
```

## Runbook Links

- Low graph path accuracy → `docs/runbooks.md#graph-rag-low-graph-path-accuracy`
- Graph expansion timeout → `docs/runbooks.md#graph-rag-expansion-timeout`
- AGE extension missing → `docs/runbooks.md#graph-rag-age-missing`
- Cypher injection → `docs/runbooks.md#graph-rag-cypher-injection`
- PII in graph → `docs/runbooks.md#graph-rag-pii-leakage`