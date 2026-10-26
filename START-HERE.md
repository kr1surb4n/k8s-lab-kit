# Start here

This repository is two things at once:

1. a hands-on Kubernetes lab (A1-A7, failure drills, observability, stacks);
2. a reusable pattern library (Kustomize base, stack overlays, paczki templates,
   scripts, runbooks, and a local Graph RAG tool).

**Short answer to "can I use this in the real world?"** Yes, for the methods,
templates, and operational patterns. No, not by copying the lab unchanged. The
repository is a learning environment; it is not a production platform, and
`boilerplates/stacks/README.md` calling the stack overlays "production-ready" is
an aspiration, not a certification.

The full answer, including what to reuse and what to replace, is in
[`guides/real-world-use.md`](guides/real-world-use.md).

## Choose a path

| If you want to... | Read | Time |
|---|---|---|
| know whether the repo is useful at work | [`guides/real-world-use.md`](guides/real-world-use.md) | 20 min |
| learn Kubernetes with this repo | [`guides/kubernetes-learning-path.md`](guides/kubernetes-learning-path.md) | 45-60 h |
| understand the repository without reading everything | [`guides/repo-reading-map.md`](guides/repo-reading-map.md) | 30 min |
| start a new project from these patterns | [`guides/project-to-project.md`](guides/project-to-project.md) | 30 min + build |
| get the guide set and reading rules | [`guides/README.md`](guides/README.md) | 5 min |

Read `guides/README.md` first if you are unsure. It contains the reading order,
conventions, and the "what is real vs simulated" warning.

## First 15 minutes

Run these from the repository root. The first three commands do not touch a
cluster.

```bash
# Show tools, RAM, disk, ports, GPU, and a suggested cluster size.
make doctor

# Offline checks: syntax, shellcheck, YAML, dry-runs, fake-cluster tests.
make test

# Show the script flow against the fake kubectl. This is NOT a real cluster.
make demo
```

Expected: `make doctor` ends without a `FAIL` line, `make test` reports the
current passing count, and `make demo` prints `demo ok (this is a fake cluster)`.
Do not quote the demo as proof that a real deployment works.

Then check the cluster state:

```bash
# Show the current kubectl context before applying anything.
kubectl config current-context
```

The lab usually uses minikube. Start it only when you are ready to run A1-A7:

```bash
make cluster
```

If minikube is already stopped, that is expected. Read the guides first; do not
start a cluster just to browse the repository.

## The one safety rule

Every lab command assumes a disposable cluster and the `k8s-lab` namespace.
Before running anything that applies manifests:

```bash
# Refuse to continue if this is a work cluster.
kubectl config current-context
```

If the context is not your local lab, stop. The lab scripts are deliberately
scoped to `k8s-lab`, but they are not a production deployment tool and cannot
protect you from a wrong kubeconfig.

## Current state, in one screen

- Core lab A1-A7 ran on a real minikube cluster. Transcripts and evidence are in
  `docs/example-runs.md` and `docs/coverage-matrix.md`.
- The offline gate is `make test`; the current state is in `resume.md`.
- Some older documents still say 36 tests. The current suite is larger; trust the
  command output and `resume.md`, not a stale snapshot.
- Observability, recovery, stack boilerplates, and the AI/RAG patterns are
  real artifacts, but they are sized for one lab machine.
- The private Graph RAG tool runs on the host by design. Its index, notes, and
  config are not in git. Do not put private data in the cluster or in a commit.
- `docs/exercises/EXERCISES.md` is imported material with known mismatches. The
  authoritative hands-on instructions are in `docs/runbooks.md`.

## Repository rules you should know before copying anything

- `manifests/a*/` are teaching examples, not production manifests.
- `scripts/demo/kubectl` is a fake client for offline transcripts. Never treat
  its output as cluster evidence.
- Demo credentials (`lab` / `labpass`) are intentionally public. Never reuse them.
- `hostPath`, `/mnt/lab`, `minikube mount`, and the single `k8s-lab` namespace are
  lab mechanics. They do not travel to a real cluster.
- Secrets must come from a secret manager or an external secret workflow, not
  from a committed YAML file.
- There is no `LICENSE` file at the repository root. Check the license and
  provenance of the source material, third-party charts, and images before
  commercial reuse.

## Where to go next

1. Read [`guides/README.md`](guides/README.md).
2. Pick one path from the table above.
3. Run one small exercise and write down the command and output.
4. Only then start the full learning path or a new project.
