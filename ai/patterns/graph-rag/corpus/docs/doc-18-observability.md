---
id: doc-18
title: Observability stack and trace propagation
section: "Operations > Observability"
corpus_version: 2026-10-26.1
source:
  kind: authored
  snapshot: 2026-10-26
  based_on:
    - observability/README.md
    - docs/example-runs.md
    - ai/patterns/graph-rag/mockup/main.py
---

The observability namespace answers four questions: what is happening (metrics),
what was said (logs), where the time went (traces), and who changed it (audit and
Git).

Components and rough budgets:

- Prometheus, node-exporter, kube-state-metrics: about 600 MiB, 7 days.
- Grafana: about 200 MiB.
- Loki plus Alloy or Promtail: about 300 MiB, 3 days.
- Tempo plus the OpenTelemetry collector: about 350 MiB, 1 day.
- Alertmanager: about 60 MiB, optional.

The `observability/install.sh` script installs the `minimal`, `logs`, `traces`,
or `full` profile. The full profile does not fit next to the whole A1–A7 lab on a
6 GiB cluster.

Applications export OTLP/HTTP to the collector at port **4318**. The collector
forwards traces to Tempo. Each structured log line carries the same `trace_id`,
so a Grafana trace can be matched to a log line, and back.

Alertmanager routes symptoms, not causes: pod crash loop, pod not ready, target
down, disk filling. One receiver is an in-cluster webhook; it was tested with a
synthetic `LabWebhookTest` alert and a real `PodNotReady`.

The models stay on the host GPU and are never deployed into this namespace.
