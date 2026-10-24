# Tools and setup

`setup/install-tools.sh` is the only installer. It prefers user-space binaries
because Debian has `kubectl` but not `minikube` or `helm`, and because this
machine's sudo needs a password.

```bash
setup/install-tools.sh --check      # what is present, what is missing
setup/install-tools.sh              # core, no root
setup/install-tools.sh --extras     # core + day-2 tools
sudo setup/install-tools.sh --apt   # also sqlite3 + apache2-utils via apt
```

What it installs into `~/.local/bin`:

| Tool | Why it is here | Verified |
|---|---|---|
| `kubectl` | the only client the lab scripts call | sha256 |
| `minikube` | default cluster, host-file mounts | sha256 |
| `helm` 3.x | charts, H1 exercise, observability | sha256 |
| `k3d` | LAN-capable comparison cluster | latest |
| `kind` | ingress-ready comparison cluster | latest |
| `yq` | readable YAML edits in scripts | latest |
| `sqlite3` | A7's host-side insert | sha3-256 |
| `htpasswd` | A5 credential (openssl fallback exists) | .deb |

`--extras` adds `k9s`, `stern`, `kubectx`, `kubens`, `kubeconform`,
`kube-linter`, `popeye`, `helmfile`, `argocd` and the `helm-diff` plugin.

## Recommended, by the job they do

Not all of these belong on day one. Install the row when the track needs it.

### Look at the cluster

| Tool | Use | Fits 6 GiB |
|---|---|---|
| `k9s` | TUI for pods, logs, events | yes, client only |
| `stern` | logs from many pods at once | yes |
| `kubectx` / `kubens` | switch context/namespace | yes |
| `kubectl-tree` | owner references as a tree | yes, plugin |
| `kubectl-neat` | remove managed fields from YAML | yes |
| `kubectl-images` | which images a namespace runs | yes |
| `kubectl-who-can` | RBAC questions | yes |
| `popeye` | cluster hygiene report | yes, client only |
| `kube-linter` | static checks on manifests | yes, client only |
| `kubeconform` | schema-validate YAML offline | yes, client only |
| `kube-score` | score manifests | yes |
| `pluto` | deprecated API detection | yes |
| `kubescape` | NSA/CISA posture scan | client only |

### Build, test, ship

| Tool | Use |
|---|---|
| `kubeconform` | replace a hand-written YAML parser |
| `hadolint` | Dockerfile lint |
| `dive` | inspect image layers |
| `shellcheck` | already used by `make check` |
| `pre-commit` | run the checks before a commit |
| `act` | run GitHub Actions locally |
| `k6` / `hey` / `fortio` | load and latency tests |
| `helmfile` | many releases, one file |
| `argocd` / `flux` | GitOps (track T4/T6) |
| `velero` | backup/restore (track T2) |

### Operate

| Tool | Use | Note |
|---|---|---|
| `metrics-server` | `kubectl top` | minikube addon |
| `ingress-nginx` | N1 ingress | ~300 MiB |
| `cert-manager` | TLS, `Certificate` objects | ~150 MiB |
| `external-secrets` / `sealed-secrets` | secrets from Git | pick one |
| `goldilocks` / VPA | right-size requests | needs metrics-server |
| `chaos-mesh` | failure injection | heavy; scripts are enough for T2 |
| `kube-bench` | CIS benchmark | run as a Job |
| `trivy-operator` | image scanning in-cluster | heavy on this disk |
| `hubble` | network flows | needs Cilium, not the minikube default |
| `netpol-visualizer` | draw NetworkPolicies | client only |

### AI / RAG (track T5)

| Tool | Use |
|---|---|
| `llama.cpp` or `ollama` | local models on the host GPU |
| `python3` + `uv` | the ingest/retrieval service |
| `pgvector`, Apache AGE | vectors + graph in one Postgres |
| `qdrant` | alternative vector store |
| `ragas` | retrieval/answer evaluation |
| `opentelemetry` SDK | traces for every question |

## Cluster skeletons

`clusters/README.md` compares minikube, kind, k3d, k3s and managed clusters.
`scripts/cluster-create.sh` drives the first four; `clusters/*/` holds the
configs. The lab manifests work on all of them; only the StorageClass and the
way traffic reaches the host change.

## Bastion

`bastion/README.md` covers the host jump box (default) and the optional
in-cluster jump pod. The host config is in `bastion/host/`, the manifests in
`bastion/k8s/`.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `command not found` after install | `~/.local/bin` not in PATH | `export PATH="$HOME/.local/bin:$PATH"` |
| `minikube start` pulls at 100 KiB/s | network, not minikube | wait, or use `k3d` |
| `htpasswd: error while loading shared libraries` | missing libcrypt | use `scripts/mkpasswd.sh` (openssl) |
| `sqlite3` checksum warning | sqlite.org publishes SHA3-256 | the installer verifies SHA3-256, not SHA-256 |
| `helm plugin install` fails | Helm 4 plugin API | this script pins Helm 3.x |
| `sudo` asks for a password | no cached credential | run `sudo setup/install-tools.sh --apt` yourself |
