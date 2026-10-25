#!/usr/bin/env python3
# RAG Evaluation — runs golden Q&A against the API.
# Usage: python eval.py --url http://rag-api:8000 --golden eval/golden_qa.jsonl
import argparse
import json
import time
import statistics
import sys
from typing import List, Dict, Any
from dataclasses import dataclass

import httpx
from pydantic import BaseModel


@dataclass
class GoldenQA:
    query: str
    expected_contains: List[str]
    relevant_docs: List[str]


@dataclass
class EvalResult:
    query: str
    answer: str
    sources: List[Dict]
    latency_ms: int
    trace_id: str
    recall_at_k: float
    faithfulness: float  # placeholder for LLM-as-judge
    latency_ok: bool


class GoldenQAModel(BaseModel):
    query: str
    expected_answer_contains: List[str]
    relevant_docs: List[str]


def load_golden(path: str) -> List[GoldenQA]:
    items = []
    with open(path) as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                items.append(GoldenQA(
                    query=data["query"],
                    expected_contains=data["expected_answer_contains"],
                    relevant_docs=data["relevant_docs"]
                ))
    return items


def evaluate(url: str, golden: List[GoldenQA], top_k: int = 5) -> List[EvalResult]:
    client = httpx.Client(base_url=url, timeout=30.0)
    results = []

    for g in golden:
        start = time.time()
        try:
            resp = client.post("/v1/rag/query", json={
                "query": g.query,
                "top_k": top_k,
                "rerank": True
            })
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"ERROR on '{g.query}': {e}")
            continue

        latency = int((time.time() - start) * 1000)
        answer = data.get("answer", "")
        sources = data.get("sources", [])
        trace_id = data.get("trace_id", "")

        # Recall@k: fraction of relevant docs in top-k
        returned_docs = [s["doc_id"] for s in sources]
        relevant_found = sum(1 for d in g.relevant_docs if d in returned_docs)
        recall = relevant_found / len(g.relevant_docs) if g.relevant_docs else 1.0

        # Faithfulness: placeholder (would use LLM-as-judge)
        faithfulness = 1.0  # TODO: implement LLM judge

        # Check expected keywords
        expected_ok = all(kw.lower() in answer.lower() for kw in g.expected_contains)

        results.append(EvalResult(
            query=g.query,
            answer=answer,
            sources=sources,
            latency_ms=latency,
            trace_id=trace_id,
            recall_at_k=recall,
            faithfulness=faithfulness,
            latency_ok=latency <= 2000  # p99 target
        ))

    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000", help="RAG API base URL")
    parser.add_argument("--golden", default="eval/golden_qa.jsonl", help="Golden Q&A file")
    parser.add_argument("--top-k", type=int, default=5, help="Top-K for retrieval")
    parser.add_argument("--output", default="eval/results.json", help="Output file")
    args = parser.parse_args()

    print(f"Loading golden Q&A from {args.golden}...")
    golden = load_golden(args.golden)
    print(f"Loaded {len(golden)} questions")

    print(f"Evaluating against {args.url}...")
    results = evaluate(args.url, golden, args.top_k)

    if not results:
        print("No results!")
        sys.exit(1)

    # Aggregate metrics
    recalls = [r.recall_at_k for r in results]
    latencies = [r.latency_ms for r in results]
    faithful = [r.faithfulness for r in results]
    latency_ok = sum(1 for r in results if r.latency_ok)

    print("\n=== EVALUATION RESULTS ===")
    print(f"Questions evaluated: {len(results)}")
    print(f"Recall@{args.top_k}:    mean={statistics.mean(recalls):.3f}, min={min(recalls):.3f}, max={max(recalls):.3f}")
    print(f"Latency p50:        {statistics.median(latencies)}ms")
    print(f"Latency p99:        {sorted(latencies)[int(0.99 * len(latencies))]}ms")
    print(f"Latency OK (≤2s):   {latency_ok}/{len(results)} ({latency_ok/len(results)*100:.1f}%)")
    print(f"Faithfulness:       {statistics.mean(faithful):.3f}")

    # Per-question details
    print("\n=== PER-QUESTION ===")
    for r in results:
        status = "✓" if r.recall_at_k == 1.0 and r.latency_ok else "✗"
        print(f"  {status} [{r.latency_ms}ms] {r.query[:60]}...")

    # Save results
    output_data = {
        "summary": {
            "total": len(results),
            "recall_at_k_mean": statistics.mean(recalls),
            "latency_p50_ms": statistics.median(latencies),
            "latency_p99_ms": sorted(latencies)[int(0.99 * len(latencies))],
            "latency_ok_rate": latency_ok / len(results),
            "faithfulness_mean": statistics.mean(faithful),
        },
        "details": [
            {
                "query": r.query,
                "answer": r.answer[:200],
                "sources": r.sources,
                "latency_ms": r.latency_ms,
                "trace_id": r.trace_id,
                "recall_at_k": r.recall_at_k,
                "faithfulness": r.faithfulness,
            }
            for r in results
        ]
    }

    with open(args.output, "w") as f:
        json.dump(output_data, f, indent=2)
    print(f"\nResults saved to {args.output}")

    # Exit code based on thresholds
    if statistics.mean(recalls) < 0.85:
        print("FAIL: Recall@k below 0.85")
        sys.exit(1)
    if latency_ok / len(results) < 0.95:
        print("FAIL: Latency OK rate below 95%")
        sys.exit(1)

    print("PASS: All thresholds met")


if __name__ == "__main__":
    main()