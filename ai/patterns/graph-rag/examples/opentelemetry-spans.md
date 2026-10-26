# Example: OpenTelemetry spans

The app already writes one structured query log line. This example adds real
spans for `graphrag.answer` and its nested `graphrag.search`, with an optional
console exporter or OTLP/HTTP collector. Tracing is off by default.

Span attributes are deliberately boring: corpus, `k`, chunk count, graph-path
count, refusal flag, rerank flag, and latency. The question text and passage
text are **not** copied into spans. The existing local log line still contains
the question; do not ship those logs to a remote collector.

## Console demo

Create a temporary config:

```bash
cat > /tmp/graphrag-otel.yaml <<'YAML'
otel:
  enabled: true
  endpoint: ""
  service_name: graphrag-otel-example
  console: true
YAML
```

Run an answer against the evaluation corpus:

```bash
cd ai/patterns/graph-rag
.venv/bin/python -m app.cli --config /tmp/graphrag-otel.yaml \
  ask "Which namespace does every exercise in this kit use?" \
  --corpus lab --db eval --stub --json \
  > /tmp/graphrag-answer.json 2> /tmp/graphrag-spans.jsonl
```

The JSON answer stays valid on stdout. Console spans go to stderr. Check the
shared trace id:

```bash
.venv/bin/python -c '
import json
answer = json.load(open("/tmp/graphrag-answer.json"))
print("answer trace:", answer["trace_id"])
spans = [json.loads(line) for line in open("/tmp/graphrag-spans.jsonl") if line.strip()]
for span in spans:
    if "name" not in span:
        continue
    print(span["name"], span["context"]["trace_id"], span.get("parent_id"))
'
```

Expected shape:

```text
answer trace: 190ef1525bf30b42d0f1d4a4492cc24f
graphrag.search 0x190ef1525bf30b42d0f1d4a4492cc24f 0xbd621c91c0312c21
graphrag.answer 0x190ef1525bf30b42d0f1d4a4492cc24f None
```

The answer trace id is the same as both spans. Search is a child of answer.

## Configuration

```yaml
otel:
  enabled: true
  endpoint: http://localhost:4318/v1/traces
  service_name: graphrag-local
  console: false
```

- `console: true` writes readable JSON spans to stderr.
- `endpoint` is an OTLP/HTTP traces URL. It defaults to the local collector
  convention on port `4318`.
- Both can be enabled together for a local collector plus console proof.
- If the OTLP collector is down, the batch exporter logs errors and the
  application still answers; tracing must not be on the request critical path.
- If the OpenTelemetry SDK is not installed, enabling tracing logs a warning and
  the app continues without spans.

The HTTP service configures telemetry at import time. The CLI configures it on
the first search or answer call. Restart the API after changing `otel`.

## Verification

```bash
.venv/bin/python -m unittest app.tests.test_telemetry -v
```

The tests use an in-memory exporter, not a collector. They assert:

- a span is exported and has a valid trace id;
- `graphrag.search` records counts;
- `graphrag.answer` records citation and refusal counts;
- neither the query text nor a private phrase appears in span attributes.

## What changed

- `app/telemetry.py` configures an SDK `TracerProvider` and optional exporters.
- `search()` starts `graphrag.search`; `answer()` starts `graphrag.answer`
  around it, so the spans share a trace.
- `trace_id` in the answer now comes from the active span when tracing is on,
  and falls back to the existing random id otherwise.
- Search responses also carry a `trace_id` field when tracing is on.
- The API initializes the tracer from `config.yaml`; CLI calls do it lazily.

## Limitations

- There is no collector, Tempo, or dashboard in this example. Point `endpoint`
  at an existing local OTLP/HTTP collector.
- Spans are not sampled explicitly; the SDK default parent-based sampler is
  used. Add a sampler in `telemetry.py` if volume matters.
- The local log line is still the place where the actual question is recorded.
  That is useful for local debugging and unsafe to ship off the machine.
- Trace ids are observability identifiers, not authentication tokens.
