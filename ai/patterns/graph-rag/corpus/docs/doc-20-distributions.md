---
id: doc-20
title: minikube, k3s, MicroK8s, k3d and kind
section: "Operations > Distributions"
corpus_version: 2026-10-26.1
source:
  kind: authored
  snapshot: 2026-10-26
  based_on:
    - docs/runbooks.md#d1
    - scripts/cluster-create.sh
    - analysis/06-scope-expansion.md
---

The default is **minikube** with the docker driver: one node in a container, no
host changes, one command up and down. Its cost is that the node network is
hidden: a NodePort is not reachable from the LAN, a LoadBalancer stays `<pending>`,
and LAN access needs `kubectl port-forward --address 0.0.0.0`.

**k3s** is a single binary run by systemd on the host. NodePort and Ingress listen
on the host interfaces, so LAN access works without a tunnel; the price is a real
installation on the host and a less trivial cleanup. **MicroK8s** is the snap
variant with the same networking property.

**k3d** runs k3s inside Docker and can publish ports
(`-p 8080:80@loadbalancer`). **kind** is Kubernetes in Docker, mainly for
conformance testing; it needs explicit port mappings for anything inbound. Both
are cheap to delete.

The StorageClass differs by distribution: `standard` on minikube, `local-path`
on k3s, `microk8s-hostpath` on MicroK8s. That name is the usual reason a manifest
that worked on one cluster leaves a claim Pending on another.

`scripts/cluster-create.sh` accepts `minikube`, `kind`, `k3d`, or `k3s`, so the
comparison is a command, not a manual install.
