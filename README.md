# Kubernetes lab kit

A step-by-step lab built from `k8_zadanie1_koper_prompt.md`, the PDF
`Kubernetes - Rozwinięcie Zagadnień.pdf`, and the outline
`kubernetes_podsumowanie.md`. One nginx app grows through seven exercises; the
surrounding theory becomes runbooks and drills.

**Status: core lab (A1–A7) executed on a real minikube cluster.** `make check`
and `make test` (36/36) are green. See `resume.md` for the exact state.

## Start here

```bash
make doctor          # what this machine can host, plus a minikube command
make test            # offline tests (no cluster, no network)
cat docs/runbooks.md # the actual step-by-step lab
```

If you have five minutes and no cluster, read
[`analysis/01-analysis.md`](analysis/01-analysis.md) and
[`docs/coverage-matrix.md`](docs/coverage-matrix.md).

## The map

| Path | What it is |
|---|---|
| `analysis/01-analysis.md` | what the three sources say, their defects, the design decisions |
| `analysis/02-todo.md` | the ordered work list, phases 0–18 |
| `analysis/03-research.md` | open questions with a test for each |
| `analysis/04-analysis-podsumowanie.md` | analysis of the outline the PDF cites |
| `analysis/05-hardware-profile.md` | measured hardware and what it allows |
| `analysis/06-scope-expansion.md` | the seven tracks after the nginx lab |
| `docs/runbooks.md` | A1–A7 plus distributions, Helm, ingress/storage, troubleshooting |
| `docs/coverage-matrix.md` | outline bullet → artifact → evidence |
| `docs/example-runs.md` | transcripts: real (A1–A3, A5–A7), and clearly-labelled simulated |
| `manifests/a*/` | the concrete YAML the scripts apply |
| `paczki/k8s/*.tpl` | templates for Coat's `paczek` (`{{ variable }}`) |
| `scripts/` | the task scripts: up, down, status, scale, rollout, tunnel, verify, doctor, env, mkpasswd, cluster-create, cluster-delete |
| `scripts/demo/kubectl` | fake client for offline transcripts, never a real cluster |
| `tests/run.sh` | the offline suite (36 checks) |
| `site/` | the static site A1 serves, images included |
| `app/` | the Laravel-shaped stand-in for A7 |
| `coat/` | the Coat module, spells and installer |
| `setup/install-tools.sh` | user-space tool installer (kubectl, minikube, helm, k3d, kind, yq, sqlite3, htpasswd) |
| `clusters/` | cluster skeletons: minikube, kind, k3d, k3s, managed |
| `observability/` | profiles (minimal/logs/traces/full), values, alerts, probes, inventory, host compose |
| `bastion/` | host jump box config + optional in-cluster jump pod manifests |

## The five layers

```
docs/runbooks.md      a human follows this
manifests/<scenario>  the cluster truth (what is applied)
paczki/k8s/*.tpl      parameterised starting points for new work
scripts/*.sh          the automation, idempotent, --dry-run everywhere
coat/                 shell shortcuts and spells on top of the scripts
```

Extended layers:

```
setup/                tool installer (no root by default)
clusters/             cluster skeletons + create/delete scripts
observability/        inventory-first, profile-based (minimal/logs/traces/full)
bastion/              host jump box + optional in-cluster jump pod
```

Nothing secret is committed. The `demo` password in `manifests/a5/` is a demo
value and is labelled as one.

## Commands

| Command | Effect |
|---|---|
| `make doctor` | tools, RAM, disk, ports, GPU, cluster, recommendation |
| `make check` | syntax + shellcheck + YAML + dry-runs (offline) |
| `make test` | `check` plus the 36-case suite against the fake client |
| `make demo` | the simulated transcript used in the docs |
| `make up` | `lab-up.sh a6 --mount` (real cluster) |
| `make status` | `lab-status.sh a6` |
| `make scale` | `+1` replica |
| `make rollout` | `+` history |
| `make verify` | checks with a non-zero exit on failure |
| `make tunnel` | `port-forward --address 0.0.0.0` in the background |
| `make down` | removes the scenario |
| `make clean` | removes demo state, pids and logs |
| `make tools` | run `setup/install-tools.sh` |
| `make tools-check` | report which tools are present |
| `make cluster` | `scripts/cluster-create.sh` (minikube, doctor sizing) |
| `make cluster-delete` | `scripts/cluster-delete.sh` |
| `make obs` | `observability/install.sh --profile minimal` |

Scenario is a variable: `make up SCENARIO=a1`, `make verify SCENARIO=a7`.
Cluster profile: `make obs PROFILE=traces`.

## Scenarios

| Name | What it shows | Needs |
|---|---|---|
| `a1` | nginx serving a host directory, images included | `--mount` |
| `a2` | `index.html` from a ConfigMap, live updates | — |
| `a3` | env vars: literal, ConfigMap, Downward API, precedence | — |
| `a5` | basic auth backed by a mounted Secret | — |
| `a6` | 3 replicas, LoadBalancer, scale, update, rollback | — |
| `a7` | nginx + php-fpm + PostgreSQL + SQLite on disk | `--mount --build` |

## Design rules

- One namespace: `k8s-lab`. The scripts never touch `default`.
- One selector label: `app.kubernetes.io/name`.
- Every script: `set -Eeuo pipefail`, `-h`, `--dry-run`, a non-zero exit on
  failure, and a message that says what it is doing.
- Every manifest: probes, resource requests, no `latest` tag.
- The fake client exists only for offline demos and is named as such.

## Next

1. `make obs PROFILE=minimal` — install observability if disk/RAM allow.
2. A4 second-machine test — when a second machine is on the LAN, run
   `scripts/lab-up.sh a6 && scripts/lab-tunnel.sh --background` and `curl
   http://192.168.1.240:8080` from it.
3. Phase 12 (boilerplates), phase 13 (drills), phase 14 (stacks), phase 15
   (observability full), phase 16–17 (AI/RAG), phase 18 (cloud free tier).

The detailed state, including the exact command to resume from, is in
[`resume.md`](resume.md).
