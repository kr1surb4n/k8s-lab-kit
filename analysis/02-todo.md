# To do — ordered work list

Legend: `[ ]` open, `[~]` in progress, `[x]` done. Effort is rough (S = under 30 min, M = 1–2 h, L = half a day).
Every phase ends with a verification step; do not start the next phase before it passes.

---

> **Status as of 2026-10-25.** Phases 0–8 are done: A1–A7 ran on the real
> minikube cluster and the transcripts are in `docs/example-runs.md`.
> Phases 9–11 are partial: D1 (k3s), H1 (Helm) and N1 (Ingress) are still
> `partial` in `docs/coverage-matrix.md`. Phases 12–16 are done.
> Phases 17–18 are open; the actionable checklist is
> `analysis/07-what-to-do.md`.
>
> Checkboxes below are kept as the original plan. A phase heading marked
> DONE means every item in it was superseded by the executed run recorded in
> git; a heading marked PARTIAL lists the genuinely open items.


## Phase 0 — Host prerequisites (S) — **DONE**

- [x] Install the client tools: `kubectl`, `minikube`, `helm`, `sqlite3`, `htpasswd` (package `apache2-utils`).
- [x] Confirm docker works as the current user: `docker info` without sudo.
- [x] Record versions in `docs/example-runs.md` (`kubectl version --client`, `minikube version`, `helm version`).
- [x] Check free disk (minikube needs ~20 GB) and free RAM (~4 GB minimum for the driver).
- [x] Confirm nothing on the host already listens on 80 or 8080: `ss -ltnp | grep -E ':(80|8080)'`.

**Verify:** `minikube status` answers (cluster not required yet), `kubectl version --client` prints a version.

---

## Phase 1 — Cluster (S–M) — **DONE**

- [x] Start the cluster: `minikube start --driver=docker --cpus=4 --memory=8192 --disk-size=20g`.
- [x] `minikube addons enable ingress` only when doing the PDF lab (not needed for A1–A6).
- [x] Validate the basic loop: `kubectl get nodes -o wide`, `kubectl run` a throwaway pod, delete it.
- [x] Decide and write down the LAN story: `kubectl port-forward --address 0.0.0.0` (default) vs k3s (later).
- [x] Try the host mount: `minikube mount ./site:/mnt/site` in a second terminal; `ls` from inside a pod.

**Verify:** `kubectl get nodes` shows `Ready`; a pod can read a file from `/mnt/site`.

---

## Phase 2 — A1: static site from disk (M) — **DONE**

- [x] Review `manifests/a1/` (hostPath + Service + Deployment).
- [x] `scripts/lab-up.sh a1` (real run, not `--dry-run`).
- [x] `curl` the page; `curl` the image; confirm the image is served, not just HTML.
- [x] Edit `site/index.html` on the host and re-`curl` **without** restarting anything.
- [x] Write the answer to "can I download images in the same directory?" into `docs/runbooks.md` A1.
- [x] Capture the transcript in `docs/example-runs.md`.

**Verify:** content changes on the fly; `lab-verify.sh a1` exits 0.

---

## Phase 3 — A2: ConfigMap (M) — **DONE**

- [x] Create the ConfigMap from the file: `kubectl create configmap web-index --from-file=index.html -n k8s-lab`.
- [x] Apply `manifests/a2/` and confirm the directory mount serves the page.
- [x] Edit the ConfigMap, measure how long the change takes to appear (kubelet sync).
- [x] Prove that `subPath` stops the propagation, then revert to the directory mount.
- [x] Try to put a PNG into the ConfigMap; document the failure (1 MiB / non-UTF-8).
- [x] Capture the transcript.

**Verify:** page changes after `kubectl edit configmap`, no pod restart; runbook explains the mechanism.

---

## Phase 4 — A3: environment variables (S–M) — **DONE**

- [x] Add env vars to the A2/A1 deployment: literal, `configMapKeyRef`, `envFrom`.
- [x] `kubectl exec ... -- printenv | sort`, `kubectl describe pod` (what is visible).
- [x] Demonstrate precedence: image `ENV` vs pod `env` vs `envFrom`, and `$(VAR)` ordering.
- [x] Demonstrate that env vars from a ConfigMap do **not** update until the pod is recreated.
- [x] Demonstrate the shell side on the host: `export`, `.env` with `set -a`, `envsubst`, `direnv`.
- [x] Write the four answers (who / when / where / mechanisms) into the runbook.
- [x] Capture the transcript.

**Verify:** the page shows a value injected from the manifest; the runbook answers all four questions with one concrete example each.

---

## Phase 5 — A4: LAN access (M) — **DONE**

- [x] From the host: `lab-tunnel.sh a6 --address 0.0.0.0 --port 8080`.
- [x] From a second machine: `curl http://<host-ip>:8080` → 200 (verified on LAN).
- [x] Open the firewall if needed (`sudo ufw allow 8080/tcp`), then close it again.
- [x] Try `minikube tunnel` and record that the LoadBalancer IP is host-only.
- [x] Try `minikube service web --url` and record that it binds 127.0.0.1.
- [x] Write the comparison table (minikube / k3d / k3s / microk8s) with what each needs for LAN.
- [x] Capture the transcript including the second machine's `curl`.

**Verify:** a page loads from another machine; the runbook states why the LoadBalancer alone is not enough.

---

## Phase 6 — A5: Secrets (M) — **DONE**

- [x] Generate the htpasswd file with `openssl passwd -apr1` or `htpasswd -c`.
- [x] Create the Secret imperatively and via `manifests/a5/`; compare `data` vs `stringData`.
- [x] Wire nginx basic auth (ConfigMap server block + Secret mount).
- [x] `curl -i` without credentials → 401; with credentials → 200.
- [x] Show the leak paths: `kubectl describe`, `printenv`, `/proc/1/environ`, shell history, Git.
- [x] Document file mode (`defaultMode: 0400`) and "base64 is not encryption".
- [x] Capture the transcript.

**Verify:** 401/200 as above; `lab-verify.sh a5` exits 0.

---

## Phase 7 — A6: LoadBalancer, 3 replicas, lifecycle (M–L) — **DONE**

- [x] Review `manifests/a6/` (Deployment 3 replicas, readiness probe, Service `LoadBalancer`).
- [x] Bring it up on a clean namespace with `lab-up.sh a6`.
- [x] `lab-status.sh a6`; `lab-scale.sh a6 --delta +1` then `--delta -1`.
- [x] `lab-rollout.sh a6 image nginx:1.28-alpine`, watch the rolling update, then `undo`.
- [x] `lab-down.sh a6`, then `--all` (namespace too), then bring it back up.
- [x] Time the update with and without a readiness probe; write down the difference.
- [x] Capture the transcript for every operation.

**Verify:** every requested operation (up, down, +1, −1, update) has a command, an expected output and a rollback.

---

## Phase 8 — A7: Laravel + PostgreSQL + SQLite (L) — **DONE**

- [x] Build the PHP image once: `docker build -t k8s-lab/php:8.3 manifests/a7/php`.
- [x] Start the stack: `lab-up.sh a7` (nginx + php-fpm + postgres + init job).
- [x] Run migrations, confirm both databases answer.
- [x] Edit `data/sqlite/database.sqlite` from the host with the `sqlite3` CLI; reload the page; see the change.
- [x] Break the mount permissions on purpose, read the error, fix it with the right uid (`82`).
- [x] Replace the stand-in app with real Laravel (optional, network): `composer create-project`, mount `storage`, opcache off.
- [x] Document the SQLite-vs-3-replicas conflict and why `database.sqlite` needs a single writer.
- [x] Capture the transcript.

**Verify:** the page reads Postgres **and** SQLite; a host-side SQLite write is visible on reload.

---

## Phase 9 — PDF topics (M) — **PARTIAL**

- [ ] Distribution comparison: run the same A6 manifest on minikube and on k3d or k3s; record what breaks.
- [ ] Helm: install the same app from a local chart, `helm template`, `helm upgrade`, `helm history`, `helm rollback`, `helm uninstall`; note that Bitnami values must be read, not copied.
- [ ] Ingress: enable the controller, route the app by host name, reproduce the `rewrite-target` 404 and then fix it.
- [ ] Storage: add a PVC, change the reclaim policy, delete the PVC, see what happens to the PV.
- [ ] Troubleshooting drills: force CrashLoopBackOff, ImagePullBackOff, Pending and OOMKilled; fix each using the PDF's sequence.

**Verify:** each PDF topic has at least one command sequence and one "what I saw" note.

---

## Phase 10 — Kit hardening (S–M) — **PARTIAL**

- [ ] Fill `docs/example-runs.md` with real output instead of the fake-shim output.
- [ ] Run `make check`: syntax, shellcheck, YAML parse, dry-runs.
- [ ] Install the Coat integration (`coat/install-coat.sh`) and test `paczek k8s`, `klab status`, the spells.
- [ ] Update `analysis/03-research.md` with answers; delete questions that no longer apply.
- [ ] Decide whether the kit stays in this folder or moves into the dotfiles repo (Coat/paczki are versioned there).

**Verify:** `make check` is green and the README's quickstart works from an empty shell.

---

## Phase 11 — Traceability against the outline (S) — **PARTIAL**

Derived from `kubernetes_podsumowanie.md`; see `04-analysis-podsumowanie.md`.

- [ ] Walk `docs/coverage-matrix.md` row by row; every `partial` must become `covered` or `out of scope` with a reason.
- [ ] Confirm each of the four outline sections has at least one executed command, not just a paragraph.
- [ ] Decide on Magento: run one isolated `helm dependency update` + `helm template` (no install) or record it as out of scope.
- [ ] Verify the two distribution commands the PDF added: `INSTALL_K3S_EXEC` (not `SH_K3S_EXEC`) and `microk8s enable dns hostpath-storage ingress`.
- [ ] Add the "reverse gap" check: each of the seven prompts has a row with evidence.
- [ ] Re-read the matrix at the end of the lab; it must describe what ran, not what was planned.

**Verify:** no row says `partial`; every `covered` row points at a transcript in `docs/example-runs.md`.

---

# Expansion tracks (from `06-scope-expansion.md`)

These start only after the core lab is closed. Order matters; each phase assumes
the previous one left a working boilerplate and a transcript.

## Phase 12 — Hardware gate and boilerplates (S–M) — **DONE**

- [x] Run `make doctor` on every machine that will host the lab; record the tier.
- [x] Add the missing CLI tools the doctor lists (`kubectl`, `minikube`, `helm`, `sqlite3`, `htpasswd`).
- [x] Finish `paczki/k8s/`: cronjob, statefulset, job, networkpolicy, pdb, rbac, hpa.
- [x] Create `boilerplates/base/` (deployment + service + probes + resources + kustomization).
- [x] Port A6 onto the base to prove the boilerplate is enough.

**Verify:** a new folder reaches a verified deployment using only the base plus one overlay. (Tested: `kubectl kustomize boilerplates/overlays/a6 | kubectl apply -f -` → 3 replicas Ready, LoadBalancer service created, nginx responds.)

## Phase 13 — Recovery drills (M) — **DONE**

- [x] `recovery/method.md`: Observe → Contain → Diagnose → Recover → Prevent (one-page runbook)
- [x] Drill scripts: `scripts/lab-drill.sh` with `--inject` and `--recover` for each T1 row:
    - CrashLoopBackOff (override container command to `exit 1`)
    - ImagePullBackOff (nonexistent image tag)
    - Pending (unschedulable via 20Gi resource request)
    - OOMKilled (1 MiB memory limit)
- [x] `make drills` target runs all four in sequence (inject → verify → recover)
- [x] Data drills documented: etcd snapshot, `pg_dump`/restore, PVC backup, GitOps revert
- [x] Decision tree: Symptom → Command → Cause → Fix in `recovery/method.md`

**Verify:** every drill fails on purpose, recovers, and leaves `lab-verify.sh` green.

## Phase 14 — Other stacks (M–L) — **DONE**

- [x] Node/Express boilerplate (Node 22 + Express, port 3000)
- [x] Python/FastAPI boilerplate (Python 3.12 + FastAPI, port 8000)
- [x] Go boilerplate (Go 1.23 + Gin, port 8080, distroless image)
- [x] Java/Spring boilerplate (Java 21 + Spring Boot 3, port 8080, **startupProbe**)
- [x] Worker + CronJob (Python worker + APScheduler CronJob + Redis)
- [x] Stateful PostgreSQL (StatefulSet, PVC per replica, headless service)
- [x] Stateful Redis (StatefulSet, AOF persistence, headless + client service)
- [x] Stateful MinIO (StatefulSet, S3 API + console, 10Gi PVC)

**Verify:** each stack has kustomize overlay extending boilerplates/base, non-root containers, health endpoints, structured logging, graceful shutdown, resource limits. Image builds documented in stack READMEs.

## Phase 15 — Observability and traceability (M–L) — **DONE**

- [x] `observability/inventory/hosts.yaml` first: names, addresses, roles, ports.
- [x] Prometheus (kube-prometheus-stack) + node-exporter + blackbox-exporter.
- [x] Grafana dashboards, retention 7d metrics.
- [x] Alerts that fire on symptoms (PodCrashLooping, PodNotReady, etc.).
- [x] Loki single-binary (logs), 3d retention.
- [x] Tempo single-binary (traces), 1d retention, OTLP HTTP ingestion.
- [x] OTel Collector (0.163.2) with OTLP HTTP/GRPC receivers, otlphttp exporter to Tempo.
- [x] Trace ingestion verified: `curl -X POST :4318/v1/traces` → visible in Tempo UI.
- [x] OTel instrumentation in two apps (RAG mockup and FastAPI stack); trace id visible in the log line and matched to Tempo (`docs/example-runs.md` §8).
- [x] Alerts routed to an in-cluster webhook; `LabWebhookTest` and a real `PodNotReady` both delivered (`docs/example-runs.md` §9).

**Verify:** a request from the LAN is traceable end to end; a deliberately broken pod produces a webhook delivery. Both are recorded in `docs/example-runs.md` §8–§9.

> **Note:** Full stack (metrics + logs + traces + uptime + Grafana) deployed and working. Trace ingestion and webhook delivery verified end-to-end.

## Phase 16 — AI patterns catalogue (S–M) — **RAG DONE**

- [x] `ai/patterns/rag/` with mockup, k8s, contracts, eval, failure-modes
- [x] One deployed example (RAG) to prove the contracts are usable.
- [x] A vocabulary page: retrieval, rerank, context window, temperature, eval, guardrail.

**Verify:** the catalogue is readable by a non-AI engineer and one entry runs.

## Phase 17 — RAG with graphs and hypergraphs (L)

- [x] Local model set chosen and imported: `bge-m3-local` + `granite3.3-8b-local`
      (fallback `qwen3-8b-local`); see `ai/patterns/graph-rag/models/README.md`.
- [ ] Sample corpus with known answers; golden question set.
- [ ] Ingest + chunk + embed (host GPU) + provenance into Postgres.
- [ ] pgvector index; BM25 for hybrid; graph tables + hyperedge join table.
- [ ] Retrieval service: hybrid → graph expand → rerank → answer with citations.
- [ ] Evaluation script: recall@k, citation precision, faithfulness, latency.
- [ ] Trace every question: chunks, graph path, scores, prompt/model version.

**Verify:** deleting a cited document changes the answer; scores are recorded per commit.

## Phase 18 — Cloud free tier (S–M, time-boxed)

- [ ] Choose one provider from the T6 table; write the budget/teardown note first.
- [ ] Deploy the A6 stack unchanged; note which overlay was needed.
- [ ] Prove access from outside, then tear everything down.
- [ ] Record the cost page and the exact teardown commands.

**Verify:** the next bill is zero and the manifests needed no rewrite.

---

## Immediate next actions (this week)

1. Run `make test`; it must stay green.
2. Work through `analysis/07-what-to-do.md` in order: Phase 15 leftovers,
   Phase 17 (Graph RAG), Phase 18 (cloud plan).
3. Keep `docs/coverage-matrix.md` honest; a row is `covered` only when a real
   transcript is pasted into `docs/example-runs.md`.
