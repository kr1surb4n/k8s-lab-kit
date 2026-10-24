# To do — ordered work list

Legend: `[ ]` open, `[~]` in progress, `[x]` done. Effort is rough (S = under 30 min, M = 1–2 h, L = half a day).
Every phase ends with a verification step; do not start the next phase before it passes.

---

## Phase 0 — Host prerequisites (S)

- [ ] Install the client tools: `kubectl`, `minikube`, `helm`, `sqlite3`, `htpasswd` (package `apache2-utils`).
- [ ] Confirm docker works as the current user: `docker info` without sudo.
- [ ] Record versions in `docs/example-runs.md` (`kubectl version --client`, `minikube version`, `helm version`).
- [ ] Check free disk (minikube needs ~20 GB) and free RAM (~4 GB minimum for the driver).
- [ ] Confirm nothing on the host already listens on 80 or 8080: `ss -ltnp | grep -E ':(80|8080)'`.

**Verify:** `minikube status` answers (cluster not required yet), `kubectl version --client` prints a version.

---

## Phase 1 — Cluster (S–M)

- [ ] Start the cluster: `minikube start --driver=docker --cpus=4 --memory=8192 --disk-size=20g`.
- [ ] `minikube addons enable ingress` only when doing the PDF lab (not needed for A1–A6).
- [ ] Validate the basic loop: `kubectl get nodes -o wide`, `kubectl run` a throwaway pod, delete it.
- [ ] Decide and write down the LAN story: `kubectl port-forward --address 0.0.0.0` (default) vs k3s (later).
- [ ] Try the host mount: `minikube mount ./site:/mnt/site` in a second terminal; `ls` from inside a pod.

**Verify:** `kubectl get nodes` shows `Ready`; a pod can read a file from `/mnt/site`.

---

## Phase 2 — A1: static site from disk (M)

- [ ] Review `manifests/a1/` (hostPath + Service + Deployment).
- [ ] `scripts/lab-up.sh a1` (real run, not `--dry-run`).
- [ ] `curl` the page; `curl` the image; confirm the image is served, not just HTML.
- [ ] Edit `site/index.html` on the host and re-`curl` **without** restarting anything.
- [ ] Write the answer to "can I download images in the same directory?" into `docs/runbooks.md` A1.
- [ ] Capture the transcript in `docs/example-runs.md`.

**Verify:** content changes on the fly; `lab-verify.sh a1` exits 0.

---

## Phase 3 — A2: ConfigMap (M)

- [ ] Create the ConfigMap from the file: `kubectl create configmap web-index --from-file=index.html -n k8s-lab`.
- [ ] Apply `manifests/a2/` and confirm the directory mount serves the page.
- [ ] Edit the ConfigMap, measure how long the change takes to appear (kubelet sync).
- [ ] Prove that `subPath` stops the propagation, then revert to the directory mount.
- [ ] Try to put a PNG into the ConfigMap; document the failure (1 MiB / non-UTF-8).
- [ ] Capture the transcript.

**Verify:** page changes after `kubectl edit configmap`, no pod restart; runbook explains the mechanism.

---

## Phase 4 — A3: environment variables (S–M)

- [ ] Add env vars to the A2/A1 deployment: literal, `configMapKeyRef`, `envFrom`.
- [ ] `kubectl exec ... -- printenv | sort`, `kubectl describe pod` (what is visible).
- [ ] Demonstrate precedence: image `ENV` vs pod `env` vs `envFrom`, and `$(VAR)` ordering.
- [ ] Demonstrate that env vars from a ConfigMap do **not** update until the pod is recreated.
- [ ] Demonstrate the shell side on the host: `export`, `.env` with `set -a`, `envsubst`, `direnv`.
- [ ] Write the four answers (who / when / where / mechanisms) into the runbook.
- [ ] Capture the transcript.

**Verify:** the page shows a value injected from the manifest; the runbook answers all four questions with one concrete example each.

---

## Phase 5 — A4: LAN access (M)

- [ ] From the host: `lab-tunnel.sh a6 --address 0.0.0.0 --port 8080`.
- [ ] From a second machine: `curl http://<host-ip>:8080`.
- [ ] Open the firewall if needed (`sudo ufw allow 8080/tcp`), then close it again.
- [ ] Try `minikube tunnel` and record that the LoadBalancer IP is host-only.
- [ ] Try `minikube service web --url` and record that it binds 127.0.0.1.
- [ ] Write the comparison table (minikube / k3d / k3s / microk8s) with what each needs for LAN.
- [ ] Capture the transcript including the second machine's `curl`.

**Verify:** a page loads from another machine; the runbook states why the LoadBalancer alone is not enough.

---

## Phase 6 — A5: Secrets (M)

- [ ] Generate the htpasswd file with `openssl passwd -apr1` or `htpasswd -c`.
- [ ] Create the Secret imperatively and via `manifests/a5/`; compare `data` vs `stringData`.
- [ ] Wire nginx basic auth (ConfigMap server block + Secret mount).
- [ ] `curl -i` without credentials → 401; with credentials → 200.
- [ ] Show the leak paths: `kubectl describe`, `printenv`, `/proc/1/environ`, shell history, Git.
- [ ] Document file mode (`defaultMode: 0400`) and "base64 is not encryption".
- [ ] Capture the transcript.

**Verify:** 401/200 as above; `lab-verify.sh a5` exits 0.

---

## Phase 7 — A6: LoadBalancer, 3 replicas, lifecycle (M–L)

- [ ] Review `manifests/a6/` (Deployment 3 replicas, readiness probe, Service `LoadBalancer`).
- [ ] Bring it up on a clean namespace with `lab-up.sh a6`.
- [ ] `lab-status.sh a6`; `lab-scale.sh a6 --delta +1` then `--delta -1`.
- [ ] `lab-rollout.sh a6 image nginx:1.28-alpine`, watch the rolling update, then `undo`.
- [ ] `lab-down.sh a6`, then `--all` (namespace too), then bring it back up.
- [ ] Time the update with and without a readiness probe; write down the difference.
- [ ] Capture the transcript for every operation.

**Verify:** every requested operation (up, down, +1, −1, update) has a command, an expected output and a rollback.

---

## Phase 8 — A7: Laravel + PostgreSQL + SQLite (L)

- [ ] Build the PHP image once: `docker build -t k8s-lab/php:8.3 manifests/a7/php`.
- [ ] Start the stack: `lab-up.sh a7` (nginx + php-fpm + postgres + init job).
- [ ] Run migrations, confirm both databases answer.
- [ ] Edit `data/sqlite/database.sqlite` from the host with the `sqlite3` CLI; reload the page; see the change.
- [ ] Break the mount permissions on purpose, read the error, fix it with the right uid (`82`).
- [ ] Replace the stand-in app with real Laravel (optional, network): `composer create-project`, mount `storage`, opcache off.
- [ ] Document the SQLite-vs-3-replicas conflict and why `database.sqlite` needs a single writer.
- [ ] Capture the transcript.

**Verify:** the page reads Postgres **and** SQLite; a host-side SQLite write is visible on reload.

---

## Phase 9 — PDF topics (M)

- [ ] Distribution comparison: run the same A6 manifest on minikube and on k3d or k3s; record what breaks.
- [ ] Helm: install the same app from a local chart, `helm template`, `helm upgrade`, `helm history`, `helm rollback`, `helm uninstall`; note that Bitnami values must be read, not copied.
- [ ] Ingress: enable the controller, route the app by host name, reproduce the `rewrite-target` 404 and then fix it.
- [ ] Storage: add a PVC, change the reclaim policy, delete the PVC, see what happens to the PV.
- [ ] Troubleshooting drills: force CrashLoopBackOff, ImagePullBackOff, Pending and OOMKilled; fix each using the PDF's sequence.

**Verify:** each PDF topic has at least one command sequence and one "what I saw" note.

---

## Phase 10 — Kit hardening (S–M)

- [ ] Fill `docs/example-runs.md` with real output instead of the fake-shim output.
- [ ] Run `make check`: syntax, shellcheck, YAML parse, dry-runs.
- [ ] Install the Coat integration (`coat/install-coat.sh`) and test `paczek k8s`, `klab status`, the spells.
- [ ] Update `analysis/03-research.md` with answers; delete questions that no longer apply.
- [ ] Decide whether the kit stays in this folder or moves into the dotfiles repo (Coat/paczki are versioned there).

**Verify:** `make check` is green and the README's quickstart works from an empty shell.

---

## Phase 11 — Traceability against the outline (S)

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

## Phase 12 — Hardware gate and boilerplates (S–M)

- [ ] Run `make doctor` on every machine that will host the lab; record the tier.
- [ ] Add the missing CLI tools the doctor lists (`kubectl`, `minikube`, `helm`, `sqlite3`, `htpasswd`).
- [ ] Finish `paczki/k8s/`: cronjob, statefulset, job, networkpolicy, pdb, rbac, hpa.
- [ ] Create `boilerplates/base/` (deployment + service + probes + resources + kustomization).
- [ ] Port A6 onto the base to prove the boilerplate is enough.

**Verify:** a new folder reaches a verified deployment using only the base plus one overlay.

## Phase 13 — Recovery drills (M)

- [ ] `recovery/method.md`: observe → contain → diagnose → recover → prevent.
- [ ] One drill script per row of the T2 table, each with `--inject` and `--recover`.
- [ ] A single `make drills` that runs them in order and restores the lab.
- [ ] Data drills: etcd snapshot, `pg_dump`/restore, PVC backup, GitOps revert.
- [ ] One-page decision tree: symptom → command → cause → fix.

**Verify:** every drill fails on purpose, recovers, and leaves `lab-verify.sh` green.

## Phase 14 — Other stacks (M–L)

- [ ] Node/Express boilerplate, then Python/FastAPI, then Go.
- [ ] A worker (no port) and a CronJob, to cover non-HTTP shapes.
- [ ] Stateful set: Postgres, Redis, MinIO with PVCs.
- [ ] Java/Spring with a startupProbe (slow JVM) — the probe lesson.
- [ ] Record per-runtime notes: image size, build time, probe tuning, memory floor.

**Verify:** each stack has `make up|verify|down` and a captured transcript; disk free stays above 30 GiB.

## Phase 15 — Observability and traceability (M–L)

- [ ] `observability/inventory/hosts.yaml` first: names, addresses, roles, ports.
- [ ] Prometheus (or VictoriaMetrics) + node-exporter + blackbox-exporter outside the cluster.
- [ ] Loki single-binary, Tempo single-binary, Grafana, retention 7/3 days.
- [ ] One dashboard per layer: cluster, namespace, host, uptime.
- [ ] OTel instrumentation in one app; trace id visible in the log line.
- [ ] Alerts that fire on symptoms, routed to a webhook.

**Verify:** a request from the LAN is traceable end to end; a host reboot raises an alert.

## Phase 16 — AI patterns catalogue (S–M)

- [ ] `ai/patterns/<name>/` for each row in the T7 table: README, mockup, contract, k8s, failure.
- [ ] One deployed example (RAG or router) to prove the contracts are usable.
- [ ] A vocabulary page: retrieval, rerank, context window, temperature, eval, guardrail.

**Verify:** the catalogue is readable by a non-AI engineer and one entry runs.

## Phase 17 — RAG with graphs and hypergraphs (L)

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

1. `make doctor` → install the missing CLI tools.
2. `minikube start` with the doctor's flags.
3. Run phases 1–2 for real (A1), capture the first real transcript.
4. Replace the fake-cluster examples in `docs/example-runs.md` with real ones.
