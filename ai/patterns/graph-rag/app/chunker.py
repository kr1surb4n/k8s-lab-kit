"""Word-based chunking with exact offsets and page mapping."""
from __future__ import annotations

import re
from bisect import bisect_right
from dataclasses import dataclass

WORD = re.compile(r"\S+")


# One chunk of a document; offsets point into the normalized document text.
@dataclass(frozen=True)
class Chunk:
    ordinal: int
    text: str
    start: int
    end: int
    page_start: int | None
    page_end: int | None


# Find the page that contains a character offset.
def page_for_offset(page_map: list[tuple[int, int]] | None, offset: int) -> int | None:
    if not page_map:
        return None
    starts = [start for start, _ in page_map]
    index = bisect_right(starts, offset) - 1
    return page_map[max(0, index)][1]


# Split text into overlapping chunks of at most max_words words.
def chunk_text(
    text: str,
    max_words: int = 320,
    overlap_words: int = 50,
    page_map: list[tuple[int, int]] | None = None,
) -> list[Chunk]:
    if max_words < 20:
        raise ValueError("max_words must be at least 20")
    if overlap_words < 0 or overlap_words >= max_words:
        raise ValueError("overlap_words must be between 0 and max_words - 1")

    words = list(WORD.finditer(text))
    if not words:
        return []

    chunks: list[Chunk] = []
    step = max_words - overlap_words
    index = 0
    while index < len(words):
        end_index = min(index + max_words, len(words))
        start = words[index].start()
        end = words[end_index - 1].end()
        chunks.append(
            Chunk(
                ordinal=len(chunks),
                text=text[start:end],
                start=start,
                end=end,
                page_start=page_for_offset(page_map, start),
                page_end=page_for_offset(page_map, max(start, end - 1)),
            )
        )
        if end_index == len(words):
            break
        index += step
    return chunks
