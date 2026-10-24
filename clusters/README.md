# Cluster skeletons

Four local shapes and one cloud note. The lab manifests do not care which one
runs them; only the StorageClass name, the ingress class and the way traffic
reaches the host differ.

| Skeleton | What it is | Host changes | LAN NodePort | Teardown | Fits here |
|---|---|---|---|---|---|
| `minikube/` | one node in a Docker container | none | no (use port-forward) | `minikube delete` | yes, default |
| `kind/` | Kubernetes in Docker, ingress-ready | none | via published ports | `kind delete cluster` | yes, for the A4 comparison |
| `k3d/` | k3s in Docker, load balancer publishes ports | none | **yes**, via `8080:80` | `k3d cluster delete` | yes, best LAN demo |
| `k3s/` | real k3s on the host, systemd | systemd, containerd, iptables | **yes** | `k3s-uninstall.sh` | possible, not default |
| `managed/` | EKS, GKE, AKS, OKE | none local | cloud LoadBalancer | provider console | free tiers only |

## Which one to use

- **Learning the exercises (A1–A7):** minikube. One command up, one down, no
  host surprises, `minikube mount` for the host-file lessons.
- **Proving the LAN story (A4) without a second machine:** k3d. The load
  balancer publishes `8080` and `8443` on the host, so a phone on the same
  network can reach it with no port-forward.
- **A real node, a real ingress, a real `NodePort`:** k3s. Use it after the
  minikube lab, and expect to clean up systemd units and iptables.
- **Someone else's control plane:** the free tier in `managed/`, once the
  manifests are stable.

## Common commands

```bash
scripts/cluster-create.sh                 # minikube, doctor sizing
scripts/cluster-create.sh k3d --name lab  # publish 8080/8443
scripts/cluster-create.sh kind
scripts/cluster-delete.sh minikube
scripts/cluster-delete.sh all --yes
```

The sizing comes from `recommend_sizing` in `scripts/lib/common.sh`, the same
function `make doctor` uses. `--profile minimal|standard|full` overrides it.

## What changes between them

| | minikube | kind | k3d | k3s |
|---|---|---|---|---|
| StorageClass | `standard` | `standard` | `local-path` | `local-path` |
| Ingress class | `nginx` (addon) | `nginx` (install) | `traefik` (default) | `traefik` (default) |
| API endpoint | Docker network | Docker network | Docker network | host:6443 |
| Node IP reachable from LAN | no | no | no (ports only) | yes |
| `kubectl top` | needs metrics-server addon | needs metrics-server | included | included |

A manifest that hard-codes `storageClassName: standard` will stay `Pending` on
k3d/k3s. That is the exercise, not a bug; use the overlay or the class name in
`clusters/<driver>/README.md`.
