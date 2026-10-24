# Hardware profile and what it allows

Measured on this machine with `scripts/lab-doctor.sh`. Re-run that script instead
of trusting this file after a hardware change.

## Measured

| Item | Value | Consequence |
|---|---|---|
| OS / kernel | Debian 13 (trixie), 6.12.105 | Docker, minikube docker driver, cgroup v2 all supported |
| CPU | Intel Core Ultra 9 275HX, 24 threads | plenty; the cluster gets 6, the rest stays for the browser and builds |
| RAM | 30.8 GiB total, **11.9 GiB available** at check time | 6 GiB cluster is comfortable, 8 GiB is the ceiling, do not run two stacks |
| Swap | 31 GiB partition | hides leaks, does not make k8s faster; do not count on it |
| Disk | 677 GiB total, **64.5 GiB free (90% used)** | the real bottleneck; 15 GiB minikube + images + observability is close to the edge |
| GPU | RTX 5070 Laptop, **8151 MiB VRAM**, driver 610.57.04 | local 7–8B quantised chat, embeddings and reranking are realistic; 70B is not |
| Docker | 29.8.0, overlayfs, cgroup v2, no sudo needed | minikube `--driver=docker` works as the current user |
| Ports | 80, 8080, 8443 free | port-forward and ingress can use the defaults |
| Cluster | none, and no kubectl/minikube/helm/sqlite3/htpasswd yet | phase 0 of the todo is still open |

## Tiers the doctor reports

| Tier | Condition | What fits |
|---|---|---|
| BLOCKED | a FAIL line (disk < 20 GiB free, RAM < 4 GiB available) | fix it first |
| LIGHT | 4 GiB available | A1–A5, one pod at a time, no observability |
| STANDARD | 5–7 GiB available | A1–A6, A7 with care, a single lightweight add-on |
| FULL | 8 GiB+ available | A1–A7 plus one small observability stack |

This machine is **STANDARD**, close to FULL when nothing else is running.

## Recommended cluster

```bash
minikube start --driver=docker --cpus=6 --memory=6144 --disk-size=15g
```

Why not the PDF's `--cpus=4 --memory=8192 --disk-size=20g`:

- 8 GiB is two thirds of what is available; the host starts swapping during a
  PHP build or an observability install.
- 20 GiB of disk on a 90%-full NVMe leaves no room for a docker build cache.
- 6 CPU / 6 GiB already runs 3 replicas, PostgreSQL, PHP-FPM and a metrics
  stack. Disk is the constraint to watch, not CPU.

## Per-track feasibility

| Track | Feasible here? | Limit |
|---|---|---|
| A1–A6 (nginx, ConfigMap, env, LAN, Secret, 3 replicas) | yes | needs the 5 missing CLI tools |
| A7 (Laravel shape, PHP-FPM, PostgreSQL, SQLite) | yes, with care | one replica, `Recreate` strategy, expect the PHP image build to use 1–2 GiB |
| Observability (Prometheus + Grafana + Loki + Tempo) | yes, but not the full `kube-prometheus-stack` defaults | budget ~1.5–2 GiB; use single-binary Loki, short retention, 6 GiB cluster |
| Traceability of networks/hosts | yes | scrape the LAN from outside the cluster; do not deploy a second monitoring stack per host |
| Other stacks (Node, Python, Go, Java, PHP, queues, object storage) | yes, one at a time | 64 GiB free disk is the hard stop; prune images between stacks |
| Local AI (embeddings, rerank, 7–8B chat) | yes, on the host GPU | 8 GiB VRAM: one model at a time; no GPU passthrough into k8s |
| RAG + graph/hypergraph | yes | vector store + graph DB in the cluster (~1 GiB), models outside it |
| Cloud free tiers | yes, but not as the primary | free tiers expire, need a card, and add network latency; use one provider for one experiment |
| Observability of "controlled networks and hosts" | yes | needs an inventory of hosts first; that is a document, not a chart |

## What not to do on this machine

- Magento: 4 dependencies, 50 GiB PVC, several GiB of RAM. It would eat the free
  disk and teach nothing that one chart does not.
- A full ELK stack: Elasticsearch alone wants more RAM than the whole cluster.
- Kafka + Zookeeper + Schema Registry + Connect: fine in theory, not with 6 GiB
  and 64 GiB of disk.
- GPU passthrough into the cluster: the 8 GiB card is more useful shared by the
  host, with the cluster calling it over HTTP.
- Two clusters at once (minikube + k3d for the A4 comparison): run them
  sequentially and delete the first.

## Changes this profile forces on the kit

1. `scripts/lab-doctor.sh` is the pre-flight check; `make doctor` runs it.
2. The recommended flags live in the doctor, not in the runbooks, so they follow
   the machine instead of a stale document.
3. The A7 image build is optional and explicitly sized; SQLite stays at one
   replica (already decided).
4. Observability, stacks and AI tracks are ordered by memory cost, cheapest
   first, and each one is installed alone.
5. `tests/run.sh` is offline on purpose: CI must pass on a machine without a
   cluster or a GPU.
