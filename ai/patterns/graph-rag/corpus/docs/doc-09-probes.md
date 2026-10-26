---
id: doc-09
title: Readiness, liveness, and why a probe is not paperwork
section: "Concepts > Workloads > Probes"
corpus_version: 2026-10-26.1
source:
  kind: authored
  snapshot: 2026-10-26
  based_on:
    - docs/runbooks.md#a6
    - manifests/a6/web.yaml
    - manifests/a7/postgres.yaml
---

A **readiness probe** answers "may this container receive traffic?". A failing
probe removes the Pod from the Service endpoints without restarting it. A
**liveness probe** answers "is this container still alive?"; failure restarts
the container. A startup probe exists for slow-starting processes and disables
the other two until it passes.

A6 sets a readiness probe on `GET /` every 3 seconds and a liveness probe every
10 seconds. The Deployment also sets `maxUnavailable: 0`, so a rolling update
waits for a new Pod to become Ready before removing an old one.

Remove the readiness probe and update the image: Kubernetes will send traffic to
containers that are still starting, and the drill in the runbook counts the 5xx
responses. With the probe in place the update is invisible.

A7 uses an `exec` probe, `pg_isready -U lab -d lab`, for both readiness and
liveness on PostgreSQL, and a `tcpSocket` probe on port 9000 for php-fpm. A
`tcpSocket` probe proves a listener exists, not that the application inside is
healthy.
