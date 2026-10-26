---
id: doc-14
title: Helm charts, releases, and rollback
section: "Concepts > Packaging > Helm"
corpus_version: 2026-10-26.1
source:
  kind: authored
  snapshot: 2026-10-26
  based_on:
    - docs/runbooks.md#h1
---

A **chart** is a directory of templates plus default values. A **release** is one
installed instance of a chart in a namespace. Helm renders the templates against
the values and sends the result to the API server; after that, Kubernetes owns
the objects and Helm only records the revision.

The H1 exercise installs `bitnami/nginx` as release `web` in namespace
`helm-lab`, with three replicas and a ClusterIP Service, then upgrades to four
replicas, prints `helm history`, and rolls back.

Rollback takes a revision number. `helm rollback web 1` means revision 1, the
first install, **not** "one step back". Without a number it returns to the
previous revision. `--reuse-values` silently keeps settings from the old
release; an explicit values file is easier to audit.

Before applying anything, `helm template` renders locally and `helm lint` checks
the chart. `helm diff upgrade` shows a plan but needs a plugin.

Helm does not replace the manifests in this repo. The lab uses plain YAML for the
exercises because the point is to see the objects, and Helm for the install,
upgrade, and rollback drill.
