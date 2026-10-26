"""Ollama client, deterministic stub embedder, and JSON parsing helpers."""
from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any

import httpx

STUB_MODEL = "stub-hash-1024"
DIMENSION = 1024
TOKEN_RE = re.compile(r"[\wąćęłńóśźżĄĆĘŁŃÓŚŹŻ]+", re.UNICODE)


# Raised when Ollama is unreachable or returns an error.
class OllamaError(RuntimeError):
    pass


# Small wrapper around the two Ollama endpoints this project uses.
class OllamaClient:
    def __init__(self, base_url: str, timeout: float = 180.0):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.Client(base_url=self.base_url, timeout=timeout)

    # Check that Ollama answers and which models are loaded.
    def healthy(self) -> dict[str, Any]:
        response = self.client.get("/api/tags")
        response.raise_for_status()
        return response.json()

    # Embed a list of texts in batches; returns one 1024-dim vector each.
    def embed(self, texts: list[str], model: str, batch_size: int = 16) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), batch_size):
            batch = texts[start : start + batch_size]
            response = self.client.post("/api/embed", json={"model": model, "input": batch})
            if response.status_code != 200:
                raise OllamaError(f"embed failed: {response.status_code} {response.text[:300]}")
            data = response.json()
            batch_vectors = data.get("embeddings") or []
            if len(batch_vectors) != len(batch):
                raise OllamaError(
                    f"embed returned {len(batch_vectors)} vectors for {len(batch)} texts"
                )
            for vector in batch_vectors:
                if len(vector) != DIMENSION:
                    raise OllamaError(
                        f"model {model} returned {len(vector)} dimensions, expected {DIMENSION}"
                    )
            vectors.extend(batch_vectors)
        return vectors

    # Send a chat prompt and return the assistant text.
    def chat(
        self,
        prompt: str,
        model: str,
        system: str | None = None,
        temperature: float = 0.0,
        num_predict: int = 800,
        num_ctx: int = 8192,
        json_mode: bool = False,
        format_schema: dict[str, Any] | None = None,
    ) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": num_predict,
                "num_ctx": num_ctx,
            },
        }
        if format_schema is not None:
            payload["format"] = format_schema
        elif json_mode:
            payload["format"] = "json"
        response = self.client.post("/api/chat", json=payload)
        if response.status_code != 200:
            raise OllamaError(f"chat failed: {response.status_code} {response.text[:300]}")
        data = response.json()
        content = data.get("message", {}).get("content", "")
        if not content.strip():
            raise OllamaError("chat returned an empty message")
        return content

    # Ask for a JSON object and parse it, tolerating code fences.
    def chat_json(self, prompt: str, model: str, system: str | None = None) -> dict[str, Any]:
        text = self.chat(prompt, model, system=system, json_mode=True)
        return parse_json_object(text)


# Deterministic feature-hashing embedder used by tests and offline runs.
class StubEmbedder:
    model = STUB_MODEL

    # Hash tokens into a fixed vector, with sign and sublinear term frequency.
    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._one(text) for text in texts]

    # Build one normalized 1024-dim vector.
    def _one(self, text: str) -> list[float]:
        vector = [0.0] * DIMENSION
        counts: dict[str, int] = {}
        for token in TOKEN_RE.findall(text.lower()):
            counts[token] = counts.get(token, 0) + 1
        for token, count in counts.items():
            digest = hashlib.sha1(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % DIMENSION
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign * (1.0 + math.log(count))
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]


# Extract the first JSON object from a model response.
def parse_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end <= start:
            raise ValueError(f"no JSON object in response: {text[:200]!r}")
        value = json.loads(cleaned[start : end + 1])
    if not isinstance(value, dict):
        raise ValueError("response is not a JSON object")
    return value
