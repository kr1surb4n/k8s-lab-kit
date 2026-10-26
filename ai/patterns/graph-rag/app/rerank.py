"""Local listwise reranking for the fused retrieval candidates."""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from .llm import OllamaClient, parse_json_object

LOGGER = logging.getLogger("graphrag")
RERANK_SYSTEM = (
    "You rank retrieved passages by how directly they answer the question. "
    "Return only the requested JSON object. Do not add commentary."
)
RERANK_TEMPLATE = """Rank these passages for the question.

Rules:
- Put the most useful passage first.
- Use only the chunk ids shown in the list.
- Return every id exactly once.
- Return JSON in this shape: {{"ranking": ["chunk-id-1", "chunk-id-2"]}}

Question: {question}

Passages:
{passages}
"""


# Build the compact listwise prompt; long chunks are truncated on purpose.
def build_rerank_prompt(
    question: str, chunks: list[dict[str, Any]], max_chars: int = 320
) -> str:
    passages = []
    for chunk in chunks:
        text = " ".join(chunk["text"].split())[:max_chars]
        passages.append(f"[{chunk['chunk_id']}] {chunk['title']}\n{text}")
    return RERANK_TEMPLATE.format(
        question=question,
        passages="\n\n".join(passages),
    )


# Read a ranking from JSON, accepting a list or a ranking/order/ids field.
def parse_ranking(text: str, valid_ids: list[str]) -> list[str]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned).strip()
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        try:
            value = parse_json_object(cleaned)
        except ValueError:
            # A model may return a bare JSON array even when asked for an object.
            if cleaned.startswith("["):
                value = json.loads(cleaned)
            else:
                raise

    if isinstance(value, dict):
        items = value.get("ranking") or value.get("order") or value.get("ids") or []
    elif isinstance(value, list):
        items = value
    else:
        items = []

    valid = set(valid_ids)
    order: list[str] = []
    for item in items:
        if isinstance(item, str):
            chunk_id = item
        elif isinstance(item, dict):
            chunk_id = item.get("chunk_id")
        else:
            chunk_id = None
        if chunk_id in valid and chunk_id not in order:
            order.append(chunk_id)
    if not order:
        raise ValueError("reranker returned no known chunk ids")
    # A short model response must not drop candidates; keep the rest in place.
    order.extend(chunk_id for chunk_id in valid_ids if chunk_id not in order)
    return order


# Reorder chunks with one local listwise call; fall back to the original order.
def rerank_chunks(
    chunks: list[dict[str, Any]],
    question: str,
    client: OllamaClient,
    model: str,
    max_candidates: int = 20,
) -> tuple[list[dict[str, Any]], bool]:
    if len(chunks) < 2:
        return chunks, False
    candidates = chunks[:max_candidates]
    remainder = chunks[max_candidates:]
    prompt = build_rerank_prompt(question, candidates)
    try:
        text = client.chat(
            prompt,
            model,
            system=RERANK_SYSTEM,
            temperature=0.0,
            num_predict=400,
            num_ctx=8192,
            json_mode=True,
        )
        order = parse_ranking(text, [chunk["chunk_id"] for chunk in candidates])
    except Exception as exc:  # noqa: BLE001 - reranking must never break search
        LOGGER.warning("rerank failed (%s); keeping RRF order", type(exc).__name__)
        return chunks, False

    by_id = {chunk["chunk_id"]: chunk for chunk in candidates}
    reordered = [by_id[chunk_id] for chunk_id in order]
    return reordered + remainder, True
