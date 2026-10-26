# Spec: HA (High Availability) Definition for This Lab

## Problem Statement
The repository states "Sized for a 6-8 GiB lab. Single-binary, short retention, no HA." This spec defines what **HA means in this context**, what is explicitly excluded, and what would be required to add it.

## HA Definition (Kubernetes Context)

**High Availability** = the system continues operating correctly when individual components fail, with no manual intervention required for the failure of any single component.

### HA Dimensions

| Dimension | What It Means | Lab Status |
|---|---|---|
| **Control Plane** | ≥ 3 API server replicas, etcd quorum, scheduler/controller-manager leader election | ❌ Single minikube control plane |
| **Worker Nodes** | ≥ 3 nodes in multiple zones; pod anti-affinity spreads replicas | ❌ Single minikube node |
| **Stateful Workloads** | ≥ 3 replicas with `PodDisruptionBudget`, persistent storage with replication, automated failover | ❌ Single replica, hostPath/emptyDir, no PDB |
| **Ingress/Load Balancing** | External LB with health checks, multiple ingress controller replicas | ❌ `kubectl port-forward` or `NodePort` only |
| **Observability** | Prometheus HA (remote write to object storage), Alertmanager HA, Tempo/Loki replication | ❌ Single replica each, local storage |
| **Secrets/Config** | External secret manager (Vault, SealedSecrets, External Secrets Operator) | ❌ Plaintext in `Secret`/`ConfigMap` |
| **Networking** | CNI with network policies, service mesh (mTLS), multi-AZ subnets | ❌ Default CNI, no policies (except Graph RAG demo) |
| **Backup/DR** | Automated etcd backup, PVC snapshots, restore tested, RPO/RTO defined | ❌ Manual `pg_dump`/`velero` only |

## What "No HA" Means Here (Explicit Exclusions)

| Component | Current Lab Design | Why It's Not HA |
|---|---|---|
| **API Server** | 1 (minikube) | No budget for 3 control plane VMs |
| **etcd** | Embedded in minikube | Single node, no quorum |
| **Postgres (Graph RAG)** | 1 container, named volume | No streaming replication, no Patroni |
| **Prometheus** | 1 replica, local TSDB | No remote write, no HA pair |
| **Alertmanager** | 1 replica | No HA gossip cluster |
| **Grafana** | 1 replica, SQLite | No shared DB, no replica |
| **Loki/Tempo** | 1 replica, filesystem | No replication, no compaction |
| **Graph RAG API** | 2 replicas (Kustomize), no PDB | Can survive 1 pod loss but not node loss |
| **Ingress** | None (port-forward) | No external LB, no TLS termination |
| **Secrets** | `Secret` with `changeme` | No rotation, no external manager |

## What Would Be Required for HA (Incremental)

| Level | Additions | Approx. Resource Cost |
|---|---|---|
| **HA Lite** (single zone, 3 nodes) | 3 worker nodes, PDBs, 2+ replicas per Deployment, Prometheus remote write to MinIO, Alertmanager HA (2), external secret manager | +4–6 GiB RAM, +2 vCPU |
| **HA Standard** (multi-AZ) | 3 nodes across 2 AZs, topology spread constraints, multi-AZ PVC (CSI), ingress controller with LB, etcd backup to object storage | +8–12 GiB, managed control plane |
| **HA Full** (production-grade) | Managed control plane (EKS/GKE/AKS), multi-region, service mesh, automated failover testing, chaos engineering | Cloud pricing |

## Lab-Sizing Context

The lab targets **6–8 GiB total RAM** on a single machine (minikube). This forces trade-offs:

| Component | Lab Config | HA Config | RAM Delta |
|---|---|---|---|
| minikube control plane | ~2 GiB | N/A (managed) | — |
| Prometheus | 1 × 512 MiB | 2 × 1 GiB + remote write | +1.5 GiB |
| Grafana | 1 × 256 MiB | 2 × 256 MiB + Postgres | +0.5 GiB |
| Loki | 1 × 512 MiB | 2 × 1 GiB + S3 | +1.5 GiB |
| Tempo | 1 × 512 MiB | 2 × 1 GiB + S3 | +1.5 GiB |
| Postgres (Graph RAG) | 1 × 1 GiB | 3 × 1 GiB (Patroni) | +2 GiB |
| Graph RAG API | 2 × 1 GiB | 3 × 2 GiB + PDB | +4 GiB |
| **Total** | **~6–7 GiB** | **~18–25 GiB** | **3–4×** |

## Acceptance Criteria for "No HA" Label
- Documentation explicitly states which HA dimensions are absent
- No component claims HA in its manifest (no `replicas: 3` without PDB, no `Patroni`, no `remote_write`)
- Users understand: **node failure = lab downtime**; **pod failure = self-heals if replicas > 1**
- Recovery drills (`scripts/lab-drill.sh`) cover pod-level failures only, not node/zone/control-plane

## References
- `analysis/07-what-to-do.md` — "Sized for a 6-8 GiB lab. Single-binary, short retention, no HA."
- Kubernetes HA topology: <https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/high-availability/>
- Prometheus HA: <https://prometheus.io/docs/prometheus/latest/high_availability/>
- Postgres HA on K8s: <https://github.com/zalando/postgres-operator> (Patroni)
- CNCF "Running Kubernetes in Production" whitepaper