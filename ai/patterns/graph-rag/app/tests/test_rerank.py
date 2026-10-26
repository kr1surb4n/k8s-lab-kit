"""Reranker parsing and fallback tests; no Ollama process is needed."""
import unittest

from app.rerank import build_rerank_prompt, parse_ranking, rerank_chunks


# Small fake client that returns one prepared response.
class _Client:
    def __init__(self, text=None, error=None):
        self.text = text
        self.error = error
        self.calls = 0

    # Return the prepared assistant text, or raise the prepared error.
    def chat(self, *args, **kwargs):
        self.calls += 1
        if self.error:
            raise self.error
        return self.text


# Build three chunks with stable ids for ordering checks.
def _chunks():
    return [
        {"chunk_id": "a", "title": "A", "text": "alpha"},
        {"chunk_id": "b", "title": "B", "text": "beta"},
        {"chunk_id": "c", "title": "C", "text": "gamma"},
    ]


class RerankTests(unittest.TestCase):
    def test_prompt_contains_ids_and_truncated_text(self):
        chunks = [{"chunk_id": "a", "title": "A", "text": "word " * 200}]
        prompt = build_rerank_prompt("question", chunks, max_chars=20)
        self.assertIn("[a] A", prompt)
        self.assertIn("question", prompt)
        self.assertLess(len(prompt), 1000)

    def test_parse_ranking_keeps_known_ids_and_adds_missing(self):
        order = parse_ranking('{"ranking": ["b", "a", "missing"]}', ["a", "b", "c"])
        self.assertEqual(order, ["b", "a", "c"])

    def test_parse_ranking_accepts_bare_array_and_code_fence(self):
        order = parse_ranking('```json\n[{"chunk_id": "c"}, "a"]\n```', ["a", "b", "c"])
        self.assertEqual(order, ["c", "a", "b"])

    def test_rerank_chunks_reorders_and_keeps_remainder(self):
        chunks = _chunks()
        client = _Client('{"ranking": ["b", "a"]}')
        reordered, applied = rerank_chunks(chunks, "q", client, "model", max_candidates=2)
        self.assertTrue(applied)
        self.assertEqual([chunk["chunk_id"] for chunk in reordered], ["b", "a", "c"])
        self.assertEqual(client.calls, 1)

    def test_rerank_chunks_falls_back_on_model_error(self):
        chunks = _chunks()
        client = _Client(error=RuntimeError("offline"))
        reordered, applied = rerank_chunks(chunks, "q", client, "model")
        self.assertFalse(applied)
        self.assertEqual([chunk["chunk_id"] for chunk in reordered], ["a", "b", "c"])

    def test_rerank_chunks_skips_single_candidate(self):
        client = _Client('{"ranking": ["a"]}')
        reordered, applied = rerank_chunks(_chunks()[:1], "q", client, "model")
        self.assertFalse(applied)
        self.assertEqual(reordered[0]["chunk_id"], "a")
        self.assertEqual(client.calls, 0)


if __name__ == "__main__":
    unittest.main()
