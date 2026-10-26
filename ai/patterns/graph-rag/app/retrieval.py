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
from .rerank import rerank_chunks
from .telemetry import configure_telemetry, current_trace_id, span

LOGGER = logging.getLogger("graphrag")
REFUSAL = "The corpus does not contain enough information to answer this question."
RRF_K = 60

ANSWER_SYSTEM = (
    "You answer questions about documents. Use only the provided context. "
    "Never use outside knowledge and never invent a citation."
)

ANSWER_TEMPLATE = """Answer the question using only the context below.

Rules:
- Cite every factual claim with the exact chunk id that starts the context block, in square brackets.
- Copy the whole id, including the document prefix and the #cNNNN suffix. Never shorten, invent, or use an example id.
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
    # HNSW filters after the index scan. A small corpus can lose every
    # candidate when the global nearest neighbours belong to a larger corpus.
    # The local dataset is small, so force an exact scan for correctness.
    conn.execute("SET LOCAL enable_indexscan = off")
    conn.execute("SET LOCAL enable_bitmapscan = off")
    try:
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
    finally:
        conn.execute("RESET enable_indexscan")
        conn.execute("RESET enable_bitmapscan")
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


# Split the question into lower-case tokens for graph ranking.
def _query_tokens(query: str) -> set[str]:
    return {token.casefold() for token in re.findall(r"[\wąćęłńóśźż]+", query)}


# Collect database rows into edge dictionaries, keeping the node ids for hops.
def _collect_edges(rows, rank_by_doc: dict[str, int]) -> dict[str, dict[str, Any]]:
    edges: dict[str, dict[str, Any]] = {}
    for edge_id, kind, arity, document_id, role, node_id, name, _position in rows:
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
                "node_ids": {},
            },
        )
        edge["members"].append(name)
        edge["roles"].setdefault(role, name)
        edge["node_ids"].setdefault(node_id, name)
    return edges


# Score an edge by document rank, question overlap, and relation size.
def _edge_key(edge: dict[str, Any], query_tokens: set[str]) -> tuple:
    overlap = sum(
        1
        for member in edge["members"]
        if any(token in member.casefold() for token in query_tokens)
    )
    return (overlap > 0, -edge["doc_rank"], -edge["arity"], edge["relation"])


# Convert an internal edge into the public graph-path shape.
def _graph_entry(edge: dict[str, Any], hop: int, via: str | None = None) -> dict[str, Any]:
    if edge["arity"] >= 3:
        entry = {
            "relation": edge["relation"],
            "members": edge["members"],
            "document_id": edge["document_id"],
            "hop": hop,
        }
    else:
        entry = {
            "source": edge["roles"].get("source", edge["members"][0]),
            "relation": edge["relation"],
            "target": edge["roles"].get("target", edge["members"][-1]),
            "document_id": edge["document_id"],
            "hop": hop,
        }
    if via:
        entry["via"] = via
    return entry


# Fetch one-hop edges from the retrieved documents.
def _first_hop(conn: psycopg.Connection, document_ids: list[str], limit: int) -> list:
    return conn.execute(
        """
        SELECT g.id, g.kind, g.arity, g.document_id, en.role, en.node_id, n.name, en.position
        FROM edges g
        JOIN edge_nodes en ON en.edge_id = g.id
        JOIN nodes n ON n.id = en.node_id
        WHERE g.document_id = ANY(%s)
        ORDER BY g.id, en.position
        LIMIT %s
        """,
        (document_ids, limit * 20),
    ).fetchall()


# Fetch edges from other documents that share a bridge node with the first hop.
def _second_hop(
    conn: psycopg.Connection,
    bridge_ids: list[str],
    document_ids: list[str],
    limit: int,
) -> list:
    if not bridge_ids:
        return []
    return conn.execute(
        """
        SELECT g.id, g.kind, g.arity, g.document_id, en.role, en.node_id, n.name, en.position
        FROM edges g
        JOIN edge_nodes en ON en.edge_id = g.id
        JOIN nodes n ON n.id = en.node_id
        WHERE en.node_id = ANY(%s)
          AND NOT (g.document_id = ANY(%s))
        ORDER BY g.id, en.position
        LIMIT %s
        """,
        (bridge_ids, document_ids, limit * 20),
    ).fetchall()


# Return graph edges attached to the retrieved documents, best first.
def graph_context(
    conn: psycopg.Connection,
    document_ids: list[str],
    limit: int = 30,
    query: str = "",
    hops: int = 1,
) -> list[dict[str, Any]]:
    if not document_ids or hops < 1:
        return []
    hops = min(hops, 2)
    rank_by_doc = {doc_id: rank for rank, doc_id in enumerate(document_ids)}
    tokens = _query_tokens(query)
    edges = _collect_edges(_first_hop(conn, document_ids, limit), rank_by_doc)
    ranked = sorted(edges.values(), key=lambda edge: _edge_key(edge, tokens), reverse=True)
    first = [edge for edge in ranked if len(edge["members"]) >= 2][:limit]
    result = [_graph_entry(edge, 1) for edge in first]

    # A second hop starts at entities shared with the first-hop documents.
    if hops >= 2 and first:
        bridge_names: dict[str, str] = {}
        for edge in first:
            for node_id, name in edge["node_ids"].items():
                bridge_names.setdefault(node_id, name)
        # Keep the bridge set small; the highest-ranked edges are the anchors.
        bridge_ids = list(bridge_names)[:40]
        bridge_rank = {node_id: rank for rank, node_id in enumerate(bridge_ids)}
        second_by_id = _collect_edges(
            _second_hop(conn, bridge_ids, document_ids, limit), rank_by_doc
        )
        second_edges = sorted(
            second_by_id.values(),
            key=lambda edge: _edge_key(edge, tokens),
            reverse=True,
        )
        seen = {edge["id"] for edge in first}
        added = 0
        second_limit = max(3, limit // 3)
        for edge in second_edges:
            if edge["id"] in seen or len(edge["members"]) < 2:
                continue
            # Prefer the best-ranked shared entity as the explainable bridge.
            shared = [node_id for node_id in edge["node_ids"] if node_id in bridge_rank]
            via = bridge_names[min(shared, key=bridge_rank.get)] if shared else None
            result.append(_graph_entry(edge, 2, via=via))
            seen.add(edge["id"])
            added += 1
            if added >= second_limit:
                break
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
    graph_hops: int | None = None,
    rerank: bool | None = None,
) -> dict[str, Any]:
    configure_telemetry(settings)
    hops = 2 if (graph_hops or settings.graph_hops) >= 2 else 1
    with span(
        "graphrag.search",
        {
            "graphrag.corpus": ",".join(corpora_list(corpus)),
            "graphrag.k": k,
            "graphrag.graph_hops": hops if with_graph else 0,
            "graphrag.with_graph": with_graph,
            "graphrag.stub": stub,
        },
    ) as current:
        result = _search_impl(
            settings,
            dsn,
            query,
            corpus=corpus,
            k=k,
            stub=stub,
            with_graph=with_graph,
            graph_hops=graph_hops,
            rerank=rerank,
        )
        result["trace_id"] = current_trace_id()
        if current is not None:
            current.set_attribute("graphrag.chunks", len(result["chunks"]))
            current.set_attribute("graphrag.graph_path", len(result["graph_path"]))
            current.set_attribute("graphrag.rerank", result["rerank"])
            current.set_attribute("graphrag.latency_ms", result["latency_ms"])
        return result


# Implementation behind the traced search wrapper.
def _search_impl(
    settings: Settings,
    dsn: str,
    query: str,
    corpus: str | None = None,
    k: int = 8,
    stub: bool = False,
    with_graph: bool = True,
    graph_hops: int | None = None,
    rerank: bool | None = None,
) -> dict[str, Any]:
    corpora = corpora_list(corpus)
    graph_hops = 2 if (graph_hops or settings.graph_hops) >= 2 else 1
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
        rerank_enabled = settings.rerank if rerank is None else rerank
        reranked = False
        # Rerank before selecting the final top k; the graph follows that order.
        if rerank_enabled and not stub and len(fused) > 1:
            rerank_model = settings.rerank_model or settings.generate_model
            fused, reranked = rerank_chunks(
                fused,
                query,
                OllamaClient(settings.ollama_url),
                rerank_model,
                max_candidates=settings.rerank_candidates,
            )
        top = fused[:k]

        document_ids = list(dict.fromkeys(item["doc_id"] for item in top))[:5]
        graph_path = (
            graph_context(conn, document_ids, query=query, hops=graph_hops)
            if with_graph
            else []
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
        "graph_hops": graph_hops if with_graph else 0,
        "rerank": reranked,
        "rerank_model": (
            (settings.rerank_model or settings.generate_model) if reranked else ""
        ),
        "embed_model": "stub-hash-1024" if stub else settings.embed_model,
        "latency_ms": int((time.time() - started) * 1000),
    }


# Return retrieved chunk ids that appear in the answer, in citation order.
def find_citations(text: str, retrieved_ids: set[str]) -> list[str]:
    # Match whole ids as strings: notes paths contain spaces, so a
    # whitespace-delimited regex would truncate the id.
    return sorted(
        {chunk_id for chunk_id in retrieved_ids if chunk_id in text},
        key=text.find,
    )


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
    graph_hops: int | None = None,
    rerank: bool | None = None,
) -> dict[str, Any]:
    configure_telemetry(settings)
    effective_top_k = top_k or settings.answer_top_k
    with span(
        "graphrag.answer",
        {
            "graphrag.corpus": corpus or "",
            "graphrag.top_k": effective_top_k,
            "graphrag.question_length": len(question),
            "graphrag.stub": stub,
        },
    ) as current:
        response = _answer_impl(
            settings,
            dsn,
            question,
            corpus=corpus,
            top_k=top_k,
            stub=stub,
            graph_hops=graph_hops,
            rerank=rerank,
        )
        if current is not None:
            current.set_attribute("graphrag.citations", len(response["citations"]))
            current.set_attribute("graphrag.graph_path", len(response["graph_path"]))
            current.set_attribute("graphrag.refused", response["refused"])
            current.set_attribute("graphrag.rerank", response["rerank"])
            current.set_attribute("graphrag.latency_ms", response["latency_ms"])
        return response


# Implementation behind the traced answer wrapper.
def _answer_impl(
    settings: Settings,
    dsn: str,
    question: str,
    corpus: str | None = None,
    top_k: int | None = None,
    stub: bool = False,
    graph_hops: int | None = None,
    rerank: bool | None = None,
) -> dict[str, Any]:
    top_k = top_k or settings.answer_top_k
    graph_hops = graph_hops or settings.graph_hops
    trace_id = current_trace_id() or secrets.token_hex(16)
    started = time.time()
    retrieved = search(
        settings,
        dsn,
        question,
        corpus=corpus,
        k=top_k,
        stub=stub,
        with_graph=True,
        graph_hops=graph_hops,
        rerank=rerank,
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
            "graph_hops": retrieved["graph_hops"],
            "rerank": retrieved["rerank"],
            "rerank_model": retrieved["rerank_model"],
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
    cited_ids = find_citations(text, retrieved_ids)
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
        "graph_hops": retrieved["graph_hops"],
        "rerank": retrieved["rerank"],
        "rerank_model": retrieved["rerank_model"],
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
