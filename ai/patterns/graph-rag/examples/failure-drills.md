# Example: destructive failure drills

Two destructive drills prove the Phase 17 failure acceptance rules against the
**evaluation** database only. Neither drill touches the private database, and
both restore the evaluation state afterwards.

| Drill | Question type | Guard under test |
|---|---|---|
| Delete a cited document | Answer question | the answer must change and the deleted citation must disappear |
| Empty the graph layer | Relation question | the answer must fail loudly, not fall back to a confident wrong answer |

## Drill 1 — deleted cited document

A golden answer cites a document (`must_cite: true`). If that document is gone,
the citation has to go, and the answer has to follow.

```bash
cd ai/patterns/graph-rag
make db-up migrate

# 1. Baseline: the question must already cite its expected document.
.venv/bin/python -m app.cli ask "What object does a Deployment create when its pod template changes?" \
  --corpus lab --db eval --json > /tmp/drill-before.json
.venv/bin/python -c '
import json
before = json.load(open("/tmp/drill-before.json"))
print(before["citations"])
'

# 2. Break it on purpose: delete the cited document from the eval database.
docker compose exec -T postgres psql -U graphrag -d graphrag \
  -c "DELETE FROM documents WHERE id = 'doc-03';"

# 3. Ask again; the deleted citation must not come back.
.venv/bin/python -m app.cli ask "What object does a Deployment create when its pod template changes?" \
  --corpus lab --db eval --json > /tmp/drill-after.json
.venv/bin/python -c '
import json
after = json.load(open("/tmp/drill-after.json"))
cited = [c["chunk_id"] for c in after["citations"]]
print(cited)
assert not any("doc-03" in cid for cid in cited), "the deleted document was cited again"
'
```

Expected outcome: the answer changes, or becomes a clean refusal, and the
deleted citation disappears. The retrieval guardrail already refuses weak
answers, so a vanished document should surface as a changed answer or a refusal,
never as a citation into missing data.

## Drill 2 — broken graph layer

An empty `edge_nodes` table means the graph layer has nothing to say. A relation
question must fail loudly instead of answering from chunk context alone.

```bash
# 1. Break it on purpose: empty the edge membership table.
docker compose exec -T postgres psql -U graphrag -d graphrag \
  -c "DELETE FROM edge_nodes;"

# 2. Ask a relation question with the fail-loudly guard.
.venv/bin/python -m app.cli ask "What object does a Deployment create when its pod template changes?" \
  --corpus lab --db eval --require-graph --json > /tmp/drill-graph.json
cat /tmp/drill-graph.json
```

The expected response for a relation question:

```json
{
  "answer": "The graph context is unavailable for this relation question.",
  "citations": [],
  "graph_path": [],
  "refused": true,
  "graph_error": "graph_path_empty"
}
```

The command exits with status 2 because the answer is refused, which a drill
script can assert on.

## Restore after every drill

Both drills only touch the evaluation database, but a destructive drill must
always put it back. Take a dump before breaking anything and restore after:

```bash
# Backup before the drill (plain dumps carry a \restrict token that psql
# rejects, so filter it out first).
docker compose exec -T postgres pg_dump -U graphrag -d graphrag > /tmp/graphrag-eval-before.dump
grep -v -E '^\\(un)?restrict ' /tmp/graphrag-eval-before.dump > /tmp/graphrag-eval-clean.dump

# ... run the drill ...

# Restore: drop the public schema and reload the dump.
docker compose exec -T postgres psql -U graphrag -d graphrag \
  -c 'DROP SCHEMA public CASCADE; CREATE SCHEMA public;'
docker compose exec -T postgres psql -U graphrag -d graphrag -f - < /tmp/graphrag-eval-clean.dump
```

As an alternative to the dump, the disposable evaluation fixture can be rebuilt
from scratch:

```bash
make db-down
make db-up
make migrate
make ingest-lab
```

## Metrics each drill should move

| Drill | Expected outcome | Metric that moves |
|---|---|---|
| Deleted cited document | The answer changes; the deleted citation disappears | Citation precision (the deleted document should stop being cited) and answer-fact match. A surviving correct citation set means the deleted document was handled as intended. |
| Empty graph layer | The relation question is refused with `graph_error: graph_path_empty` | Graph-path accuracy and refusal correctness. With the guard, the question no longer answers from vector context alone; the refusal is a correct failure, not a confident wrong answer. |

Record the before/after numbers in `eval/local-results.json` style output for
the session, and re-run `make eval-local` after restoring to confirm the
baseline (recall@k 1.00, citation precision 0.75, graph-path accuracy 0.7875,
refusal correctness 1.00) is back.

## Offline checks

```bash
.venv/bin/python -m unittest app.tests.test_retrieval -v
```

The offline tests fake the retrieval layer and cover the fail-loudly branch:
an empty graph path with the guard enabled returns the graph error response, the
settings default is honoured, and a present graph context lets the answer
through.
