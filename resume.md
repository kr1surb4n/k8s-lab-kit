# Resume — where this work stands

Read this first when coming back. It is deliberately short and points at the
details.

- **Folder:** `/home/kris/00___Castle/07__WorkShops/k8s`
- **Date:** 2026-10-26
- **State:** **Phases 0–16 done; Phase 17 scaffold imported but not built; Phase 18 open**
- **Git:** repository on `main`; conventional commits, one change per commit
- **Offline gate:** `make test` → **36 passed, 0 failed**
- **Cluster:** minikube stopped at last snapshot; `observability` was healthy earlier
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
pattern with a recorded evaluation baseline (16). Graph RAG (17) and the cloud
free-tier experiment (18) are the remaining phases; see
`analysis/07-what-to-do.md`.

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
| Offline test suite | `tests/run.sh` → 36 passed |
| Coat module, spells, installer | `coat/` (installer tested with `--dry-run`) |
| Observability full stack (Prometheus, Grafana, Loki, Tempo, OTel) | `observability/`, running in `observability` namespace |
| RAG pattern + eval baseline | `ai/patterns/rag/`, `ai/patterns/rag/eval/results.json` |
| Bastion scaffold (host + in-cluster) | `bastion/` |
| Cluster skeletons (minikube, kind, k3d, k3s, managed) | `clusters/` |
| Tool installer (user-space + apt fallback) | `setup/install-tools.sh` |

## What is not done

1. **Phase 17 — Graph RAG.** Corpus, pgvector/AGE schema, ingest, hybrid +
   2-hop retrieval, rerank, eval harness, k8s packaging. A cleaned scaffold was
   imported from the abandoned capital-S copy and is marked in
   `ai/patterns/graph-rag/PROVENANCE.md`; it is mock-only, so the phase itself
   is still open. The detailed checklist is `analysis/07-what-to-do.md` §3.
2. **Phase 18 — cloud free tier.** Plan-only until an account is provided; the
   deliverable is provider docs, Terraform validated with `terraform plan`, the
   A6 overlay, and a teardown checklist.
3. **Two Phase 15 boxes.** OTel instrumentation in one or two apps (trace id in
   the log line) and one Alertmanager alert routed to an in-cluster webhook.
4. **Coat is not installed.** Only `coat/install-coat.sh --dry-run` was run.
5. **Bastion not deployed.** Manifests and host config exist, not applied.
6. **`paczki/k8s` was not exercised through `paczek`.** The `fill_template`
   syntax (`{{ VAR }}`) matches Coat, but it was not run.

## Next actions, in order

```bash
cd /home/kris/00___Castle/07__WorkShops/k8s

# 1. confirm the kit still passes
make test

# 2. read the current plan
sed -n '1,120p' analysis/07-what-to-do.md

# 3. Phase 15 leftovers (cluster is already running)
kubectl -n observability get pods
make obs PROFILE=full   # only if the stack is missing

# 4. Phase 17
make -C ai/patterns/graph-rag up
make -C ai/patterns/graph-rag eval

# 5. Phase 18 — plan only until an account exists
terraform -chdir=cloud/oracle init -backend=false
terraform -chdir=cloud/oracle validate
terraform -chdir=cloud/oracle plan
```

## Known traps, already measured or reasoned

| Trap | Where it will bite | Handle |
|---|---|---|
| Disk is 77% full (~151 GiB free) | minikube images + model downloads | prune images after each stack, `make doctor` warns below 40 GiB |
| ~11 GiB RAM available | 6 GiB cluster + Postgres + observability | one stack at a time |
| `minikube mount` is a foreground process | A1/A7 pods stuck in `ContainerCreating` | `scripts/lab-up.sh a1 --mount` detaches it and records the pid |
| `subPath` mounts never update | A2 would look broken | A2/A5 use directory mounts; written into manifests and runbook |
| ConfigMap is 1 MiB, UTF-8 only | images cannot live there | images go on the hostPath (A1) |
| LoadBalancer on minikube is `<pending>` | A4 expectations | `docs/runbooks.md` A4 table; port-forward 0.0.0.0 is the answer |
| SQLite + more than one replica | data corruption | one replica, `Recreate`, `journal_mode=DELETE` |
| PHP-FPM runs as uid 82 | `permission denied` on `database/` | init container chowns and chmods; documented in A7 |
| Fake `kubectl` always succeeds | false confidence | `tests/run.sh` includes failure cases; the doc labels the fake |
| Bitnami tag drift | H1 breaks | `helm show values` before copying any snippet |
| Ollama models are host-side | eval cannot run inside the cluster | query the host endpoint from the service, never bake models into the image |
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
3. `analysis/02-todo.md` — the full phase list.
4. `docs/runbooks.md` — the exercise you are about to run.

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
