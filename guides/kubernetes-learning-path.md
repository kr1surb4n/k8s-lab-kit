# Kubernetes learning path

**Read this when:** you want to learn Kubernetes by working through this
repository, in a deliberate order, with proof that you understood each stage.

**After reading you can:** run the core lab, explain the mechanisms, break and
recover a workload, package a new project, and move the same manifests to a
second cluster.

This is a plan, not a race. The full path is about **45-60 focused hours**. The
core Kubernetes path (stages 0-8) is about **30-35 hours**; recovery, observability,
AI/RAG, and portability are advanced branches.

## 1. Who this is for

You need:

- basic Linux shell: `cd`, pipes, environment variables, editing files;
- basic YAML: indentation, lists, maps;
- basic container knowledge: image, container, port;
- a machine with enough disk/RAM for a local cluster (check `make doctor`);
- a disposable local cluster. Do not use a work cluster.

You do **not** need to know Kubernetes first. That is the point of the lab.

## 2. Setup

Run these from the repository root.

```bash
# 1. Read the orientation.
sed -n '1,200p' START-HERE.md
sed -n '1,220p' guides/README.md

# 2. Check the machine before installing or starting anything.
make doctor

# 3. Install the clients if they are missing.
make tools

# 4. Confirm the offline suite is green.
make test

# 5. Start the cluster only when you are ready for stage 1.
make cluster

# 6. Confirm where kubectl is pointed.
kubectl config current-context
kubectl get nodes -o wide
```

If `make doctor` reports a `FAIL`, fix that before continuing. The common
blockers are missing tools, insufficient disk, a port already in use, or Docker
not running as your user.

Create a learning journal outside the repository:

```bash
mkdir -p ~/k8s-notes
cd ~/k8s-notes
git init
printf '# Kubernetes lab notes\n' > README.md
git add README.md
git commit -m "docs: start the lab journal"
```

For every stage, write four lines:

```text
Command:
Output:
Why:
What I would change in a real project:
```

That last line is how the lab becomes reusable instead of a set of memorized
commands.

## 3. The stages at a glance

| Stage | Focus | Time | Main evidence |
|---|---|---|---|
| 0 | Orientation and safety | 1 h | `make doctor`, `make test`, `make demo` |
| 1 | Cluster and kubectl | 2 h | nodes, pods, describe, logs, exec |
| 2 | A1 + A2: host files and ConfigMaps | 4 h | live edit without restart; ConfigMap propagation |
| 3 | A3 + A5: environment and Secrets | 3 h | env precedence; 401 -> 200 |
| 4 | A4 + N1: networking and ingress | 4 h | LAN access; host/path routing; rewrite 404 |
| 5 | A6: replicas, probes, rollout | 3 h | scale, rolling update, rollback, probe failure |
| 6 | A7: stateful multi-container stack | 5 h | nginx + PHP + PostgreSQL + SQLite |
| 7 | Failure and recovery | 4 h | inject -> diagnose -> recover -> prevent |
| 8 | Packaging and portability | 5 h | base + overlay; image load; second cluster |
| 9 | Observability and traceability | 4 h | metrics, logs, traces, alert |
| 10 | AI/RAG branch (optional) | 6 h | local index, answer with citations, eval |
| 11 | Capstone: new project | 6-8 h | deployed app, runbook, rollback, drill |
| 12 | Cloud branch (optional) | 4 h | plan, deploy, prove, tear down |

Total: ~50-60 hours including both optional branches.

## 4. Stage details

### Stage 0 - Orientation and safety (1 h)

**Read:** `START-HERE.md`, `guides/README.md`, root `README.md`,
`analysis/01-analysis.md` (first pages), `docs/coverage-matrix.md`.

**Run:**

```bash
make doctor
make test
make demo
```

**Prove:** you can explain the difference between the real lab and the fake
kubectl, and you can name the five important directories: `docs/`, `manifests/`,
`scripts/`, `boilerplates/`, `observability/`.

**Checkpoint:** "`make demo` passed" is not evidence that a cluster works. Why
not? If you cannot answer, read `guides/repo-reading-map.md` before continuing.

### Stage 1 - Cluster and kubectl (2 h)

**Read:** `docs/runbooks.md` "Common setup" and `docs/example-runs.md` section 1.

**Run:**

```bash
make cluster
kubectl get nodes -o wide
kubectl get namespaces
kubectl get pods -A
kubectl run hello --image=nginx:1.27-alpine --port=80
kubectl get pod hello -o wide
kubectl describe pod hello
kubectl logs hello
kubectl exec hello -- nginx -v
kubectl delete pod hello
```

**Prove:** you can read a pod's state, events, logs, and container environment.
You can explain `Pending`, `ContainerCreating`, `Running`, and `CrashLoopBackOff`
at a high level.

**Checkpoint:** why does `kubectl get pods` show a different set of pods than
`kubectl get pods -n k8s-lab`? What is the namespace for?

### Stage 2 - A1 and A2: files and configuration (4 h)

**Read:** `docs/runbooks.md` A1 and A2; `manifests/a1/web.yaml`;
`manifests/a2/web.yaml`.

**Run A1:**

```bash
scripts/lab-up.sh a1 --mount
scripts/lab-tunnel.sh --background
curl -s http://127.0.0.1:8080 | head -5
curl -sI http://127.0.0.1:8080/images/logo.svg | head -3
```

Edit `site/index.html` on the host and re-run `curl`. The page must change with
no pod restart. Then clean up:

```bash
scripts/lab-down.sh a1
```

**Run A2:**

```bash
scripts/lab-up.sh a2
scripts/lab-tunnel.sh --background
curl -s http://127.0.0.1:8080 | head -5
kubectl edit configmap web-index -n k8s-lab
```

Change the heading, save, and watch the page change. Then try a `subPath` mount
to prove it stops updating, and restore the directory mount. Read the 1 MiB
ConfigMap limit section in the runbook.

**Prove:** you can explain `hostPath`, projected ConfigMap volumes, kubelet sync,
and why images do not belong in a ConfigMap.

**Checkpoint:** what changes without a restart, and what requires a new pod?
Name one thing that requires a new pod even though the source object changed.

### Stage 3 - A3 and A5: environment and Secrets (3 h)

**Read:** `docs/runbooks.md` A3 and A5; `manifests/a3/`, `manifests/a5/`.

**Run A3:**

```bash
scripts/lab-up.sh a3
kubectl exec deploy/web -n k8s-lab -- printenv | sort
kubectl describe pod -n k8s-lab -l app.kubernetes.io/name=web
```

Answer the four questions from the runbook: who sets the variable, when is it
read, where does it live, and which mechanism wins when several define it.

**Run A5:**

```bash
scripts/lab-up.sh a5
scripts/lab-tunnel.sh --background
curl -si http://127.0.0.1:8080/ | head -3
curl -si -u lab:labpass http://127.0.0.1:8080/ | head -3
kubectl get secret web-basic-auth -n k8s-lab -o yaml
```

**Prove:** you can explain why a Secret is not encrypted, why a mounted file can
be safer than an env var, and why the demo password must never be reused.

**Checkpoint:** name three places a secret can leak in this setup. Then name the
production replacement for a committed Secret.

### Stage 4 - Networking, LAN, and ingress (4 h)

**Read:** `docs/runbooks.md` A4 and N1; `clusters/README.md`.

**Run A4:**

```bash
scripts/lab-up.sh a6
scripts/lab-tunnel.sh --background --port 8080
curl -s http://127.0.0.1:8080 | head -3
curl -s http://$(hostname -I | awk '{print $1}'):8080 | head -3
```

If you have a second machine on the same LAN, open `http://<host-ip>:8080` there.
If not, read the comparison table and explain why the `LoadBalancer` alone is
not enough on minikube.

**Run N1:**

```bash
minikube addons enable ingress
kubectl get pods -n ingress-nginx
scripts/lab-up.sh a6
# Follow the ingress steps in docs/runbooks.md N1.
```

Prove host-based routing with a `Host` header, then reproduce the `rewrite-target`
404 and fix it.

**Prove:** you can explain ClusterIP, NodePort, LoadBalancer, port-forward,
Ingress, and the difference between "reachable on the host" and "reachable from
the LAN".

**Checkpoint:** which mechanism works on minikube, k3d, and a bare cluster for
LAN access? What changes on managed Kubernetes?

### Stage 5 - A6: replicas, probes, rollout (3 h)

**Read:** `docs/runbooks.md` A6; `manifests/a6/web.yaml`.

**Run:**

```bash
scripts/lab-down.sh all --yes
scripts/lab-up.sh a6
scripts/lab-status.sh a6
scripts/lab-scale.sh --delta 1
scripts/lab-scale.sh --delta -1
scripts/lab-rollout.sh image nginx:1.28-alpine
kubectl get pods -n k8s-lab -w
scripts/lab-rollout.sh undo
```

Then remove the readiness probe and update the image again. Watch for failed
requests during the rollout, then restore the probe.

**Prove:** you can explain `maxSurge`, `maxUnavailable`, ReplicaSets, readiness,
liveness, and `kubectl rollout undo`.

**Checkpoint:** why did the update become invisible with the probe, and visible
without it? What is the risk of an aggressive liveness probe?

### Stage 6 - A7: state, init, and permissions (5 h)

**Read:** `docs/runbooks.md` A7; `manifests/a7/app.yaml`;
`manifests/a7/postgres.yaml`; `app/`.

**Run:**

```bash
scripts/lab-up.sh a7 --build --mount
scripts/lab-status.sh a7
scripts/lab-tunnel.sh --background
curl -s http://127.0.0.1:8080 | grep -E 'SQLite|PostgreSQL|row'
```

Then insert a row into `app/database/database.sqlite` from the host, reload, and
see it. Use `kubectl exec` to run `psql` against PostgreSQL. Break the mount
permissions, read `SQLITE_CANTOPEN` / `permission denied`, and fix it with the
init container.

**Prove:** you can explain why nginx and PHP-FPM share a pod, why SQLite needs a
single writer, and why PostgreSQL is a Service while SQLite is a file.

**Checkpoint:** what would break with three replicas of A7? What is the
production answer to that constraint?

### Stage 7 - Failure and recovery (4 h)

**Read:** `recovery/method.md`, `recovery/decision-tree.md`,
`docs/runbooks.md` T1, `scripts/lab-drill.sh`.

**Run one drill at a time:**

```bash
# Inject the failure, then verify the bad state yourself.
scripts/lab-drill.sh crashloop --inject
kubectl get pods -n k8s-lab
kubectl describe pod -n k8s-lab -l app.kubernetes.io/name=web
kubectl logs -n k8s-lab -l app.kubernetes.io/name=web --previous

# Recover and let the script verify the lab.
scripts/lab-drill.sh crashloop --recover
```

`make drills` is the fast path: it injects all four drills, waits, then recovers
all four. It is useful for a smoke test, but it is not a substitute for observing
one failure at a time.

Then pick one failure and do it manually: read the state with `describe`, `logs
--previous`, and events; contain it; diagnose the root cause; recover; add one
preventive change. Write the five steps in your journal.

**Prove:** you can explain why "delete the pod" is not a diagnosis, and why every
incident needs a prevention step.

**Checkpoint:** what is the difference between a readiness failure and a liveness
failure? Which one should page a human?

### Stage 8 - Packaging and portability (5 h)

**Read:** `boilerplates/base/*.yaml`,
`boilerplates/stacks/python-fastapi/kustomization.yaml`, `paczki/k8s/_about.md`,
`guides/project-to-project.md`, `clusters/README.md`.

**Run:**

```bash
# Render the base without touching a cluster.
kubectl kustomize boilerplates/base

# Build and load one stack image.
docker build -t boilerplate/python-fastapi:1.0 boilerplates/stacks/python-fastapi
minikube image load boilerplate/python-fastapi:1.0

# Apply one stack in the lab namespace.
kubectl apply -k boilerplates/stacks/python-fastapi
kubectl get pods -n k8s-lab -l app.kubernetes.io/name=python-fastapi
# The stack overlays in this repository keep the base object name (base-app).
kubectl port-forward -n k8s-lab svc/base-app 8000:80
curl -s http://127.0.0.1:8000/healthz
```

The stack overlays are references, not a finished naming scheme: they keep the
base object name `base-app`, so applying two stacks at once collides on the
Service. Rename the objects in the copied base before using more than one stack.

Then copy the base outside the repo and make a small overlay for a new name,
namespace, image, and replica count. Render it and diff it.

**Prove:** you can explain why `kubectl apply -k` is not the same as
`kubectl apply -f`, how an overlay changes a base, and why images must be loaded
into minikube/kind/k3d.

**Checkpoint:** which values belong in a base and which belong in an overlay?
Name three things that should never be in the base.

### Stage 9 - Observability and traceability (4 h)

**Read:** `observability/README.md`, `observability/trace/README.md`,
`docs/example-runs.md` sections 8 and 9.

**Run:**

```bash
make obs PROFILE=minimal
kubectl -n observability get pods
kubectl -n observability port-forward svc/kube-prometheus-stack-grafana 3000:80
```

Open Grafana, find a target, and read one metric. Then add the `traces` profile if
your machine has room, instrument or run one app that emits a trace, and follow
one trace id from the app log to Tempo. Finally, trigger the alert webhook or
read the recorded proof.

**Prove:** you can explain the difference between metrics, logs, and traces, and
why "a Grafana screenshot" is not observability.

**Checkpoint:** what does a trace id let you do that a log line alone does not?
Why should host monitoring survive the cluster it watches?

### Stage 10 - AI/RAG branch (optional, 6 h)

Do this only after the core lab. It is a separate product pattern, not a
Kubernetes basic.

**Read:** `ai/patterns/rag/README.md`, `ai/patterns/graph-rag/app/README.md`,
`ai/patterns/graph-rag/failure-modes/failure-modes.md`,
`ai/patterns/graph-rag/models/README.md`.

**Run:** follow the app README with the local Ollama models and the eval database.
Run `make eval-local` and read the score table. Ask one question over the lab
corpus and one over private notes, if configured. Verify citations and refusal
behavior.

**Prove:** you can explain hybrid retrieval, RRF, graph context, reranking, and
why private queries must use a local model. You can also explain why the current
service must not be exposed publicly.

**Checkpoint:** what would you add before letting another person query your
private index? Name at least three controls.

### Stage 11 - Capstone: new project (6-8 h)

Use [`project-to-project.md`](project-to-project.md) to create a new project
outside this repository:

1. Choose a tiny app (or one stack template).
2. Copy the base and create dev/staging overlays.
3. Build, push or load the image.
4. Deploy to the local cluster.
5. Prove readiness, endpoints, and a smoke test.
6. Run one failure drill, then roll back.
7. Write a one-page runbook.
8. Promote the same image digest to a second namespace or cluster.

**Prove:** someone else can read your README, run two commands, and get the same
result. That is the real definition of portability.

### Stage 12 - Cloud branch (optional, 4 h)

**Read:** `cloud/README.md` and `analysis/07-what-to-do.md` section 5.

This branch is plan-only until you have an account. Before spending money:

- write the budget and teardown note first;
- keep Terraform state and credentials out of git;
- deploy the smallest shape;
- prove outside access;
- destroy everything and verify the bill is zero.

Do not start with the cloud branch. The local lab teaches the same Kubernetes
concepts without a bill or a provider-specific control plane.

## 5. Six-week schedule

At 7-9 hours per week:

| Week | Stages | Goal |
|---|---|---|
| 1 | 0, 1, 2 | Get oriented, run the cluster, understand host files and ConfigMaps |
| 2 | 3, 4 | Secrets, environment, Service/Ingress, LAN access |
| 3 | 5, 6 | Replicas, probes, rollout, stateful stack |
| 4 | 7, 8 | Recovery drills, packaging, portability |
| 5 | 9, 11 start | Observability, then start the capstone |
| 6 | 11 finish, 12 optional | Capstone, rollback drill, optional cloud plan |

At 2-3 hours per week, stretch this to 12-16 weeks. Do not compress stages 2, 3,
6, and 7; they are where the real understanding lives.

## 6. Checkpoint rubric

Do not advance just because the command exited 0. Use this rubric:

| Level | What it looks like |
|---|---|
| 1 - Reproduce | You can run the commands from the runbook and get the expected output. |
| 2 - Explain | You can explain why it worked without reading the runbook. |
| 3 - Diagnose | You can break it on purpose, identify the cause, and recover. |
| 4 - Port | You can apply the same pattern to a new app or a different cluster. |
| 5 - Teach | You can write a short runbook that lets someone else do levels 1-3. |

The core path is complete when you reach level 3 on A1-A7 and level 4 on at
least one stack. The advanced path is complete when you reach level 4 on
recovery, packaging, and observability.

## 7. Common traps

- `make demo` uses a fake kubectl. It is not cluster evidence.
- A1/A7 need `minikube mount`; without it, pods stay in `ContainerCreating`.
- A2 breaks if you use `subPath`; the file stops updating.
- A ConfigMap is text-only and limited to 1 MiB.
- A LoadBalancer on minikube stays `<pending>`; port-forward is the LAN answer.
- A7 must stay at one replica because SQLite has a single writer.
- A7's PHP-FPM runs as uid 82; the init container fixes ownership.
- The demo password is `labpass` on purpose. Never reuse it.
- The observability `full` profile may not fit next to a build and the models.
- `make test` is an offline suite, not a cluster integration test.
- `docs/exercises/EXERCISES.md` has mismatched commands; use
  `docs/runbooks.md`.
- Old documents say 36 tests; run `make test` for the current count.

## 8. What to skip on the first pass

Skip these until the core path is done:

- `ai/patterns/` and local models;
- `cloud/`;
- the `full` observability profile;
- `bastion/`;
- the imported Graph RAG Kubernetes scaffold;
- the PDF and the original prompt files (they are source material, not a
  tutorial).

Read them later as branches, not as prerequisites.

## 9. Completion test

You are done with the core path when you can do all of these without following a
runbook line by line:

- [ ] Start a local cluster and prove it is healthy.
- [ ] Deploy a stateless app, expose it, and explain the Service path.
- [ ] Change configuration without rebuilding the image, and explain which
      changes need a restart.
- [ ] Use a Secret safely enough to explain its limits.
- [ ] Scale, roll out, and roll back with probes.
- [ ] Run a stateful stack and explain the single-writer constraint.
- [ ] Inject a failure, diagnose it, recover it, and add a prevention.
- [ ] Package an app with a base and an overlay and move it to a second cluster.
- [ ] Explain which parts of this repository you would not put in production.

If you can do those, the repository has served its purpose: you can now learn a
new project from its manifests and runbooks rather than from a blank page.
