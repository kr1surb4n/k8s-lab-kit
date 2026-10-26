# What is to be done — remaining work after Phase 16

This is the accurate, current work description. It complements the short
pointer in `resume.md` and the phase list in `analysis/02-todo.md`.

Written: 2026-10-25; updated 2026-10-26
Branch: `main`
HEAD: `0856b88` before the Phase 17 model-selection commit; see `git log -1`

---

## 1. Where the tree actually stands

| Area | State | Evidence |
|---|---|---|
| Phases 0–11 (core lab A1–A7, kit hardening, traceability) | **done** | commits `0db5723` … `ae54839`, `docs/example-runs.md`, `docs/coverage-matrix.md` |
| Phase 12 — boilerplates and paczki | **done** | `boilerplates/`, `paczki/k8s/`, commit `d45d7b1` |
| Phase 13 — recovery drills | **done** | `recovery/`, `scripts/lab-drill.sh`, commit `f94145c` |
| Phase 14 — other stacks | **done** | `boilerplates/stacks/` (8 stacks), commit `da0b869` |
| Phase 15 — observability | **done** | commits `5e920a2`, `fffdfc0`; trace and webhook proofs in `docs/example-runs.md` §8–§9 |
| Phase 16 — RAG pattern | **done** | `ai/patterns/rag/`, commits `c1adaae` … `f7b0f3c` |
| Phase 17 — Graph RAG | **local app, private notes/papers index, and local eval baseline done; optional packaging open** | `ai/patterns/graph-rag/app/`, private DB on 5434, `app/README.md` |
| Phase 18 — cloud free tier | **not started** | same |
| `make test` | **38/38 green** | verified on a clean checkout of `HEAD` |
| minikube | **running** | control plane, kubelet, apiserver up |
| Host headroom | ~151 GiB free disk, ~11 GiB available RAM | `df -h /`, `free -h` |

Two cleanup items were done while writing this description:

- The abandoned rewrite of `scripts/demo/kubectl` in the working tree (it did not
  parse and broke `make check`) was discarded. A copy is kept at
  `/tmp/opencode/kubectl-wip-backup/kubectl.broken` in case any idea from it is
  wanted. `HEAD`'s version is the one that passes the suite.
- The last line of `.gitignore` was a corrupted rule (`*.secret.yamleval/results.json`);
  it is now `*.secret.yaml` plus a separate `eval/results.json` rule.

---

## 2. Cleanup before new phases (S, do first)

- [x] Re-run `make test` and confirm 38/38 after the two cleanup edits.
- [ ] Decide what to do with the untracked `eval/results.json` (it is the Phase 16
      RAG eval output). Keep it ignored, or move it to `ai/patterns/rag/eval/`
      and commit a baseline. Do not commit it at the repo root.
- [ ] Truth-up the status documents so they stop lying:
  - `resume.md` says "this folder is not a git repo" and "phases 12–17 exist only
    as plans". Both are false now.
  - `analysis/02-todo.md` leaves every Phase 0–11 checkbox open although those
    phases ran on the real cluster.
  - `docs/example-runs.md` mixes the first real A1 transcript with fake-shim output;
    label which is which.
- [ ] Confirm the observability namespace is still healthy after the reboot/test
      cycle: `kubectl -n observability get pods`.

**Verify:** `make test` 38/38, `git status` clean except intentionally ignored
files, `resume.md` matches the commit log.

---

## 3. Phase 17 — RAG with graphs and hypergraphs (L, the big remaining item)

Design source: `analysis/06-scope-expansion.md`, section **T5**, and the working
RAG baseline in `ai/patterns/rag/`.

Goal: answers that trace back to documents **and** to relations between them,
with a reproducible score per commit.

Proposed location: `ai/patterns/graph-rag/` (same shape as the Phase 16 entry, so
the catalogue stays uniform). Keep `ai/patterns/rag/` untouched as the baseline.

**Model decision (done, 2026-10-26):** embeddings use `bge-m3-local` (1024-dim,
8192 ctx); generation uses `granite3.3-8b-local` (Q4_K_M, 8k runtime context)
with `qwen3-8b-local` as the fallback. The GGUFs were already local; both
required models are imported and verified. Reranking starts as a listwise LLM
prompt on Granite; add `BAAI/bge-reranker-v2-m3` only if the evaluation
justifies it. See `ai/patterns/graph-rag/models/README.md`.

**Host note:** a `llama.cpp` server was holding about 6.4 GiB of the 8 GiB GPU
when the models were verified. Stop it only if it is yours; otherwise the 8B
model runs on CPU (correct but slow).

### Local private extension (2026-10-26)

The Phase 17 app is also a working local tool over the personal notes in
`~/Documents` and the paper library under `~/00___Castle/99_TEMP/download-papers`.
It deliberately does not use a cluster for private data:

- **Eval DB:** `graphrag` on `5433`, corpus `lab`, 20 documents / 42 golden
  questions. Private corpora are rejected by the CLI guard.
- **Private DB:** `graphrag_private` on `5434`, corpora `notes` and `papers`, own
  named volume and compose profile `private`.
- **Notes index:** 179 documents, 1,608 chunks/embeddings, 1,204 edges. Includes
  PDFs, DOCX, Markdown, text, and saved HTML up to 30 MB.
- **Papers index:** 861 documents, 24,745 chunks/embeddings, 7,021 edges. 634
  have full PDF text, 227 are summary-only. Graph edges come from summary tags
  (`HAS_TOPIC`, `COVERS_TOPICS`), not 861 LLM calls.
- **Interfaces:** CLI (`app/cli.py`), HTTP (`POST /v1/search`, `POST /v1/ask`),
  MCP stdio (`search_knowledge`, `ask_knowledge`, `list_corpora`).
- **Privacy:** local Ollama and local Postgres only; config at
  `~/.config/graphrag/config.yaml` (0600, git-ignored). MCP strips absolute
  paths, but Hermes must use a local model (`granite3.3-8b-local` or
  `qwen3-8b-local`), not the default `gpt-oss:120b-cloud`, or snippets leave
  the machine.

### 17.1 Corpus and golden set (M)

- [x] A 20-document sample corpus with known answers, committed to the repo.
- [x] Provenance per chunk: source path, page/section, SHA-256 of the source,
      corpus version (plus optional PDF page numbers).
- [x] A golden question set of 42 questions, each with:
      `question`, `expected_doc_ids`, `expected_answer_facts`, `must_cite`.
- [x] A "trap" subset that only the graph layer can answer (relation questions).

**Acceptance:** every golden question is answerable from the corpus alone, and a
human can check the expected citations by hand.

### 17.2 Storage schema (M)

- [x] Postgres with `pgvector`; Apache AGE is **not** used. The graph is plain
      tables and recursive CTEs. Two databases: eval on 5433, private on 5434.
- [x] Tables: `documents` (with `corpus`), `chunks` (with page numbers),
      `embeddings`, `nodes`, `edges`, `edge_nodes`, `provenance`.
- [x] Idempotent migrations (`schema.sql` + `make migrate` / `private-migrate`).
- [x] Indexes: HNSW cosine on vectors, GIN on tsvector, edge membership indexes.

**Acceptance:** `make migrate` twice produces the same schema and exit 0.

### 17.3 Ingest job (M–L)

- [x] Chunk (fixed size + overlap; record offsets and PDF page numbers).
- [x] Embed on the host GPU (`bge-m3-local`) with a deterministic stub embedder
      for offline tests.
- [x] Extract entities and relations; pairwise edges plus real hyperedges
      (lab `OWNS/REQUIRES`, paper `COVERS_TOPICS`).
- [x] Write provenance for every chunk, node, and edge.
- [x] Re-running ingest skips unchanged documents by content hash; `--prune`
      removes missing files; each document commits separately.

**Acceptance:** row counts after a second run are identical; the hyperedge join
table returns the expected 3-member relation for a known document set.

### 17.4 Retrieval service (L)

- [x] One small Python service, run on the host as CLI, HTTP, and MCP
      (`ai/patterns/graph-rag/app/`); Kubernetes packaging is not done.
- [~] Hybrid retrieve (Postgres ts_rank + vector, RRF k=60) → one-hop graph
      context. No query rewrite, no two-hop expansion.
- [ ] Rerank with a listwise LLM prompt; deferred. RRF order goes to the
      generator in the current app.
- [x] Response contract: `answer`, `citations[]` (doc id, chunk id, span,
      page), `graph_path[]`, `scores`, `trace_id`, `prompt_version`,
      `model_version`.
- [ ] OpenTelemetry spans. The app writes a structured log line with the same
      `trace_id`; no exporter or Tempo.
- [x] Guardrails: refuse below the cosine threshold, and only cite a chunk that
      was actually retrieved.

**Acceptance:** a question returns an answer whose citations resolve to real
chunks; a relation-only question returns the graph path that justified it.

### 17.5 Evaluation harness (M)

- [x] `eval/local_eval.py` computes recall@k, citation precision, strict
      answer-fact match, refusal correctness, latency p50/p95, and graph-path
      hit rate.
- [x] Writes JSON with the git commit and corpus version.
- [~] `make eval-local` runs against the real lab index. Offline determinism is
      covered by 36 app tests; a full stub golden run would need a separate DB.
- [x] Record the real baseline: recall@k 1.00, citation precision 0.75, strict
      fact match 0.825, graph-path accuracy 0.7875, refusal correctness 1.00,
      latency p50 2,364 ms / p95 3,266 ms at commit `b005ffb`.

**Acceptance:** two consecutive offline runs produce identical scores; the real
run is recorded with its commit hash.

### 17.6 Failure acceptance (S)

- [ ] Delete a document that a golden answer cites → the answer must change and
      the deleted citation must disappear.
- [ ] Break the graph layer (empty `edge_nodes`) → relation questions must fail
      loudly, not silently fall back to a confident wrong answer.
- [ ] Document both outcomes in `failure-modes.md` with the metric each one moves.

Not run as a destructive drill yet. The observed ingest failures (NUL bytes,
bad edge ids, filtered HNSW, truncated extraction) are documented with their
fixes in `failure-modes.md`.

### 17.7 Kubernetes packaging (M)

- [ ] `ai/patterns/graph-rag/k8s/` with kustomize base + overlay, non-root,
      resource requests/limits, readiness/liveness probes.
- [ ] Secrets via `Secret` (`envFrom`), never inline credentials.
- [ ] NetworkPolicy allowing only Postgres + OTel collector.
- [ ] Honest resource note: Postgres+AGE+pgvector plus the service must fit
      alongside the observability stack on a 6 GiB minikube.

Deferred: the private tool runs on the host by design so personal notes do not
enter the lab cluster. The lab corpus still has no in-cluster service.

**Verify (Phase 17 done):**
`make -C ai/patterns/graph-rag up` → `make eval` → `make -C ai/patterns/graph-rag down`,
with the score table and one trace id pasted into the README.

---

## 4. Phase 15 — closed (S–M)

Both boxes are done:

- [x] Instrument two deployed apps with the OTel SDK (RAG mockup and FastAPI
      stack) so the log line carries the trace id visible in Tempo. Verified
      end to end; see `docs/example-runs.md` §8.
- [x] Route one alert to a webhook (Alertmanager receiver), and prove it fires.
      `LabWebhookTest` and a real `PodNotReady` from an unschedulable pod both
      reached the in-cluster receiver; see `docs/example-runs.md` §9.

**Verify (done):** one LAN request is traceable end to end (Grafana → Tempo →
log line), and a deliberately broken pod produces a webhook delivery.

---

## 5. Phase 18 — Cloud free tier (S–M, time-boxed)

Design source: `analysis/06-scope-expansion.md`, section **T6**.

Recommendation: **Oracle Cloud Always Free** (4 OCPU Ampere + 24 GiB, k3s on a
VM) because it is the only option that does not expire. GKE free zonal tier is
the fallback if Oracle capacity is unavailable.

- [ ] Write the budget/teardown note **first**: `cloud/<provider>/README.md` —
      what is free, what is billable, what expires, every delete command.
- [ ] Provision the smallest free shape with Terraform (or documented CLI);
      keep state out of git.
- [ ] Install k3s (or use the managed control plane); record the kubeconfig
      handling without committing it.
- [ ] Deploy the A6 stack **unchanged**; if an overlay is needed, it lives in
      `cloud/<provider>/overlay/` and the diff is one line.
- [ ] Prove outside access (public IP + Service, or a documented
      `kubectl port-forward`).
- [ ] Tear everything down; screenshot/record the zero-cost page and paste the
      exact commands into the README.

**Verify:** the A6 page answers from outside the LAN, the teardown is reproducible
from the written checklist, and no billable object remains.

---

## 6. Suggested order and commits

1. `chore: fix corrupted gitignore rule` — already staged work in §2.
2. `docs: replace stale resume and todo status` — §2 truth-up.
3. `docs: describe remaining work for phases 17–18` — this file.
4. `feat(ai): graph-rag corpus, schema and ingest` — 17.1–17.3.
5. `feat(ai): graph-rag retrieval service with tracing` — 17.4, 17.7.
6. `test(ai): graph-rag evaluation harness and baseline` — 17.5–17.6.
7. `feat(observability): instrument app and route one alert` — §4.
8. `docs(cloud): free-tier budget, deployment and teardown` — Phase 18.

Run `make test` before each commit; each phase ends only when its own verify
step passes. Do not start Phase 18 until Phase 17's baseline score is recorded.

---

## 7. Known traps to respect

| Trap | Where it bites | Handle |
|---|---|---|
| pgvector + AGE in one image | extension availability differs per tag | pin the image and test `CREATE EXTENSION` on first run |
| GPU models are not in the cluster | eval cannot run on a clean machine | ship a deterministic stub for CI and a recorded real run |
| graph expansion hides bad retrieval | confident wrong answers | score graph-path hit rate separately; fail loudly when empty |
| `eval/results.json` at repo root | accidentally committed / ignored by a broken rule | fixed rule; keep output under the pattern directory |
| minikube 6 GiB | Postgres + observability + app at once | one stack at a time, `make doctor` before starting |
| cloud trial expiry | surprise bill | teardown checklist written before provisioning |

---

## 8. Definition of done for the whole kit

- `make test` → 38/38 on a clean checkout.
- Phases 0–18 each have: commands, expected output, a verification step, and a
  transcript or recorded score.
- `analysis/02-todo.md`, `resume.md`, `docs/coverage-matrix.md` describe what
  actually ran, with no open `partial` rows.
- The RAG and Graph-RAG scores are recorded per commit.
- The cloud experiment is torn down and the zero bill is documented.
