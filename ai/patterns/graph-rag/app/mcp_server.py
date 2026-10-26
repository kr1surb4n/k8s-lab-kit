"""MCP stdio server exposing the local knowledge base to Hermes.

Tools:
  search_knowledge(query, corpus, k)
  ask_knowledge(question, corpus)
  list_corpora()

Only local models and local Postgres are used by this server. However, the MCP
client sees the tool results, so connect it to an agent that runs a local model.
A cloud-hosted agent would send note and paper excerpts to its provider.

Absolute paths are removed from tool results; doc ids and local snippets remain.
"""
from __future__ import annotations

import logging

from mcp.server.mcpserver import MCPServer

from .config import load_settings
from .db import connect, corpus_stats
from .retrieval import answer, search

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

SETTINGS = load_settings()
PRIVATE_DSN = SETTINGS.dsn("private")
EVAL_DSN = SETTINGS.dsn("eval")

mcp = MCPServer("graphrag-local")


# Choose the database that owns a corpus.
def dsn_for(corpus: str) -> str:
    return EVAL_DSN if corpus == "lab" else PRIVATE_DSN


# Search notes, papers, or the lab corpus and return short excerpts.
@mcp.tool()
def search_knowledge(query: str, corpus: str = "notes,papers", k: int = 5) -> dict:
    """Search the local notes and papers. corpus is notes, papers, notes,papers, or lab."""
    k = max(1, min(int(k), 20))
    result = search(SETTINGS, dsn_for(corpus), query, corpus=corpus, k=k)
    for chunk in result["chunks"]:
        chunk["text"] = chunk["text"][:1200]
        # Keep absolute personal paths out of the agent transcript.
        chunk.pop("path", None)
    return result


# Answer a question from the local documents and return citations.
@mcp.tool()
def ask_knowledge(question: str, corpus: str = "notes,papers") -> dict:
    """Answer a question from local notes and papers, with citations."""
    result = answer(SETTINGS, dsn_for(corpus), question, corpus=corpus)
    citations = [
        {
            "doc_id": citation["doc_id"],
            "chunk_id": citation["chunk_id"],
            "title": citation["title"],
            "page_start": citation["page_start"],
            "page_end": citation["page_end"],
        }
        for citation in result["citations"]
    ]
    return {
        "answer": result["answer"],
        "citations": citations,
        "refused": result["refused"],
        "trace_id": result["trace_id"],
    }


# List corpora with document and chunk counts.
@mcp.tool()
def list_corpora() -> dict:
    """List indexed corpora and their document counts."""
    rows = []
    for database, dsn in (("private", PRIVATE_DSN), ("eval", EVAL_DSN)):
        try:
            with connect(dsn) as conn:
                for row in corpus_stats(conn):
                    row["database"] = database
                    rows.append(row)
        except Exception as exc:  # noqa: BLE001 - report instead of crashing
            rows.append({"database": database, "error": type(exc).__name__})
    return {"corpora": rows}


# Run the MCP server over stdio.
def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
