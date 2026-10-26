"""Local HTTP API for search and question answering.

The service binds to localhost by default and has no authentication. It reads
private notes and papers, so never expose it on a public interface.
"""
from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .config import load_settings
from .db import connect, corpus_stats
from .llm import OllamaClient, OllamaError
from .retrieval import answer, search

LOGGER = logging.getLogger("graphrag.api")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
SETTINGS = load_settings()
PRIVATE_DSN = SETTINGS.dsn("private")
EVAL_DSN = SETTINGS.dsn("eval")

app = FastAPI(
    title="Local Graph RAG",
    version="0.1.0",
    description="Search and ask questions over local notes and papers.",
)


# A search request from a client such as Hermes or the papers web app.
class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    corpus: str = Field(default="notes,papers", max_length=100)
    k: int = Field(default=8, ge=1, le=50)
    graph_hops: int | None = Field(default=None, ge=1, le=2)
    rerank: bool | None = None
    stub: bool = False


# A question request; the answer always includes citations.
class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    corpus: str = Field(default="notes,papers", max_length=100)
    top_k: int | None = Field(default=None, ge=1, le=30)
    graph_hops: int | None = Field(default=None, ge=1, le=2)
    rerank: bool | None = None
    stub: bool = False


# The lab corpus lives in the eval database; notes and papers are private.
def dsn_for(corpus: str) -> str:
    return EVAL_DSN if corpus == "lab" else PRIVATE_DSN


# Report database and model health without leaking connection strings.
@app.get("/healthz")
def healthz() -> dict:
    databases = {}
    for name, dsn in (("private", PRIVATE_DSN), ("eval", EVAL_DSN)):
        try:
            with connect(dsn) as conn:
                conn.execute("SELECT 1")
            databases[name] = "ok"
        except Exception as exc:  # noqa: BLE001 - health must not crash
            databases[name] = f"error: {type(exc).__name__}"
    try:
        OllamaClient(SETTINGS.ollama_url, timeout=5).healthy()
        ollama = "ok"
    except Exception as exc:  # noqa: BLE001 - health must not crash
        ollama = f"error: {type(exc).__name__}"
    status = "ok" if all(value == "ok" for value in databases.values()) and ollama == "ok" else "degraded"
    return {
        "status": status,
        "databases": databases,
        "ollama": ollama,
        "embed_model": SETTINGS.embed_model,
        "generate_model": SETTINGS.generate_model,
    }


# Search chunks across the local corpora.
@app.post("/v1/search")
def api_search(request: SearchRequest) -> dict:
    try:
        return search(
            SETTINGS,
            dsn_for(request.corpus),
            request.query,
            corpus=request.corpus,
            k=request.k,
            stub=request.stub,
            graph_hops=request.graph_hops,
            rerank=request.rerank,
        )
    except OllamaError as exc:
        raise HTTPException(status_code=502, detail=f"model error: {exc}") from exc
    except Exception as exc:  # noqa: BLE001 - surface a clean API error
        LOGGER.exception("search failed")
        raise HTTPException(status_code=503, detail=f"search failed: {type(exc).__name__}") from exc


# Answer a question with citations from the private corpora.
@app.post("/v1/ask")
def api_ask(request: AskRequest) -> dict:
    try:
        return answer(
            SETTINGS,
            dsn_for(request.corpus),
            request.question,
            corpus=request.corpus,
            top_k=request.top_k,
            stub=request.stub,
            graph_hops=request.graph_hops,
            rerank=request.rerank,
        )
    except OllamaError as exc:
        raise HTTPException(status_code=502, detail=f"model error: {exc}") from exc
    except Exception as exc:  # noqa: BLE001 - surface a clean API error
        LOGGER.exception("ask failed")
        raise HTTPException(status_code=503, detail=f"ask failed: {type(exc).__name__}") from exc


# List corpora and row counts from both databases.
@app.get("/v1/corpora")
def api_corpora() -> dict:
    corpora = []
    for database, dsn in (("private", PRIVATE_DSN), ("eval", EVAL_DSN)):
        try:
            with connect(dsn) as conn:
                for row in corpus_stats(conn):
                    row["database"] = database
                    corpora.append(row)
        except Exception as exc:  # noqa: BLE001 - one database may be stopped
            corpora.append({"database": database, "error": type(exc).__name__})
    return {"corpora": corpora}
