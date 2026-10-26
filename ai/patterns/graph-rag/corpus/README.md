# Evaluation corpus — Phase 17

Twenty short documents about the Kubernetes objects and exercises in this kit.
They exist so the Graph RAG pattern can be measured against answers a human can
check by hand, not against invented questions.

## Why these documents

- Each document covers **one concept** used by the lab (a resource, a mechanism,
  or one exercise) and states facts that appear in `docs/runbooks.md` or in
  `manifests/`. The statements are true of this kit, not a copy of the upstream
  Kubernetes documentation.
- The documents are **purpose-written**, but each one lists the repo files it was
  grounded in. `PROVENANCE.md` explains why the corpus is not a snapshot of the
  runbooks: runbooks change every time a step is fixed, and the evaluation needs
  a stable source with known answers.
- The set is deliberately small. Twenty documents are enough to exercise chunking,
  hybrid retrieval, entity extraction and multi-hop questions, and small enough
  that a person can read the whole thing in half an hour.

## Rules for editing

1. One concept per document. If a document needs two titles, split it.
2. Keep every factual statement checkable against the listed `based_on` paths, or
   against the document itself when the fact is definitional.
3. Do not change a document quietly. Bump `corpus_version` in every file (they
   are versioned together), regenerate `MANIFEST.json`, and re-run the golden
   set. A corpus change without a new eval result is an unmeasured change.
4. Never delete a document that a golden question cites without updating that
   question. `tools/validate_corpus.py` catches the dangling reference.

## Layout

```
corpus/
├── MANIFEST.json          # generated: ids, paths, titles, sha256, versions
├── VERSION                # one line, e.g. 2026-10-26.1
├── docs/                  # the documents, Markdown with YAML front matter
└── tools/
    ├── build_manifest.py  # regenerate MANIFEST.json from docs/
    └── validate_corpus.py # check front matter, hashes, and the golden set
```

## Front matter

```yaml
---
id: doc-01
title: Kubernetes objects used in this kit
section: "Concepts > Objects"
corpus_version: 2026-10-26.1
source:
  kind: authored
  snapshot: 2026-10-26
  based_on:
    - docs/runbooks.md#common-setup
    - manifests/a1/web.yaml
---
```

`id` is the citation key used by the golden set and the API. `section` is the
human-readable location used in chunk provenance. `based_on` is provenance for
the facts, not a claim that the file is a copy.

## Commands

```bash
make -C ai/patterns/graph-rag corpus-manifest   # rewrite MANIFEST.json
make -C ai/patterns/graph-rag corpus-check      # validate docs + golden set
```

Both are offline and dependency-free apart from PyYAML, which the kit already
uses.
