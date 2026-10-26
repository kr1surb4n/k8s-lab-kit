---
id: doc-04
title: Services, ClusterIP, NodePort and LoadBalancer
section: "Concepts > Networking > Services"
corpus_version: 2026-10-26.1
source:
  kind: authored
  snapshot: 2026-10-26
  based_on:
    - docs/runbooks.md#a4
    - manifests/a6/web.yaml
    - manifests/a7/postgres.yaml
---

A Service selects Pods by label and gives them one stable address. The default
type is **ClusterIP**, reachable only inside the cluster. **NodePort** opens a
port in the 30000–32767 range on every node. **LoadBalancer** asks the
infrastructure for an external IP.

On minikube with the docker driver, a LoadBalancer stays at `EXTERNAL-IP
<pending>` because there is no cloud controller. The node IP also lives inside
the docker network, so a NodePort is not reachable from the LAN either. The
mechanism that does work is `kubectl port-forward --address 0.0.0.0`, which opens
a listener on the host; `scripts/lab-tunnel.sh` runs it in the background.

Inside the cluster, a Service name resolves through cluster DNS. A7 sets
`DB_HOST=postgres`, and that name reaches the PostgreSQL Service in the
`k8s-lab` namespace on port 5432.

A Service maps `port` to a named container `targetPort` (`http`, `pg`). It does
not run a proxy process of its own and it does not terminate TLS; Ingress and the
ingress controller handle HTTP routing.
