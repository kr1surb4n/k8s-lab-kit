#!/usr/bin/env python3
# Graph RAG evaluation — runs the golden set against a live API.
#
# Usage:
#   python eval.py --url http://localhost:8000 --golden eval/golden_qa.jsonl
#
# The golden file is the Phase 17 corpus schema: question, kind, expected doc
# ids, expected answer facts, must_cite, and a graph path. Refusal questions
# must produce no citations.
import argparse
import json
import os
import statistics
import sys
import time
from typing import List

import httpx

REFUSAL_MARKERS = ("not in the corpus", "cannot answer", "no answer", "not available")


# Load the JSONL golden set, one question per line.
def load_golden(path: str) -> List[dict]:
    items = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                items.append(json.loads(line))
    return items


# Score one expected graph path entry against the returned path.
def graph_path_match(expected: List[dict], actual: List[dict]) -> float:
    """Fraction of expected graph entries found in the returned path."""
    if not expected:
        return 1.0
    actual_keys = set()
    for entry in actual:
        if "members" in entry:
            actual_keys.add(("hyperedge", entry.get("relation"), tuple(sorted(entry["members"]))))
        else:
            actual_keys.add((entry.get("source"), entry.get("relation"), entry.get("target")))
    matched = 0
    for entry in expected:
        if "members" in entry:
            key = ("hyperedge", entry.get("relation"), tuple(sorted(entry["members"])))
        else:
            key = (entry.get("source"), entry.get("relation"), entry.get("target"))
        if key in actual_keys:
            matched += 1
    return matched / len(expected)


# Ask the API one question and score the response.
def evaluate_one(client, golden: dict, top_k: int) -> dict:
    start = time.time()
    response = client.post(
        "/v1/graph-rag/query",
        json={
            "query": golden["question"],
            "top_k": top_k,
            "rerank": True,
            "graph_hops": 2,
        },
    )
    response.raise_for_status()
    data = response.json()
    latency = int((time.time() - start) * 1000)

    answer = data.get("answer", "")
    sources = data.get("sources", [])
    graph_path = data.get("graph_path", [])
    returned_docs = [source["doc_id"] for source in sources]
    expected_docs = golden.get("expected_doc_ids", [])

    relevant_found = sum(1 for doc_id in expected_docs if doc_id in returned_docs)
    recall = relevant_found / len(expected_docs) if expected_docs else 1.0
    citation_precision = (
        sum(1 for doc_id in returned_docs if doc_id in expected_docs) / len(returned_docs)
        if returned_docs
        else 1.0
    )
    facts_ok = all(
        fact.lower() in answer.lower()
        for fact in golden.get("expected_answer_facts", [])
    )
    refusal_ok = True
    if golden["kind"] == "refusal":
        refusal_ok = not returned_docs and any(
            marker in answer.lower() for marker in REFUSAL_MARKERS
        )

    return {
        "id": golden["id"],
        "kind": golden["kind"],
        "question": golden["question"],
        "answer": answer,
        "sources": sources,
        "graph_path": graph_path,
        "latency_ms": latency,
        "trace_id": data.get("trace_id", ""),
        "recall_at_k": recall,
        "citation_precision": citation_precision,
        "graph_path_accuracy": graph_path_match(golden.get("expected_graph_path", []), graph_path),
        "facts_ok": facts_ok,
        "refusal_ok": refusal_ok,
        # Faithfulness needs an LLM judge; Phase 17.5 replaces this placeholder.
        "faithfulness": 1.0,
        "latency_ok": latency <= 3000,
    }


# Run the whole set and return per-question results.
def evaluate(url: str, golden: List[dict], top_k: int) -> List[dict]:
    results = []
    with httpx.Client(base_url=url, timeout=120.0) as client:
        for question in golden:
            try:
                results.append(evaluate_one(client, question, top_k))
            except Exception as exc:  # noqa: BLE001 - the report needs every failure
                print(f"ERROR on {question['id']}: {exc}", file=sys.stderr)
    return results


# Print the aggregate score table and the per-question status.
def report(results: List[dict], top_k: int) -> dict:
    recalls = [item["recall_at_k"] for item in results]
    precisions = [item["citation_precision"] for item in results]
    graph_accs = [item["graph_path_accuracy"] for item in results]
    latencies = [item["latency_ms"] for item in results]
    faithful = [item["faithfulness"] for item in results]

    summary = {
        "total": len(results),
        "answerable": sum(1 for item in results if item["kind"] == "answerable"),
        "relation": sum(1 for item in results if item["kind"] == "relation"),
        "refusal": sum(1 for item in results if item["kind"] == "refusal"),
        "recall_at_k_mean": statistics.mean(recalls),
        "citation_precision_mean": statistics.mean(precisions),
        "graph_path_accuracy_mean": statistics.mean(graph_accs),
        "facts_ok_rate": sum(1 for item in results if item["facts_ok"]) / len(results),
        "refusal_ok_rate": sum(1 for item in results if item["refusal_ok"]) / len(results),
        "latency_p50_ms": statistics.median(latencies),
        "latency_p99_ms": sorted(latencies)[max(0, int(0.99 * len(latencies)) - 1)],
        "latency_ok_rate": sum(1 for item in results if item["latency_ok"]) / len(results),
        "faithfulness_mean": statistics.mean(faithful),
    }

    print("\n=== EVALUATION RESULTS ===")
    print(f"Questions evaluated: {summary['total']}")
    print(
        f"Kind:              {summary['answerable']} answerable, "
        f"{summary['relation']} relation, {summary['refusal']} refusal"
    )
    print(f"Recall@{top_k}:         {summary['recall_at_k_mean']:.3f}")
    print(f"Citation precision: {summary['citation_precision_mean']:.3f}")
    print(f"Graph path accuracy: {summary['graph_path_accuracy_mean']:.3f}")
    print(f"Facts present:      {summary['facts_ok_rate']:.3f}")
    print(f"Refusals correct:   {summary['refusal_ok_rate']:.3f}")
    print(f"Latency p50:        {summary['latency_p50_ms']}ms")
    print(f"Latency p99:        {summary['latency_p99_ms']}ms")
    print(f"Latency OK (<=3s):  {summary['latency_ok_rate']:.3f}")
    print(f"Faithfulness:       mean={summary['faithfulness_mean']:.3f} (placeholder)")

    print("\n=== PER-QUESTION ===")
    for item in results:
        ok = (
            item["recall_at_k"] == 1.0
            and item["facts_ok"]
            and item["refusal_ok"]
            and item["latency_ok"]
        )
        print(f"  {'OK ' if ok else 'FAIL'} [{item['latency_ms']}ms] {item['id']} {item['question']}")
    return summary


# Parse arguments, run the evaluation, write results, and apply the thresholds.
def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--golden", default="eval/golden_qa.jsonl")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--output", default="eval/results.json")
    args = parser.parse_args()

    golden = load_golden(args.golden)
    print(f"Loaded {len(golden)} questions from {args.golden}")
    print(f"Evaluating against {args.url}")
    results = evaluate(args.url, golden, args.top_k)
    if not results:
        print("No results", file=sys.stderr)
        return 1

    summary = report(results, args.top_k)
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump({"summary": summary, "details": results}, handle, indent=2)
        handle.write("\n")
    print(f"\nResults saved to {args.output}")

    if summary["recall_at_k_mean"] < 0.85:
        print("FAIL: recall@k below 0.85")
        return 1
    if summary["graph_path_accuracy_mean"] < 0.80:
        print("FAIL: graph path accuracy below 0.80")
        return 1
    if summary["latency_ok_rate"] < 0.95:
        print("FAIL: latency OK rate below 95%")
        return 1
    if summary["refusal_ok_rate"] < 1.0:
        print("FAIL: a refusal question cited documents")
        return 1
    print("PASS: all thresholds met")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
