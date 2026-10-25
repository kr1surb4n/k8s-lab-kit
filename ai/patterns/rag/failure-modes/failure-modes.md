# RAG Failure Modes — known issues and mitigations

| # | Symptom | Root Cause | Detection | Mitigation | Priority |
|---|---------|------------|-----------|------------|----------|
| 1 | Low recall (< 0.85) | Embedding model mismatch between ingest and query | Evaluation Recall@k < threshold | Re-ingest with same embedding model; verify model version in ConfigMap | P0 |
| 2 | Hallucination rate > 5% | Weak retrieval (top-k too low, poor reranker) | LLM-as-judge faithfulness score < 0.85 | Increase top-k to 50; improve reranker; add "I don't know" fallback | P0 |
| 3 | Latency p99 > 2s | GPU memory pressure; model too large | Prometheus `rag_latency_seconds` p99 > 2 | Reduce batch size; enable flash-attention; quantize to 4-bit; offload layers to CPU | P1 |
| 4 | OOM on GPU | Model + KV cache > VRAM | Pod `OOMKilled`; `nvidia-smi` shows 100% mem | Quantize to 4-bit GPTQ; reduce max_tokens; enable gradient checkpointing | P0 |
| 5 | Stale answers | Corpus not re-ingested after updates | User reports outdated info; `ingest_timestamp` lag > 24h | Automate re-ingest pipeline (cronjob); add `last_ingested` to health endpoint | P1 |
| 6 | PII leakage | Guardrail not catching sensitive data | Audit log shows SSN/email in response | Tighten Presidio rules; add custom regex for org-specific patterns; enable output filter | P0 |
| 7 | Toxic output | Generator produces harmful content | Guardrail logs toxicity flag; user reports | Add toxicity classifier (Detoxify); enforce output format (JSON only) | P0 |
| 8 | Rate limit exceeded | Burst traffic from single tenant | 429 responses; `rag_rate_limit_exceeded` metric | Per-tenant token bucket (60/min); burst allowance 10; return 429 with retry-after | P1 |
| 9 | Embedding drift | Corpus embeddings become stale over time | Recall drops gradually; cosine similarity to centroid decreases | Monthly re-embed schedule; monitor embedding centroid distance | P2 |
| 10 | Vector index corruption | PGVector HNSW index broken | `SELECT * FROM vectors` errors; pgvector errors in logs | Rebuild index: `REINDEX INDEX vectors_idx`; automate weekly | P1 |
| 11 | BM25 + vector fusion imbalance | One retriever dominates | RRF weights not working; inspect `fusion_scores` histogram | Tune RRF k parameter; add weight config; log per-retriever contribution | P2 |
| 12 | Reranker timeout | Cross-encoder too slow for top-50 | `rerank_latency_seconds` p99 > 500ms | Reduce rerank candidates to top-20; use smaller reranker model; async rerank | P2 |
| 13 | Generator repeats/loops | Temperature too high; no repetition penalty | Answer contains repeated phrases; `repetition_penalty` not set | Set `repetition_penalty=1.1`, `temperature=0.3`, `top_p=0.9` | P1 |
| 14 | Context window overflow | Retrieved chunks too long for model | Truncation warnings in logs; answer cuts off | Enforce chunk size ≤ 512 tokens; limit total context to 3000 tokens | P1 |
| 15 | Multi-tenant data leakage | Tenant A sees Tenant B docs | Audit log shows cross-tenant `doc_id` in sources | Enforce tenant_id filter in vector query; add row-level security in PGVector | P0 |

## Monitoring Alerts

```yaml
# PrometheusRule for RAG
- alert: RAGLowRecall
  expr: rag_recall_at_5 < 0.85
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "RAG recall@5 below 85%"

- alert: RAGHighLatency
  expr: histogram_quantile(0.99, rag_latency_seconds) > 2
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "RAG p99 latency above 2s"

- alert: RAGHallucinationRate
  expr: rag_faithfulness_score < 0.85
  for: 10m
  labels:
    severity: critical
  annotations:
    summary: "RAG faithfulness below 85%"

- alert: RAGGPUOOM
  expr: kube_pod_container_status_terminated_reason{pod=~"rag-api.*",reason="OOMKilled"} > 0
  for: 1m
  labels:
    severity: critical
  annotations:
    summary: "RAG pod OOMKilled"
```

## Runbook Links

- Low recall → `docs/runbooks.md#rag-low-recall`
- Hallucination → `docs/runbooks.md#rag-hallucination`
- GPU OOM → `docs/runbooks.md#rag-gpu-oom`
- PII leakage → `docs/runbooks.md#rag-pii-leakage`