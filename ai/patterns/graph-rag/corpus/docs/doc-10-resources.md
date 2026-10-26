---
id: doc-10
title: Requests, limits, QoS, and autoscaling
section: "Concepts > Workloads > Resources"
corpus_version: 2026-10-26.1
source:
  kind: authored
  snapshot: 2026-10-26
  based_on:
    - manifests/a6/web.yaml
    - manifests/a7/postgres.yaml
    - ai/patterns/graph-rag/k8s/hpa.yaml
---

A **request** is what the scheduler reserves on a node. A **limit** is the
ceiling the kernel enforces. Memory above the limit ends in an OOM kill; CPU
above the limit is throttled.

The three QoS classes follow from those numbers:

- **Guaranteed**: every container sets requests equal to limits.
- **Burstable**: some requests are lower than limits.
- **BestEffort**: no requests or limits at all.

The lab Pods are Burstable on purpose. A6 requests `cpu: 25m` and `memory: 32Mi`
with a `memory: 128Mi` limit; PostgreSQL requests `50m` / `128Mi` with a `512Mi`
limit. Small requests keep the 6 GiB minikube usable; limits stop one container
from taking the node.

A HorizontalPodAutoscaler scales replicas from a metric, normally CPU from
metrics-server. `cluster-create.sh` enables metrics-server on minikube. An HPA
needs requests to calculate utilisation, and it does nothing useful for a
Deployment whose Pods cannot start quickly.
