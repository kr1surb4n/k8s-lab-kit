"""Embedding and JSON parsing tests."""
import math
import unittest

from app.llm import DIMENSION, StubEmbedder, parse_json_object


class LlmTests(unittest.TestCase):
    def test_stub_embedding_is_deterministic_and_normalized(self):
        embedder = StubEmbedder()
        first = embedder.embed(["Kubernetes Pod networking"])[0]
        second = embedder.embed(["Kubernetes Pod networking"])[0]
        self.assertEqual(first, second)
        self.assertEqual(len(first), DIMENSION)
        norm = math.sqrt(sum(value * value for value in first))
        self.assertAlmostEqual(norm, 1.0, places=6)

    def test_stub_embedding_separates_different_texts(self):
        embedder = StubEmbedder()
        a, b = embedder.embed(["pods and containers", "baking sourdough bread"])
        dot = sum(x * y for x, y in zip(a, b))
        self.assertLess(dot, 0.2)

    def test_parse_json_object_handles_code_fences(self):
        self.assertEqual(parse_json_object('```json\n{"a": 1}\n```'), {"a": 1})

    def test_parse_json_object_handles_prose_around_json(self):
        self.assertEqual(parse_json_object('Here:\n{"a": 1}\nDone.'), {"a": 1})

    def test_parse_json_object_rejects_arrays(self):
        with self.assertRaises(ValueError):
            parse_json_object("[1, 2, 3]")


if __name__ == "__main__":
    unittest.main()
