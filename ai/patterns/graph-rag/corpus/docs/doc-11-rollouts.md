---
id: doc-11
title: Rolling updates, surge, and rollback
section: "Concepts > Workloads > Update strategies"
corpus_version: 2026-10-26.1
source:
  kind: authored
  snapshot: 2026-10-26
  based_on:
    - docs/runbooks.md#a6
    - manifests/a6/web.yaml
---

A Deployment's default strategy is **RollingUpdate**. Two numbers control it:

- `maxSurge: 1` allows one extra Pod above the desired count during the update.
- `maxUnavailable: 0` forbids dropping below the desired count of ready Pods.

A6 combines them with three replicas and a readiness probe, so a new Pod must be
Ready before an old one is removed. That is what makes the update invisible to a
client polling the page.

Every pod-template change creates a new ReplicaSet. `kubectl rollout history
deploy/web` lists revisions, `kubectl rollout undo deploy/web` returns to the
previous one, and `revisionHistoryLimit: 5` keeps five old ReplicaSets.
`scripts/lab-rollout.sh` wraps these commands.

The other strategy is **Recreate**: all old Pods are killed before new ones
start. A7 uses it for the SQLite application and for PostgreSQL because both need
a single writer and the old Pod must release the hostPath or the claim first.

A rollback is not a time machine for data. It swaps the Pod template back; schema
migrations and written rows stay where they are.
