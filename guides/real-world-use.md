# Using this repository in real projects

**Read this when:** you want to know whether the lab's sources and solutions can
be reused at work, and what must change before they are production-safe.

**After reading you can:** choose a starting point, implement a first deployment,
and state exactly what is still missing before production.

## 1. The honest verdict

There are three different things in this repository, and they have different
answers:

| Thing | Real-world answer |
|---|---|
| **Methods and operating patterns** (runbooks, recovery method, probe/resource discipline, evidence-first docs) | Reuse them. They are the most valuable part and they transfer to any cluster. |
| **Templates and skeletons** (Kustomize base, stack overlays, paczki objects, cluster notes, observability profiles) | Reuse them **as starting points**, then replace environment-specific values and add the missing controls. |
| **The lab itself** (A1-A7 manifests, demo secrets, `k8s-lab` namespace, minikube mounts, fake kubectl, single-node sizing) | Do not deploy unchanged. It is deliberately small, local, and openly unsafe in places. |

The repository has no root `LICENSE` file. Before commercial redistribution,
check the license and provenance of the source material, the third-party images,
and the Helm charts. "It is in my git repo" is not a license grant.

The phrase "Production-ready Kubernetes overlays" in
`boilerplates/stacks/README.md` should be read as "a better starting point than a
blank folder", not as a certification. The overlays still lack production
controls listed in section 5.

## 2. What is directly reusable

| Asset | Use it for | Reality check |
|---|---|---|
| `boilerplates/base/` | A stateless HTTP Deployment + Service skeleton with probes, rolling update, and resource requests | It uses `base-app`, `nginx:1.27-alpine`, and `namespace: default`. Rename and retarget it. |
| `boilerplates/stacks/*` | Runtime-specific examples: Node, Python, Go, Java, worker/CronJob, PostgreSQL, Redis, MinIO | Each stack references `../../base`, so it works inside this repo. Copy the base too when you leave. |
| `paczki/k8s/*.tpl` | Single-object starting points: Deployment, Service, ConfigMap, Secret, PVC, Job, CronJob, StatefulSet, NetworkPolicy, PDB, RBAC, HPA, Ingress | They are deliberately generic. They are not policy-compliant by default. |
| `docs/runbooks.md` A1-A7, D1, H1, N1, T1 | Teaching sequences and operational explanations | Written for the lab. Commands assume `k8s-lab` and a local cluster. |
| `recovery/method.md` | The Observe -> Contain -> Diagnose -> Recover -> Prevent loop | Directly reusable as an incident method. It is not a replacement for your on-call process. |
| `observability/` | Profiles, trimmed values, alert rules, host monitoring, trace instrumentation | Sized for a 6-8 GiB lab. Single-binary, short retention, no HA. |
| `clusters/` | Local/testing cluster skeletons and the portability differences between minikube, kind, k3d, k3s, managed | Use managed Kubernetes for production; these are dev/test references. |
| `scripts/lab-*.sh` | Examples of idempotent, `--dry-run`-friendly, failure-loud scripts | They are lab automation. Do not point them at a work cluster. |
| `tests/run.sh` | An example of an offline, fake-cluster test harness and executable specification | The fake kubectl proves script flow, not Kubernetes behavior. |
| `ai/patterns/graph-rag/app/` | A working local search/ask tool over private notes and papers | Host-side, localhost-only, no authentication. Read section 4.4 first. |
| `app/` and `site/` | Small demo workloads for learning | Not a production application. |

## 3. What not to use as-is

| Artifact | Why it is not production-ready |
|---|---|
| `manifests/a*/` | Teaching manifests with `hostPath`, `/mnt/lab`, demo values, one namespace, no TLS, no auth, no backup, no NetworkPolicy, no PDB. |
| `manifests/a5/` | Contains a public demo password (`lab` / `labpass`). It is intentionally public and must never be reused. |
| `scripts/demo/kubectl` | A fake client. It always succeeds. It is named and labeled as fake, but copied commands can still confuse a reader. |
| `boilerplates/base/` | No TLS, no Ingress, no NetworkPolicy, no PDB, no HPA, no `securityContext`, no image digest, no secret manager, and only a memory limit. |
| `boilerplates/stacks/*` | Local image names such as `boilerplate/python-fastapi:1.0`, `namespace: k8s-lab`, no policy objects, no production secrets, no backup. |
| `scripts/lab-*.sh` | Assumes a disposable cluster, a single namespace, and a local image registry. The scripts are not a CI/CD system. |
| `observability/install.sh` | Convenience installer for one machine. It does not create highly available monitoring, durable long-term storage, or tenant isolation. |
| `bastion/` | A jump-box scaffold with SSH and setup scripts. It is not deployed or hardened here; review it as security-sensitive code. |
| `cloud/` | Notes and provider research only. There is no Terraform implementation in this repository. |
| `ai/patterns/graph-rag/k8s/` | The imported scaffold is not the current app packaging. The local tool is the source of truth; do not deploy that old mockup. |
| `ai/patterns/graph-rag` as a service | No authentication, no multi-user isolation, no TLS, no rate limits, private data, and local model dependencies. |
| `tests/run.sh` and `make test` | They do not prove that a real cluster applies, schedules, connects, or recovers. They prove offline script and manifest consistency. |
| `docs/exercises/EXERCISES.md` | Imported material with mismatched `make` targets and placeholder scenarios. Use `docs/runbooks.md` instead. |

## 4. Implementation recipes

The general rule is: **copy the smallest useful unit, replace every environment
value, and validate against a disposable cluster before production.**

For a full new-project workflow, see
[`project-to-project.md`](project-to-project.md). The recipes below are the
decision points.

### 4.1 New stateless HTTP service

Use `boilerplates/base` plus one runtime stack as a reference. Do not copy the
whole repository.

```bash
# Create a new repository and copy the base skeleton.
mkdir -p my-service/deploy/base
cp /path/to/k8s/boilerplates/base/*.yaml my-service/deploy/base/

# Copy only the runtime files you need; this example uses the Python stack.
cp /path/to/k8s/boilerplates/stacks/python-fastapi/main.py my-service/app/
cp /path/to/k8s/boilerplates/stacks/python-fastapi/requirements.txt my-service/app/
cp /path/to/k8s/boilerplates/stacks/python-fastapi/Dockerfile my-service/
```

Then do these edits before the first deploy:

1. Rename `base-app` to your service name in the Deployment and Service.
2. Change the selector label only once, and make both objects agree. The
   Deployment selector is immutable; a rename means recreate, not patch.
3. Replace `nginx:1.27-alpine` with your image. Use a registry path and a
   version or digest, never `latest`.
4. Set the container port, probe paths, CPU/memory requests and limits, and a
   `startupProbe` if the runtime is slow to boot (Java is the obvious case).
5. Put non-secret configuration in a ConfigMap. Keep secrets out of the repo.
6. Add an Ingress with TLS if the service is reachable from outside the cluster.
7. Add `NetworkPolicy` with a default-deny posture and explicit allows.
8. Add a `PodDisruptionBudget` and an `HPA` only after you know the traffic and
   disruption requirements.
9. Add a namespace per environment (or per team), not one shared `k8s-lab`.

Build and validate:

```bash
# Build and push (or load into the local cluster).
docker build -t registry.example.com/me/my-service:1.2.3 .
docker push registry.example.com/me/my-service:1.2.3

# Render exactly what will be applied.
kubectl kustomize deploy/overlays/dev > /tmp/my-service.yaml

# Compare with the live state before applying.
kubectl diff -f /tmp/my-service.yaml

# Apply and wait for readiness.
kubectl apply -f /tmp/my-service.yaml
kubectl rollout status deploy/my-service -n my-service-dev --timeout=120s

# Prove the Service has endpoints.
kubectl get endpoints my-service -n my-service-dev
```

For a local cluster, replace the push with the cluster-specific image load:

```bash
# minikube
minikube image load registry.example.com/me/my-service:1.2.3

# kind
kind load docker-image registry.example.com/me/my-service:1.2.3

# k3d
k3d image import registry.example.com/me/my-service:1.2.3 -c k8s-lab
```

The exact registry/load command must match the cluster. A local image that is not
loaded will produce `ImagePullBackOff`, not a code bug.

### 4.2 Stateful workload

Do not copy `boilerplates/stacks/stateful-postgres` into production and call it a
database platform. It is a useful demonstration of a StatefulSet with a PVC per
replica. A production database needs more:

- a managed database or a well-maintained operator;
- tested backups and a restore drill, not only a PVC;
- a real StorageClass with the right reclaim policy;
- one writer where the engine requires it (the lab's SQLite lesson);
- anti-affinity, PDB, resource limits, and monitoring;
- an upgrade plan for the engine, not just the YAML.

A safe sequence is:

```bash
# Read the demonstration, do not apply it to production.
sed -n '1,220p' boilerplates/stacks/stateful-postgres/postgres.yaml

# In a disposable namespace, prove the PVC binds and data survives a pod restart.
kubectl apply -k boilerplates/stacks/stateful-postgres
kubectl get pvc -n k8s-lab
kubectl delete pod -n k8s-lab -l app.kubernetes.io/name=postgres
kubectl get pods -n k8s-lab -w
```

Then replace the demo database with your platform's database service. The lesson
that transfers is the failure mode, not the YAML.

### 4.3 Observability

The `observability/` stack is a learning lab with useful defaults. It is not a
production monitoring platform.

```bash
# Smallest profile; check disk and RAM first.
make obs PROFILE=minimal

# Verify the stack is alive.
kubectl -n observability get pods
kubectl -n observability port-forward svc/kube-prometheus-stack-grafana 3000:80
```

Read the full cautions in `observability/README.md`. For production:

- run host/cluster monitoring outside the cluster it watches, or use a second
  independent instance;
- use durable remote storage and an explicit retention budget;
- put authentication, TLS, and network policy in front of Grafana, Loki, Tempo,
  and Alertmanager;
- use secrets from a secret manager;
- test alert delivery, not only alert rules;
- define SLOs and symptom-based alerts before adding dashboards;
- do not install the `full` profile next to a build job on a 6 GiB machine.

### 4.4 Local RAG and Graph RAG

The working tool is `ai/patterns/graph-rag/app/`. Read its README before using
it. The important properties are:

- local Ollama and local Postgres; private notes and papers stay on the host;
- two databases: eval on `5433`, private on `5434`;
- CLI, HTTP, and MCP interfaces;
- citations and a graph path in the answer;
- a golden-set evaluation with a recorded baseline.

Do **not** expose the current HTTP service as-is. It has no authentication, is
designed for localhost, and can read private material. If you need a shared
service, add at minimum:

- authentication and per-user authorization;
- TLS and network restrictions;
- per-tenant data isolation and retention rules;
- audit logging that does not leak document text;
- rate limits and request size limits;
- a secret manager for model/provider credentials;
- a packaging and migration plan (the current Kubernetes packaging is deferred);
- a privacy review before any remote model or provider is used.

For local use, follow `app/README.md` and keep the private configuration at
`~/.config/graphrag/config.yaml` (mode `0600`, never committed). The repository's
`make eval-local` benchmark is a regression test, not a production SLA.

### 4.5 Choosing a cluster

Use the cluster skeletons in `clusters/` for development and CI, not as a
recommendation for production.

| Cluster | Good for | What changes when you move |
|---|---|---|
| minikube | one-machine learning, A1-A7 | LoadBalancer stays `<pending>`; host mounts; port-forward for LAN; `standard` StorageClass |
| kind | CI, quick disposable clusters | images must be loaded; no built-in ingress; node ports are not host ports |
| k3d | local cluster with published ports | images must be imported; `local-path` StorageClass; Traefik may be disabled |
| k3s | small real server or homelab | host changes (systemd, iptables); `local-path`; NodePort works on the host |
| managed | production | external load balancer, cloud StorageClass, IAM, audit, provider-specific ingress |

The app manifests should be the same across them. Only the overlay values
(image, storage class, ingress class, replicas, resources) should differ. If you
need to edit the base for every cluster, the base is not portable enough.

## 5. Production hardening checklist

This is the gap between the lab and a real deployment. It is intentionally
strict; not every item applies to every service, but each one needs a decision.

### Workload

- [ ] Image pinned by digest or immutable version; no `latest`.
- [ ] Non-root user, read-only root filesystem where possible, dropped
      capabilities, seccomp/AppArmor profile.
- [ ] CPU and memory requests and limits; right-sized from measurement.
- [ ] Startup, readiness, and liveness probes with realistic timings.
- [ ] `terminationGracePeriodSeconds` and graceful shutdown.
- [ ] Multiple replicas where the app supports it; anti-affinity/topology spread.
- [ ] PodDisruptionBudget for voluntary disruptions.
- [ ] HPA only after the app is safely horizontally scalable.

### Configuration and secrets

- [ ] ConfigMap for non-secret config; no config baked into images.
- [ ] External Secrets, Sealed Secrets, SOPS, or a cloud secret manager.
- [ ] Secret rotation and a plan for pods that do not reload env vars.
- [ ] Namespace-scoped RBAC; no cluster-admin service accounts.
- [ ] ServiceAccount token automount disabled where not needed.

### Network and exposure

- [ ] Default-deny NetworkPolicy with explicit ingress/egress.
- [ ] Ingress with TLS, host allowlist, and authentication where needed.
- [ ] No public admin dashboards, databases, or RAG endpoints.
- [ ] DNS and egress requirements documented.
- [ ] Rate limits and request size limits at the edge.

### Data

- [ ] A StorageClass with the correct reclaim policy and encryption.
- [ ] Backups scheduled and **restore tested**.
- [ ] Data retention and deletion rules, especially for private notes/papers.
- [ ] Single-writer constraints understood (SQLite is a lab lesson, not a
      production database).
- [ ] Migration jobs are idempotent and observed.

### Delivery

- [ ] CI builds, tests, scans, signs, and pushes the image.
- [ ] GitOps or a controlled apply pipeline; no manual edits without a commit.
- [ ] Drift detection and a rollback path.
- [ ] Environment overlays for dev/staging/prod, with the same digest promoted.
- [ ] Cluster upgrades and deprecation checks are planned.

### Observability and operations

- [ ] Metrics, logs, and traces with a retention budget.
- [ ] SLOs and symptom-based alerts; a tested notification route.
- [ ] Dashboards that answer "what is broken?" not "what is pretty?".
- [ ] Runbooks for the top failure modes.
- [ ] On-call ownership and escalation.
- [ ] Disaster recovery and restore drills.

### Supply chain and policy

- [ ] Image and dependency scanning.
- [ ] Admission policy (Pod Security Standards, OPA/Gatekeeper/Kyverno).
- [ ] Resource quotas and limit ranges per namespace.
- [ ] Audit logging and a change trail.
- [ ] License review for all copied artifacts.

## 6. Lab-to-production migration sequence

Do not rewrite everything at once. Move in small, reversible steps.

1. **Pick one service.** Start with a stateless service, not the database or the
   RAG tool.
2. **Create a new repository section** for deployment manifests. Do not edit
   the lab in place.
3. **Copy the smallest base.** Use `boilerplates/base` or one paczek object.
4. **Replace names, namespace, image, ports, probes, and resources.**
5. **Add configuration and secret references**, not secret values.
6. **Render and diff** with `kubectl kustomize` and `kubectl diff`.
7. **Deploy to dev**, prove readiness and endpoints, then run a smoke test.
8. **Add policy and disruption controls** (NetworkPolicy, PDB, quotas).
9. **Promote the same image digest** to staging; change only environment values.
10. **Run a failure drill** and a rollback before calling it production-ready.
11. **Write a one-page runbook** with the five recovery steps.
12. **Record the evidence**: commit, image digest, command output, date, owner.

If step 6 shows a change you cannot explain, stop. A production apply should be
boring and reviewed, not a surprise.

## 7. What to validate before you claim success

```bash
# The manifest is syntactically valid and renders.
kubectl kustomize deploy/overlays/dev > /tmp/app.yaml

# The diff against the live cluster is intentional.
kubectl diff -f /tmp/app.yaml

# The rollout completed and the Service has endpoints.
kubectl rollout status deploy/my-service -n my-service-dev --timeout=120s
kubectl get endpoints my-service -n my-service-dev

# The probes are real, not decorative.
kubectl get pod -n my-service-dev -l app.kubernetes.io/name=my-service -o wide
kubectl describe pod -n my-service-dev -l app.kubernetes.io/name=my-service

# The rollback path exists.
kubectl rollout history deploy/my-service -n my-service-dev
kubectl rollout undo deploy/my-service -n my-service-dev
```

The lab's `make test` is useful, but it is not this validation. It proves the
repository's scripts and manifests are internally consistent; it does not prove
your application, cluster, DNS, storage, or network work.

## 8. Cost, hardware, and scope

- The lab is sized for one machine: roughly 6-8 GiB for the cluster and extras,
  with a 20 GiB disk target; check `make doctor` for the real host.
- The observability `full` profile competes with builds and models for RAM.
- The RAG models run on the host GPU; they are not a cluster workload in the
  current design.
- Managed Kubernetes has costs that the lab does not model: load balancers,
  storage, egress, logging, and idle control planes.
- `cloud/` is research, not a provisioned environment. Read it as a checklist
  before spending money, and write the teardown first.

## 9. The reusable sentence

If you remember one thing: **use this repository to learn the decisions and to
start the files; do not use it to skip the production controls.**
