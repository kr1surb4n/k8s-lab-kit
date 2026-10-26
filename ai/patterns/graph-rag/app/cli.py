"""Command line entry point: ingest, search, ask, stats, serve, mcp."""
from __future__ import annotations

import argparse
import json
import logging
import sys
from typing import Any

from .config import PRIVATE_CORPORA, Settings, load_settings
from .db import connect, corpus_stats
from .ingest import ingest_corpus
from .retrieval import answer, search

DEFAULT_DB_FOR_CORPUS = {"lab": "eval", "notes": "private", "papers": "private"}


# Print a search result in a readable form.
def print_search(result: dict[str, Any]) -> None:
    for chunk in result["chunks"]:
        page = f" p.{chunk['page_start']}" if chunk.get("page_start") else ""
        print(f"{chunk['chunk_id']}  {chunk['title']}{page}  rrf={chunk['rrf']:.4f}")
        print("  " + " ".join(chunk["text"].split())[:240] + "\n")
    graph = result.get("graph_path") or []
    if graph:
        print(f"graph: {len(graph)} relation(s)")
        for edge in graph[:10]:
            if "members" in edge:
                print(f"  ({', '.join(edge['members'])}) --{edge['relation']}-->")
            else:
                print(f"  {edge['source']} --{edge['relation']}--> {edge['target']}")


# Print an answer with its citations.
def print_answer(result: dict[str, Any]) -> None:
    print(result["answer"])
    if result["citations"]:
        print("\nCitations:")
        for citation in result["citations"]:
            print(f"  {citation['chunk_id']}  {citation['title']}")
    print(
        f"\ntrace={result['trace_id']} model={result['model_version']} "
        f"latency={result['latency_ms']}ms"
    )


# Resolve a --db value to a DSN.
def resolve_dsn(settings: Settings, name: str) -> str:
    if name in settings.databases:
        return settings.dsn(name)
    if name.startswith("postgres"):
        return name
    raise SystemExit(f"unknown database {name!r}; use eval, private, or a DSN")


# Reject a private corpus in the evaluation database.
def guard_corpus_db(corpus: str, db_name: str, dsn: str, settings: Settings) -> None:
    # Compare the resolved DSN as well, so an explicit eval URL cannot bypass
    # the name check.
    if corpus in PRIVATE_CORPORA and (
        db_name == "eval" or dsn == settings.dsn("eval")
    ):
        raise SystemExit(
            f"{corpus} holds private documents and must use the private database"
        )
    if corpus == "lab" and (db_name == "private" or dsn == settings.dsn("private")):
        raise SystemExit("the lab evaluation corpus belongs in the eval database")


# Run the ingest subcommand.
def cmd_ingest(args: argparse.Namespace) -> int:
    settings = load_settings(args.config)
    db_name = args.db or DEFAULT_DB_FOR_CORPUS.get(args.corpus, "private")
    dsn = resolve_dsn(settings, db_name)
    guard_corpus_db(args.corpus, db_name, dsn, settings)
    extract_mode = args.extract
    if extract_mode == "auto":
        extract_mode = "tags" if args.corpus == "papers" else "llm"
    if args.stub and extract_mode in ("llm", "tags"):
        extract_mode = "stub"
    result = ingest_corpus(
        settings,
        dsn,
        args.corpus,
        limit=args.limit,
        stub=args.stub,
        extract_mode=extract_mode,
        force=args.force,
        chunk_words=args.chunk_words,
        overlap=args.overlap,
        prune=args.prune,
    )
    print(json.dumps(result, indent=2))
    return 0


# Run the search subcommand.
def cmd_search(args: argparse.Namespace) -> int:
    settings = load_settings(args.config)
    db_name = args.db or ("eval" if args.corpus == "lab" else "private")
    result = search(
        settings,
        resolve_dsn(settings, db_name),
        args.query,
        corpus=args.corpus,
        k=args.k,
        stub=args.stub,
    )
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print_search(result)
    return 0


# Run the ask subcommand.
def cmd_ask(args: argparse.Namespace) -> int:
    settings = load_settings(args.config)
    db_name = args.db or ("eval" if args.corpus == "lab" else "private")
    result = answer(
        settings,
        resolve_dsn(settings, db_name),
        args.question,
        corpus=args.corpus,
        top_k=args.top_k,
        stub=args.stub,
    )
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print_answer(result)
    return 0 if not result["refused"] else 2


# Run the stats subcommand.
def cmd_stats(args: argparse.Namespace) -> int:
    settings = load_settings(args.config)
    with connect(resolve_dsn(settings, args.db or "private")) as conn:
        stats = corpus_stats(conn, args.corpus)
    print(json.dumps(stats, indent=2))
    return 0


# Run the HTTP service.
def cmd_serve(args: argparse.Namespace) -> int:
    import uvicorn

    uvicorn.run(
        "app.api:app",
        host=args.host,
        port=args.port,
        log_level="info",
    )
    return 0


# Run the MCP stdio server for Hermes.
def cmd_mcp(_: argparse.Namespace) -> int:
    from .mcp_server import main as mcp_main

    mcp_main()
    return 0


# Build the parser and dispatch the chosen command.
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="graphrag", description="Local Graph RAG")
    parser.add_argument("--config", help="path to config.yaml")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest = subparsers.add_parser("ingest", help="index a corpus")
    ingest.add_argument("corpus", choices=["lab", "notes", "papers"])
    ingest.add_argument("--db", help="eval, private, or a DSN")
    ingest.add_argument("--limit", type=int, help="only the first N documents")
    ingest.add_argument("--stub", action="store_true", help="deterministic local stub")
    ingest.add_argument(
        "--extract",
        choices=["auto", "llm", "tags", "stub", "none"],
        default="auto",
        help="graph extraction; auto uses tags for papers and the LLM for notes/lab",
    )
    ingest.add_argument("--force", action="store_true", help="reindex unchanged documents")
    ingest.add_argument("--prune", action="store_true", help="delete documents that disappeared")
    ingest.add_argument("--chunk-words", type=int)
    ingest.add_argument("--overlap", type=int)
    ingest.set_defaults(func=cmd_ingest)

    search_cmd = subparsers.add_parser("search", help="retrieve chunks")
    search_cmd.add_argument("query")
    search_cmd.add_argument("--corpus", default="notes,papers")
    search_cmd.add_argument("--db")
    search_cmd.add_argument("--k", type=int, default=8)
    search_cmd.add_argument("--stub", action="store_true")
    search_cmd.add_argument("--json", action="store_true")
    search_cmd.set_defaults(func=cmd_search)

    ask = subparsers.add_parser("ask", help="answer a question with citations")
    ask.add_argument("question")
    ask.add_argument("--corpus", default="notes,papers")
    ask.add_argument("--db")
    ask.add_argument("--top-k", type=int)
    ask.add_argument("--stub", action="store_true")
    ask.add_argument("--json", action="store_true")
    ask.set_defaults(func=cmd_ask)

    stats = subparsers.add_parser("stats", help="row counts per corpus")
    stats.add_argument("--db")
    stats.add_argument("--corpus")
    stats.set_defaults(func=cmd_stats)

    serve = subparsers.add_parser("serve", help="run the local HTTP API")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8099)
    serve.set_defaults(func=cmd_serve)

    mcp = subparsers.add_parser("mcp", help="run the MCP stdio server")
    mcp.set_defaults(func=cmd_mcp)

    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    # Keep HTTP client request logs quiet; our own query log line is enough.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
