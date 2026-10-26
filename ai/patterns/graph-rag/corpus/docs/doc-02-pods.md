---
id: doc-02
title: Pods, shared network namespaces, and init containers
section: "Concepts > Pods > Lifecycle"
corpus_version: 2026-10-26.1
source:
  kind: authored
  snapshot: 2026-10-26
  based_on:
    - docs/runbooks.md#a3
    - docs/runbooks.md#a7
    - manifests/a7/app.yaml
---

Containers inside one Pod share a network namespace. They reach each other over
`127.0.0.1`, which is why the nginx container in exercise A7 can forward PHP
requests to `fastcgi_pass 127.0.0.1:9000` and reach the php-fpm container beside
it. No Service sits between the two.

Containers in a Pod can also share volumes. A7 mounts the same hostPath at
`/var/www/html` in both containers, so nginx and php-fpm always read the same
code and the same SQLite file.

An **init container** runs before the application containers and must exit
successfully. A3 uses one to render `env.txt` and `index.html` from the
environment it received. A7 uses one to wait for PostgreSQL with `nc -z postgres
5432` and then fix ownership of the writable folders.

A Pod managed by a Deployment is replaceable: deleting it causes the ReplicaSet
to create another. The Pod object is not edited in place when a ConfigMap
changes; only mounted volume files eventually change, and environment variables
stay frozen for the life of the container.
