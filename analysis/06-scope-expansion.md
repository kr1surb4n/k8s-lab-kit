# Scope expansion — the tracks after the nginx lab

Everything here is **planned, not built**. It records the goals added after the
original seven exercises, splits them into tracks, and puts each one in an order
that the hardware can actually survive (`05-hardware-profile.md`).

## The tracks

| ID | Track | Goal | First artifact | Hardware fit |
|---|---|---|---|---|
| T1 | Stacks on Kubernetes | run several real stacks, not just nginx | `stacks/` boilerplate per stack | one at a time, disk-bound |
| T2 | Failure and recovery | break things on purpose, then recover with a method | `recovery/` drills + decision tree | fits easily |
| T3 | Observability and traceability | see metrics, logs, traces and host/network state | `observability/` single-binary stack | ~2 GiB, fits with 6 GiB cluster |
| T4 | Boilerplate library | reusable, parameterised starting points | `paczki/` expansion + `boilerplates/` | free |
| T5 | RAG with graphs and hypergraphs | retrieval over documents with a graph layer | `ai/rag/` compose + manifests | vector+graph ~1 GiB, models on host GPU |
| T6 | Cloud free tiers | use someone else's cluster without paying | `cloud/` per-provider notes + one experiment | free, time-boxed |
| T7 | AI patterns, mockups and models | a catalogue of common AI system shapes | `ai/patterns/` diagrams + contracts | free |

Dependencies:

```
T4 (boilerplates) ──> T1 (stacks) ──> T3 (observability of those stacks)
                         │
                         ├──> T2 (break and recover them)
                         └──> T5 (RAG stack is just another stack)
T7 (patterns) ──> T5 (RAG is pattern #1)
T6 (cloud) independent, but reuses T4
```

Do T4 first: every other track is cheaper once the boilerplates exist.

---

## T1 — Other stacks on Kubernetes

Goal: prove the same deployment shape works for different runtimes, and record
what changes per runtime.

| Stack | Why it is interesting | Runtime | Extra objects |
|---|---|---|---|
| static (nginx) | baseline, already done | nginx | ConfigMap/hostPath |
| Node/Express | trivial HTTP, fast build | node:22-alpine | — |
| Next.js | SSR, build-time env, larger image | node:22 | build args, cache |
| Python/FastAPI | worker model, venv vs image | python:3.12-slim | — |
| Go | static binary, tiny image | scratch/distroless | — |
| PHP/Laravel | FPM + nginx split (A7) | php:8.3-fpm | 2 containers, PVC |
| Java/Spring | JVM memory, slow start, probes matter | eclipse-temurin | startupProbe |
| Worker | no port, consumes a queue | python/node | liveness by liveness file |
| CronJob | scheduled work, history limits | any | CronJob, concurrencyPolicy |
| Stateful | Postgres, Redis, MinIO | vendor images | PVC, headless Service |

Every stack gets the same files:

```
stacks/<name>/
  app/                 minimal app, no framework magic
  Dockerfile           multi-stage, pinned base
  k8s/base/            deployment, service, probes, resources
  k8s/overlays/dev/    image tag, replicas, env
  Makefile             build, up, verify, down
  README.md            what is specific to this runtime
```

Acceptance per stack: `make up` → page/endpoint answers → `make verify` exits 0
→ `make down` leaves nothing. One stack installed at a time.

Avoid: Magento, ELK, Kafka+Zookeeper, Spark. They do not fit and add no new
lesson beyond the table.

---

## T2 — Failure and recovery

Goal: a repeatable method, not anecdotes. The PDF's sequence is the start, not
the whole answer.

**Method (five steps, always the same):**

1. **Observe** — `kubectl get pods -o wide`, `get events --sort-by=.lastTimestamp`,
   `kubectl top`, dashboards. What is the actual state, not the expected one.
2. **Contain** — stop the bleeding: scale down, roll back, cordon, delete the
   bad object. Restore service before finding the root cause.
3. **Diagnose** — `describe`, `logs --previous`, `exec`, `port-forward`,
   `kubectl debug`, `nslookup` from inside, `curl` between services.
4. **Recover** — apply the fix, watch the rollout, verify with `lab-verify.sh`.
5. **Prevent** — a probe, a limit, an alert, a backup, or a runbook entry. Every
   incident ends with one of these, or it will happen again.

**Drills (each is a script under `recovery/drills/`):**

| Drill | Injection | Expected lesson |
|---|---|---|
| crashloop | app exits 1 | `logs --previous`, exit codes |
| imagepull | wrong tag | `describe`, `imagePullSecrets` |
| pending | request 64 GiB | scheduler events, requests vs limits |
| oom | limit 16 MiB + allocation | exit 137, right-sizing |
| readiness | point probe at `/missing` | endpoints empty, 503, rollout stuck |
| liveness | probe too aggressive | restart loop caused by the probe |
| dns | wrong service name | `nslookup`, search domains |
| pvc-stuck | claim a class that does not exist | `Pending`, StorageClass names |
| ingress-404 | `rewrite-target` + prefix | L7 path semantics |
| node-notready | stop the node | rescheduling, `NotReady` tolerations |
| bad-secret | rotate the secret | pods do not reload env vars |
| data-loss | delete a PVC | reclaim policy, backup or regret |

**Recovery assets (data, not just pods):**

- `etcd` snapshot/restore (minikube: `minikube ssh`, `etcdctl snapshot save`).
- `pg_dump`/`pg_restore` on a schedule + restore drill.
- PVC backup (Velero if it fits, otherwise `tar` from a helper pod).
- GitOps revert: the manifests are the source of truth, so `git revert` is a
  recovery tool. That is why nothing is edited live without being written back.
- A one-page decision tree: symptom → first command → likely cause → fix.

Acceptance: every drill has a script, an expected output, a fix, and a
"prevent" line. The suite runs in under 15 minutes and leaves the lab healthy.

---

## T3 — Observability and traceability for controlled networks and hosts

Goal: answer "what is happening, where, since when, and who changed it" for the
cluster **and** the LAN hosts it talks to.

Layers, cheapest first:

| Layer | Component | What it answers | Cost |
|---|---|---|---|
| metrics | Prometheus (or VictoriaMetrics single) + node-exporter + kube-state-metrics | rates, saturation, restarts | ~600 MiB |
| logs | Loki single-binary + Alloy/Promtail | what was logged, correlation by pod | ~300 MiB |
| traces | Tempo single-binary + OTel collector | where a request spent its time | ~300 MiB |
| uptime | blackbox-exporter | is the host/URL up from outside | ~50 MiB |
| network | SNMP exporter (switches), node-exporter (hosts) | link state, errors, traffic | ~100 MiB |
| dashboards | Grafana | one place to look | ~200 MiB |
| alerts | Alertmanager → webhook/email | someone finds out | ~50 MiB |

Rules that make it traceable rather than decorative:

- **Instrument for identity:** every deployment carries `app.kubernetes.io/name`,
  `version`, and the Git SHA as a label. A metric without a version is a guess.
- **One trace id end to end:** W3C `traceparent` propagated through nginx →
  app → database. Log it in every service.
- **Host monitoring must survive the cluster.** Run the host exporters and
  Prometheus outside the cluster (or with a second, tiny instance). A monitoring
  stack that dies with the thing it monitors is useless.
- **Inventory before dashboards:** `observability/inventory/hosts.yaml` with
  name, address, role, owner, expected ports. No dashboard for a host that is
  not in the inventory.
- **Retention is a budget:** 7 days of metrics, 3 days of logs on this disk.
  Anything longer goes to object storage or it does not exist.
- **Alert on symptoms, not causes:** "page latency > 2 s", not "CPU > 80%".

Kubernetes-side extras: audit log shipping, events to Loki, `kubectl` command
logging, and a `who-changed-it` trail (Git history + `kubectl.kubernetes.io/last-applied-configuration`).

Acceptance: a request from the LAN can be followed through ingress → service →
pod → log line → trace span; a host reboot appears as an alert, not as a mystery.

---

## T4 — Boilerplate library

Goal: stop rewriting the same manifests, without hiding the decisions.

Two layers, matching what already exists:

1. **`paczki/k8s/`** — single-object templates for `paczek` (already started:
   deployment, service, configmap, secret, pvc, ingress, values, kustomization).
   Add: `cronjob`, `statefulset`, `job`, `networkpolicy`, `pdb`, `serviceaccount`,
   `rbac`, `hpa`, `externalsecret`, `otel-instrumentation`.
2. **`boilerplates/<stack>/`** — whole runnable projects (T1 layout), copied as a
   unit and then edited. A boilerplate is allowed to be opinionated; a paczek is
   not.

Conventions every boilerplate inherits:

- One namespace variable, one image variable, one port variable.
- Probes and resource requests present by default; no "add later".
- `make up|verify|down` always; `make check` offline.
- A README with "what I changed and why", not a copy of the Kubernetes docs.
- Images pinned by tag, never `latest`.

Acceptance: a new stack goes from empty folder to verified in under 10 minutes,
and the diff against the boilerplate is only the app.

---

## T5 — RAG with graphs and hypergraphs

Goal: a retrieval system whose answers can be traced back to documents and to
relations between them, not just to "some chunk".

Architecture (fits in ~1 GiB plus the models):

```
documents ──> ingest ──> chunks ──> embeddings ──> pgvector (vectors)
                 │                        │
                 ├──> entities/relations ─┴──> Postgres graph (nodes, hyperedges)
                 │
                 └──> provenance (source, page, hash, version)

question ──> rewrite ──> hybrid retrieve (BM25 + vector)
                      ──> graph expand (2 hops / hyperedge members)
                      ──> rerank (host GPU)
                      ──> answer + citations + trace id
```

Component choices for this hardware:

| Piece | Choice | Why |
|---|---|---|
| vector store | pgvector in the existing Postgres | one database, one backup, no extra 500 MiB |
| graph store | Postgres tables + recursive CTEs (or Apache AGE) | same reason; Neo4j Community later if queries get deep |
| hypergraph | `edges(id, kind, source, confidence)` + `edge_nodes(edge_id, node_id, role)` | a hyperedge is a set, so a join table is the honest model |
| embeddings | host GPU: `bge-m3` or `nomic-embed-text` | 8 GiB VRAM is plenty |
| rerank | host GPU: `bge-reranker-v2-m3` | biggest quality win per megabyte |
| generation | host: llama.cpp or Ollama, 7–8B Q4 | do not put the model in the cluster |
| orchestration | one Python service in the cluster | small, observable, replaceable |
| tracing | OpenTelemetry → Tempo | reuse T3 |

Why a hypergraph and not just a graph: a relation like "document A, document B
and person C jointly define policy P" has three members and one meaning. Modelling
it as pairwise edges loses the fact that it is one relation. The join table above
keeps arity, provenance and confidence, and still answers "what is connected to
this node" with a normal SQL query.

Deliverables:

- `ai/rag/compose.yaml` for local runs + `ai/rag/k8s/` for the cluster.
- A 20-document sample corpus with known answers (otherwise evaluation is fiction).
- A golden question set (30–50 questions) and a score script: recall@k, citation
  precision, answer faithfulness, latency.
- A trace per question: retrieved chunks, graph path, rerank scores, prompt
  version, model version. Without this, "the answer is wrong" is untraceable.

Acceptance: a question returns an answer with citations; removing a cited
document changes the answer; the golden set score is recorded per commit.

---

## T6 — Cloud free tiers

Goal: run one experiment on somebody else's cluster, learn the difference from a
laptop, and get out before the bill arrives.

| Provider | What is free (verify at signup) | Shape | Good for | Trap |
|---|---|---|---|---|
| Oracle Cloud | Always Free: 4 OCPU Ampere + 24 GiB RAM + block storage | self-managed k3s on a VM | the only "always free" real cluster | capacity availability, idle reclamation |
| Google Cloud | credit for new accounts; GKE has a free zonal tier | managed control plane | real LoadBalancer, ingress, cloud storage | credit expires, LB costs |
| Azure | credit for new accounts; AKS free tier control plane | managed | enterprise-ish defaults | node VMs are not free |
| AWS | 12-month trial; EKS control plane is paid | managed | IAM/RBAC depth | the most expensive mistake |
| Civo | short-lived credit, k3s | managed k3s | fastest k3s experience | expires quickly |
| GitHub Codespaces / Killercoda | hours per month | k3d in a container | a smoke test, not a cluster | no inbound networking |

Rules:

- One provider, one experiment, one teardown checklist.
- A budget note in `cloud/<provider>/README.md`: what is free, what is not, what
  expires, how to delete every billable object.
- Never put secrets or real data in a trial account.
- The lab manifests must run unchanged; if they need cloud-specific objects
  (LoadBalancer, StorageClass), the overlay says so.

Acceptance: the A6 stack runs on one free cluster, the LAN-equivalent access
works (public IP or `kubectl port-forward`), and the teardown is proven by a zero
bill the next day.

---

## T7 — AI patterns: mockups and models

Goal: a catalogue of the shapes that recur in AI systems, each with a diagram, a
data contract, a failure mode and a metric. Not a framework, a reference.

| Pattern | Shape | k8s pieces | Fails when | Metric |
|---|---|---|---|---|
| RAG | retrieve → rerank → generate | api + pgvector + job | retrieval is bad, prompt is blamed | recall@k, citation rate |
| tool-using agent | plan → call → observe → repeat | api + workers + queue | loops, unbounded cost | steps per task, cost per task |
| router | cheap model first, escalate | api + two model endpoints | router drift | escalation rate, quality delta |
| guardrails | input filter → model → output filter | sidecar or gateway | false positives block real work | block rate, false-positive rate |
| eval loop | golden set → score → report | CronJob + results table | the set never grows | score per commit |
| semantic cache | embed question → nearest answer | redis/pgvector | stale answers | hit rate, staleness |
| HITL | model proposes, human approves | api + queue + UI | queue grows silently | approval latency |
| batch inference | chunk input → workers → merge | Job + queue | partial output looks complete | completion ratio |
| streaming | token stream + backpressure | api + SSE | timeouts under load | time to first token |
| memory | short-term + long-term store | redis + pgvector | memory poisoning | contradiction rate |
| multi-tenant | namespace per tenant, quota per tenant | namespaces + ResourceQuota | noisy neighbour | p95 per tenant |
| drift | compare live vs golden | CronJob + metrics | nobody reads the report | score delta |

Each entry gets, in `ai/patterns/<name>/`:

- `README.md` — problem, shape, when not to use it.
- `mockup.svg` (or mermaid) — boxes and arrows, no vendor logos.
- `contract.yaml` — request/response schema, limits, timeouts, retry policy.
- `k8s/` — the minimal deployment that demonstrates the shape.
- `failure.md` — how it breaks, what the metric looks like when it does.

Acceptance: the catalogue is readable by someone who has never built an AI
system, and each entry can be deployed and broken on this laptop.

---

## Order of work

1. Finish the core lab (phases 0–10 in `02-todo.md`).
2. T4 boilerplates (cheap, unblocks everything).
3. T2 recovery drills (no new dependencies).
4. T1 first three stacks (Node, Python, Go), then stateful.
5. T3 observability, minimal, installed once.
6. T7 patterns catalogue (documents only), then T5 RAG as the first real pattern.
7. T6 cloud experiment last: it needs the manifests to be stable.

Each track is closed only when it has: a runbook, a script, a captured output,
and a row in `docs/coverage-matrix.md`.
