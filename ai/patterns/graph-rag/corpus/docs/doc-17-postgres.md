---
id: doc-17
title: PostgreSQL in the cluster
section: "Concepts > Data > PostgreSQL"
corpus_version: 2026-10-26.1
source:
  kind: authored
  snapshot: 2026-10-26
  based_on:
    - manifests/a7/postgres.yaml
    - docs/runbooks.md#a7
---

The lab database is `postgres:16-alpine`, deployed as a one-replica Deployment
with a ClusterIP Service named `postgres` on port 5432. Other Pods in the
namespace reach it by that name.

Configuration arrives through `envFrom.secretRef: postgres-credentials`, which
sets `POSTGRES_DB=lab`, `POSTGRES_USER=lab`, and a demo password. The password is
a demo value; a real deployment creates the Secret outside Git.

`PGDATA` points at `/var/lib/postgresql/data/pgdata` inside the claim, a
subdirectory rather than the volume root, so `initdb` is not confused by
`lost+found`.

Both probes are `pg_isready -U lab -d lab`: readiness every 5 seconds after 5
seconds, liveness every 15 seconds after 30. `pg_isready` checks that the server
accepts connections; it does not run a query.

The Deployment strategy is `Recreate`, because the old Pod must release the
`ReadWriteOnce` claim before the new one starts. Backups are taken with
`pg_dump -U lab lab`, which produces a logical dump; a physical backup is a
different exercise. Deleting the PVC deletes the data.
