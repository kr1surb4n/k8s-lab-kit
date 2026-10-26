"""OpenTelemetry tests use an in-memory exporter; no collector is needed."""
import unittest
from unittest.mock import patch

from app.config import Settings
from app.telemetry import OTEL_AVAILABLE, configure_telemetry, current_trace_id, span

if OTEL_AVAILABLE:
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter


# Settings that are safe to use in a test process.
def _settings() -> Settings:
    return Settings(
        otel_enabled=True,
        otel_endpoint="",
        otel_console=False,
        otel_service_name="graphrag-test",
    )


@unittest.skipUnless(OTEL_AVAILABLE, "the OpenTelemetry SDK is not installed")
class TelemetryTests(unittest.TestCase):
    def setUp(self):
        self.exporter = InMemorySpanExporter()
        configure_telemetry(_settings(), exporter=self.exporter, force=True)

    def tearDown(self):
        configure_telemetry(Settings(otel_enabled=False), force=True)

    def test_span_is_exported_with_a_trace_id(self):
        with span("graphrag.test", {"graphrag.question_length": 7}) as current:
            trace_id = current_trace_id()
            current.set_attribute("graphrag.chunks", 2)
        finished = self.exporter.get_finished_spans()
        self.assertEqual(len(finished), 1)
        self.assertEqual(finished[0].name, "graphrag.test")
        self.assertEqual(finished[0].attributes["graphrag.question_length"], 7)
        self.assertEqual(finished[0].attributes["graphrag.chunks"], 2)
        self.assertEqual(len(trace_id), 32)

    def test_search_span_does_not_include_the_query_text(self):
        from app.retrieval import search

        response = {
            "chunks": [{"chunk_id": "a"}],
            "graph_path": [],
            "rerank": False,
            "latency_ms": 1,
        }
        with patch("app.retrieval._search_impl", return_value=response):
            result = search(_settings(), "postgresql://unused", "private question text", k=1)
        self.assertEqual(len(result["trace_id"]), 32)
        finished = self.exporter.get_finished_spans()
        values = [str(value) for value in finished[0].attributes.values()]
        self.assertFalse(any("private question text" in value for value in values))

    def test_answer_span_has_counts_only(self):
        from app.retrieval import answer

        response = {
            "answer": "ok",
            "citations": [{"chunk_id": "a"}],
            "graph_path": [],
            "chunks": [],
            "scores": {},
            "trace_id": "",
            "prompt_version": "p1",
            "model_version": "stub",
            "latency_ms": 2,
            "refused": False,
            "graph_hops": 1,
            "rerank": False,
            "rerank_model": "",
        }
        with patch("app.retrieval._answer_impl", return_value=response):
            answer(_settings(), "postgresql://unused", "private question text")
        finished = self.exporter.get_finished_spans()
        self.assertEqual(finished[0].name, "graphrag.answer")
        self.assertEqual(finished[0].attributes["graphrag.question_length"], 21)
        self.assertEqual(finished[0].attributes["graphrag.citations"], 1)
        values = [str(value) for value in finished[0].attributes.values()]
        self.assertFalse(any("private question text" in value for value in values))


if __name__ == "__main__":
    unittest.main()
