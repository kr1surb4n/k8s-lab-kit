#!/usr/bin/env bash
# Check that the schema applies twice without drift and that a hyperedge
# round-trips through the tables. Requires docker and docker compose.
set -Eeuo pipefail

pattern=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$pattern"

db_user=${GRAPHRAG_DB_USER:-graphrag}
db_name=${GRAPHRAG_DB_NAME:-graphrag}
tmpdir=$(mktemp -d "${TMPDIR:-/tmp}/graph-rag-schema.XXXXXX")
trap 'rm -rf "$tmpdir"' EXIT

# Wait until Postgres accepts connections.
wait_for_db() {
  local attempt
  for attempt in $(seq 1 60); do
    if docker compose exec -T postgres pg_isready -U "$db_user" -d "$db_name" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  printf 'postgres did not become ready\n' >&2
  docker compose logs postgres | tail -30 >&2
  return 1
}

# Dump the schema without ownership or grants, so two runs can be compared.
# pg_dump 16.15 adds a random \restrict token; drop it to keep the dump stable.
dump_schema() {
  docker compose exec -T postgres \
    pg_dump --schema-only --no-owner --no-privileges -U "$db_user" "$db_name" |
    grep -v -E '^\\(un)?restrict '
}

docker compose up -d postgres >/dev/null
wait_for_db

# First application, then the same file again; the dumps must match.
make -s migrate
dump_schema >"$tmpdir/first.sql"
make -s migrate
dump_schema >"$tmpdir/second.sql"

if ! diff -u "$tmpdir/first.sql" "$tmpdir/second.sql"; then
  printf 'FAIL: schema changed on the second migrate\n' >&2
  exit 1
fi

# Apply the hyperedge fixture and roll it back.
docker compose exec -T postgres \
  psql -v ON_ERROR_STOP=1 -q -U "$db_user" -d "$db_name" <db/smoke.sql

# The plan's tables must all exist.
tables=$(docker compose exec -T postgres \
  psql -tA -U "$db_user" -d "$db_name" -c \
  "SELECT count(*) FROM information_schema.tables
    WHERE table_schema = 'public'
      AND table_name IN ('documents','chunks','embeddings','nodes','edges',
                         'edge_nodes','provenance','schema_migrations');")
if [[ $tables != 8 ]]; then
  printf 'FAIL: expected 8 tables, found %s\n' "$tables" >&2
  exit 1
fi

printf 'schema ok: 8 tables, migrate is idempotent, hyperedge round-trip ok\n'
