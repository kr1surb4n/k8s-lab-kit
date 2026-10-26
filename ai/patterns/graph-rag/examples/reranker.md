# Example: local listwise reranker

Hybrid retrieval produces a fused list. This example asks the local generation
model to reorder that list once, with the whole candidate set in one prompt.
It is listwise reranking without a cross-encoder model.

The reranker is opt-in. If Ollama is down, the response is unusable, or the
model returns an unknown chunk id, the original RRF order is kept and the
search still succeeds.

## Run it

```bash
cd ai/patterns/graph-rag

# RRF order only.
.venv/bin/python -m app.cli search \
  "How is a Service connected to Pods?" \
  --corpus lab --db eval --k 5

# Rerank the fused candidates with granite3.3-8b-local.
.venv/bin/python -m app.cli search \
  "How is a Service connected to Pods?" \
  --corpus lab --db eval --k 5 --rerank

# Show the applied flag and model in JSON.
.venv/bin/python -m app.cli search \
  "How is a Service connected to Pods?" \
  --corpus lab --db eval --k 5 --rerank --json \
  | .venv/bin/python -c '
import json, sys
result = json.load(sys.stdin)
print(result["rerank"], result["rerank_model"], result["latency_ms"])
for chunk in result["chunks"]:
    print(chunk["chunk_id"], chunk["rrf"])
'
```

On the local 8B model the extra call added about 7 seconds to one search. The
latency is reported in `latency_ms`; do not enable reranking by default without
checking that trade-off.

## Configuration

```yaml
rerank: true
rerank_candidates: 20
rerank_model: ""   # empty = models.generate
```

The API accepts the same override:

```bash
curl -s http://127.0.0.1:8099/v1/search \
  -H 'content-type: application/json' \
  -d '{"query":"How is a Service connected to Pods?","corpus":"lab","k":5,"rerank":true}'
```

`rerank=true` is ignored when `--stub` is used, because the point is to exercise
the real local model.

## The prompt

The model receives the question and up to `rerank_candidates` compact passages:

```text
[doc-01#c0000] Kubernetes objects
A Deployment owns a ReplicaSet ...
```

It must return every id once:

```json
{"ranking": ["doc-01#c0000", "doc-03#c0000"]}
```

The parser accepts an object with `ranking`, `order`, or `ids`, a bare JSON
array, and code fences. Unknown ids are dropped, duplicate ids are ignored, and
missing candidates are appended in their original order. A model failure never
changes the retrieval path.

## Verification

```bash
.venv/bin/python -m unittest app.tests.test_rerank -v
```

To measure the golden set with reranking:

```bash
.venv/bin/python eval/local_eval.py --rerank --json-out /tmp/rerank-eval.json
```

Compare its score and p50/p95 latency with the no-rerank baseline before
changing `rerank` in the private config.

## Limitations

- This is a generative listwise ranker, not a trained relevance model. It can
  prefer a passage that looks plausible but does not answer the question.
- It reranks only the fused candidate list. A passage missing from the first
  `rerank_candidates` cannot be recovered.
- The prompt sends the question and local passage snippets to Ollama. Keep
  `ollama_url` local; never point it at a cloud endpoint for private corpora.
- The reranker uses the generation model by default. A smaller dedicated model
  can be set with `rerank_model` if it follows the JSON contract reliably.
