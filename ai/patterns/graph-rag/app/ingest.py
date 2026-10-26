"""Ingest documents: chunk, embed, extract, and store with provenance."""
from __future__ import annotations

import sys
import time
from typing import Any

from .chunker import chunk_text
from .config import Settings
from .db import connect, corpus_stats, prune_missing, store_document, stored_hashes
from .extract import extract_document
from .llm import OllamaClient, StubEmbedder
from .sources import iter_documents


# Embed chunk texts with either the stub or the real model.
def embed_texts(embedder, texts: list[str], model: str) -> list[list[float]]:
    if isinstance(embedder, StubEmbedder):
        return embedder.embed(texts)
    return embedder.embed(texts, model)


# Ingest one corpus and return counters for the caller.
def ingest_corpus(
    settings: Settings,
    dsn: str,
    corpus: str,
    limit: int | None = None,
    stub: bool = False,
    extract_mode: str = "llm",
    force: bool = False,
    chunk_words: int | None = None,
    overlap: int | None = None,
    prune: bool = False,
    ocr: bool | None = None,
    verbose: bool = True,
) -> dict[str, Any]:
    max_words = chunk_words or settings.chunk_words
    overlap_words = overlap if overlap is not None else settings.chunk_overlap
    embedder = StubEmbedder() if stub else OllamaClient(settings.ollama_url)
    embed_model = embedder.model if stub else settings.embed_model
    llm = None if stub or extract_mode != "llm" else OllamaClient(settings.ollama_url)

    started = time.time()
    counters = {
        "corpus": corpus,
        "documents": 0,
        "skipped": 0,
        "failed": 0,
        "chunks": 0,
        "edges": 0,
        "pruned": 0,
    }
    seen_paths: set[str] = set()

    with connect(dsn) as conn:
        stored = stored_hashes(conn, corpus)
        for number, document in enumerate(
            iter_documents(settings, corpus, limit=limit, ocr=ocr), 1
        ):
            seen_paths.add(document.path)
            # Unchanged documents are skipped unless a forced rebuild was asked for.
            if not force and stored.get(document.path) == document.sha256:
                counters["skipped"] += 1
                if verbose and number % 25 == 0:
                    print(f"[{number}] skipped unchanged documents", file=sys.stderr)
                continue

            chunks = chunk_text(document.text, max_words, overlap_words, document.page_map)
            if not chunks:
                counters["failed"] += 1
                print(f"skip (no text): {document.path}", file=sys.stderr)
                continue

            vectors = embed_texts(embedder, [chunk.text for chunk in chunks], embed_model)
            try:
                extraction = extract_document(
                    document,
                    mode=extract_mode,
                    client=llm,
                    model=settings.generate_model,
                )
            except RuntimeError as exc:
                counters["failed"] += 1
                extraction = {"entities": [], "relations": [], "hyperedges": []}
                print(f"extract failed, storing text only: {exc}", file=sys.stderr)

            store_document(conn, document, chunks, vectors, extraction, embed_model)
            counters["documents"] += 1
            counters["chunks"] += len(chunks)
            counters["edges"] += len(extraction.get("relations", [])) + len(
                extraction.get("hyperedges", [])
            )
            if verbose:
                elapsed = time.time() - started
                print(
                    f"[{number}] {document.id} {len(chunks)} chunks, "
                    f"{len(extraction.get('entities', []))} entities, "
                    f"{counters['edges']} edges, {elapsed:.1f}s",
                    flush=True,
                )

        # Only a complete run may delete documents that disappeared from disk.
        if prune and limit is None:
            removed = prune_missing(conn, corpus, seen_paths)
            counters["pruned"] = len(removed)
            for path in removed:
                print(f"pruned: {path}", file=sys.stderr)

        counters["stats"] = corpus_stats(conn, corpus)

    counters["elapsed_s"] = round(time.time() - started, 1)
    return counters
