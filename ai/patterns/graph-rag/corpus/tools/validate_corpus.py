#!/usr/bin/env python3
"""Check the corpus, the manifest, and the golden question set."""
import json
import sys
from pathlib import Path

from build_manifest import CORPUS, build_manifest, read_version, split_front_matter

# The pattern directory and the golden set that accompanies the corpus.
PATTERN = CORPUS.parent
GOLDEN = PATTERN / "eval" / "golden_qa.jsonl"
REPO_ROOT = PATTERN.parents[2]

# The plan requires at least twenty documents and 30-50 questions.
MIN_DOCUMENTS = 20
MIN_QUESTIONS = 30
MAX_QUESTIONS = 50
MIN_RELATION = 8
MIN_REFUSAL = 2

REQUIRED_QUESTION_FIELDS = (
    "id",
    "kind",
    "question",
    "expected_doc_ids",
    "expected_answer_facts",
    "must_cite",
    "expected_graph_path",
)


# Fold case, dashes, quotes and whitespace so a fact check is about words.
def normalize(text):
    table = str.maketrans({"–": "-", "—": "-", "’": "'", "‘": "'", "“": '"', "”": '"'})
    return " ".join(text.translate(table).lower().split())


# Read the body of a document without its front matter.
def document_body(path):
    meta, body = split_front_matter(path.read_text(encoding="utf-8"), path)
    return body, meta


# Return a list of error strings for the corpus files and manifest.
def check_corpus():
    errors = []
    try:
        version = read_version()
        manifest = build_manifest()
    except (KeyError, ValueError, OSError) as exc:
        return [str(exc)], {}, {}

    stored_path = CORPUS / "MANIFEST.json"
    if not stored_path.exists():
        errors.append("MANIFEST.json is missing; run make corpus-manifest")
    else:
        stored = json.loads(stored_path.read_text(encoding="utf-8"))
        if stored != manifest:
            errors.append("MANIFEST.json is stale; run make corpus-manifest")

    documents = {doc["id"]: doc for doc in manifest["documents"]}
    if len(documents) < MIN_DOCUMENTS:
        errors.append(
            f"only {len(documents)} documents; the Phase 17 corpus needs {MIN_DOCUMENTS}"
        )

    bodies = {}
    # Check that every claimed source still exists in the repo.
    for doc in manifest["documents"]:
        path = CORPUS / doc["path"]
        try:
            bodies[doc["id"]], meta = document_body(path)
        except (OSError, ValueError) as exc:
            errors.append(f"{doc['id']}: {exc}")
            continue
        if meta.get("corpus_version") != version:
            errors.append(f"{doc['id']}: corpus_version is not {version}")
        for source in meta.get("source", {}).get("based_on", []):
            source_path = REPO_ROOT / source.split("#", 1)[0]
            if not source_path.exists():
                errors.append(f"{doc['id']}: based_on path not found: {source}")
    return errors, documents, bodies


# Check that a graph path entry is a triple or a real hyperedge.
def graph_entry_error(entry):
    if not isinstance(entry, dict):
        return "graph path entry is not an object"
    if {"source", "relation", "target"} <= entry.keys():
        return None
    if "members" in entry and "relation" in entry:
        if len(entry["members"]) < 3:
            return "hyperedge needs at least three members"
        return None
    return "graph path entry needs source/relation/target or relation/members"


# Return a list of error strings for the golden question set.
def check_golden(documents, bodies):
    errors = []
    if not GOLDEN.exists():
        return [f"{GOLDEN} is missing"]
    questions = []
    # Parse the JSONL file and reject malformed lines.
    for number, line in enumerate(GOLDEN.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            questions.append(json.loads(line))
        except json.JSONDecodeError as exc:
            errors.append(f"line {number}: invalid JSON: {exc}")

    if not MIN_QUESTIONS <= len(questions) <= MAX_QUESTIONS:
        errors.append(
            f"{len(questions)} questions; expected {MIN_QUESTIONS}-{MAX_QUESTIONS}"
        )

    ids = [question.get("id") for question in questions]
    duplicates = sorted({item for item in ids if ids.count(item) > 1})
    if duplicates:
        errors.append(f"duplicate question ids: {', '.join(duplicates)}")

    kinds = {"answerable": 0, "relation": 0, "refusal": 0}
    cited = set()
    seen_questions = set()

    # Validate one question at a time, so the error names it.
    for question in questions:
        qid = question.get("id", "<no id>")
        missing = [field for field in REQUIRED_QUESTION_FIELDS if field not in question]
        if missing:
            errors.append(f"{qid}: missing fields: {', '.join(missing)}")
            continue
        kind = question["kind"]
        if kind not in kinds:
            errors.append(f"{qid}: unknown kind {kind!r}")
            continue
        kinds[kind] += 1
        prompt = question["question"]
        if not isinstance(prompt, str) or not prompt.strip():
            errors.append(f"{qid}: empty question")
        if prompt in seen_questions:
            errors.append(f"{qid}: duplicate question text")
        seen_questions.add(prompt)

        doc_ids = question["expected_doc_ids"]
        unknown = [doc_id for doc_id in doc_ids if doc_id not in documents]
        if unknown:
            errors.append(f"{qid}: unknown doc ids: {', '.join(unknown)}")
        cited.update(doc_ids)

        facts = question["expected_answer_facts"]
        if not isinstance(facts, list) or not all(isinstance(f, str) for f in facts):
            errors.append(f"{qid}: expected_answer_facts must be a list of strings")
            facts = []

        text = normalize(" ".join(bodies.get(doc_id, "") for doc_id in doc_ids))
        for fact in facts:
            if normalize(fact) not in text:
                errors.append(f"{qid}: fact not found in cited docs: {fact!r}")

        path = question["expected_graph_path"]
        if not isinstance(path, list):
            errors.append(f"{qid}: expected_graph_path must be a list")
            path = []

        if kind == "refusal":
            if question["must_cite"]:
                errors.append(f"{qid}: refusal must set must_cite to false")
            if doc_ids or facts:
                errors.append(f"{qid}: refusal must not cite docs or facts")
            if path:
                errors.append(f"{qid}: refusal must not have a graph path")
        else:
            if not question["must_cite"]:
                errors.append(f"{qid}: must_cite must be true for {kind}")
            if not doc_ids:
                errors.append(f"{qid}: needs at least one expected doc")
            if not facts:
                errors.append(f"{qid}: needs at least one expected answer fact")

        if kind == "relation":
            if len(path) < 1:
                errors.append(f"{qid}: relation question needs a graph path")
            if len(set(doc_ids)) < 2:
                errors.append(f"{qid}: relation question needs at least two docs")
        for entry in path:
            problem = graph_entry_error(entry)
            if problem:
                errors.append(f"{qid}: {problem}")

    if kinds["relation"] < MIN_RELATION:
        errors.append(f"{kinds['relation']} relation questions; need {MIN_RELATION}")
    if kinds["refusal"] < MIN_REFUSAL:
        errors.append(f"{kinds['refusal']} refusal questions; need {MIN_REFUSAL}")

    uncovered = sorted(set(documents) - cited)
    if uncovered:
        errors.append(f"no golden question cites: {', '.join(uncovered)}")

    return errors, questions, kinds


# Print the summary or the errors.
def main():
    errors, documents, bodies = check_corpus()
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1
    errors, questions, kinds = check_golden(documents, bodies)
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1
    print(
        f"corpus ok: {len(documents)} documents, version {read_version()}, "
        f"{len(questions)} questions "
        f"({kinds['answerable']} answerable, {kinds['relation']} relation, "
        f"{kinds['refusal']} refusal)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
