# Kubernetes Fundamentals — Deployment vs StatefulSet (Deep Dive)

## The Core Question

> **Czym różni się Deployment od StatefulSet?**
> (How does Deployment differ from StatefulSet beyond the obvious?)

This document answers the "hard question" from the plan — the nuanced differences that matter in production.

---

## Summary Table

| Dimension | Deployment | StatefulSet |
|-----------|------------|-------------|
| **Pod Identity** | Random suffix (`app-7d5f8-xyz`) | **Stable ordinal** (`web-0`, `web-1`) |
| **DNS** | Service-level only | **Per-Pod DNS** (`web-0.svc.ns.svc.cluster.local`) |
| **Storage** | Shared PVC (all Pods same volume) | **Per-Pod PVC** (via `volumeClaimTemplate`) |
| **Scaling** | Parallel (any order) | **Sequential** (0→1→2) |
| **Scaling Down** | Parallel | **Reverse order** (2→1→0) |
| **Updates** | Parallel rolling | **Sequential** (0→1→2, wait ready) |
| **Rollback** | Easy (ReplicaSet history) | **Manual** (delete Pod, let recreate) |
| **Headless Service** | Optional | **Required** (for Pod DNS) |
| **volumeClaimTemplates** | Not supported | **Required** for per-Pod PVCs |
| **Use Case** | Stateless apps | Stateful apps (DBs, queues, clusters) |

---

## Deep Dive: The "Why" Behind Each Difference

### 1. Pod Identity: Random vs Ordinal

**Deployment:**
```
myapp-7d5f8b9c4-abc12
myapp-7d5f8b9c4-def34
myapp-7d5f8b9c4-ghi56
```
- Suffix = ReplicaSet hash + random
- **No stable identity** — Pods are cattle

**StatefulSet:**
```
web-0
web-1
web-2
```
- **Ordinal index** = stable identity
- **Predictable** — `web-0` always `web-0`
- Critical for: cluster membership, leader election, sharding

### 2. DNS: Service-Level vs Per-Pod

**Deployment (via ClusterIP Service):**
```
myapp.default.svc.cluster.local → 10.96.1.42 (Service VIP)
```
- Single DNS → load balanced across all Pods
- No way to reach specific Pod

**StatefulSet (via Headless Service):**
```
web-0.nginx.default.svc.cluster.local → 10.244.1.5
web-1.nginx.default.svc.cluster.local → 10.244.2.3
web-2.nginx.default.svc.cluster.local → 10.244.3.7
```
- **Direct Pod IPs** returned by DNS
- **SRV records** for port discovery
- Enables: peer discovery, leader election, client-side routing

### 3. Storage: Shared vs Per-Pod PVC

**Deployment:**
```yaml
# All Pods mount SAME PVC
volumes:
  - name: data
    persistentVolumeClaim:
      claimName: shared-data
```
- All replicas read/write **same volume**
- Works for: read-only, shared cache, single-writer with locking
- **Dangerous** for multi-writer databases

**StatefulSet:**
```yaml
volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: ["ReadWriteOnce"]
      storageClassName: "fast-ssd"
      resources:
        requests:
          storage: 10Gi
```
- **Per-Pod PVC**: `data-web-0`, `data-web-1`, `data-web-2`
- **Stable binding**: `web-0` always gets `data-web-0`
- PVC **survives Pod recreation** (same ordinal = same PVC)
- Enables: databases, message queues, any persistent state

### 4. Scaling: Parallel vs Sequential

**Deployment (Parallel):**
```
Scale 3→5: Creates Pod 4, Pod 5 simultaneously
Scale 5→3: Deletes Pod 4, Pod 5 simultaneously
```
- **No ordering** — any Pod can start/stop anytime
- Fast but **no ordering guarantees**

**StatefulSet (Sequential - `OrderedReady`):**
```
Scale 3→5: web-3 created → Ready → web-4 created → Ready
Scale 5→3: web-4 deleted → web-3 deleted (reverse order!)
```
- **Order matters**: `web-N` not created until `web-(N-1)` is **Ready**
- **Scale down reverse order**: highest ordinal first
- Ensures: quorum, leader election, data sync complete

**Parallel Option (`podManagementPolicy: Parallel`):**
```
All Pods created/deleted simultaneously
Use when: No ordering dependency (rare for true stateful apps)
```

### 5. Updates: Parallel vs Sequential

**Deployment (Parallel Rolling):**
```
v1: 3 Pods
v2: Create 1 new → 4 total → Delete 1 old → 3 v2 + 0 v1
```
- Multiple versions coexist during rollout
- **maxSurge/maxUnavailable** control parallelism

**StatefulSet (Sequential Rolling):**
```
v1: web-0, web-1, web-2
v2: web-0 updated → Ready → web-1 updated → Ready → web-2 updated
```
- **One at a time** — wait for Ready before next
- **No maxSurge** — can't exceed replicas
- **partition** for canary: only update ordinals >= N

### 6. Rollback: Easy vs Manual

**Deployment:**
```bash
kubectl rollout undo deploy/myapp  # Instant, to previous ReplicaSet
kubectl rollout undo deploy/myapp --to-revision=3
```
- **ReplicaSet history** retained
- **Instant rollback** — scale up old RS, scale down new

**StatefulSet:**
```bash
# No built-in rollback!
# Manual process:
kubectl delete pod web-1  # Recreates from current template (v2)
# To rollback to v1:
# 1. Update StatefulSet template to v1 image
# 2. Delete Pods in reverse order (web-2, web-1, web-0)
# 3. Each recreates with v1
```
- **No revision history** for automatic rollback
- **Manual process** — update template, delete Pods in reverse order
- `partition` in `updateStrategy` can limit update scope

### 7. Headless Service Requirement

**Deployment:**
```yaml
# Service optional, ClusterIP default
spec:
  type: ClusterIP  # or NodePort, LoadBalancer
```

**StatefulSet:**
```yaml
spec:
  serviceName: "nginx"  # REQUIRED — must match Headless Service
```
```yaml
# Headless Service (clusterIP: None)
apiVersion: v1
kind: Service
metadata:
  name: nginx
spec:
  clusterIP: None
  selector:
    app: nginx
```
- **Mandatory** — provides Pod DNS
- `clusterIP: None` = no VIP, DNS returns Pod IPs
- Without it: no stable DNS, no peer discovery

---

## When to Choose Which

### Choose Deployment When:
- ✅ App is **stateless** (or state externalized)
- ✅ **Horizontal scaling** needed (parallel)
- ✅ **Fast rollouts/rollbacks** important
- ✅ **No stable identity** needed
- ✅ Examples: Web servers, API servers, workers, frontends

### Choose StatefulSet When:
- ✅ **Stable network identity** required (DNS, clustering)
- ✅ **Persistent storage per instance** required
- ✅ **Ordered operations** required (startup, shutdown, scaling)
- ✅ **Leader election** / quorum needed
- ✅ Examples: MySQL, PostgreSQL, MongoDB, Kafka, ZooKeeper, etcd, Redis Cluster, Cassandra

### Edge Cases

| Scenario | Recommendation |
|----------|----------------|
| Stateless but needs stable hostname | StatefulSet with `podManagementPolicy: Parallel` |
| Single replica DB | Deployment + PVC (simpler) |
| Multi-replica DB with leader election | StatefulSet (required) |
| Read replicas only | Deployment (if primary external) |
| Cache (Redis) with persistence | StatefulSet (for AOF/RDB persistence) |

---

## Migration: Deployment → StatefulSet

**Not in-place** — must recreate:
```bash
# 1. Backup data (if any)
# 2. Delete Deployment
kubectl delete deploy myapp

# 3. Create StatefulSet with same PVC name pattern
# 4. PVCs may bind automatically if labels match
```

**Or:** Use `volumeClaimTemplates` with same PVC names if possible.

---

## Production Checklist

### Deployment
- [ ] Readiness probe defined
- [ ] Liveness probe defined
- [ ] Resources (requests/limits) set
- [ ] `maxUnavailable: 0` for zero-downtime
- [ ] `revisionHistoryLimit` set
- [ ] HPA configured if needed

### StatefulSet
- [ ] Headless Service created (`clusterIP: None`)
- [ ] `serviceName` matches Headless Service
- [ ] `volumeClaimTemplates` defined for persistent data
- [ ] `podManagementPolicy: OrderedReady` (default)
- [ ] `updateStrategy: RollingUpdate` with `partition` for canary
- [ ] PVC reclaim policy understood (Retain vs Delete)
- [ ] Anti-affinity rules for HA
- [ ] Backup/restore procedure for PVCs
- [ ] Monitoring on PVC capacity

---

## The "Tricky" Parts Summary

| Tricky Part | Deployment | StatefulSet |
|-------------|------------|-------------|
| **Rollback** | `kubectl rollout undo` | Manual: update template + delete Pods reverse order |
| **Scale down** | Any Pod | Must be highest ordinal first |
| **PVC cleanup** | Auto with Deployment | **Manual** — PVCs persist! |
| **Canary** | Easy (two Deployments) | `partition` in updateStrategy |
| **Debugging** | `kubectl logs pod-xyz` | `kubectl logs web-0` (predictable) |
| **Disaster recovery** | Recreate Deployment | Recreate StatefulSet + PVCs bind automatically |

---

## References

- [StatefulSet vs Deployment](https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/#limitations)
- [StatefulSet Updates](https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/#update-strategies)
- [StatefulSet Rollback](https://kubernetes.io/docs/tasks/run-application/debug-stateful-set/#rolling-back-a-statefulset)