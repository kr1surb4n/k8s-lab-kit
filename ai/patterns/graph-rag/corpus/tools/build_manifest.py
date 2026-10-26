#!/usr/bin/env python3
"""Regenerate corpus/MANIFEST.json from the documents in corpus/docs."""
import hashlib
import json
import sys
from datetime import date, datetime
from pathlib import Path

import yaml

# The corpus directory, two levels above this tool.
CORPUS = Path(__file__).resolve().parents[1]
DOCS = CORPUS / "docs"
MANIFEST = CORPUS / "MANIFEST.json"
VERSION_FILE = CORPUS / "VERSION"


# Read the one-line corpus version.
def read_version():
    return VERSION_FILE.read_text(encoding="utf-8").strip()


# Split a Markdown file into its YAML front matter and its body.
def split_front_matter(text, path):
    if not text.startswith("---\n"):
        raise ValueError(f"{path}: missing YAML front matter")
    try:
        _, meta, body = text.split("---\n", 2)
    except ValueError as exc:
        raise ValueError(f"{path}: unterminated YAML front matter") from exc
    return yaml.safe_load(meta) or {}, body


# Load one document and return the manifest entry for it.
def describe_document(path, version):
    raw = path.read_bytes()
    meta, body = split_front_matter(raw.decode("utf-8"), path)
    if meta.get("corpus_version") != version:
        raise ValueError(
            f"{path}: corpus_version {meta.get('corpus_version')!r} "
            f"does not match VERSION {version!r}"
        )
    return {
        "id": meta["id"],
        "title": meta["title"],
        "section": meta["section"],
        "path": str(path.relative_to(CORPUS)),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "words": len(body.split()),
        "source": datetime_to_string(meta["source"]),
    }


# Turn YAML date values into plain strings so the manifest is JSON and stable.
def datetime_to_string(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: datetime_to_string(item) for key, item in value.items()}
    if isinstance(value, list):
        return [datetime_to_string(item) for item in value]
    return value


# Build the whole manifest in a deterministic order.
def build_manifest():
    version = read_version()
    paths = sorted(DOCS.glob("*.md"))
    if not paths:
        raise ValueError(f"no documents in {DOCS}")
    docs = [describe_document(path, version) for path in paths]
    ids = [doc["id"] for doc in docs]
    duplicates = sorted({doc_id for doc_id in ids if ids.count(doc_id) > 1})
    if duplicates:
        raise ValueError(f"duplicate document ids: {', '.join(duplicates)}")
    return {
        "corpus_version": version,
        "document_count": len(docs),
        "documents": docs,
    }


# Write the manifest and report what changed.
def main():
    try:
        manifest = build_manifest()
    except (KeyError, ValueError, yaml.YAMLError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    text = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    MANIFEST.write_text(text, encoding="utf-8")
    print(
        f"wrote MANIFEST.json "
        f"({manifest['document_count']} documents, version {manifest['corpus_version']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
