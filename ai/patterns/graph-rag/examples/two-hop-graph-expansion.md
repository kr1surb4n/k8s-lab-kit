# Example: two-hop graph expansion

This example starts from the documents found by hybrid retrieval, takes the
entities in their graph edges, and follows a shared entity into one other
document. The second-hop edge records the shared entity as `via`, so the extra
context is explainable.

The default is still one hop. Two-hop expansion is opt-in.

## Run it

The evaluation database is enough; no private notes are involved.

```bash
cd ai/patterns/graph-rag
make db-up migrate

# One hop, the default.
.venv/bin/python -m app.cli search \
  "How is a Service connected to Pods?" \
  --corpus lab --db eval --graph-hops 1 --k 5

# Two hops: follow a shared entity into another document.
.venv/bin/python -m app.cli search \
  "How is a Service connected to Pods?" \
  --corpus lab --db eval --graph-hops 2 --k 5
```

In the two-hop output, entries marked `hop 2` include a `via` entity:

```text
graph: 35 relation(s)
  ...
  minikube --USED_WITH--> Tool (hop 2, via Tool)
  A7 --REQUIRES--> Secret (hop 2, via A7)
```

The JSON response contains the same information:

```bash
.venv/bin/python -m app.cli search \
  "How is a Service connected to Pods?" \
  --corpus lab --db eval --graph-hops 2 --k 5 --json \
  | .venv/bin/python -c '
import json, sys
result = json.load(sys.stdin)
print(result["graph_hops"])
for edge in result["graph_path"]:
    if edge["hop"] == 2:
        print(edge)
'
```

## Configuration

Set it once in the private config instead of passing the flag every time:

```yaml
graph_hops: 2
```

The HTTP API accepts the same override:

```bash
curl -s http://127.0.0.1:8099/v1/search \
  -H 'content-type: application/json' \
  -d '{"query":"How is a Service connected to Pods?","corpus":"lab","k":5,"graph_hops":2}'
```

`graph_hops` is limited to `1` or `2`.

## What changed

- `graph_context()` fetches first-hop edges from the top retrieved documents.
- It keeps up to 40 bridge entities from those edges.
- It fetches edges in **other** documents that share a bridge entity.
- The second-hop result is capped at one third of the first-hop limit and is
  skipped when there is no shared entity.
- The answer response is unchanged except for the extra `hop` and `via` fields.

## Verification

Offline tests use a fake connection and cover both the one-hop and two-hop SQL
paths:

```bash
.venv/bin/python -m unittest app.tests.test_retrieval -v
```

To compare the golden set with and without the second hop:

```bash
.venv/bin/python eval/local_eval.py --graph-hops 1
.venv/bin/python eval/local_eval.py --graph-hops 2 --json-out /tmp/two-hop.json
```

Second-hop edges are extra context. They do not replace the first-hop edges, so
the graph-path score should not drop unless the larger path confuses the
generator. Check the score before changing the default.

## Limitations

- The bridge is a shared **node name**, not a typed traversal. A common word
  such as `Tool` can connect unrelated documents.
- The second hop excludes the top documents to avoid repeating context. It is
  one extra hop, not an arbitrary graph walk.
- A two-hop path increases prompt size and can add noisy evidence. Keep it
  opt-in until the evaluation justifies it.
