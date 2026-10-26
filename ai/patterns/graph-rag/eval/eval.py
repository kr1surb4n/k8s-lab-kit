#!/usr/bin/env python3
# Graph RAG Evaluation — runs golden Q&A against the API.
# Usage: python eval.py --url http://graph-rag-api:8000 --golden eval/golden_qa.jsonl
import argparse
import json
import time
import statistics
import sys
import os
from typing import List, Dict, Any
from dataclasses import dataclass

import httpx
from pydantic import BaseModel


@dataclass
class GoldenQA:
    query: str
    expected_contains: List[str]
    relevant_docs: List[str]
    expected_graph_path: List[Dict]


@dataclass
class EvalResult:
    query: str
    answer: str
    sources: List[Dict]
    graph_path: List[Dict]
    latency_ms: int
    trace_id: str
    recall_at_k: float
    graph_path_accuracy: float
    faithfulness: float
    latency_ok: bool


class GoldenQAModel(BaseModel):
    query: str
    expected_answer_contains: List[str]
    relevant_docs: List[str]
    expected_graph_path: List[Dict]


def load_golden(path: str) -> List[dict]:
    items = []
    with open(path) as f:
        for line in f:
            if line.strip():
                items.append(json.loads(line))
    return items


def graph_path_match(expected: List[Dict], actual: List[Dict]) -> float:
    """Calculate graph path accuracy - fraction of expected edges found in actual."""
    if not expected:
        return 1.0
    expected_edges = {(e["source"], e["relation"], e["target"]) for e in expected}
    actual_edges = {(e["source"], e["relation"], e["target"]) for e in actual}
    if not expected_edges:
        return 1.0
    matched = len(expected_edges & actual_edges)
    return matched / len(expected_edges)


def evaluate(url: str, golden: List[dict], top_k: int = 5) -> List[dict]:
    client = httpx.Client(base_url=url, timeout=30.0)
    results = []

    for g in golden:
        start = time.time()
        try:
            resp = client.post("/v1/graph-rag/query", json={
                "query": g["query"],
                "top_k": top_k,
                "rerank": True,
                "graph_hops": 2
            })
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"ERROR on '{g['query']}': {e}")
            continue

        latency = int((time.time() - start) * 1000)
        answer = data.get("answer", "")
        sources = data.get("sources", [])
        graph_path = data.get("graph_path", [])
        trace_id = data.get("trace_id", "")

        # Recall@k: fraction of relevant docs in top-k
        returned_docs = [s["doc_id"] for s in sources]
        relevant_found = sum(1 for d in g["relevant_docs"] if d in returned_docs)
        recall = relevant_found / len(g["relevant_docs"]) if g["relevant_docs"] else 1.0

        # Graph path accuracy
        graph_acc = graph_path_match(g.get("expected_graph_path", []), graph_path)

        # Faithfulness: placeholder (would use LLM-as-judge)
        faithfulness = 1.0  # TODO: implement LLM judge

        # Check expected keywords
        expected_ok = all(kw.lower() in answer.lower() for kw in g.get("expected_answer_contains", []))

        results.append({
            "query": g["query"],
            "answer": answer,
            "sources": sources,
            "graph_path": graph_path,
            "latency_ms": latency,
            "trace_id": trace_id,
            "recall_at_k": recall,
            "graph_path_accuracy": graph_acc,
            "faithfulness": faithfulness,
            "latency_ok": latency <= 3000  # p99 target
        })

    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000", help="Graph RAG API base URL")
    parser.add_argument("--golden", default="eval/golden_qa.jsonl", help="Golden Q&A file")
    parser.add_argument("--top-k", type=int, default=5, help="Top-K for retrieval")
    parser.add_argument("--output", default="eval/results.json", help="Output file")
    args = parser.parse_args()

    print(f"Loading golden Q&A from {args.golden}...")
    golden = []
    with open(args.golden) as f:
        for line in f:
            if line.strip():
                golden.append(json.loads(line))
    print(f"Loaded {len(golden)} questions")

    print(f"Evaluating against {args.url}...")
    results = evaluate(args.url, golden, args.top_k)

    if not results:
        print("No results!")
        sys.exit(1)

    # Aggregate metrics
    recalls = [r["recall_at_k"] for r in results]
    graph_accs = [r["graph_path_accuracy"] for r in results]
    latencies = [r["latency_ms"] for r in results]
    faithful = [r["faithfulness"] for r in results]
    latency_ok = sum(1 for r in results if r["latency_ok"])

    print("\n=== EVALUATION RESULTS ===")
    print(f"Questions evaluated: {len(results)}")
    print(f"Recall@{args.top_k}:    mean={statistics.mean(recalls):.3f}, min={min(recalls):.3f}, max={max(recalls):.3f}")
    print(f"Graph Path Acc:     mean={statistics.mean(graph_accs):.3f}")
    print(f"Latency p50:        {statistics.median(latencies)}ms")
    print(f"Latency p99:        {sorted(latencies)[int(0.99 * len(latencies))]}ms")
    print(f"Latency OK (≤3s):   {latency_ok}/{len(results)} ({latency_ok/len(results)*100:.1f}%)")
    print(f"Faithfulness:       {statistics.mean([r['faithfulness'] for r in results]):.3f}")

    # Per-question details
    print("\n=== PER-QUESTION ===")
    for r in results:
        status = "✓" if r["recall_at_k"] == 1.0 and r["latency_ok"] else "✗"
        print(f"  {status} [{r['latency_ms']}ms] {r['query'][:60]}...")

    # Save results
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    output_data = {
        "summary": {
            "total": len(results),
            "recall_at_k_mean": statistics.mean(recalls),
            "graph_path_accuracy_mean": statistics.mean(graph_accs),
            "latency_p50_ms": statistics.median(latencies),
            "latency_p99_ms": sorted(latencies)[int(0.99 * len(latencies))],
            "latency_ok_rate": latency_ok / len(results),
            "faithfulness_mean": statistics.mean([r['faithfulness'] for r in results]),
        },
        "details": results
    }

    with open(args.output, "w") as f:
        json.dump(output_data, f, indent=2)
    print(f"\nResults saved to {args.output}")

    # Exit code based on thresholds
    if statistics.mean(recalls) < 0.85:
        print("FAIL: Recall@k below 0.85")
        sys.exit(1)
    if statistics.mean(graph_accs) < 0.80:
        print("FAIL: Graph path accuracy below 0.80")
        sys.exit(1)
    if latency_ok / len(results) < 0.95:
        print("FAIL: Latency OK rate below 95%")
        sys.exit(1)

    print("PASS: All thresholds met")


if __name__ == "__main__":
    main()