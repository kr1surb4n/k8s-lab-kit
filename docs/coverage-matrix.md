# Coverage matrix — outline bullet → lab artifact → evidence

One row per claim in `kubernetes_podsumowanie.md`. This is the answer to "did we
actually do what the summary says, or did we only read about it?".

Status: `covered` = artifact exists and is exercised by a runbook step;
`partial` = artifact exists but needs a real cluster run; `out of scope` = on
purpose, with a reason. Nothing is `covered` until `docs/example-runs.md` holds a
real transcript.

| 1.1 | minikube as the local environment | all | `scripts/lab-up.sh --start-cluster` | `minikube status` | covered |
| 1.2 | K3s as a lighter alternative | A4 | `docs/runbooks.md` §A4 + research R9 | `curl http://<lan-ip>:30080` after K3s install | partial |
| 1.3 | MicroK8s as a lighter alternative | A4 | `docs/runbooks.md` §A4 | `microk8s status --wait-ready` | out of scope (same lesson as K3s, doubles install time) |
| 2.1 | Helm deploys and versions apps | H1 | `paczki/k8s/values.yaml.tpl` + `docs/runbooks.md` §H1 | `helm history web` | partial |
| 2.2 | Helm with Nginx | H1 | same chart, local `values.yaml` | `helm upgrade --install` then `curl` | partial |
| 2.3 | Helm with Magento | H2 (optional) | none | `helm dependency update` on a Magento chart | out of scope (heavy, 4 dependencies, no learning value beyond H1) |
| 3.1 | Service exposes an app | A1, A2, A6 | `manifests/a*/web.yaml`, `paczki/k8s/service.yaml.tpl` | `kubectl get endpoints web` | covered |
| 3.2 | Ingress exposes an app outside | N1 | `paczki/k8s/ingress.yaml.tpl` | `curl -H 'Host: app.example.com' http://<addr>/` | partial |
| 3.3 | PV/PVC assign and persist disk | A7 | `paczki/k8s/pvc.yaml.tpl` | `kubectl get pvc` → `Bound` | covered |
| 3.4 | But live host files need hostPath, not PV/PVC | A1, A7 | `manifests/a1/web.yaml` | edit `site/index.html`, reload, see the change | covered |
| 3.5 | ConfigMap configures the app | A2, A3, A5 | `manifests/a2/`, `a3/`, `a5/` | `kubectl edit configmap web-index` → page changes | covered |
| 3.6 | Environment variables reach the container | A3 | `manifests/a3/web.yaml` | `kubectl exec deploy/web -- printenv` | covered |
| 4.1 | Troubleshooting from real errors | T1 | `docs/runbooks.md` §T1 (four drills) | one captured failure per state | partial |
| 4.2 | No dry theory | all | `docs/example-runs.md` | a transcript per exercise | partial |

## Reverse gap — required by the prompts, absent from the outline

These rows cannot be traced to the summary at all. They are the reason the
summary is not a task list.

| Requirement | Exercise | Artifact | Status |
|---|---|---|---|
| Serve a host directory, images included | A1 | `manifests/a1/`, `site/` | covered |
| `index.html` from a ConfigMap, live updates | A2 | `manifests/a2/` | covered |
| Who/when/where/mechanisms of env vars | A3 | runbook A3 + `scripts/env-demo.sh` | covered |
| LAN access from another machine | A4 | `scripts/lab-tunnel.sh` | partial |
| Secrets in a test deployment | A5 | `manifests/a5/` | covered |
| 3 replicas, Service + Deployment lifecycle | A6 | `manifests/a6/`, `scripts/lab-*.sh` | covered |
| Laravel + PostgreSQL + SQLite on disk | A7 | `manifests/a7/` | covered |

## How to keep this honest

1. At the end of each exercise, replace `partial` with `covered` only after
   pasting the real command and its real output into `docs/example-runs.md`.
2. If a row is still `partial` at the end of the lab, it goes to
   `analysis/02-todo.md` as open work, not into a "done" list.
3. Never mark a row `covered` because the YAML exists. The YAML is not evidence;
   the output is.
