"""Retrieval helper tests that do not need a database."""
import unittest
from unittest.mock import patch

from app.config import Settings
from app.retrieval import (
    GRAPH_ERROR,
    build_context,
    corpora_list,
    find_citations,
    graph_context,
    rrf_fuse,
)


# Small query result that returns prepared rows and records the SQL it saw.
class _Result:
    def __init__(self, rows):
        self.rows = rows

    # Return the prepared rows.
    def fetchall(self):
        return self.rows


# Fake connection for graph-context tests; no Postgres is started.
class _GraphConn:
    def __init__(self, first, second):
        self.first = first
        self.second = second
        self.sql = []

    # Give the first-hop or second-hop rows depending on the query.
    def execute(self, sql, params):
        self.sql.append(sql)
        if "en.node_id = ANY" in sql:
            return _Result(self.second)
        return _Result(self.first)


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

    def test_graph_context_second_hop_uses_shared_bridge(self):
        first = [
            ("e1", "RUNS_ON", 2, "doc-01", "source", "n:pod", "Pod", 1),
            ("e1", "RUNS_ON", 2, "doc-01", "target", "n:node", "Node", 2),
        ]
        second = [
            ("e2", "USES", 2, "doc-02", "source", "n:node", "Node", 1),
            ("e2", "USES", 2, "doc-02", "target", "n:network", "Network", 2),
        ]
        conn = _GraphConn(first, second)
        path = graph_context(conn, ["doc-01"], query="How does a Node work?", hops=2)
        self.assertEqual([edge["hop"] for edge in path], [1, 2])
        self.assertEqual(path[1]["via"], "Node")
        self.assertEqual(path[1]["document_id"], "doc-02")
        self.assertEqual(len(conn.sql), 2)

    def test_graph_context_one_hop_does_not_query_second_hop(self):
        first = [
            ("e1", "RUNS_ON", 2, "doc-01", "source", "n:pod", "Pod", 1),
            ("e1", "RUNS_ON", 2, "doc-01", "target", "n:node", "Node", 2),
        ]
        conn = _GraphConn(first, [])
        path = graph_context(conn, ["doc-01"], hops=1)
        self.assertEqual(len(path), 1)
        self.assertEqual(len(conn.sql), 1)


class AnswerGraphGuardTests(unittest.TestCase):
    # A fake retrieval result that mimics the shape of _search_impl's output.
    def _retrieved(self, graph_path):
        return {
            "chunks": [
                {
                    "chunk_id": "doc-09#c0001",
                    "doc_id": "doc-09",
                    "title": "Recovery drills",
                    "path": "doc-09-recovery.md",
                    "text": "Readiness probes decide when a pod is ready.",
                    "start": 10,
                    "end": 120,
                    "page_start": None,
                    "page_end": None,
                    "score": 0.9,
                    "vector_score": 0.9,
                    "lexical_score": 0.0,
                    "rrf": 0.9,
                }
            ],
            "graph_path": graph_path,
            "graph_hops": 1,
            "rerank": False,
            "rerank_model": "",
        }

    def test_answer_fails_loudly_when_graph_is_empty(self):
        from app.retrieval import _answer_impl

        settings = Settings(require_graph=True)
        with patch("app.retrieval.search", return_value=self._retrieved([])) as fake:
            response = _answer_impl(settings, "postgresql://unused", "Which exercise uses a hostPath?")
        self.assertEqual(response["answer"], GRAPH_ERROR)
        self.assertTrue(response["refused"])
        self.assertEqual(response["graph_error"], "graph_path_empty")
        self.assertEqual(response["citations"], [])
        self.assertEqual(response["graph_path"], [])
        fake.assert_called_once()

    def test_answer_uses_the_settings_default_for_the_guard(self):
        from app.retrieval import _answer_impl

        settings = Settings(require_graph=True)
        with patch("app.retrieval.search", return_value=self._retrieved([])):
            response = _answer_impl(settings, "postgresql://unused", "Which exercise uses a hostPath?")
        self.assertEqual(response["graph_error"], "graph_path_empty")

    def test_answer_answers_normally_when_graph_context_exists(self):
        from app.retrieval import _answer_impl

        settings = Settings()
        with patch(
            "app.retrieval.search",
            return_value=self._retrieved(
                [
                    {
                        "relation": "DEMONSTRATES",
                        "source": "A6",
                        "target": "readiness probe",
                        "document_id": "doc-09",
                        "hop": 1,
                    }
                ]
            ),
        ):
            response = _answer_impl(
                settings, "postgresql://unused", "What does the readiness drill show?",
                stub=True,
            )
        self.assertNotIn("graph_error", response)
        self.assertFalse(response["refused"])
        self.assertEqual(len(response["citations"]), 1)
        self.assertEqual(response["citations"][0]["chunk_id"], "doc-09#c0001")
        self.assertEqual(response["citations"][0]["doc_id"], "doc-09")


if __name__ == "__main__":
    unittest.main()
