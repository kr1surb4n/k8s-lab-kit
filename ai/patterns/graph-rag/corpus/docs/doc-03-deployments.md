---
id: doc-03
title: Deployments own ReplicaSets, ReplicaSets own Pods
section: "Concepts > Workloads > Deployments"
corpus_version: 2026-10-26.1
source:
  kind: authored
  snapshot: 2026-10-26
  based_on:
    - manifests/a1/web.yaml
    - manifests/a6/web.yaml
    - docs/runbooks.md#a6
---

A Deployment does not create Pods directly. It creates a ReplicaSet for the
current pod template, and that ReplicaSet creates the Pods. Changing the template
(a new image, a new environment variable) produces a new ReplicaSet; the old one
is scaled down only after enough new Pods are ready.

The `.spec.selector` of a Deployment is immutable. A label change on the selector
requires deleting and recreating the Deployment, which is why the lab manifests
use the stable label `app.kubernetes.io/name: web`.

Exercise A6 runs three replicas of `nginx:1.27-alpine` with
`revisionHistoryLimit: 5`, so five old ReplicaSets remain available for
`kubectl rollout undo`. Scaling is done with `kubectl scale deploy/web
--replicas=N`, or through `scripts/lab-scale.sh --delta 1` and `--delta -1`.

The Deployment, not the Pod, is the unit the lab manages: `lab-up.sh` applies it,
`lab-down.sh` deletes it, and `lab-status.sh` reports its ready replicas.
