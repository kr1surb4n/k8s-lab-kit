# Repository state — Kubernetes lab kit

**Snapshot:** 2026-10-26
**Path:** `/home/kris/00___Castle/07__WorkShops/k8s`
**Branch:** `main`
**HEAD:** `41c87d3 docs: import the hands-on exercise sheet`
**Offline gate:** `make test` → **36 passed, 0 failed, 0 skipped**
**Tracked files:** 187
**Working tree:** clean before this report was added

This report describes what the repository contains now, what changed in the
2026-10-25/26 session, what was salvaged from the abandoned capital-S copy, and
what is still open.

---

## 1. What this repository is

A self-contained Kubernetes workshop kit built from three sources:

1. the seven nginx exercises in `k8_zadanie1_koper_prompt.md`;
2. the 11-page PDF (`Kubernetes - Rozwinięcie Zagadnień.pdf`);
3. the 20-line outline the PDF cites (`kubernetes_podsumowanie.md`).

It contains the A1–A7 core lab, eight stack boilerplates, recovery drills, an
observability stack, a working RAG pattern with an evaluation baseline, an
imported Graph-RAG scaffold, cluster setup scripts, a fake `kubectl` for offline
docs, and a 36-test offline suite.

The authoritative remaining-work plan is `analysis/07-what-to-do.md`. The short
current-state pointer is `resume.md`. The phase list is `analysis/02-todo.md`.

---

## 2. Phase status

| Phase | Area | Status | Evidence |
|---|---|---|---|
| 0 | Host prerequisites | **done** | `docs/example-runs.md` |
| 1 | Cluster | **done** | `docs/example-runs.md` |
| 2–8 | A1–A7 core lab | **done** | `manifests/`, `docs/runbooks.md`, `docs/example-runs.md` |
| 9 | PDF topics (distribution, Helm, Ingress, storage, drills) | **partial** | `docs/coverage-matrix.md` |
| 10 | Kit hardening | **partial** | `make check` green; Coat not installed |
| 11 | Traceability against the outline | **partial** | some `partial` rows remain |
| 12 | Hardware gate and boilerplates | **done** | `boilerplates/`, `paczki/k8s/` |
| 13 | Recovery drills | **done** | `recovery/`, `scripts/lab-drill.sh` |
| 14 | Eight stack templates | **done** | `boilerplates/stacks/` |
| 15 | Observability | **mostly done** | stack healthy; both apps instrumented; alert webhook open |
| 16 | RAG pattern + evaluation | **done** | `ai/patterns/rag/`, `ai/patterns/rag/eval/results.json` |
| 17 | Graph RAG | **scaffold imported, not built** | `ai/patterns/graph-rag/`, `PROVENANCE.md` |
| 18 | Cloud free tier | **not started** | plan in `analysis/07` §5 |

Phases 9–11 are the only old phases with open boxes; they are documented rather
than silently marked complete.

---

## 3. What was done in this session

### 3.1 Cleanup and truth-up

- Moved the Phase 16 evaluation output to `ai/patterns/rag/eval/results.json`
  and committed it as the baseline.
- Repaired the corrupted `.gitignore` rule that had swallowed the eval output
  and split it into `*.secret.yaml` plus the eval-results rule.
- Corrected status text in `resume.md`, `analysis/02-todo.md` and
  `docs/example-runs.md`, which had described finished phases as open and
  mixed real transcripts with fake-shim output.
- Verified the `observability` namespace was healthy before the later reboot
  cycle.

### 3.2 Phase 15 — trace-to-log correlation

**RAG mockup (`ai/patterns/rag/mockup/main.py`)**

- The response and the `X-Trace-ID` header now carry the **live OpenTelemetry
  span id**, not a random UUID.
- Tracing is set up before application startup.
- Dependency pins were corrected so the image builds.
- A GPU-free overlay was added at `ai/patterns/rag/overlays/local/` for
  minikube runs without the model stack.

**FastAPI boilerplate (`boilerplates/stacks/python-fastapi/main.py`)**

- Instrumented with the OTel SDK and a pure ASGI logging middleware, so the
  structured log line carries the active trace id.
- Added `httpx` and `setuptools<81` (the instrumentation still imports
  `pkg_resources`).
- Fixed probe paths to `/healthz`.

**Verified end to end:** traces
`f86f678f38135c6deb3f33a81670bb24` and
`bd627ac76f5b353d122f2a0fb5c34a07` exist in Tempo, and the matching log lines
carry the same ids. The transcript is recorded in `docs/example-runs.md` §8.

**Still open:** one Alertmanager alert routed to an in-cluster webhook receiver,
with a delivered test alert. Alertmanager is currently `enabled: false` in
`observability/values/kube-prometheus-stack.yaml`.

### 3.3 Salvage from the capital-S copy

The abandoned copy at `~/00___Castle/07__WorkShOps/k8s` was a partial duplicate:
55 files, a single commit (`db68801`), and 134 files missing compared with the
current repo. Its `DOCUMENTATION.md` was **not** imported because it claims all
phases are complete, including the unfinished Phase 17 and 18.

What was imported, and what was changed first:

| Imported path | What it is | Changes made on import |
|---|---|---|
| `ai/patterns/graph-rag/` | Graph-RAG scaffold: mockup, eval, contracts, failure modes, manifests | Removed duplicated FastAPI routes; removed two no-op loops; replaced random trace ids with the live span id; moved tracing before startup; fixed the OTLP endpoint; fixed the kustomization; replaced the broken requirements set with a buildable one; fixed `make deploy`/`clean` paths |
| `cloud/README.md` | Free-tier provider research | Added a provenance warning; noted the placeholder bootstrap URL and the absence of Terraform |
| `docs/exercises/EXERCISES.md` | Hands-on exercise sheet | Added a provenance warning; noted that `make build`/`deploy`/`eval` belong to the pattern Makefiles and `SCENARIO=aX` is a placeholder |
| `ai/patterns/README.md` | Pattern catalogue | Added `graph-rag` to the tree and the pattern index |

Each imported directory carries a provenance marker. The Graph-RAG scaffold has
a full `PROVENANCE.md` with source path, commit, changes, and known limitations.

**Not imported:** `DOCUMENTATION.md` (false completion claims). Its structure is
already covered by `README.md`, `resume.md` and this report.

**Removed:** the capital-S copy, after backing it up to
`/tmp/opencode/workShOps-k8s-2026-10-26.tar.gz` (143 KB, includes untracked
files) and `/tmp/opencode/workShOps-k8s-2026-10-26.bundle` (36 KB, git history).
The empty parent `07__WorkShOps` was also removed. Only
`07__WorkShops` (lowercase `s`) remains.

### 3.4 Commits added in this session

```
41c87d3 docs: import the hands-on exercise sheet
af607b4 docs(cloud): import free-tier provider notes
b9190f5 feat(ai): import graph-rag scaffold from the abandoned copy
9cf64ab docs: record trace-to-log verification for phase 15
54f5706 feat(observability): instrument the FastAPI stack with OTel
fa9c137 fix(rag): add a GPU-free local overlay
daa4a09 fix(rag): use the live OTel span id in logs and responses
9e0aafb docs: correct the recorded test count
8d88815 docs: mark executed phases in the work list
3e0729b docs: refresh resume status after phase 16
ce48bf2 docs(rag): record phase 16 evaluation baseline
```

---

## 4. Current layout

```
ai/                 RAG baseline + imported Graph-RAG scaffold
analysis/           source analyses, phase list, remaining work
app/                small demo app
bastion/            host + in-cluster bastion scaffold (not deployed)
boilerplates/       base + 8 stack overlays
cloud/              imported free-tier provider notes (no Terraform yet)
clusters/           minikube, kind, k3d, k3s, managed skeletons
coat/               Coat module and installer (dry-run only)
docs/               runbooks, example runs, coverage matrix, exercises
manifests/          A1, A2, A3, A5, A6, A7
observability/      kube-prometheus-stack values + install script
paczki/k8s/         eight reusable templates
recovery/           recovery method + drills
scripts/            lab lifecycle, doctor, cluster, demo fake kubectl
setup/              user-space tool installer
site/               static site for A1
tests/              offline suite (36 tests)
```

---

## 5. Verification

| Check | Result |
|---|---|
| `make test` | **36 passed, 0 failed, 0 skipped** |
| `git status` | clean before the report |
| Graph-RAG image build | `boilerplate/graph-rag-api:1.0` built successfully |
| Graph-RAG smoke test | `/healthz` OK; query returns `graph_path`; `X-Trace-ID` present |
| Graph-RAG kustomize | `kubectl kustomize ai/patterns/graph-rag/k8s` renders |
| Observability | healthy earlier in the session; minikube stopped at snapshot time |

The imported Graph-RAG YAML and Python are **not** part of the 36-test suite.
They were smoke-tested by hand only.

---

## 6. Open work

### Phase 15 — one box

- Enable Alertmanager, add one receiver pointing at a small in-cluster webhook,
  break a pod on purpose, and record the delivery.

### Phase 17 — Graph RAG

The imported scaffold is raw material, not a working Phase 17. Remaining:

1. Corpus of ~20 documents with provenance and SHA-256 per chunk.
2. Golden set of 30–50 questions, including relation-only traps.
3. Postgres schema: `documents`, `chunks`, `embeddings`, `nodes`, `edges`,
   `edge_nodes`, `provenance`; pgvector + optional AGE; idempotent migrations.
4. Ingest: chunk, embed on the host GPU via Ollama, extract entities and at
   least one real hyperedge, upsert by document hash.
5. Retrieval service: hybrid BM25 + vector, reciprocal-rank fusion, 2-hop graph
   expansion, rerank, citations, OTel spans.
6. Eval: recall@k, citation precision, faithfulness, p50/p99 latency,
   graph-path hit rate, `results.json` with commit and corpus version.
7. Failure acceptance: deleted document, empty `edge_nodes`.
8. K8s packaging with a local GPU-free overlay.

Decisions already made: plain Postgres tables + recursive CTEs are primary and
Apache AGE is optional; real models only through host Ollama; the corpus is the
kit's own documentation.

**Blocker:** Ollama is installed but no models are pulled yet. A real run needs
model downloads on the RTX 5070 Laptop (8 GiB).

### Phase 18 — cloud free tier

Plan-only until an account exists. Deliverable: Oracle Cloud Always Free notes,
Terraform that passes `validate`/`plan`, an unchanged A6 overlay, and a teardown
checklist written before provisioning. Nothing billable may be created.

### Older partial boxes

Phases 9–11 still have the distribution/Helm/Ingress/storage/traceability items
listed in `analysis/02-todo.md`. They are lower priority than 15, 17 and 18.

---

## 7. Notes and risks

- **Minikube is stopped at snapshot time.** Start it with
  `minikube start --driver=docker` before cluster work.
- **Build images with host Docker, then `minikube image load`.** `minikube
  docker-env` does not work reliably on this setup.
- **The Graph-RAG manifest still requests a GPU and contains placeholder
  secrets (`changeme`).** Do not apply it as-is.
- **`analysis/07-what-to-do.md` says Phase 17 is "not started".** That remains
  true for the phase deliverable; the imported directory is a scaffold only.
- **`DOCUMENTATION.md` from the old copy is gone.** Do not recreate its
  "all phases complete" claim.
- **Backups of the removed copy are in `/tmp/opencode/`.** `/tmp` may be cleared
  on reboot; copy them somewhere durable if they need to be kept.

---

## 8. How to continue

```bash
cd /home/kris/00___Castle/07__WorkShops/k8s
make test                 # expect 36/36
git status                # expect clean
sed -n '1,200p' analysis/07-what-to-do.md

# Phase 15 leftover
minikube start --driver=docker
kubectl -n observability get pods

# Phase 17, after models are pulled
make -C ai/patterns/graph-rag build
make -C ai/patterns/graph-rag deploy

# Phase 18, plan only
terraform -chdir=cloud/oracle init -backend=false
terraform -chdir=cloud/oracle validate
```
