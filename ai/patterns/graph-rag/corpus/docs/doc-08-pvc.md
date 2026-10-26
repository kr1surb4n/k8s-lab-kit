---
id: doc-08
title: PersistentVolumes, claims, and the Postgres data directory
section: "Concepts > Storage > PersistentVolumeClaim"
corpus_version: 2026-10-26.1
source:
  kind: authored
  snapshot: 2026-10-26
  based_on:
    - docs/runbooks.md#a7
    - manifests/a7/postgres.yaml
---

A **PersistentVolume** is a piece of storage in the cluster. A
**PersistentVolumeClaim** is a Pod's request for storage with a size and an
access mode. A StorageClass provisions the volume when the claim is created.

The claim in A7 is `postgres-data`: 1Gi, access mode `ReadWriteOnce`, class
`standard`. `standard` is minikube's default class; on k3s the usual default is
`local-path`, so the same manifest needs that overlay there. `ReadWriteOnce`
means one node may mount the volume read-write, not that only one Pod may ever
use it.

PostgreSQL sets `PGDATA=/var/lib/postgresql/data/pgdata`, a subdirectory of the
mounted volume. That avoids `initdb` failing on a volume that already contains a
`lost+found` directory.

The data survives deleting and recreating the Pod; that is the point of the
claim. It does not survive deleting the namespace or the claim itself. Because
the database needs a single writer, the Deployment uses the `Recreate` strategy
so the old Pod releases the claim before the new one starts.
