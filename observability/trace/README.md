# Traceability: one request, one id

A trace is only useful if the same id appears in the log line of every service
the request touched. The rule for this lab: **every service logs `trace_id`**.

## Wiring

```text
client
  -> ingress / port-forward
  -> nginx            (propagates traceparent, optionally emits its own span)
  -> app              (starts a span, logs trace_id)
  -> postgres         (span via the driver, if supported)
  -> otel-collector   (OTLP 4317/4318)
  -> tempo            (storage)
  -> grafana          (query by trace id)
```

Environment for an app in the cluster:

```yaml
env:
  - name: OTEL_EXPORTER_OTLP_ENDPOINT
    value: http://otel-collector.observability.svc.cluster.local:4318
  - name: OTEL_SERVICE_NAME
    value: web
  - name: OTEL_RESOURCE_ATTRIBUTES
    value: deployment.environment=lab,service.version=0.1.0
```

Do not put the collector URL in a ConfigMap that changes: the SDK reads it at
start, so a change needs a pod restart, same as any env var.

## Per runtime

| Runtime | Package | Note |
|---|---|---|
| Python | `opentelemetry-distro[otlp]`, `opentelemetry-instrument` | auto-instrumentation covers Flask/FastAPI/requests |
| Go | `go.opentelemetry.io/otel`, `otelhttp` | wrap the handler and the client |
| Node | `@opentelemetry/sdk-node`, auto-instrumentations | one `tracing.js` loaded with `--require` |
| PHP | `open-telemetry/opentelemetry-php` | FPM needs the extension; start with manual spans |
| nginx | `ngx_http_opentelemetry_module` | optional; forwarding `traceparent` is enough for A1 |

## Verify it

```bash
# 1. send a request through the app
curl -s http://127.0.0.1:8080/ >/dev/null

# 2. find the trace id in the log
kubectl logs deploy/web -n k8s-lab | tail -1

# 3. query Tempo
kubectl port-forward -n observability svc/tempo 3200:3200
curl -s "http://127.0.0.1:3200/api/search?tags=service.name%3Dweb" | jq '.traces[0]'

# 4. open Grafana -> Explore -> Tempo -> paste the id
```

If step 2 has no trace id, the SDK is not loaded. If step 3 is empty, the
collector is not receiving: check its logs and the endpoint URL. If the id in
the log does not match the id in Tempo, something in the middle (nginx, a
sidecar) is creating a new trace instead of propagating `traceparent`.

## What this buys

- "The page is slow" becomes "the database span is 1.8 s of a 2.0 s request".
- "It broke at 14:03" becomes a trace you can open, not a guess.
- "Who changed it" is the Git SHA label on the deployment plus the trace's
  `service.version`.
