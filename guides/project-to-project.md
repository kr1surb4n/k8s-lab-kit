# Moving from project to project

**Read this when:** you have a working lab pattern and want to start the next
application without copying the lab's accidents.

**After reading you can:** scaffold a new project, promote it through
environments, roll it back, and move it to another cluster without rewriting the
manifests.

## 1. The principle

Do not copy a project. Copy the **decisions**:

- one base for the workload shape;
- one overlay per environment;
- one image reference, promoted by digest;
- one health check and one verification command;
- one runbook and one rollback path;
- no secrets, no private data, and no local paths in git.

The repository gives you a base and a set of examples. The new project should
contain only what that project needs.

## 2. Choose the starting point

| Situation | Start from | Do not copy |
|---|---|---|
| New stateless HTTP service | `boilerplates/base/` + your Dockerfile | A1-A7 manifests |
| Known runtime (Node, Python, Go, Java) | `boilerplates/base` + the matching `boilerplates/stacks/<runtime>` as a reference | The stack's `boilerplate/*:1.0` image tag |
| One object only (Job, CronJob, PVC, HPA) | `paczki/k8s/<object>.yaml.tpl` | The whole stack |
| Stateful database | A managed service or an operator | `boilerplates/stacks/stateful-postgres` as a production database |
| Third-party software (nginx, Prometheus, etc.) | A maintained Helm chart + a values file | Hand-written manifests for software you do not own |
| Local RAG/search | `ai/patterns/graph-rag/app/` | `ai/patterns/graph-rag/k8s/` (stale scaffold) |
| Learning clone | The lab as-is, in a disposable cluster | Anything from it in production |

When in doubt, start with the **base**, not the most feature-rich stack. A small
base with clear overlays is easier to move than a large copied stack with hidden
assumptions.

## 3. New project layout

Create this outside the lab repository:

```text
my-service/
  app/                         application source
  Dockerfile                   build, pinned base, non-root user
  deploy/
    base/
      deployment.yaml
      service.yaml
      configmap.yaml           optional, non-secret config
      kustomization.yaml
    overlays/
      dev/
        kustomization.yaml
      staging/
        kustomization.yaml
      prod/
        kustomization.yaml
  scripts/
    build.sh
    verify.sh
    rollback.sh
  docs/
    runbook.md
  README.md
  .gitignore
```

Keep `base` valid on its own. An overlay may change values, but it should not be
required to make the base parse. That is what makes the same base portable.

A minimal base `kustomization.yaml`:

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - deployment.yaml
  - service.yaml

# The overlay sets the real namespace and image.
```

A minimal dev overlay:

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - ../../base

namespace: my-service-dev

images:
  - name: my-service
    newName: registry.example.com/me/my-service
    newTag: "1.2.3"

patches:
  - target:
      kind: Deployment
      name: my-service
    patch: |-
      - op: replace
        path: /spec/replicas
        value: 2
```

The exact base object names depend on what you copied. If you started from
`boilerplates/base`, rename `base-app` consistently in the Deployment and
Service first.

## 4. The 12-step workflow

### Step 1 - Create the repository

```bash
mkdir -p my-service/{app,deploy/base,deploy/overlays/dev,scripts,docs}
cd my-service
git init
printf '*.log\n.env\n*.secret.yaml\n.DS_Store\n' > .gitignore
```

Add a README with the owner, purpose, environments, and the command to deploy.
If a new teammate cannot find the deploy command in 30 seconds, the README is not
done.

### Step 2 - Copy the smallest base

```bash
# From this repository.
cp /path/to/k8s/boilerplates/base/*.yaml /path/to/my-service/deploy/base/
```

Do not copy `manifests/a*` into a new project. Those files contain host paths,
demo credentials, and the `k8s-lab` namespace.

If you use a stack overlay as a reference, copy the **base and the runtime
files**, not the stack's `namespace: k8s-lab` or local image tag.

### Step 3 - Rename and retarget

Choose one service name and use it everywhere:

- Deployment `metadata.name`;
- Service `metadata.name`;
- `app.kubernetes.io/name` label on the pod template and Service selector;
- container name;
- probe paths;
- image name and port.

The Deployment selector is immutable. If you need a different selector label,
delete and recreate the Deployment; do not patch it in place.

### Step 4 - Make configuration explicit

Non-secret configuration belongs in a ConfigMap or the overlay:

```yaml
# deploy/base/configmap.yaml (example shape)
apiVersion: v1
kind: ConfigMap
metadata:
  name: my-service-config
data:
  APP_ENV: "dev"
  LOG_LEVEL: "info"
```

Secrets do not belong here. Use your platform's secret workflow:

- External Secrets Operator;
- Sealed Secrets;
- SOPS with a KMS/age key;
- a cloud secret manager with workload identity;
- at minimum, a Secret created by your CI/CD system, never committed.

Do not copy `paczki/k8s/secret.yaml.tpl` values or the A5 demo hash into a real
project.

### Step 5 - Set probes and resources

Every production Deployment needs:

- a readiness probe that reflects whether the app can serve traffic;
- a liveness probe that is forgiving enough not to restart during a slow start;
- a startup probe for slow runtimes (Java/Spring is the obvious case);
- CPU and memory requests;
- memory limits, and CPU limits only if you have measured the tradeoff;
- a graceful shutdown path and a matching `terminationGracePeriodSeconds`.

Use the stack examples as references, not as proof that the values are right for
your app. Measure under load.

### Step 6 - Expose the service

Start with `ClusterIP` and use port-forward for development:

```bash
kubectl port-forward -n my-service-dev svc/my-service 8080:80
curl -s http://127.0.0.1:8080/healthz
```

For external traffic, add an Ingress with TLS and an ingress class that exists
in that cluster. For a quick local test, use the repo's N1 runbook. For
production, define host names, certificate management, auth, rate limits, and
timeouts at the edge.

### Step 7 - Add policy and disruption controls

Add these after the basic deployment works:

- `NetworkPolicy`: default-deny, then explicit ingress/egress;
- `PodDisruptionBudget`: protect voluntary disruptions;
- `HorizontalPodAutoscaler`: only if the app scales horizontally;
- `ServiceAccount`: least privilege, no token automount if unused;
- `ResourceQuota` and `LimitRange`: namespace budgets;
- Pod Security labels or an admission policy.

The `paczki/k8s/networkpolicy.yaml.tpl` and `pdb.yaml.tpl` are starting points.
Read their `Bites:` comments; a NetworkPolicy with no allow rules is a common
self-inflicted outage.

### Step 8 - Build and publish one image

Build once, tag with an immutable version, and push to the registry the cluster
can reach:

```bash
docker build -t registry.example.com/me/my-service:1.2.3 .
docker push registry.example.com/me/my-service:1.2.3
```

For a local cluster, load the same image instead of pushing:

```bash
# minikube
minikube image load registry.example.com/me/my-service:1.2.3

# kind
kind load docker-image registry.example.com/me/my-service:1.2.3

# k3d
k3d image import registry.example.com/me/my-service:1.2.3 -c k8s-lab
```

Record the digest:

```bash
docker inspect --format='{{index .RepoDigests 0}}' registry.example.com/me/my-service:1.2.3
```

Promote the digest, not a mutable tag. In an overlay, `newTag` can be a digest
or a precise version; the important thing is that the same artifact moves
through environments.

### Step 9 - Render, diff, apply

Never apply a directory somewhere because it worked in the lab. Render first:

```bash
kubectl kustomize deploy/overlays/dev > /tmp/my-service-dev.yaml
kubectl diff -f /tmp/my-service-dev.yaml
kubectl apply -f /tmp/my-service-dev.yaml
kubectl rollout status deploy/my-service -n my-service-dev --timeout=120s
kubectl get endpoints my-service -n my-service-dev
```

`kubectl diff` is the review gate. If the diff contains an object or namespace
you did not expect, stop.

### Step 10 - Verify with a real check

Write `scripts/verify.sh` with a non-zero exit on failure. It should check more
than "the pod exists":

```bash
#!/usr/bin/env bash
# Verify that the service is ready and answers on its health endpoint.
set -Eeuo pipefail

namespace=${NAMESPACE:-my-service-dev}
deployment=${DEPLOYMENT:-my-service}

# Wait for the rollout and require at least one ready endpoint.
kubectl rollout status "deploy/${deployment}" -n "$namespace" --timeout=120s
kubectl get endpoints "$deployment" -n "$namespace" | grep -v '<none>'

# Port-forward in the background, then make a real request.
kubectl port-forward -n "$namespace" "svc/${deployment}" 18080:80 >/tmp/${deployment}-pf.log 2>&1 &
forward_pid=$!
trap 'kill "$forward_pid" 2>/dev/null || true' EXIT
sleep 2
curl --fail --silent --show-error http://127.0.0.1:18080/healthz
```

Keep it small and portable. Do not encode a production host name in the script;
accept it as an environment variable.

### Step 11 - Write the runbook

`docs/runbook.md` should fit on one page:

- what the service is and who owns it;
- deploy command;
- health check and expected output;
- the top three failure modes;
- rollback command;
- where logs, metrics, and traces live;
- data backup/restore contact;
- the escalation path.

Use `recovery/method.md` as the structure, but keep the project-specific facts.

### Step 12 - Promote and roll back

Promote the same image digest:

```bash
# Render staging and review the diff.
kubectl kustomize deploy/overlays/staging > /tmp/my-service-staging.yaml
kubectl diff -f /tmp/my-service-staging.yaml
kubectl apply -f /tmp/my-service-staging.yaml
kubectl rollout status deploy/my-service -n my-service-staging

# Roll back the workload if the new revision is bad.
kubectl rollout history deploy/my-service -n my-service-staging
kubectl rollout undo deploy/my-service -n my-service-staging
```

For a configuration or manifest regression, prefer `git revert` and re-render
over manual live edits. The repository is the source of truth; a live edit that
is not written back is drift.

## 5. Cluster portability

The same base should move; only the overlay should change.

| Concern | minikube | kind | k3d | k3s | managed |
|---|---|---|---|---|---|
| Image availability | `minikube image load` | `kind load docker-image` | `k3d image import` | registry or `ctr` import | registry |
| LoadBalancer | `<pending>` without tunnel | no cloud LB | published ports possible | NodePort/LB depends on setup | provider LB |
| StorageClass | `standard` | `standard` (local-path) | `local-path` | `local-path` | provider class |
| Ingress | addon | install controller | often disabled | install controller | provider or install |
| Host path | `minikube mount` | node container path | node container path | host path | do not use |
| LAN access | port-forward | port mapping | published port | NodePort/host IP | ingress/LB |

Read `clusters/README.md` before moving. If the base needs a different
StorageClass or Ingress class for every cluster, move that value into the
overlay, not into the base.

## 6. What never to copy

| Never copy | Why |
|---|---|
| `manifests/a*/` into a production repo | Host paths, demo values, one namespace, no production controls. |
| `k8s-lab` namespace, `k8s-lab` image names, `/mnt/lab` | Lab-local assumptions. |
| The A5 demo Secret/hash or `labpass` | Public demo credentials. |
| `scripts/demo/kubectl` | Fake client; it always succeeds. |
| `scripts/lab-*.sh` as a production deploy tool | Disposable-cluster automation. |
| `~/.config/graphrag/`, private notes/papers, model files | Private data; never in git. |
| `*.secret.yaml`, kubeconfig, TLS keys, Terraform state | Secrets and credentials. |
| `.venv/`, `node_modules/`, `__pycache__/`, build output | Generated artifacts. |
| `eval/local-results.json` as a baseline for a different corpus | Results are corpus-specific. |
| `ai/patterns/graph-rag/k8s/` | Stale imported scaffold, not the current app. |
| The PDF and source prompts without a license check | Provenance and redistribution rights. |

The `.gitignore` helps, but it is not a security control. Check `git status`
before every commit and use a secret scanner in CI.

## 7. Moving an existing project, not starting from zero

When the app already exists, do not rebuild it around the lab. Extract the
deployment decisions instead:

1. **Inventory:** list every runtime dependency: database, cache, object store,
   external API, cron, background worker, file storage.
2. **Map to Kubernetes objects:** Deployment, Service, ConfigMap, Secret,
   StatefulSet or managed service, Job/CronJob, PVC.
3. **Choose what not to run in the cluster:** managed databases, object storage,
   and queues are often better outside.
4. **Find the platform values:** registry, namespace, StorageClass, Ingress
   class, DNS, certificate issuer, secret provider.
5. **Replace the lab assumptions:** image loading, `hostPath`, demo secrets,
   `LoadBalancer` behavior, single replica.
6. **Build the base**, then the dev overlay.
7. **Prove one request**, then add probes, policy, and observability.
8. **Run the rollback** before the first production deploy.
9. **Write the runbook** and hand it to someone else to execute.

The output should be a small deployment repository, not a fork of the entire
Kubernetes lab.

## 8. Definition of done for a new project

- [ ] A new teammate can build the image from the README.
- [ ] The base renders with `kubectl kustomize` without an overlay.
- [ ] Dev, staging, and prod differ only in overlay values.
- [ ] The image is pinned and promoted by digest or immutable version.
- [ ] Secrets are referenced from a secret workflow, never committed.
- [ ] Readiness, liveness, and (if needed) startup probes are present.
- [ ] Requests and limits are set from measurement.
- [ ] A NetworkPolicy default-deny exists, with explicit allows.
- [ ] A PDB exists for multi-replica services.
- [ ] `kubectl diff` is part of the deploy review.
- [ ] `scripts/verify.sh` exits non-zero on a real failure.
- [ ] A rollback has been executed successfully.
- [ ] Metrics, logs, and traces are discoverable from the runbook.
- [ ] A backup/restore drill exists for stateful data.
- [ ] The runbook fits on one page.
- [ ] The repository has no private data or credentials.

## 9. The one-minute version

```bash
# New project, from the lab repository.
mkdir my-service && cd my-service
cp -r /path/to/k8s/boilerplates/base deploy/base
# Rename base-app, image, port, probes, namespace.
# Create deploy/overlays/{dev,staging,prod}.
kubectl kustomize deploy/overlays/dev > /tmp/app.yaml
kubectl diff -f /tmp/app.yaml
kubectl apply -f /tmp/app.yaml
kubectl rollout status deploy/my-service -n my-service-dev
kubectl get endpoints my-service -n my-service-dev
kubectl rollout undo deploy/my-service -n my-service-dev
```

If that sequence is boring and repeatable, the project is portable. That is the
goal.
