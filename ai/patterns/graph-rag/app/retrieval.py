"""Hybrid retrieval, graph expansion, and answer generation with citations."""
from __future__ import annotations

import json
import logging
import re
import secrets
import time
from typing import Any

import psycopg

from .config import Settings
from .db import connect, vector_literal
from .llm import OllamaClient, StubEmbedder

LOGGER = logging.getLogger("graphrag")
REFUSAL = "The corpus does not contain enough information to answer this question."
CITATION_RE = re.compile(r"\[([^\[\]\s]+#[^\[\]\s]+)\]")
RRF_K = 60

ANSWER_SYSTEM = (
    "You answer questions about documents. Use only the provided context. "
    "Never use outside knowledge and never invent a citation."
)

ANSWER_TEMPLATE = """Answer the question using only the context below.

Rules:
- Cite every factual claim with the chunk id in square brackets, for example [doc-01#c0001].
- Use only chunk ids that appear in the context.
- If the context does not answer the question, reply exactly:
  {refusal}
- Keep the answer short and direct.

Context:
{context}

Question: {question}
"""


# Turn a corpus argument into the list of corpora to search.
def corpora_list(value: str | list[str] | None) -> list[str]:
    if value is None or value == "all":
        return ["lab", "notes", "papers"]
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return list(value)


# Run vector search over chunks and return rows with cosine scores.
def vector_search(
    conn: psycopg.Connection,
    query_vector: list[float],
    corpora: list[str],
    limit: int,
) -> list[dict[str, Any]]:
    literal = vector_literal(query_vector)
    rows = conn.execute(
        """
        SELECT c.id, c.document_id, d.title, d.path, c.text,
               c.start_offset, c.end_offset, c.page_start, c.page_end,
               1 - (e.vector <=> %s::vector) AS score
        FROM embeddings e
        JOIN chunks c ON c.id = e.chunk_id
        JOIN documents d ON d.id = c.document_id
        WHERE d.corpus = ANY(%s)
        ORDER BY e.vector <=> %s::vector
        LIMIT %s
        """,
        (literal, corpora, literal, limit),
    ).fetchall()
    return [_row(row) for row in rows]


# Run Postgres full-text search and return rows with lexical scores.
def lexical_search(
    conn: psycopg.Connection,
    query: str,
    corpora: list[str],
    limit: int,
) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT c.id, c.document_id, d.title, d.path, c.text,
               c.start_offset, c.end_offset, c.page_start, c.page_end,
               ts_rank_cd(c.tsv, websearch_to_tsquery('english', %s)) AS score
        FROM chunks c
        JOIN documents d ON d.id = c.document_id
        WHERE c.tsv @@ websearch_to_tsquery('english', %s)
          AND d.corpus = ANY(%s)
        ORDER BY score DESC
        LIMIT %s
        """,
        (query, query, corpora, limit),
    ).fetchall()
    return [_row(row) for row in rows]


# Convert a database row into a chunk dictionary.
def _row(row) -> dict[str, Any]:
    return {
        "chunk_id": row[0],
        "doc_id": row[1],
        "title": row[2],
        "path": row[3],
        "text": row[4],
        "start": row[5],
        "end": row[6],
        "page_start": row[7],
        "page_end": row[8],
        "score": float(row[9] or 0.0),
        "vector_score": 0.0,
        "lexical_score": 0.0,
    }


# Fuse the two ranked lists with reciprocal-rank fusion.
def rrf_fuse(
    vector_rows: list[dict[str, Any]],
    lexical_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    fused: dict[str, dict[str, Any]] = {}
    for rank, row in enumerate(vector_rows, start=1):
        item = fused.setdefault(row["chunk_id"], dict(row))
        item["vector_score"] = row["score"]
        item["rrf"] = item.get("rrf", 0.0) + 1.0 / (RRF_K + rank)
    for rank, row in enumerate(lexical_rows, start=1):
        item = fused.setdefault(row["chunk_id"], dict(row))
        item["lexical_score"] = row["score"]
        item["rrf"] = item.get("rrf", 0.0) + 1.0 / (RRF_K + rank)
    return sorted(fused.values(), key=lambda item: item["rrf"], reverse=True)


# Return graph edges attached to the retrieved documents, best first.
def graph_context(
    conn: psycopg.Connection,
    document_ids: list[str],
    limit: int = 30,
    query: str = "",
) -> list[dict[str, Any]]:
    if not document_ids:
        return []
    rows = conn.execute(
        """
        SELECT g.id, g.kind, g.arity, g.document_id, en.role, n.name, en.position
        FROM edges g
        JOIN edge_nodes en ON en.edge_id = g.id
        JOIN nodes n ON n.id = en.node_id
        WHERE g.document_id = ANY(%s)
        ORDER BY g.id, en.position
        LIMIT %s
        """,
        (document_ids, limit * 20),
    ).fetchall()

    rank_by_doc = {doc_id: rank for rank, doc_id in enumerate(document_ids)}
    query_tokens = {token.casefold() for token in re.findall(r"[\wąćęłńóśźż]+", query)}
    edges: dict[str, dict[str, Any]] = {}
    for edge_id, kind, arity, document_id, role, name, position in rows:
        edge = edges.setdefault(
            edge_id,
            {
                "id": edge_id,
                "relation": kind,
                "arity": arity,
                "document_id": document_id,
                "doc_rank": rank_by_doc.get(document_id, 99),
                "members": [],
                "roles": {},
            },
        )
        edge["members"].append(name)
        edge["roles"].setdefault(role, name)

    # Prefer edges from the highest-ranked documents and edges whose member
    # names overlap the question. This keeps the path focused on the answer.
    def edge_key(edge: dict[str, Any]) -> tuple:
        overlap = sum(
            1
            for member in edge["members"]
            if any(token in member.casefold() for token in query_tokens)
        )
        return (overlap > 0, -edge["doc_rank"], -edge["arity"], edge["relation"])

    result = []
    for edge in sorted(edges.values(), key=edge_key, reverse=True)[:limit]:
        if edge["arity"] >= 3:
            result.append(
                {
                    "relation": edge["relation"],
                    "members": edge["members"],
                    "document_id": edge["document_id"],
                    "hop": 1,
                }
            )
        else:
            result.append(
                {
                    "source": edge["roles"].get("source", edge["members"][0]),
                    "relation": edge["relation"],
                    "target": edge["roles"].get("target", edge["members"][-1]),
                    "document_id": edge["document_id"],
                    "hop": 1,
                }
            )
    return result


# Retrieve and fuse chunks for a query, then attach the graph context.
def search(
    settings: Settings,
    dsn: str,
    query: str,
    corpus: str | None = None,
    k: int = 8,
    stub: bool = False,
    with_graph: bool = True,
) -> dict[str, Any]:
    corpora = corpora_list(corpus)
    embedder = StubEmbedder() if stub else OllamaClient(settings.ollama_url)
    started = time.time()
    with connect(dsn) as conn:
        if stub:
            query_vector = embedder.embed([query])[0]
        else:
            query_vector = embedder.embed([query], settings.embed_model)[0]
        vector_rows = vector_search(conn, query_vector, corpora, settings.vector_top_k)
        lexical_rows = lexical_search(
            conn, query, corpora, settings.lexical_top_k
        )
        fused = rrf_fuse(vector_rows, lexical_rows)
        top = fused[:k]

        document_ids = list(dict.fromkeys(item["doc_id"] for item in top))[:5]
        graph_path = (
            graph_context(conn, document_ids, query=query) if with_graph else []
        )

    return {
        "query": query,
        "corpora": corpora,
        "chunks": [
            {
                "chunk_id": item["chunk_id"],
                "doc_id": item["doc_id"],
                "title": item["title"],
                "path": item["path"],
                "page_start": item["page_start"],
                "page_end": item["page_end"],
                "text": item["text"],
                "start": item["start"],
                "end": item["end"],
                "rrf": round(item["rrf"], 6),
                "vector_score": round(item["vector_score"], 6),
                "lexical_score": round(item["lexical_score"], 6),
            }
            for item in top
        ],
        "graph_path": graph_path,
        "embed_model": "stub-hash-1024" if stub else settings.embed_model,
        "latency_ms": int((time.time() - started) * 1000),
    }


# Build the context block sent to the generator.
def build_context(chunks: list[dict[str, Any]], max_chars: int = 12000) -> str:
    parts = []
    used = 0
    for chunk in chunks:
        block = f"[{chunk['chunk_id']}] ({chunk['title']})\n{chunk['text']}"
        if used + len(block) > max_chars:
            break
        parts.append(block)
        used += len(block)
    return "\n\n".join(parts)


# Answer a question with retrieval, a generator, and citation guardrails.
def answer(
    settings: Settings,
    dsn: str,
    question: str,
    corpus: str | None = None,
    top_k: int | None = None,
    stub: bool = False,
) -> dict[str, Any]:
    top_k = top_k or settings.answer_top_k
    trace_id = secrets.token_hex(16)
    started = time.time()
    retrieved = search(
        settings, dsn, question, corpus=corpus, k=top_k, stub=stub, with_graph=True
    )
    chunks = retrieved["chunks"]
    top_score = max((chunk["vector_score"] for chunk in chunks), default=0.0)
    has_lexical = any(chunk["lexical_score"] > 0 for chunk in chunks)

    # A guardrail: refuse when retrieval found nothing convincing.
    if not chunks or (top_score < 0.20 and not has_lexical):
        response = {
            "answer": REFUSAL,
            "citations": [],
            "graph_path": [],
            "chunks": chunks,
            "scores": {"top_vector": top_score, "top_rrf": 0.0},
            "trace_id": trace_id,
            "prompt_version": "p1",
            "model_version": "stub-hash-1024" if stub else settings.generate_model,
            "latency_ms": int((time.time() - started) * 1000),
            "refused": True,
        }
        _log(response, question)
        return response

    context = build_context(chunks)
    if stub:
        text = " ".join(chunk["text"] for chunk in chunks[:3])[:800]
        text = f"{text} [{chunks[0]['chunk_id']}]"
    else:
        client = OllamaClient(settings.ollama_url)
        prompt = ANSWER_TEMPLATE.format(
            refusal=REFUSAL, context=context, question=question
        )
        text = client.chat(
            prompt,
            settings.generate_model,
            system=ANSWER_SYSTEM,
            temperature=0.1,
            num_predict=500,
            num_ctx=8192,
        ).strip()

    # Only retrieved chunk ids may appear in citations.
    retrieved_ids = {chunk["chunk_id"] for chunk in chunks}
    cited_ids = [match for match in CITATION_RE.findall(text) if match in retrieved_ids]
    citations = []
    for chunk_id in dict.fromkeys(cited_ids):
        chunk = next(item for item in chunks if item["chunk_id"] == chunk_id)
        citations.append(
            {
                "doc_id": chunk["doc_id"],
                "chunk_id": chunk["chunk_id"],
                "title": chunk["title"],
                "path": chunk["path"],
                "page_start": chunk["page_start"],
                "page_end": chunk["page_end"],
                "span": [chunk["start"], chunk["end"]],
            }
        )

    refused = REFUSAL.lower() in text.lower()
    response = {
        "answer": text,
        "citations": citations,
        "graph_path": [] if refused else retrieved["graph_path"],
        "chunks": chunks,
        "scores": {
            "top_vector": top_score,
            "top_rrf": chunks[0]["rrf"] if chunks else 0.0,
        },
        "trace_id": trace_id,
        "prompt_version": "p1",
        "model_version": "stub-hash-1024" if stub else settings.generate_model,
        "latency_ms": int((time.time() - started) * 1000),
        "refused": refused,
    }
    _log(response, question)
    return response


# Write one structured log line with the same trace id as the response.
def _log(response: dict[str, Any], question: str) -> None:
    LOGGER.info(
        json.dumps(
            {
                "event": "query",
                "trace_id": response["trace_id"],
                "question": question,
                "citations": len(response["citations"]),
                "graph_path": len(response["graph_path"]),
                "latency_ms": response["latency_ms"],
                "refused": response["refused"],
                "model": response["model_version"],
                "prompt_version": response["prompt_version"],
            },
            ensure_ascii=False,
        )
    )
