---
id: doc-15
title: The seven exercises and what each one proves
section: "Lab > Exercises A1–A7"
corpus_version: 2026-10-26.1
source:
  kind: authored
  snapshot: 2026-10-26
  based_on:
    - docs/runbooks.md
    - docs/coverage-matrix.md
---

The core lab is seven nginx exercises. They build on each other and share the
namespace `k8s-lab` and the scripts in `scripts/`.

| Exercise | Mechanism | What it proves |
|---|---|---|
| A1 | hostPath `Directory` | host files reach the container; edits need no restart |
| A2 | ConfigMap directory mount | ConfigMap edits propagate as files, not as env vars |
| A3 | `env`, `envFrom`, `fieldRef` | explicit env beats envFrom; values freeze at container start |
| A4 | `kubectl port-forward --address 0.0.0.0` | a LAN client reaches the app; LoadBalancer does not do it on minikube |
| A5 | Secret mounted as a file | basic auth works; base64 is not encryption |
| A6 | Deployment, 3 replicas, LoadBalancer | scale, rolling update, rollback, and the readiness-probe drill |
| A7 | nginx + php-fpm + PostgreSQL + SQLite | a three-tier stack with two storage models |

A1 and A7 depend on a hostPath mount, which is why `lab-up.sh` accepts
`--mount`. A2 and A5 mount ConfigMaps as directories, so edits propagate. A5 and
A7 both use a Secret: one for an htpasswd file, one for the database password.

Only A7 combines a Deployment, a Service, a Secret, a PersistentVolumeClaim, and
a hostPath in one exercise. That makes it the document most golden questions
about relations point at.
