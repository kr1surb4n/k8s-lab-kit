---
id: doc-16
title: "A7: nginx, php-fpm, PostgreSQL and SQLite in one stack"
section: "Lab > A7 > Three-tier stack"
corpus_version: 2026-10-26.1
source:
  kind: authored
  snapshot: 2026-10-26
  based_on:
    - docs/runbooks.md#a7
    - manifests/a7/app.yaml
    - manifests/a7/postgres.yaml
---

A7 is the only exercise that combines a Deployment, a Service, a Secret, a
PersistentVolumeClaim, and a hostPath.

The **application Pod** holds two containers. nginx serves static files and sends
every `.php` request to `fastcgi_pass 127.0.0.1:9000`, where php-fpm is listening
in the same network namespace. Both mount `/mnt/lab/app` at `/var/www/html`, so
they read the same code and the same SQLite file. An init container waits for
PostgreSQL with `nc -z postgres 5432`, creates `database/database.sqlite`, and
sets the writable folders to uid 82 (`www-data` on Alpine).

The application reads **two databases**:

- **SQLite**, at `/var/www/html/database/database.sqlite`, on the hostPath. A row
  inserted from the host with `sqlite3` appears on the next page load.
- **PostgreSQL**, reached at `DB_HOST=postgres` port 5432, with credentials from
  the `postgres-credentials` Secret. It lives on a 1Gi claim.

The Deployment runs **one replica** with the `Recreate` strategy. SQLite on a
shared filesystem has no reliable multi-writer locking, and PostgreSQL needs a
single writer.
