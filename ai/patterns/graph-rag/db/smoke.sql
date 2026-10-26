-- Prove the schema accepts a real hyperedge without leaving test rows behind.
-- Run inside a transaction; the rollback is part of the check.
BEGIN;

INSERT INTO documents (id, corpus_version, title, section, path, sha256, source)
VALUES ('smoke-doc', 'smoke', 'Smoke document', 'smoke', 'smoke.md', repeat('0', 64), '{}'::jsonb)
ON CONFLICT (id) DO NOTHING;

INSERT INTO nodes (id, name, type) VALUES
    ('smoke-nginx', 'smoke-nginx', 'Component'),
    ('smoke-php', 'smoke-php', 'Component'),
    ('smoke-host', 'smoke-host', 'Volume')
ON CONFLICT (id) DO NOTHING;

INSERT INTO edges (id, kind, arity, document_id)
VALUES ('smoke-edge', 'JOINTLY_SERVE', 3, 'smoke-doc')
ON CONFLICT (id) DO NOTHING;

INSERT INTO edge_nodes (edge_id, node_id, role, position) VALUES
    ('smoke-edge', 'smoke-nginx', 'member', 1),
    ('smoke-edge', 'smoke-php', 'member', 2),
    ('smoke-edge', 'smoke-host', 'member', 3)
ON CONFLICT DO NOTHING;

-- A three-member relation must come back as one edge with three members.
DO $$
DECLARE
    member_count integer;
    member_names text[];
BEGIN
    SELECT cardinality(members), members
      INTO member_count, member_names
      FROM edge_summary
     WHERE id = 'smoke-edge';
    IF member_count IS DISTINCT FROM 3 THEN
        RAISE EXCEPTION 'expected 3 members, got %', member_count;
    END IF;
    IF member_names IS DISTINCT FROM ARRAY['smoke-nginx', 'smoke-php', 'smoke-host'] THEN
        RAISE EXCEPTION 'unexpected member order: %', member_names;
    END IF;
    RAISE NOTICE 'hyperedge ok: %', member_names;
END $$;

ROLLBACK;
