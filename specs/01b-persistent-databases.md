# Spec: Persistent Databases — Postgres Access for Other Projects

## Problem Statement
The lab uses two Postgres databases (eval on 5433, private on 5434) via Docker Compose with named volumes. The user wants to:
1. Confirm persistent storage is used
2. Connect to these databases from other projects/tools
3. Use them as general-purpose Postgres instances

## Current State

| Database | Port | Volume | Corpora | Compose Service |
|---|---|---|---|---|
| `graphrag` (eval) | 5433 | `graphrag-pgdata` | `lab` | `postgres` |
| `graphrag_private` | 5434 | `graphrag-private-pgdata` | `notes`, `papers` | `postgres-private` (profile `private`) |

Both use `pgvector/pgvector:pg16` image with `POSTGRES_USER=graphrag`, `POSTGRES_PASSWORD=graphrag-dev-only` (dev only).

Volumes are **named volumes** — they survive `docker compose down` and `make db-down`. Only `docker compose down -v` or manual volume removal deletes data.

## Connection Details (Local)

```bash
# Eval database
psql "postgresql://graphrag:graphrag-dev-only@localhost:5433/graphrag"

# Private database
psql "postgresql://graphrag:graphrag-private-dev-only@localhost:5434/graphrag_private"

# Or via make targets
make db-shell          # eval
make private-db-shell  # private
```

## Requirements for External Project Use
1. **Stable credentials** — override dev-only passwords via environment
2. **Network accessibility** — expose on `0.0.0.0` or specific interface
3. **Separate databases/schemas** — don't pollute the lab corpora
4. **Backup/restore** — documented procedure
5. **Connection pooling** — optional PgBouncer for high-churn apps

## Implementation Steps

### 1. Make Credentials Configurable (Already Supported)
```bash
# In .env or shell
export GRAPHRAG_DB_PASSWORD="strong-password"
export GRAPHRAG_PRIVATE_DB_PASSWORD="strong-password-2"
make db-up migrate
```

### 2. Create Additional Databases/Schemas for Other Projects
```sql
-- Connect as superuser (graphrag) and create:
CREATE DATABASE my_other_project;
CREATE USER my_app WITH PASSWORD '...';
GRANT ALL PRIVILEGES ON DATABASE my_other_project TO my_app;

-- Or use schemas inside graphrag:
CREATE SCHEMA my_project;
GRANT USAGE ON SCHEMA my_project TO graphrag;
```

### 3. Document Connection Strings for Common Tools
| Tool | Connection String |
|---|---|
| `psql` | `postgresql://user:pass@localhost:5433/dbname` |
| Python `psycopg` | `psycopg.connect("postgresql://user:pass@localhost:5433/dbname")` |
| DBeaver/DataGrip | Host: localhost, Port: 5433, DB: graphrag, User: graphrag |
| `pg_dump` | `pg_dump -h localhost -p 5433 -U graphrag graphrag > dump.sql` |

### 4. Add Backup/Restore Procedures
```bash
# Backup (filtered to remove \restrict token)
docker compose exec -T postgres pg_dump -U graphrag graphrag \
  | grep -v -E '^\(un\)?restrict ' > backup-$(date +%F).sql

# Restore
docker compose exec -T postgres psql -U graphrag graphrag < backup-2026-10-26.sql
```

### 5. Optional: PgBouncer for Connection Pooling
Add to `compose.yaml` if needed:
```yaml
pgbouncer:
  image: edoburu/pgbouncer:latest
  environment:
    DATABASES_HOST: postgres
    DATABASES_PORT: "5432"
    DATABASES_DBNAME: graphrag
    DATABASES_USER: graphrag
    DATABASES_PASSWORD: ${GRAPHRAG_DB_PASSWORD}
    POOL_MODE: transaction
    MAX_CLIENT_CONN: 100
    DEFAULT_POOL_SIZE: 20
  ports:
    - "6432:6432"
  depends_on:
    - postgres
```

## Acceptance Criteria
- User can connect to both databases from external tools (DBeaver, psql, Python)
- Data persists across `make db-down && make db-up`
- Custom databases/schemas can be created without breaking lab corpora
- Backup/restore procedure documented and tested
- Credentials are not hardcoded in repo

## References
- `ai/patterns/graph-rag/compose.yaml` — volume and service definitions
- `ai/patterns/graph-rag/db/README.md` — database architecture
- `ai/patterns/graph-rag/db/check_schema.sh` — idempotency proof