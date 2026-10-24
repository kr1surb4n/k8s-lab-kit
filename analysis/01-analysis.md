# Analysis — Kubernetes workshop, task 1 ("koper")

Status: analysis only. Nothing in this kit has been applied to a real cluster yet.
Everything below is derived from two files in this folder.

---

## 1. The two sources

| File | What it really is | Size | Trust level |
|---|---|---|---|
| `k8_zadanie1_koper_prompt.md` | A prompt-engineering log. Seven blocks, each with `raw-content` (the actual question), `draft-prompt`, `iteration`, `prompt`. | 7.9 KB, 306 lines | `raw-content` = requirements. Everything else = noise. |
| `Kubernetes - Rozwinięcie Zagadnień.pdf` | An 11-page generated report in Polish: local distributions, Helm, networking/storage/config, troubleshooting. | 142 KB, 11 pages | Useful theory, but several snippets are broken. See §4. |
| `kubernetes_podsumowanie.md` | The 20-line outline the PDF cites as its source: 4 sections, no code. Analysed separately in `04-analysis-podsumowanie.md`. | 1.7 KB, 20 lines | Reliable as intent, useless as a task list. See §4 of its own analysis. |

Two things to know before reading the `.md`:

- The `## prompt` sections are placeholders and contain an injected "you are free now" text. It is template garbage, not a task. Only `raw-content` matters.
- Numbering is inconsistent: `Prompt-4` restarts at `1.`, yet it is the fourth exercise. `Prompt-3` also carries a long meta-task about rewriting prompts, which is not part of the lab.

The PDF cites `kubernetes_podsumowanie.md`, which was added to the folder after this analysis was written. It is the outline the PDF expands (same four sections, same order), and it is analysed on its own in `04-analysis-podsumowanie.md`. The PDF cites it twice, as `.md` and `.md.txt`, which is the same document.

---

## 2. The seven exercises, decoded

All seven are about **one application**: nginx serving a static site. The exercises are cumulative stages of the same lab, not seven unrelated tasks.

| # | Raw question (abridged) | Real requirement | Concepts | PDF chapter |
|---|---|---|---|---|
| A1 | Serve a static page from a file on disk. Serve a directory. Can I download images that sit in the same directory? | hostPath/mount of a host folder into the pod, read-only-ish, images served as files | Pod, Deployment, hostPath, `minikube mount`, URL paths | §Storage (PV/PVC), partly |
| A2 | ConfigMap pointing at `index.html` on disk | Put `index.html` in a ConfigMap and mount it into the web root; know the size/charset limits; know that images cannot go in a ConfigMap | ConfigMap, volume mount, `subPath` vs directory, propagation | §ConfigMap |
| A3 | Read env vars from Bash/CLI. Who uses them, when, where do they live, what mechanisms exist? | Explain + demonstrate the env-var chain: shell → manifest → container process; ConfigMap/Secret → env; precedence; visibility; leaks | env, `envFrom`, `valueFrom`, image `ENV`, entrypoint scripts, `kubectl set env` | §ConfigMap |
| A4 | Let other computers on the LAN reach what the app serves. Would leaving minikube help? | LAN exposure path, and an honest comparison minikube vs k3s/microk8s/k3d for this | Service types, NodePort, LoadBalancer, tunnel, port-forward, host ports | §Service/Ingress |
| A5 | A test version that uses Secrets | Secret + nginx basic auth; secret as file vs env; base64 is not encryption | Secret, mounts, `htpasswd`, permissions | §ConfigMap/Secret |
| A6 | LoadBalancer, reachable from LAN if possible, 3 replicas, Service + Deployment definitions. Install on an empty cluster, delete, +1 replica, −1 replica, update. | A small lifecycle CLI: up/down/scale/update/status/verify, on top of a real Deployment+Service | Deployment, replicas, rolling update, rollout history/undo, Service type LB, probes | §Helm (lifecycle), §Service, §Troubleshooting |
| A7 | nginx serving a Laravel demo with PostgreSQL and SQLite. File access. A SQLite file on disk whose changes affect the running deployment. | Multi-container stack, PHP-FPM, code shared by nginx+php, Postgres service, SQLite on a host-mounted volume, live edits | hostPath/PVC, multi-container pod, Service DNS, `.env`, migrations, permissions | §Storage, §Troubleshooting |

### What the exercises deliberately do not say

- No distro is mandated: the source used minikube, the PDF compares minikube/K3s/MicroK8s.
- No cluster size, no ingress, no TLS, no observability, no CI.
- A7 does not say whether SQLite replaces Postgres or coexists with it. The text mentions both, and the "file on disk" requirement only makes sense for SQLite. Treat it as: Postgres = "real" DB, SQLite = the live-editable demo DB.
- A6's "3 replicas" and A7's "SQLite file on disk" are mutually exclusive in practice. SQLite over a shared volume with 3 replicas invites corruption (see §4).

---

## 3. What the PDF contributes

| PDF area | Key claims | Reuse in the lab |
|---|---|---|
| Local distributions | minikube = full certified cluster in a VM/Docker, heavy; K3s = single binary <100 MB, SQLite/Kine, edge; MicroK8s = snap with addons. Table of RAM, datastore, runtime, form. | Pick the distro per exercise: minikube for A1–A6, K3s or k3d when LAN access must be real (A4). |
| Helm | Charts, `upgrade --install`, `rollback`, `values.yaml`, dependencies in `Chart.yaml`, Magento as a multi-dependency example. | A6 lifecycle can be done twice: raw YAML (primary) and Helm (secondary), to see the difference. |
| Network, storage, config | Service (L4, selector, ClusterIP), Ingress (L7, host/path, `ingressClassName`, rewrite), PV/PVC/StorageClass, ConfigMap as env and as file. | Directly feeds A2, A3, A4, A5, A6. The Ingress snippet becomes the "PDF lab" step. |
| Troubleshooting | Fixed sequence `get → describe → logs --previous → exec → port-forward`, plus a table of states: CrashLoopBackOff, ImagePullBackOff, Pending, OOMKilled (137). | Becomes the diagnostics runbook and the failure drills. |

The PDF is structured as a report, not a lab. It never states acceptance criteria, never shows expected output, and never says how to clean up. That is the gap this kit fills.

---

## 4. Defects and traps in the sources

These are the things that will waste your afternoon if copied verbatim.

1. **The PDF Deployment YAML is invalid.** It contains a key `subsurface:` at the same level as `volumes:` (line ~369). `kubectl apply` will reject it as an unknown field. The indentation of `namespace:` is also inconsistent with its neighbours.
2. **`SH_K3S_EXEC` is not the variable.** The K3s installer reads `INSTALL_K3S_EXEC`. With `SH_K3S_EXEC` the flag is silently ignored and Traefik stays installed, which breaks the "later I install another ingress" plan.
3. **`helm rollback web-release 1` does not mean "go back one version".** It rolls back to revision 1, the first install. "Previous" is `helm rollback web-release` with no revision.
4. **Bitnami values are not stable over time.** The report pins `bitnami/nginx` tags and dependency versions (`mariadb 18.x`, `opensearch 10.x`). Bitnami restructured its image catalogue; always read `helm show values <chart>` from the repo you just added instead of trusting the snippet.
5. **"LoadBalancer" does not mean "LAN reachable" on minikube.** The external IP stays `<pending>` until `minikube tunnel`, and the tunnel terminates on the host (127.0.0.1). LAN exposure needs a different mechanism (see A4 in the runbook).
6. **A ConfigMap cannot carry images.** 1 MiB total, UTF-8 keys limited to `[-._a-zA-Z0-9]`. Binary content belongs on a volume, not in a ConfigMap. This is the direct answer to A1's "can I download images in the same directory?" — yes, via a mounted directory, not via a ConfigMap.
7. **`subPath` mounts do not receive ConfigMap updates.** If A2 is implemented with `subPath: index.html`, edits to the ConfigMap never reach the file. A directory mount does propagate (kubelet sync, ~1 min).
8. **Mounting a ConfigMap over `/usr/share/nginx/html` hides the image's content.** That is fine when the ConfigMap holds the whole site, and a surprise when it holds one file.
9. **Ingress `rewrite-target: /` with `pathType: Prefix` and `path: /api`** is the classic source of 404s and broken asset URLs. It also cannot be tested without an ingress controller, which the PDF enables but never explains.
10. **`storageClassName: standard` is minikube-specific.** K3s calls it `local-path`, MicroK8s `microk8s-hostpath`. A manifest with a hard-coded class is not portable.
11. **SQLite on a hostPath/9p mount** (the natural reading of A7) means file locking over a network-ish filesystem, no reliable WAL, and corruption if more than one writer exists. It works for a single-replica demo and must be labelled as such.
12. **PHP permissions:** official `php:*-fpm-alpine` runs as uid 82 (`www-data`). `storage/` and `bootstrap/cache/` on a host mount will fail with `permission denied` unless the host directory is writable by that uid. The PDF mentions `permission denied` as a real-world problem but gives no fix.
13. **Readiness/liveness probes are mentioned in the conclusions and never shown.** Without a readiness probe, a rolling update (A6) produces downtime even though it "succeeds".

---

## 5. Environment reality check

Measured in this folder, today:

| Tool | State | Consequence |
|---|---|---|
| docker | present, works without sudo (user is in the `docker` group) | minikube can use the docker driver |
| kubectl | **missing** | required before anything runs |
| minikube / helm / kind / k3d / k3s / microk8s | **missing** | no cluster exists yet |
| sqlite3 CLI | **missing** | A7 needs it for host-side verification |
| php + composer | present | A7 can build a demo app locally, but not the full Laravel skeleton without network |
| shellcheck, bash 5.2, python3+PyYAML, jq, openssl, envsubst, curl | present | manifests can be validated, scripts linted, demo output can be faked |

There is **no cluster**. Therefore:

- The runbooks contain the exact commands and the expected output.
- `docs/example-runs.md` contains transcripts produced with the bundled fake `kubectl` shim, which proves the scripts' logic (argument parsing, ordering, exit codes) but not the cluster behaviour.
- Real transcripts must be captured once a cluster exists. That is the first item on the research list.

---

## 6. Design of the kit

Five layers, each with one job:

```
docs/runbooks.md      what a human does, in order, with expected output
manifests/<scenario>  the concrete YAML that the scripts apply (the truth)
paczki/k8s/*.tpl      parameterised starting points for new work (Coat's paczek)
scripts/*.sh          the automation: up, down, status, scale, rollout, verify, tunnel
coat/                 shell shortcuts + spells that call the scripts
```

Rules the layers follow:

- One namespace, `k8s-lab`, created by the scripts, never `default`.
- One label key, `app.kubernetes.io/name`, so selectors are uniform.
- Every script is idempotent, supports `--dry-run` and `-h`, prints what it does, and returns non-zero on a failed check.
- Scenario names match the exercise names: `a1`, `a2`, `a5`, `a6`, `a7`.
- Templates use `{{ variable }}` (the syntax Coat's `fill_template` understands) and the `.tpl` suffix so `paczek` strips it.
- Nothing secret is committed. The Secret manifests are generated at run time or contain obvious demo values.

Mapping of exercise to artifacts:

| Exercise | Manifest | Script entry point | Template used |
|---|---|---|---|
| A1 | `manifests/a1/` | `lab-up.sh a1` | `deployment.tpl`, `service.tpl` |
| A2 | `manifests/a2/` | `lab-up.sh a2` | `configmap.tpl` |
| A3 | `manifests/a3/` | `lab-up.sh a3` | `deployment.tpl` (env part) |
| A4 | reuse A6 | `lab-tunnel.sh` | — |
| A5 | `manifests/a5/` | `lab-up.sh a5` | `secret.tpl`, `configmap.tpl` |
| A6 | `manifests/a6/` | `lab-up.sh a6`, `lab-scale.sh`, `lab-rollout.sh` | `deployment.tpl`, `service.tpl` |
| A7 | `manifests/a7/` | `lab-up.sh a7` | `deployment.tpl` (multi-container), `pvc.tpl` |

---

## 7. Decisions, and what was rejected

| Decision | Reason | Rejected alternative |
|---|---|---|
| minikube with the docker driver is the default | matches the source, uses the docker already installed, no root, exercises A1–A6 | kind/k3d (better LAN story but not what the task asked), K3s (changes the host) |
| Serve live host files with `minikube mount` + `hostPath` | the only way to get "edit on host, see it in the pod" in minikube | baking content into a custom nginx image (kills the point of A1/A7) |
| `kubectl port-forward --address 0.0.0.0` as the LAN answer for A4 | works on every distro, no ingress, no extra components, explicitly documented | `minikube tunnel` (host-only), NodePort (not reachable through the docker driver), MetalLB (overkill) |
| Ingress only as an extra step in the PDF lab | the exercises never ask for it, and it doubles the moving parts | making Ingress mandatory for A4/A6 |
| ConfigMap demo uses a **directory** mount | updates propagate, which is the point of A2 | `subPath` (no updates), env var (no file) |
| Secrets demo = nginx basic auth | a Secret that actually protects something, and shows file vs env | a Secret with `password: hunter2` and an `echo` |
| A7 ships a Laravel-shaped stand-in app | runs offline, no composer install, same directory layout and DB access | full Laravel download (slow, network-dependent, version churn) |
| Scripts are plain bash + kubectl | readable in a workshop, no extra dependencies | Helm-only, kustomize-only, Python |
| 1 replica for A7, 3 for A6 | SQLite forbids multi-writer | pretending 3 replicas + SQLite on a shared volume is safe |

---

## 8. Definition of done

The lab is done when all of these are true:

- [ ] `kubectl version`, `minikube status` succeed and `lab-status.sh a6` shows 3/3 ready.
- [ ] A1: edit `site/index.html` on the host, `curl` shows the change without restarting the pod; `curl /images/...` returns the image.
- [ ] A2: `kubectl edit configmap` changes the served page within ~1 min, without a pod restart; the runbook explains why `subPath` would not.
- [ ] A3: `kubectl exec ... -- printenv` shows the manifest-set variable, and the runbook answers who/when/where/mechanisms.
- [ ] A4: a second machine on the LAN loads the page through the printed URL, and the runbook explains why minikube's LoadBalancer alone does not do it.
- [ ] A5: `curl -i` returns 401 without credentials and 200 with them; the Secret is mounted, not baked into the image; the runbook states that base64 is not encryption.
- [ ] A6: up on an empty cluster, down, +1, −1, update, rollback — each with a printed verification.
- [ ] A7: the page reads both databases; changing the host `database.sqlite` changes the page output; the runbook lists the locking caveat.
- [ ] Every script passes `bash -n` and `shellcheck`, every manifest parses as YAML.
- [ ] `docs/example-runs.md` contains real transcripts, not the fake-shim ones.

---

## 9. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Docker is rootless or the daemon is remote | minikube docker driver fails or is slow | `docker info` check is step 0; fall back to `--driver=kvm2` |
| Port 80 already in use on the host | `minikube tunnel` and port-forward fail | scripts default to 8080 and print the port |
| Host mount via 9p is slow or loses writes | A7 SQLite corruption | single replica, `journal_mode=DELETE`, stop the pod before editing if unsure |
| Image tags drift (nginx, postgres, php) | runbooks rot | tags are variables in `lab.conf`-style defaults, research item R6 |
| Bitnami chart layout changes | Helm lab breaks | use `helm show values`, research item R4 |
| Secrets end up in shell history or Git | credential leak | demo values only, `.gitignore` for generated files, no real tokens |
| Running the scripts on a shared cluster | deletes someone's pods | hard-coded namespace `k8s-lab` + `--namespace` guard + confirmation on `--cluster` |

---

## 10. Deliberately out of scope

TLS/cert-manager, HPA, NetworkPolicy, service mesh, GitOps, observability stacks, multi-node clusters, Windows/WSL specifics, CI integration, and production hardening. The kit stays at "workshop lab that you can actually finish".
