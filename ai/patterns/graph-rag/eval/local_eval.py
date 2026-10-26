#!/usr/bin/env python3
"""Evaluate the local Graph RAG app against the 42-question golden set.

Unlike eval.py, this runner does not need a deployed service or a port
forward. It calls the same retrieval and answer code as the CLI, directly
against the evaluation database.

Usage:
    .venv/bin/python eval/local_eval.py
    .venv/bin/python eval/local_eval.py --stub
    .venv/bin/python eval/local_eval.py --json-out eval/local-results.json
"""
from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import load_settings  # noqa: E402
from app.retrieval import answer  # noqa: E402

REFUSAL_MARKERS = (
    "does not contain enough information",
    "cannot answer",
    "no answer",
)


# Load the JSONL golden set, one question per line.
def load_golden(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


# Normalize an entity name for comparison.
def name_key(value: str) -> str:
    return " ".join(str(value).lower().split())


# Score one expected graph entry against the returned path.
def graph_entry_match(expected: dict, actual: list[dict]) -> bool:
    for entry in actual:
        if "members" in expected:
            if "members" not in entry:
                continue
            if entry.get("relation") != expected.get("relation"):
                continue
            if sorted(name_key(m) for m in entry["members"]) == sorted(
                name_key(m) for m in expected["members"]
            ):
                return True
        else:
            if entry.get("relation") != expected.get("relation"):
                continue
            if name_key(entry.get("source", "")) == name_key(expected.get("source", "")) and name_key(
                entry.get("target", "")
            ) == name_key(expected.get("target", "")):
                return True
    return False


# Score the whole expected graph path as a fraction of matched entries.
def graph_path_score(expected: list[dict], actual: list[dict]) -> float:
    if not expected:
        return 1.0
    return sum(graph_entry_match(entry, actual) for entry in expected) / len(expected)


# Run one golden question through the local answer pipeline.
def evaluate_one(
    settings,
    dsn: str,
    golden: dict,
    stub: bool,
    graph_hops: int | None = None,
    rerank: bool | None = None,
) -> dict:
    started = time.time()
    result = answer(
        settings,
        dsn,
        golden["question"],
        corpus="lab",
        top_k=settings.answer_top_k,
        stub=stub,
        graph_hops=graph_hops,
        rerank=rerank,
    )
    latency = int((time.time() - started) * 1000)
    answer_text = result["answer"]
    citations = result["citations"]
    cited_docs = [citation["doc_id"] for citation in citations]
    returned_docs = list(dict.fromkeys(chunk["doc_id"] for chunk in result["chunks"]))
    expected_docs = golden.get("expected_doc_ids", [])

    relevant = sum(1 for doc_id in expected_docs if doc_id in returned_docs)
    recall = relevant / len(expected_docs) if expected_docs else 1.0
    precision = (
        sum(1 for doc_id in cited_docs if doc_id in expected_docs) / len(cited_docs)
        if cited_docs
        else (1.0 if not expected_docs else 0.0)
    )
    facts_ok = all(
        fact.lower() in answer_text.lower()
        for fact in golden.get("expected_answer_facts", [])
    )
    if golden["kind"] == "refusal":
        refusal_ok = result["refused"] and not citations
    else:
        refusal_ok = not result["refused"]
    graph_accuracy = graph_path_score(
        golden.get("expected_graph_path", []), result.get("graph_path", [])
    )

    return {
        "id": golden["id"],
        "kind": golden["kind"],
        "question": golden["question"],
        "answer": answer_text,
        "citations": citations,
        "graph_path": result.get("graph_path", []),
        "latency_ms": latency,
        "trace_id": result["trace_id"],
        "recall_at_k": recall,
        "citation_precision": precision,
        "graph_path_accuracy": graph_accuracy,
        "facts_ok": facts_ok,
        "refusal_ok": refusal_ok,
        "refused": result["refused"],
    }


# Print and return aggregate metrics.
def summarize(results: list[dict]) -> dict:
    answerable = [item for item in results if item["kind"] != "refusal"]
    refusals = [item for item in results if item["kind"] == "refusal"]
    latencies = sorted(item["latency_ms"] for item in results)
    summary = {
        "questions": len(results),
        "answerable": len(answerable),
        "refusals": len(refusals),
        "recall_at_k": round(
            statistics.mean(item["recall_at_k"] for item in answerable), 4
        )
        if answerable
        else 0.0,
        "citation_precision": round(
            statistics.mean(item["citation_precision"] for item in answerable), 4
        )
        if answerable
        else 0.0,
        "graph_path_accuracy": round(
            statistics.mean(item["graph_path_accuracy"] for item in answerable), 4
        )
        if answerable
        else 0.0,
        "facts_ok_rate": round(
            statistics.mean(1.0 if item["facts_ok"] else 0.0 for item in answerable), 4
        )
        if answerable
        else 0.0,
        "refusal_ok_rate": round(
            statistics.mean(1.0 if item["refusal_ok"] else 0.0 for item in refusals), 4
        )
        if refusals
        else 1.0,
        "latency_ms_p50": int(statistics.median(latencies)) if latencies else 0,
        "latency_ms_p95": latencies[int(len(latencies) * 0.95) - 1] if latencies else 0,
    }
    print(json.dumps(summary, indent=2))
    return summary


# Return the current git commit, or an empty string outside git.
def git_commit() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


# Return the corpus version from the manifest.
def corpus_version() -> str:
    try:
        manifest = json.loads(
            (ROOT / "corpus" / "MANIFEST.json").read_text(encoding="utf-8")
        )
        return manifest.get("corpus_version", "")
    except (OSError, json.JSONDecodeError):
        return ""


# Parse arguments and run the golden set.
def main() -> int:
    parser = argparse.ArgumentParser(description="Local Graph RAG evaluation")
    parser.add_argument(
        "--golden",
        type=Path,
        default=ROOT / "eval" / "golden_qa.jsonl",
    )
    parser.add_argument("--config", help="path to the private config.yaml")
    parser.add_argument("--db", default="eval", help="eval, private, or a DSN")
    parser.add_argument("--stub", action="store_true", help="offline stub generator")
    parser.add_argument(
        "--graph-hops", type=int, choices=[1, 2], help="one or two graph hops"
    )
    parser.add_argument("--rerank", action="store_true", help="rerank with the local LLM")
    parser.add_argument("--json-out", type=Path, help="write per-question results")
    args = parser.parse_args()

    settings = load_settings(args.config)
    dsn = settings.dsn(args.db) if args.db in settings.databases else args.db
    golden = load_golden(args.golden)
    results = []
    for item in golden:
        result = evaluate_one(
            settings, dsn, item, args.stub, args.graph_hops, args.rerank or None
        )
        results.append(result)
        status = "ok" if result["facts_ok"] else "fact-miss"
        if result["kind"] == "refusal":
            status = "ok" if result["refusal_ok"] else "refusal-miss"
        print(
            f"{result['id']:>6} {status:<12} recall={result['recall_at_k']:.2f} "
            f"graph={result['graph_path_accuracy']:.2f} {result['latency_ms']}ms",
            flush=True,
        )
    summary = summarize(results)
    metadata = {
        "commit": git_commit(),
        "corpus_version": corpus_version(),
        "stub": args.stub,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    if args.json_out:
        args.json_out.write_text(
            json.dumps(
                {"metadata": metadata, "summary": summary, "results": results},
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        print(f"wrote {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
