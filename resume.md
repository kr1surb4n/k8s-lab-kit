# Resume — where this work stands

Written at the end of the session that ran the core lab. Read this first when
coming back; it is deliberately short and points at the details.

- **Folder:** `/home/kris/00___Castle/07__WorkShops/k8s`
- **Date:** 2026-10-25
- **State:** **core lab (A1–A7) executed on a real minikube cluster**
- **Offline gate:** `make check` green, `make test` 36/36
- **Files:** 70+ (5 sources/inputs, 6 analyses, 4 docs, 6 manifests, 8 templates,
  12 scripts, 1 test suite, 4 coat files, 1 Makefile, 1 README,
  observability/bastion/cluster scaffolds)

## One paragraph

The lab is derived from three sources: the seven nginx exercises in
`k8_zadanie1_koper_prompt.md`, the 11-page PDF, and the 20-line outline the PDF
cites (`kubernetes_podsumowanie.md`). The analysis found that the outline covers
about half of the exercise, that the PDF adds several broken snippets, and that
this machine can host the whole core lab plus a small observability stack. The
kit is built in five layers (runbooks → manifests → paczki → scripts → coat), the
offline tests pass, and the core lab has now been executed for real:
A1 (host mount + live edit), A2 (ConfigMap + live edit), A3 (env precedence),
A6 (3 replicas + rolling), A5 (basic auth Secret), A7 (nginx + PHP-FPM +
PostgreSQL + SQLite with host live insert). All transcripts captured in
`docs/example-runs.md`, rows closed in `docs/coverage-matrix.md`.

## What is done and verified

| Item | Evidence |
|---|---|
| Analysis of all three sources | `analysis/01` … `04` |
| Hardware profile and tiers | `analysis/05`, `make doctor` |
| Expanded scope, seven tracks | `analysis/06` |
| Ordered work list, phases 0–18 | `analysis/02-todo.md` |
| Research list with 22 testable questions | `analysis/03-research.md` |
| Runbooks A1–A7 + D1/H1/N1/T1 | `docs/runbooks.md` |
| Traceability against the outline | `docs/coverage-matrix.md` (A1–A3, A5–A7 = covered) |
| Manifests for a1, a2, a3, a5, a6, a7 | `manifests/` (22+ YAML documents parse) |
| Eight paczki templates | `paczki/k8s/` |
| Scripts: up, down, status, scale, rollout, tunnel, verify, doctor, env, mkpasswd, cluster-create, cluster-delete | `scripts/` |
| Fake kubectl for offline transcripts | `scripts/demo/kubectl` |
| Offline test suite | `tests/run.sh` → 36 passed |
| Coat module, spells, installer | `coat/` (installer tested with `--dry-run`) |
| README, example runs (real A1, simulated rest) | `README.md`, `docs/example-runs.md` |
| Observability scaffold (profiles, values, alerts, probes) | `observability/` |
| Bastion scaffold (host + in-cluster) | `bastion/` |
| Cluster skeletons (minikube, kind, k3d, k3s, managed) | `clusters/` |
| Tool installer (user-space + apt fallback) | `setup/install-tools.sh` |

## What is not done

1. **A4 LAN verification from a second machine** — host-side curl works
   (`curl http://192.168.1.240:8080` returns 200), but no second machine available.
2. **Coat is not installed.** Only `coat/install-coat.sh --dry-run` was run.
   Nothing in `~/.coat` or `~/.coatrc` was changed.
3. **Observability stack not installed** — scaffolded only. Install with
   `make obs PROFILE=minimal` after disk/RAM check.
4. **Bastion not deployed** — manifests and host config exist, not applied.
5. **The expansion tracks exist only as plans:** no stacks (phase 14), no drills
   (phase 13), no RAG (phase 16–17), no cloud experiment (phase 18), no AI
   pattern catalogue.
6. **`paczki/k8s` was not exercised through `paczek`.** The `fill_template`
   syntax (`{{ VAR }}`) matches Coat, but it was not run.

## Next actions, in order

```bash
cd /home/kris/00___Castle/07__WorkShops/k8s

# 1. confirm the kit still passes
make test

# 2. install observability (minimal profile) if disk/RAM allow
make doctor
make obs PROFILE=minimal

# 3. deploy host bastion (if a second machine will be used)
# sudo bastion/host/setup.sh --user labjump --key ~/.ssh/id_ed25519.pub --lan 192.168.1.0/24

# 4. A4 second-machine test — when a second machine is on the LAN
# scripts/lab-up.sh a6
# scripts/lab-tunnel.sh --background
# on second machine: curl http://192.168.1.240:8080

# 5. phase 12 (boilerplates), phase 13 (drills), phase 14 (stacks),
#    phase 15 (observability full), phase 16–17 (AI/RAG), phase 18 (cloud)
```

## Known traps, already measured or reasoned

| Trap | Where it will bite | Handle |
|---|---|---|
| Disk is 90% full (64.5 GiB free) | minikube 15 GiB + images + build cache | keep `--disk-size=15g`, prune after each stack, `make doctor` warns below 40 GiB |
| 11.9 GiB RAM available now | 8 GiB cluster would swap during a PHP build | 6 GiB cluster, one stack at a time |
| `minikube mount` is a foreground process | A1/A7 pods stuck in `ContainerCreating` | `scripts/lab-up.sh a1 --mount` detaches it and records the pid |
| `subPath` mounts never update | A2 would look broken | A2/A5 use directory mounts; this is written into the manifests and the runbook |
| ConfigMap is 1 MiB, UTF-8 only | images cannot live there | images go on the hostPath (A1) |
| LoadBalancer on minikube is `<pending>` | A4 expectations | `docs/runbooks.md` A4 table; port-forward 0.0.0.0 is the answer |
| SQLite + more than one replica | data corruption | one replica, `Recreate`, `journal_mode=DELETE` |
| PHP-FPM runs as uid 82 | `permission denied` on `database/` | init container chowns and chmods; documented in A7 |
| Fake `kubectl` always succeeds | false confidence | `tests/run.sh` includes failure cases; the doc labels the fake |
| Bitnami tag drift | H1 breaks | `helm show values` before copying any snippet |

## Decisions to keep, and the ones to revisit

Keep:

- minikube + docker driver as the default; `port-forward --address 0.0.0.0` for
  the LAN; one namespace `k8s-lab`; scripts with `--dry-run`; fake client only
  for offline docs; A7 single replica.
- The module is sourced from `.coatrc`, **not** added to `COAT_MODULE_ORDER`, so
  a Coat update never conflicts.

Revisit:

- Whether `loot` should detect this kit (needs a 3-line change in Coat's
  `spells.sh`; documented in `coat/README.md`, not applied).
- Whether the kit should move into the dotfiles repo. Right now it lives in the
  workshop folder and the Coat symlinks point here; moving it breaks those links.
- The observability stack choice (Prometheus vs VictoriaMetrics) — decide after
  measuring, see research R17.
- pgvector+AGE vs Neo4j for the graph layer — research R18.

## How to resume a session

Read in this order, then run the commands:

1. `resume.md` (this file) — state and next actions.
2. `README.md` — the map of the folder.
3. `analysis/02-todo.md` — the ordered list; find the first open checkbox.
4. `docs/runbooks.md` — the exercise you are about to run.

```bash
make test        # must be green before changing anything
make doctor      # must show no FAIL line
git status       # this folder is not a git repo; copy it out if that matters
```

## Session log (what changed here)

- Created the analysis of the prompt file and the PDF, including the defect list.
- Added and analysed `kubernetes_podsumowanie.md`; produced the coverage matrix.
- Measured the hardware and derived the tiers; wrote the doctor and the tests.
- Built 6 scenario manifests, 8 paczki templates, 9 scripts, a fake client, a
  26-case offline suite, the runbooks, the example runs, the README and Coat wiring.
- Fixed three bugs found by the checks: an `if/fi` mismatch in `lab-tunnel.sh`,
  shellcheck warnings treated as errors, and a failing `--dry-run` without kubectl.
- Restructured A5 from a `subPath` mount to two directory-mounted ConfigMaps.
- Installed tools via `setup/install-tools.sh` (user-space binaries: kubectl v1.37.1,
  minikube v1.39.0, helm v3.22.1, k3d v5.9.0, kind v0.34.0-alpha, yq v4.54.1,
  sqlite3 3.54.1, htpasswd from .deb + mkpasswd.sh fallback).
- Built cluster scaffolds: minikube, kind, k3d, k3s, managed; `scripts/cluster-create.sh`
  and `cluster-delete.sh` with hardware-aware sizing from shared `recommend_sizing`.
- Built observability scaffold: `observability/install.sh` with profiles
  (minimal/logs/traces/full), trimmed Helm values for kube-prometheus-stack, Tempo,
  Loki, OTel collector, alerts, probes, inventory, host compose.
- Built bastion scaffold: host `sshd_config.d`, `setup.sh`/`audit.sh`, client SSH
  config, in-cluster jump pod (namespace, RBAC, deployment, service, NetworkPolicy,
  Dockerfile, entrypoint).
- Started minikube with doctor flags (`--driver=docker --cpus=6 --memory=6144
  --disk-size=20g`), enabled metrics-server.
- Ran A1–A7 on the real cluster; captured transcripts in `docs/example-runs.md`,
  closed coverage rows A1–A3, A5–A7.
