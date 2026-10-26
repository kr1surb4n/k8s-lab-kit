# Repository reading map

**Read this when:** the tree feels too large, or you want to know which files are
the source of truth and which are history.

**After reading you can:** navigate the repository in four passes, read one
scenario vertically, and avoid wasting time on generated, stale, or fake files.

## 1. Read it like an onion, not a book

Do not open every YAML file. Read in four passes, each with a different question.

| Pass | Question | Files | Time |
|---|---|---|---|
| 1. Orientation | What is here, and what is real? | `START-HERE.md`, `guides/`, `README.md`, `resume.md`, `git log` | 20 min |
| 2. Core lab | How does one exercise actually work? | `docs/runbooks.md` A1-A7, `manifests/a*/`, `docs/example-runs.md` | 2-3 h |
| 3. Machinery | How is it automated and tested? | `scripts/`, `tests/run.sh`, `scripts/demo/kubectl`, `Makefile` | 2 h |
| 4. Extension | How do I reuse or extend it? | `boilerplates/`, `paczki/`, `recovery/`, `observability/`, `clusters/`, `ai/`, `cloud/` | as needed |

The most common mistake is starting at pass 4 (AI/RAG, cloud, full
observability) before pass 2. The advanced files assume you understand the core
lab's vocabulary.

## 2. The first 20 minutes

```bash
# The one-page orientation and the guide index.
sed -n '1,220p' START-HERE.md
sed -n '1,240p' guides/README.md

# The repository map and current state.
sed -n '1,180p' README.md
sed -n '1,120p' resume.md

# What changed recently, and what the helper targets are.
git log --oneline -12
make help
```

Then answer these questions in your own words:

1. What is the difference between `docs/runbooks.md` and `docs/example-runs.md`?
2. Why is `scripts/demo/kubectl` dangerous if you forget it is fake?
3. What is the lab namespace, and why does every script use it?
4. Which directory would you copy for a new app, and which would you never copy?

If you cannot answer them, read `docs/runbooks.md` "Common setup" and
`guides/real-world-use.md` sections 1-3.

## 3. The file map

| Path | What it is | Read it when |
|---|---|---|
| `START-HERE.md` | Orientation and first commands | always, first |
| `guides/` | This guide set: reuse, learning, reading, portability | before acting |
| `README.md` | Repository map and command table | orientation |
| `resume.md` | Short current-state pointer | returning after a break |
| `analysis/01-analysis.md` | Analysis of the three source documents and design decisions | you want the "why" |
| `analysis/02-todo.md` | Phase-by-phase work list, phases 0-18 | you want the full project history |
| `analysis/03-research.md` | Open questions and experiments | you are investigating a design choice |
| `analysis/05-hardware-profile.md` | Measured hardware and what fits | `make doctor` needs context |
| `analysis/06-scope-expansion.md` | The seven tracks after the nginx lab | you want the advanced map |
| `analysis/07-what-to-do.md` | Current remaining work and the Phase 17 details | you are maintaining the repo |
| `docs/runbooks.md` | Authoritative A1-A7, D1, H1, N1, T1 procedures | you are doing an exercise |
| `docs/example-runs.md` | Transcripts, labeled real or simulated | you need evidence or expected output |
| `docs/coverage-matrix.md` | Source claim -> artifact -> evidence | you want to know what was actually done |
| `docs/REPO-STATE.md` | Historical snapshot | you need history; check its date |
| `docs/exercises/EXERCISES.md` | Imported exercise sheet | rarely; it has known mismatches |
| `manifests/a1` ... `a7` | The concrete YAML for each lab scenario | you are running that scenario |
| `scripts/lab-*.sh` | Lifecycle automation with `--dry-run` | you want to see how the lab is driven |
| `scripts/lib/common.sh` | Shared defaults, logging, guards | you are reading or adapting a script |
| `scripts/demo/kubectl` | Fake kubectl for offline transcripts | you are debugging the test harness; never for real work |
| `tests/run.sh` | Offline test suite against the fake client | you want the executable specification |
| `Makefile` | Entry points and safety checks | you want the command surface |
| `boilerplates/base/` | Reusable stateless Deployment + Service | you are starting a new app |
| `boilerplates/stacks/` | Runtime-specific overlays and app examples | you need a runtime starting point |
| `paczki/k8s/` | Single-object templates for new projects | you need one object, not a whole stack |
| `recovery/` | Observe -> Contain -> Diagnose -> Recover -> Prevent | you are debugging or drilling |
| `observability/` | Profiles, values, alerts, host monitoring, traces | you are adding visibility |
| `clusters/` | minikube, kind, k3d, k3s, managed skeletons | you are moving between clusters |
| `bastion/` | Host and in-cluster jump-box scaffold | security-sensitive; not applied |
| `app/`, `site/` | Demo application and static site | you are running A1 or A7 |
| `cloud/` | Provider research; no Terraform implementation | you are planning, not deploying |
| `ai/patterns/rag/` | Baseline RAG pattern | you are studying the AI branch |
| `ai/patterns/graph-rag/` | Working local Graph RAG tool, eval, failure modes | you are using the local tool |
| `setup/` | User-space tool installer | tools are missing |
| `coat/` | Optional Coat shell integration | you use Coat; not required for the lab |
| `k8_zadanie1_koper_prompt.md`, PDF, `kubernetes_podsumowanie.md` | Original source material | you want provenance; not a tutorial |

## 4. How to read one scenario vertically

Do not read a manifest in isolation. Read the same scenario across five layers:

1. **Procedure:** the runbook section.
2. **Desired state:** the manifest.
3. **Automation:** the script that applies it.
4. **Test:** the fake-cluster check.
5. **Evidence:** the real transcript, if it exists.

Example for A1:

```bash
# 1. The procedure and the "why".
rg -n '^# A1|^### Steps|^### Why it works|^### Pitfalls' docs/runbooks.md
sed -n '66,118p' docs/runbooks.md

# 2. The desired state.
sed -n '1,220p' manifests/a1/web.yaml

# 3. The automation that applies it.
sed -n '1,220p' scripts/lab-up.sh
sed -n '1,160p' scripts/lib/common.sh

# 4. The offline check that exercises the script flow.
rg -n 'test_up|a1|fake' tests/run.sh
sed -n '96,120p' tests/run.sh

# 5. The real transcript, if present.
rg -n 'Real A1|A1 transcript|host mount' docs/example-runs.md
```

Repeat for A2 (ConfigMap), A6 (rollout), or A7 (stateful) as needed. One vertical
slice teaches more than skimming all seven manifests.

## 5. How to read each artifact type

### A runbook

Read in this order:

1. **Done when:** the observable proof.
2. **Steps:** the commands, in order.
3. **Why it works:** the mechanism.
4. **Pitfalls:** the failure you are meant to hit.
5. **Cleanup:** how to leave no residue.

Do not skip "Pitfalls". The lab is designed so the failure teaches the concept.

### A manifest

Read top down:

1. `apiVersion` and `kind`: what object is this?
2. `metadata.name` and `namespace`: where does it live?
3. `spec.selector` / `labels`: how does it find its pods?
4. `template.spec.containers`: image, port, env, probes, resources.
5. `volumes` / `volumeMounts`: what state or config is mounted?
6. `strategy` and replicas: what happens during an update?

Then compare the manifest with what the cluster actually has:

```bash
kubectl diff -f manifests/a6/
kubectl get deploy web -n k8s-lab -o yaml
kubectl explain deployment.spec.strategy --recursive | head -40
```

### A script

Read the surface first, then the body:

```bash
sed -n '1,120p' scripts/lab-up.sh
sed -n '1,120p' scripts/lib/common.sh
scripts/lab-up.sh --help
```

Look for:

- `set -Eeuo pipefail`: fail loudly;
- `--dry-run`: what it refuses to do without a cluster;
- `LAB_NAMESPACE`: the blast radius;
- `kubectl apply/delete` calls: what it changes;
- cleanup/trap handlers: what it leaves behind if it fails.

Do not assume the script is production-safe because it is tested. It is a lab
automation layer.

### The test suite

`tests/run.sh` is an executable specification, not a substitute for a real
cluster. Read the test names and the fake-client behavior:

```bash
sed -n '1,120p' tests/run.sh
sed -n '96,180p' tests/run.sh
sed -n '220,260p' tests/run.sh
```

Run one test group:

```bash
TEST_FILTER=scale make test
```

The fake client proves that the script sequence is stable. It does not prove
scheduling, networking, storage, or images.

### Analysis versus evidence

- `analysis/` records thinking, options, and plans. It can contain ideas that
  were never built.
- `docs/` records procedures and evidence. `coverage-matrix.md` and
  `example-runs.md` are where claims should be backed by output.
- A plan in `analysis/02-todo.md` is not a promise that the feature exists.

When in doubt, search for the artifact and the command output, not the claim.

## 6. Reading recipes by goal

### "I need to deploy something now"

Read `boilerplates/base/*.yaml`, `paczki/k8s/deployment.yaml.tpl`,
`paczki/k8s/service.yaml.tpl`, and `guides/project-to-project.md`. Do not start
with the A1-A7 runbooks.

### "I want to understand networking"

Read `docs/runbooks.md` A4 and N1, then `manifests/a6/web.yaml`, then
`clusters/README.md`. Run the port-forward and ingress examples.

### "I need to debug a failing pod"

Read `recovery/method.md` and `recovery/decision-tree.md` first, then
`docs/runbooks.md` T1. Use the command table before changing anything.

### "I want to add observability"

Read `observability/README.md`, then `observability/trace/README.md`, then
`docs/example-runs.md` sections 8-9. Start with the `minimal` profile.

### "I want the AI tool, not Kubernetes"

Read `ai/patterns/graph-rag/app/README.md`,
`ai/patterns/graph-rag/failure-modes/failure-modes.md`, and
`guides/real-world-use.md` section 4.4. The Kubernetes lab is not required.

### "I am returning to this repo after months"

Read `resume.md`, `git log --oneline -20`, `git status`, then
`analysis/07-what-to-do.md`. Run `make test` before trusting any status text.

## 7. What to skip, and why

| Skip or defer | Why |
|---|---|
| `.venv/`, `__pycache__/`, `node_modules/` | Generated dependencies; never edit or commit. |
| `*.log`, `*.pid`, `k8s-lab-fake-state*` | Runtime residue; `make clean` removes it. |
| `docs/REPO-STATE.md` numbers | Historical snapshot; use current commands. |
| `docs/exercises/EXERCISES.md` commands | Imported sheet with mismatched Make targets and placeholder scenarios. Use `docs/runbooks.md`. |
| `scripts/demo/kubectl` | Fake client for offline tests. Not a cluster. |
| `ai/patterns/graph-rag/k8s/` | Stale imported scaffold, not the current app packaging. |
| `cloud/` | Notes only; no implementation. Read before spending money. |
| `bastion/` | Security-sensitive scaffold; not deployed and needs review. |
| The full observability profile on a small machine | It competes with builds and models for RAM. |
| The original PDF/prompt files on a first pass | Source material, not the tutorial. Read them for provenance later. |

## 8. Search commands that save time

```bash
# Find a concept across docs and manifests.
rg -n 'readinessProbe|NetworkPolicy|PDB|hostPath' docs manifests boilerplates

# Find which script owns a scenario.
rg -n 'SCENARIO|a[1-7]' scripts Makefile

# Find the tests for a behavior.
rg -n 'test_(up|status|scale|verify|down|yaml|graph)' tests/run.sh

# Find a phase or a design decision.
rg -n '^## Phase|^### ' analysis/02-todo.md analysis/07-what-to-do.md

# Show the Kustomize output without applying it.
kubectl kustomize boilerplates/stacks/python-fastapi

# Check a manifest against a live cluster without applying.
kubectl diff -f manifests/a6/
```

## 9. Evidence hierarchy

Use this order when deciding what to believe:

1. The command you ran and its output.
2. `docs/example-runs.md`, if the section is labeled **real**.
3. `docs/runbooks.md`.
4. `docs/coverage-matrix.md`.
5. `resume.md` and `README.md`.
6. `analysis/` plans and old snapshots.

The repository intentionally keeps some history and some imported warnings. Do
not "fix" a historical transcript to match today's result; add a dated note
instead. The same applies to a stale test count: run the command.

## 10. Note-taking template

When you finish a reading session, add this to `~/k8s-notes/`:

```text
Date:
Files read:
Commands run:
Output/evidence:
What I can now explain:
What I would change for a real project:
Next file:
```

This is more useful than highlighting a runbook. The "what I would change"
line is the bridge to [`project-to-project.md`](project-to-project.md).
