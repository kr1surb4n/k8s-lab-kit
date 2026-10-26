# Guides

These guides turn the repository into something you can use in three different
ways: understand what is reusable, learn Kubernetes in order, and start the next
project without re-learning the same lessons.

They are deliberately split into small files. Do not read them all in one sitting.

## The answer in one paragraph

The repository is **strong material to learn from and copy decisions from**, not a
production platform to deploy as-is. Its runbooks, probes/resources patterns,
Kustomize base, paczki templates, recovery method, observability profiles, and
local RAG tool are useful starting points. Its lab manifests, demo secrets,
`k8s-lab` namespace, host mounts, fake kubectl, single-node sizing, and
"production-ready" stack claims must be replaced or hardened before real use.

## Read this first

| File | Question it answers | Read when | Time |
|---|---|---|---|
| [`../START-HERE.md`](../START-HERE.md) | What is this repository, and where do I begin? | always, first | 10 min |
| [`real-world-use.md`](real-world-use.md) | Can I use these sources and solutions at work? How? | you need a real project | 20-30 min |
| [`kubernetes-learning-path.md`](kubernetes-learning-path.md) | How do I learn the whole repository as a Kubernetes tutorial? | you are learning | 45-60 h |
| [`repo-reading-map.md`](repo-reading-map.md) | What should I read, skip, and in what order? | you are lost in the tree | 20-30 min |
| [`project-to-project.md`](project-to-project.md) | How do I move a working pattern to the next project? | you are starting a new app | 20 min + build |

## Recommended reading paths

### "I have 20 minutes"

1. `../START-HERE.md`
2. `real-world-use.md`, sections 1-3
3. `repo-reading-map.md`, the file map

You will know what is reusable, what is not, and where the important files are.

### "I want to learn Kubernetes properly"

1. `../START-HERE.md`
2. `repo-reading-map.md`
3. `kubernetes-learning-path.md`
4. Follow the stages in order. Use `docs/runbooks.md` for each exercise.

Do not start with `ai/patterns/`, `cloud/`, or the full observability stack. They
are advanced branches, not the trunk of the tutorial.

### "I have a real project to ship"

1. `real-world-use.md`, sections 1-4 and the hardening checklist
2. `project-to-project.md`
3. `repo-reading-map.md`, only the base/overlay and paczki entries
4. `boilerplates/base/*.yaml` and `boilerplates/stacks/*/kustomization.yaml`

### "I need to reuse the AI/RAG work"

1. `real-world-use.md`, section "Local RAG and Graph RAG"
2. `ai/patterns/graph-rag/app/README.md`
3. `ai/patterns/graph-rag/failure-modes/failure-modes.md`
4. `ai/patterns/graph-rag/eval/local-results.json` (read the scores, not the
   raw answers)

Treat the host-side tool as a private local tool. Do not expose it without
authentication, TLS, data-retention rules, and a privacy review.

## How to read these guides

- All paths are relative to the repository root unless stated otherwise.
- Commands in code blocks are meant to be run from the repository root. The
  surrounding text says whether a cluster is required.
- Every stage has a **checkpoint**: you can explain it, reproduce it, and prove
  it with command output. Reading without doing is not progress.
- If a command fails, stop and read the corresponding runbook section. Do not
  skip a failure and continue; the lab is built around learning from the failure.

## Source-of-truth order

When two files disagree, use this order:

1. **The command output you just produced** (`kubectl get`, `make test`,
   `curl`, `kubectl diff`).
2. `docs/example-runs.md` for labeled real transcripts; never treat the
   "simulated" sections as evidence.
3. `docs/runbooks.md` for the hands-on procedure.
4. `docs/coverage-matrix.md` for what was actually exercised.
5. `README.md`, `resume.md`, and `analysis/` for orientation and history.
6. Old snapshots such as `docs/REPO-STATE.md`. They are useful history, not
   current state.

The repository has stale counts in a few older files (for example, 36 tests).
Run `make test` and use its actual output. `resume.md` is the short current-state
pointer, but even it can lag behind the working tree.

## Safety rules

- Work in a disposable cluster. Check `kubectl config current-context` before
  every `apply`.
- Never run the lab against a shared, work, or production cluster.
- Keep private notes, API keys, model credentials, and the Graph RAG index out of
  git. The `.gitignore` excludes the private config, but it cannot protect a file
  you force-add.
- Do not copy a Secret YAML into a new project. Create secrets through your
  platform's secret workflow.
- The demo password `labpass` is public on purpose. Replace it everywhere.
- The fake kubectl under `scripts/demo/` is for offline tests only. It always
  reports success; that is the point and the trap.

## What "done" means in this repository

An exercise is done when you have:

- run the real command, not only read the YAML;
- captured the command and its output in your notes or in
  `docs/example-runs.md` if you are changing the repo;
- verified the result with a non-zero exit on failure (`make verify` or a
  scenario-specific check);
- cleaned up with `make down` / `scripts/lab-down.sh`;
- written one sentence explaining **why** it worked.

The last item is the one that transfers to a new project.

## Next file

- For the practical verdict: [`real-world-use.md`](real-world-use.md)
- For the study plan: [`kubernetes-learning-path.md`](kubernetes-learning-path.md)
- For the tree map: [`repo-reading-map.md`](repo-reading-map.md)
- For the next project: [`project-to-project.md`](project-to-project.md)
