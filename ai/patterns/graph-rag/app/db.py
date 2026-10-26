"""Postgres access for documents, chunks, embeddings, and the graph."""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from typing import Any, Iterable

import psycopg

SLUG_RE = re.compile(r"[^a-z0-9]+")


# Connect to Postgres with a short statement timeout for interactive use.
def connect(dsn: str) -> psycopg.Connection:
    return psycopg.connect(dsn, connect_timeout=10)


# Turn a display name into a stable node id component.
def slug(value: str, max_length: int = 80) -> str:
    folded = unicodedata.normalize("NFKD", value)
    ascii_only = folded.encode("ascii", "ignore").decode("ascii").lower()
    cleaned = SLUG_RE.sub("-", ascii_only).strip("-")
    return (cleaned or "unnamed")[:max_length]


# Build a readable but collision-safe node id from name and type.
def node_id(name: str, node_type: str) -> str:
    return f"n:{slug(node_type, 24)}:{slug(name)}"


# Format a float vector as the text literal pgvector understands.
def vector_literal(values: Iterable[float]) -> str:
    return "[" + ",".join(f"{value:.7f}" for value in values) + "]"


# Return the stored content hash for every path in a corpus.
def stored_hashes(conn: psycopg.Connection, corpus: str) -> dict[str, str]:
    rows = conn.execute(
        "SELECT path, sha256 FROM documents WHERE corpus = %s", (corpus,)
    ).fetchall()
    return {path: digest for path, digest in rows}


# Return one document row, or None when it has not been ingested.
def stored_document(conn: psycopg.Connection, document_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT id, sha256, corpus, path FROM documents WHERE id = %s", (document_id,)
    ).fetchone()
    if row is None:
        return None
    return {"id": row[0], "sha256": row[1], "corpus": row[2], "path": row[3]}


# Write one document with its chunks, embeddings, graph rows and provenance.
def store_document(
    conn: psycopg.Connection,
    document: Any,
    chunks: list[Any],
    vectors: list[list[float]],
    extraction: dict[str, Any],
    embed_model: str,
) -> None:
    if len(chunks) != len(vectors):
        raise ValueError("chunk and vector counts differ")

    with conn.transaction():
        conn.execute(
            """
            INSERT INTO documents
                (id, corpus, corpus_version, title, section, path, sha256, source)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)
            ON CONFLICT (id) DO UPDATE SET
                corpus = EXCLUDED.corpus,
                corpus_version = EXCLUDED.corpus_version,
                title = EXCLUDED.title,
                section = EXCLUDED.section,
                path = EXCLUDED.path,
                sha256 = EXCLUDED.sha256,
                source = EXCLUDED.source,
                updated_at = now()
            """,
            (
                document.id,
                document.corpus,
                document.corpus_version,
                document.title,
                document.section,
                document.path,
                document.sha256,
                json.dumps(document.source, ensure_ascii=False, default=str),
            ),
        )

        # Replacing the chunks is cheaper and safer than diffing them.
        conn.execute("DELETE FROM chunks WHERE document_id = %s", (document.id,))
        for chunk, vector in zip(chunks, vectors):
            chunk_id = f"{document.id}#c{chunk.ordinal:04d}"
            conn.execute(
                """
                INSERT INTO chunks
                    (id, document_id, ordinal, text, start_offset, end_offset,
                     content_sha256, page_start, page_end)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    chunk_id,
                    document.id,
                    chunk.ordinal,
                    chunk.text,
                    chunk.start,
                    chunk.end,
                    hashlib.sha256(chunk.text.encode("utf-8")).hexdigest(),
                    chunk.page_start,
                    chunk.page_end,
                ),
            )
            conn.execute(
                """
                INSERT INTO embeddings (chunk_id, model, dim, vector)
                VALUES (%s, %s, %s, %s::vector)
                ON CONFLICT (chunk_id) DO UPDATE SET
                    model = EXCLUDED.model,
                    dim = EXCLUDED.dim,
                    vector = EXCLUDED.vector
                """,
                (chunk_id, embed_model, len(vector), vector_literal(vector)),
            )

        # Graph rows are document-scoped; remove the old ones before writing.
        conn.execute("DELETE FROM edges WHERE document_id = %s", (document.id,))
        conn.execute("DELETE FROM provenance WHERE document_id = %s", (document.id,))

        entities = list(extraction.get("entities", []))
        relations = list(extraction.get("relations", []))
        hyperedges = list(extraction.get("hyperedges", []))

        # One canonical type per name, so edges and nodes agree on the node id.
        type_by_name: dict[str, str] = {}
        for item in entities:
            type_by_name.setdefault(item["name"], item.get("type", "Entity"))
        for relation in relations:
            type_by_name.setdefault(relation["source"], "Entity")
            type_by_name.setdefault(relation["target"], "Entity")
        for hyperedge in hyperedges:
            for member in hyperedge.get("members", []):
                type_by_name.setdefault(member, "Entity")

        for name, node_type in sorted(type_by_name.items()):
            conn.execute(
                """
                INSERT INTO nodes (id, name, type)
                VALUES (%s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name
                """,
                (node_id(name, node_type), name, node_type),
            )

        inserted_edges = []
        for relation in relations:
            members = [relation["source"], relation["target"]]
            inserted_edges.append(
                _insert_edge(
                    conn,
                    document,
                    relation["type"],
                    members,
                    float(relation.get("confidence", 1.0)),
                    ["source", "target"],
                    type_by_name,
                )
            )
        for hyperedge in hyperedges:
            members = list(hyperedge.get("members", []))
            if len(members) < 3:
                continue
            inserted_edges.append(
                _insert_edge(
                    conn,
                    document,
                    hyperedge["relation"],
                    members,
                    float(hyperedge.get("confidence", 1.0)),
                    ["member"] * len(members),
                    type_by_name,
                )
            )

        # Provenance for the document, every chunk, every node, every edge.
        provenance_rows = [
            (
                "document",
                document.id,
                document.id,
                None,
                document.path,
                document.section,
                document.sha256,
                document.corpus_version,
            )
        ]
        for chunk in chunks:
            provenance_rows.append(
                (
                    "chunk",
                    f"{document.id}#c{chunk.ordinal:04d}",
                    document.id,
                    f"{document.id}#c{chunk.ordinal:04d}",
                    document.path,
                    document.section,
                    document.sha256,
                    document.corpus_version,
                )
            )
        for edge_id in inserted_edges:
            provenance_rows.append(
                (
                    "edge",
                    edge_id,
                    document.id,
                    None,
                    document.path,
                    document.section,
                    document.sha256,
                    document.corpus_version,
                )
            )
        for name, node_type in sorted(type_by_name.items()):
            provenance_rows.append(
                (
                    "node",
                    node_id(name, node_type),
                    document.id,
                    None,
                    document.path,
                    document.section,
                    document.sha256,
                    document.corpus_version,
                )
            )
        with conn.cursor() as cursor:
            cursor.executemany(
                """
                INSERT INTO provenance
                    (entity_table, entity_id, document_id, chunk_id, source_path,
                     section, doc_sha256, corpus_version)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (entity_table, entity_id, document_id) DO NOTHING
                """,
                provenance_rows,
            )


# Insert one pairwise edge or hyperedge and its members; return the edge id.
def _insert_edge(
    conn: psycopg.Connection,
    document: Any,
    kind: str,
    members: list[str],
    confidence: float,
    roles: list[str],
    type_by_name: dict[str, str],
) -> str:
    key = f"{document.id}|{kind}|{'|'.join(sorted(members))}"
    edge_id = "e:" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:20]
    conn.execute(
        """
        INSERT INTO edges (id, kind, arity, confidence, document_id)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET
            kind = EXCLUDED.kind,
            arity = EXCLUDED.arity,
            confidence = EXCLUDED.confidence
        """,
        (edge_id, kind, len(members), confidence, document.id),
    )
    for position, (member, role) in enumerate(zip(members, roles), start=1):
        conn.execute(
            """
            INSERT INTO edge_nodes (edge_id, node_id, role, position)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (edge_id, node_id, role) DO UPDATE SET
                position = EXCLUDED.position
            """,
            (edge_id, node_id(member, type_by_name.get(member, "Entity")), role, position),
        )
    return edge_id


# Delete documents of a corpus whose source file no longer exists.
def prune_missing(conn: psycopg.Connection, corpus: str, keep_paths: set[str]) -> list[str]:
    rows = conn.execute(
        "SELECT id, path FROM documents WHERE corpus = %s", (corpus,)
    ).fetchall()
    stale = [(doc_id, path) for doc_id, path in rows if path not in keep_paths]
    if not stale:
        return []
    with conn.transaction():
        for doc_id, _ in stale:
            conn.execute("DELETE FROM documents WHERE id = %s", (doc_id,))
    return [path for _, path in stale]


# Return row counts per corpus for the CLI and the API.
def corpus_stats(conn: psycopg.Connection, corpus: str | None = None) -> list[dict[str, Any]]:
    where = "WHERE d.corpus = %s" if corpus else ""
    params = (corpus,) if corpus else ()
    rows = conn.execute(
        f"""
        SELECT d.corpus,
               count(DISTINCT d.id) AS documents,
               count(DISTINCT c.id) AS chunks,
               count(DISTINCT e.chunk_id) AS embeddings,
               count(DISTINCT g.id) AS edges
        FROM documents d
        LEFT JOIN chunks c ON c.document_id = d.id
        LEFT JOIN embeddings e ON e.chunk_id = c.id
        LEFT JOIN edges g ON g.document_id = d.id
        {where}
        GROUP BY d.corpus
        ORDER BY d.corpus
        """,
        params,
    ).fetchall()
    return [
        {
            "corpus": row[0],
            "documents": row[1],
            "chunks": row[2],
            "embeddings": row[3],
            "edges": row[4],
        }
        for row in rows
    ]
