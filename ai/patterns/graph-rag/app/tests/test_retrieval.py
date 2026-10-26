"""Retrieval helper tests that do not need a database."""
import unittest

from app.retrieval import build_context, corpora_list, find_citations, rrf_fuse


class RetrievalTests(unittest.TestCase):
    def test_corpora_list_expands_all(self):
        self.assertEqual(corpora_list(None), ["lab", "notes", "papers"])
        self.assertEqual(corpora_list("all"), ["lab", "notes", "papers"])
        self.assertEqual(corpora_list("notes,papers"), ["notes", "papers"])
        self.assertEqual(corpora_list(["notes"]), ["notes"])

    def test_rrf_prefers_chunks_found_by_both_lists(self):
        vector = [
            {"chunk_id": "a", "score": 0.9},
            {"chunk_id": "b", "score": 0.8},
        ]
        lexical = [
            {"chunk_id": "b", "score": 0.5},
            {"chunk_id": "c", "score": 0.4},
        ]
        fused = rrf_fuse(vector, lexical)
        self.assertEqual(fused[0]["chunk_id"], "b")
        self.assertEqual(fused[0]["vector_score"], 0.8)
        self.assertEqual(fused[0]["lexical_score"], 0.5)
        self.assertEqual({item["chunk_id"] for item in fused}, {"a", "b", "c"})

    def test_build_context_stops_at_budget(self):
        chunks = [
            {"chunk_id": f"d#c{i}", "title": "t", "text": "x" * 100}
            for i in range(10)
        ]
        context = build_context(chunks, max_chars=250)
        self.assertIn("d#c0", context)
        self.assertIn("d#c1", context)
        self.assertNotIn("d#c9", context)

    def test_find_citations_keeps_ids_with_spaces(self):
        chunk_id = "notes:html/a file with spaces.html#c0001"
        text = f"Fact [{chunk_id}] and another [doc-01#c0002]."
        found = find_citations(
            text, {chunk_id, "doc-01#c0002", "doc-01#c0003"}
        )
        self.assertEqual(found, [chunk_id, "doc-01#c0002"])


if __name__ == "__main__":
    unittest.main()
