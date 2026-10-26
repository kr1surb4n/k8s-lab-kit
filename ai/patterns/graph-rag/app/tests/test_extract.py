"""Extraction tests: normalization, name cleanup, and the offline stub."""
import unittest
from types import SimpleNamespace

from app.extract import (
    clean_name,
    normalize_extraction,
    relation_kind,
    stub_extract,
)


class ExtractionTests(unittest.TestCase):
    def test_clean_name_strips_punctuation(self):
        self.assertEqual(clean_name("  Kubernetes API  "), "Kubernetes API")
        self.assertIsNone(clean_name("x"))
        self.assertIsNone(clean_name(""))

    def test_relation_kind_is_upper_snake(self):
        self.assertEqual(relation_kind("part of"), "PART_OF")
        self.assertEqual(relation_kind("uses->"), "USES")
        self.assertEqual(relation_kind(""), "RELATED_TO")

    def test_normalize_adds_missing_endpoints(self):
        data = {
            "entities": [{"name": "Pod", "type": "Resource"}],
            "relations": [{"source": "Pod", "type": "runs on", "target": "Node"}],
            "hyperedges": [],
        }
        result = normalize_extraction(data)
        names = {item["name"] for item in result["entities"]}
        self.assertEqual(names, {"Pod", "Node"})
        self.assertEqual(result["relations"][0]["type"], "RUNS_ON")

    def test_normalize_drops_self_relations_and_small_hyperedges(self):
        data = {
            "entities": [{"name": "Pod", "type": "Resource"}],
            "relations": [{"source": "Pod", "type": "IS", "target": "Pod"}],
            "hyperedges": [{"relation": "GROUP", "members": ["Pod", "Node"]}],
        }
        result = normalize_extraction(data)
        self.assertEqual(result["relations"], [])
        self.assertEqual(result["hyperedges"], [])

    def test_normalize_keeps_three_member_hyperedge(self):
        data = {
            "entities": [],
            "relations": [],
            "hyperedges": [
                {"relation": "runs together", "members": ["Pod", "Node", "Network"]}
            ],
        }
        result = normalize_extraction(data)
        self.assertEqual(len(result["hyperedges"]), 1)
        self.assertEqual(result["hyperedges"][0]["relation"], "RUNS_TOGETHER")
        self.assertEqual(len(result["hyperedges"][0]["members"]), 3)

    def test_stub_extractor_uses_markdown_emphasis(self):
        document = SimpleNamespace(
            title="Pods and Nodes",
            text="A **Pod** runs on a **Node** with `kubelet`.",
        )
        result = stub_extract(document)
        names = {item["name"] for item in result["entities"]}
        self.assertTrue({"Pod", "Node", "kubelet"}.issubset(names))
        self.assertEqual(result["relations"], [])

    def test_tags_extractor_builds_topic_edges_and_hyperedge(self):
        from app.extract import tags_extract

        document = SimpleNamespace(
            title="A Paper",
            source={"tags": ["Graphs", "Retrieval", "Evaluation"]},
        )
        result = tags_extract(document)
        self.assertEqual(len(result["relations"]), 3)
        self.assertTrue(
            all(edge["type"] == "HAS_TOPIC" for edge in result["relations"])
        )
        self.assertEqual(len(result["hyperedges"]), 1)
        self.assertEqual(result["hyperedges"][0]["relation"], "COVERS_TOPICS")

    def test_tags_extractor_deduplicates_tags(self):
        from app.extract import tags_extract

        document = SimpleNamespace(
            title="A Paper", source={"tags": ["Graphs", "Graphs", "Retrieval"]}
        )
        result = tags_extract(document)
        self.assertEqual(len(result["relations"]), 2)
        self.assertEqual(len(result["hyperedges"]), 0)

    def test_tags_extractor_needs_three_tags_for_a_hyperedge(self):
        from app.extract import tags_extract

        document = SimpleNamespace(title="A Paper", source={"tags": ["One", "Two"]})
        result = tags_extract(document)
        self.assertEqual(len(result["relations"]), 2)
        self.assertEqual(result["hyperedges"], [])


if __name__ == "__main__":
    unittest.main()
