# Resume — where this work stands

Read this first when coming back. It is deliberately short and points at the
details.

- **Folder:** `/home/kris/00___Castle/07__WorkShops/k8s`
- **Date:** 2026-10-26
- **State:** **Phases 0–16 done; Phase 17 local app, lab ingest, private notes/papers index and eval baseline done; optional packaging remains; Phase 18 open**
- **Git:** repository on `main`; conventional commits, one change per commit
- **Offline gate:** `make test` → **38 passed, 0 failed**; `make app-test` → **36 passed, 0 failed**
- **Private tool:** `ai/patterns/graph-rag/app/`, private DB on `5434`; see
  `app/README.md` and `~/.config/graphrag/config.yaml` (0600, not in git)
- **Local eval:** recall@k 1.00, citation precision 0.75, strict facts 0.825,
  graph path 0.7875, refusal 1.00, p50 2,364 ms / p95 3,266 ms (42 questions)
- **Cluster:** minikube **stopped** (start with `make cluster`); the observability stack and its data are still defined, not running
- **Full snapshot:** `docs/REPO-STATE.md`

## One paragraph

The lab is derived from three sources: the seven nginx exercises in
`k8_zadanie1_koper_prompt.md`, the 11-page PDF, and the 20-line outline the PDF
cites (`kubernetes_podsumowanie.md`). The core lab A1–A7 ran on a real minikube
cluster: A1 (host mount + live edit), A2 (ConfigMap + live edit), A3 (env
precedence), A4 (LAN access from a second machine), A5 (basic-auth Secret),
A6 (3 replicas + rolling update), A7 (nginx + PHP-FPM + PostgreSQL + SQLite).
The expansion tracks followed: boilerplates and paczki (12), recovery drills (13),
eight stack templates (14), the metrics/logs/traces stack (15), and the RAG
pattern with a recorded evaluation baseline (16). Graph RAG (17) now has a real
local app over the synthetic lab corpus plus the private notes and papers, with
a recorded golden-set baseline; optional packaging remains. The cloud free-tier
experiment (18) is still open; see `analysis/07-what-to-do.md`.

## What is done and verified

| Item | Evidence |
|---|---|
| Analysis of all three sources | `analysis/01` … `04` |
| Hardware profile and tiers | `analysis/05`, `make doctor` |
| Expanded scope, seven tracks | `analysis/06` |
| Ordered work list, phases 0–18 | `analysis/02-todo.md` |
| Remaining-work description | `analysis/07-what-to-do.md` |
| Core lab A1–A7 on a real cluster | `docs/example-runs.md`, `docs/coverage-matrix.md` |
| Runbooks A1–A7 + D1/H1/N1/T1 | `docs/runbooks.md` |
| Manifests for a1, a2, a3, a5, a6, a7 | `manifests/` |
| Eight paczki templates | `paczki/k8s/` |
| Boilerplate base + 8 stack overlays | `boilerplates/` |
| Four recovery drills (inject/recover) | `recovery/`, `scripts/lab-drill.sh` |
| Scripts: up, down, status, scale, rollout, tunnel, verify, doctor, env, mkpasswd, cluster-create, cluster-delete | `scripts/` |
| Fake kubectl for offline transcripts | `scripts/demo/kubectl` |
| Offline test suite | `tests/run.sh` → 38 passed |
| Phase 17 corpus + golden set | `ai/patterns/graph-rag/corpus/`, `eval/golden_qa.jsonl`; `make corpus-check` |
| Phase 17 storage schema | `ai/patterns/graph-rag/db/schema.sql`; `make db-check` → 8 tables, idempotent, hyperedge ok |
| Phase 17 local app + private index | `ai/patterns/graph-rag/app/`; notes 179 docs / 1,608 chunks / 1,204 edges; papers 861 / 24,745 / 7,021; CLI, HTTP, MCP verified |
| Phase 17 local eval baseline | `make eval-local`; recall 1.00, citations 0.75, facts 0.825, graph 0.7875, refusal 1.00 |
| Coat module, spells, installer | `coat/` (installer tested with `--dry-run`) |
| Observability full stack (Prometheus, Grafana, Loki, Tempo, OTel) | `observability/`, running in `observability` namespace |
| Alertmanager → in-cluster webhook | `observability/alert-webhook/`, proof in `docs/example-runs.md` §9 |
| RAG pattern + eval baseline | `ai/patterns/rag/`, `ai/patterns/rag/eval/results.json` |
| Phase 17 local model set | `ai/patterns/graph-rag/models/`; `bge-m3-local` + `granite3.3-8b-local` imported and verified |
| Bastion scaffold (host + in-cluster) | `bastion/` |
| Cluster skeletons (minikube, kind, k3d, k3s, managed) | `clusters/` |
| Tool installer (user-space + apt fallback) | `setup/install-tools.sh` |

## What is not done

1. **Phase 17 — Graph RAG.** §17.1 (corpus, provenance, golden set) and §17.2
   (schema, idempotent migrate, hyperedge encoding) are **done**. Remaining:
   §17.3 ingest (chunk, embed on the GPU, extract entities/relations, provenance),
   §17.4 retrieval service, §17.5 evaluation harness, §17.6 failure acceptance,
   §17.7 Kubernetes packaging. The corpus is 20 documents; the golden set is 42
   questions (30 answerable, 10 relation, 2 refusals). The imported scaffold in
   `ai/patterns/graph-rag/mockup/` is still mock-only and is not the deliverable.
   The detailed checklist is `analysis/07-what-to-do.md` §3; the model setup is
   `ai/patterns/graph-rag/models/README.md`.
2. **Phase 18 — cloud free tier.** Plan-only until an account is provided; the
   deliverable is provider docs, Terraform validated with `terraform plan`, the
   A6 overlay, and a teardown checklist.
3. **Coat is not installed.** Only `coat/install-coat.sh --dry-run` was run.
4. **Bastion not deployed.** Manifests and host config exist, not applied.
5. **`paczki/k8s` was not exercised through `paczek`.** The `fill_template`
   syntax (`{{ VAR }}`) matches Coat, but it was not run.

## Next actions, in order

```bash
cd /home/kris/00___Castle/07__WorkShops/k8s

# 1. confirm the kit still passes
make test

# 2. read the current plan
sed -n '1,120p' analysis/07-what-to-do.md

# 3. confirm the observability path is still alive
kubectl -n observability get pods
kubectl -n observability port-forward svc/alert-webhook 8080:80 &
curl -s http://127.0.0.1:8080/alerts | python3 -m json.tool

# 4. Phase 17 — confirm the local models first
ollama list | grep -E 'bge-m3|granite3.3|qwen3'
curl -s http://localhost:11434/api/embed \
  -d '{"model":"bge-m3-local","input":["hello"]}' \
  | python3 -c 'import json,sys; print(len(json.load(sys.stdin)["embeddings"][0]))'
# expect 1024

curl -s http://localhost:11434/api/chat \
  -d '{"model":"granite3.3-8b-local","messages":[{"role":"user","content":"Reply with exactly: ok"}],"stream":false}' \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["message"]["content"])'
# expect ok

# 5. Phase 17 — corpus and schema are already in place; check them first
cd ai/patterns/graph-rag
make corpus-check                  # 20 documents, 42 questions
make db-check                      # 8 tables, idempotent, hyperedge ok
# Next: §17.3 ingest. It embeds the corpus with bge-m3-local on the GPU and
# extracts relations with granite3.3-8b-local. Check nvidia-smi first.
# See ai/patterns/graph-rag/models/README.md for the model commands.

# 6. Phase 18 — plan only until an account exists
terraform -chdir=cloud/oracle init -backend=false
terraform -chdir=cloud/oracle validate
terraform -chdir=cloud/oracle plan
```

## Known traps, already measured or reasoned

| Trap | Where it will bite | Handle |
|---|---|---|
| Disk is 76% full (~157 GiB free) | minikube images + model downloads | prune images after each stack, `make doctor` warns below 40 GiB |
| 30 GiB RAM total, ~22 GiB available with models idle | 6 GiB cluster + Postgres + observability | one stack at a time; stop Ollama models when not in use |
| `minikube mount` is a foreground process | A1/A7 pods stuck in `ContainerCreating` | `scripts/lab-up.sh a1 --mount` detaches it and records the pid |
| `subPath` mounts never update | A2 would look broken | A2/A5 use directory mounts; written into manifests and runbook |
| ConfigMap is 1 MiB, UTF-8 only | images cannot live there | images go on the hostPath (A1) |
| LoadBalancer on minikube is `<pending>` | A4 expectations | `docs/runbooks.md` A4 table; port-forward 0.0.0.0 is the answer |
| SQLite + more than one replica | data corruption | one replica, `Recreate`, `journal_mode=DELETE` |
| PHP-FPM runs as uid 82 | `permission denied` on `database/` | init container chowns and chmods; documented in A7 |
| Fake `kubectl` always succeeds | false confidence | `tests/run.sh` includes failure cases; the doc labels the fake |
| Bitnami tag drift | H1 breaks | `helm show values` before copying any snippet |
| `severity: info` alerts never notify | webhook route matches but stays silent | chart's `InfoInhibitor` inhibits all info alerts; use `warning` for the test route |
| Ollama models and the GPU are host-side | eval cannot run inside the cluster; 8B models fall back to CPU if the GPU is busy | query the host endpoint from the service; never bake models into the image; check `nvidia-smi` |
| `llama.cpp` server holds ~6.4 GiB of the 8 GiB GPU | Granite/Qwen3 load on CPU and are slow | stop PID 47489 only if it is yours; `ollama ps` shows the processor |
| pgvector + Apache AGE in one image | extension availability differs per tag | tables are primary; AGE is an optional adapter |

## Decisions to keep, and the ones to revisit

Keep:

- minikube + docker driver as the default; `port-forward --address 0.0.0.0` for
  the LAN; one namespace `k8s-lab`; scripts with `--dry-run`; fake client only
  for offline docs; A7 single replica.
- Graph RAG uses plain Postgres tables + recursive CTEs as the primary graph
  layer; Apache AGE is optional and must not be required for evaluation.
- Embeddings and generation run on the host GPU through Ollama; the cluster
  service is a thin client. Real models only — no stub in the recorded path.
  Chosen: `bge-m3-local` + `granite3.3-8b-local`; `qwen3-8b-local` is the
  fallback; rerank with the LLM first, add a cross-encoder only if needed.
- The module is sourced from `.coatrc`, **not** added to `COAT_MODULE_ORDER`, so
  a Coat update never conflicts.

Revisit:

- Whether `loot` should detect this kit (needs a 3-line change in Coat's
  `spells.sh`; documented in `coat/README.md`, not applied).
- Whether the kit should move into the dotfiles repo. Right now it lives in the
  workshop folder and the Coat symlinks point here; moving it breaks those links.
- The observability stack choice (Prometheus vs VictoriaMetrics) — decide after
  measuring, see research R17.
- pgvector+AGE vs Neo4j for the graph layer — research R18.

## How to resume a session

Read in this order, then run the commands:

1. `resume.md` (this file) — state and next actions.
2. `analysis/07-what-to-do.md` — the remaining work, in order.
3. `ai/patterns/graph-rag/models/README.md` — the chosen local models.
4. `analysis/02-todo.md` — the full phase list.
5. `docs/runbooks.md` — the exercise you are about to run.

```bash
make test        # must be green before changing anything
make doctor      # must show no FAIL line
git status       # must be clean before you start
```

## Session log (what changed here)

- Created the analysis of the prompt file and the PDF, including the defect list.
- Added and analysed `kubernetes_podsumowanie.md`; produced the coverage matrix.
- Measured the hardware and derived the tiers; wrote the doctor and the tests.
- Built scenario manifests, paczki templates, scripts, a fake client, the offline
  suite, the runbooks, the example runs, the README and Coat wiring.
- Fixed three bugs found by the checks: an `if/fi` mismatch in `lab-tunnel.sh`,
  shellcheck warnings treated as errors, and a failing `--dry-run` without kubectl.
- Restructured A5 from a `subPath` mount to directory-mounted ConfigMaps.
- Installed tools in user space (`kubectl`, `minikube`, `helm`, `k3d`, `kind`,
  `sqlite3`, `htpasswd` plus the `mkpasswd.sh` fallback).
- Built cluster scaffolds and hardware-aware `cluster-create.sh`/`cluster-delete.sh`.
- Built the observability stack with profiles, values, alerts and probes.
- Built the bastion scaffold.
- Started minikube with the doctor flags and ran A1–A7 on the real cluster;
  captured transcripts and closed the coverage rows.
- Added boilerplates, paczki templates, recovery drills and eight stack overlays.
- Deployed the full observability stack (metrics, logs, traces, Grafana).
- Added the RAG pattern, its contracts, failure modes and evaluation harness.
- Reverted an abandoned fake-kubectl rewrite that broke `make check`.
- Fixed a corrupted `.gitignore` rule and moved the eval output under the pattern.
- Recorded the Phase 16 evaluation baseline in `ai/patterns/rag/eval/results.json`.
- Instrumented the RAG mockup and FastAPI stack with OTel; the live span id is in
  the response, header and log line, and matches Tempo.
- Imported the Graph-RAG scaffold, cloud notes and exercise sheet from the
  abandoned capital-S copy, each with provenance markers.
- Removed the capital-S copy after backing it up under `/tmp/opencode/`.
- Enabled Alertmanager, added the in-cluster webhook receiver, and proved both
  the synthetic `LabWebhookTest` and a real `PodNotReady` delivery.
- Added `docs/REPO-STATE.md` as the full repository snapshot.
- Inventoried the local GGUF and LM Studio models; chose `bge-m3` for embeddings
  and Granite 3.3 8B for generation, with Qwen3 8B as the fallback.
- Imported and verified `bge-m3-local` (1024-dim), `granite3.3-8b-local` and
  `qwen3-8b-local`; added the missing chat templates.
- Recorded the model setup in `ai/patterns/graph-rag/models/` and updated the
  Phase 17 docs.
- Phase 17.1: added the 20-document corpus with hashes and provenance, the
  42-question golden set, a manifest generator and a validator, and wired the
  check into `make test` (38 assertions).
- Phase 17.2: added the idempotent Postgres 16 + pgvector schema, a local
  compose file, `make migrate`, and `make db-check` proving that a second
  migrate is a no-op and that a 3-member hyperedge round-trips.
- Found and fixed a runbook error: A5 claimed the mounted Secret was `0400`
  while the manifest sets `0644` so the non-root nginx worker can read it.
