# Kubernetes Fundamentals — StatefulSet

## What is a StatefulSet?

A **StatefulSet** is a controller for **stateful applications** that require:
- **Stable, unique network identifiers** (persistent hostname, DNS)
- **Stable, persistent storage** (persistent volumes per Pod)
- **Ordered, graceful deployment and scaling**
- **Ordered, automated rolling updates**

## When to Use StatefulSet

| Use Case | Example |
|----------|---------|
| **Databases** | MySQL, PostgreSQL, MongoDB, Cassandra |
| **Distributed systems** | Kafka, ZooKeeper, etcd, Redis Cluster |
| **Message queues** | RabbitMQ, Pulsar |
| **Any app needing** | Stable identity, persistent storage, ordered operations |

## StatefulSet vs Deployment

| Feature | Deployment | StatefulSet |
|---------|------------|-------------|
| **Pod identity** | Random hash (`app-7d5f8-abc12`) | **Stable ordinal** (`web-0`, `web-1`, `web-2`) |
| **DNS** | Single Service DNS | **Per-Pod DNS** (`web-0.nginx.default.svc.cluster.local`) |
| **Storage** | Shared PVC (all Pods same volume) | **Per-Pod PVC** (via `volumeClaimTemplate`) |
| **Scaling** | Parallel (any order) | **Sequential** (0→1→2) |
| **Deletion** | Parallel | **Sequential reverse** (2→1→0) |
| **Updates** | Parallel (rolling) | **Sequential** (0→1→2, wait for ready) |
| **Rollback** | Easy (ReplicaSet history) | **Manual** (delete Pod, let recreate) |
| **Headless Service** | Optional | **Required** (for Pod DNS) |
| `volumeClaimTemplates` | Not supported | **Required** for per-Pod PVCs |
| **Use Case** | Stateless apps | Stateful apps (DBs, queues, clusters) |

## StatefulSet Spec

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: web
spec:
  serviceName: "nginx"           # Headless Service (required)
  replicas: 3
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
        - name: nginx
          image: nginx:latest
          ports:
            - containerPort: 80
              name: web
          volumeMounts:
            - name: www
              mountPath: /usr/share/nginx/html
  volumeClaimTemplates:
    - metadata:
        name: www
      spec:
        accessModes: ["ReadWriteOnce"]
        storageClassName: "standard"
        resources:
          requests:
            storage: 1Gi
  # podManagementPolicy: OrderedReady  # or Parallel
  # updateStrategy:
  #   type: RollingUpdate
  #   rollingUpdate:
  #     partition: 0
```

## Key Fields

| Field | Purpose |
|-------|---------|
| `serviceName` | **Required** — Headless Service for Pod DNS |
| `replicas` | Desired Pod count |
| `selector` | Must match template labels |
| `template` | Pod spec (same as Deployment) |
| `volumeClaimTemplates` | **Per-Pod PVC** — creates PVC per Pod |
| `podManagementPolicy` | `OrderedReady` (default) or `Parallel` |
| `updateStrategy` | `RollingUpdate` (default) or `OnDelete` |

## Pod Identity

### Predictable Names
```
web-0, web-1, web-2  # Not random hashes!
```

### Stable DNS (via Headless Service)
```
# Headless Service: clusterIP: None
web-0.nginx.default.svc.cluster.local
web-1.nginx.default.svc.cluster.local
web-2.nginx.default.svc.cluster.local
```

### Stable Storage
Each Pod gets its **own PVC** from `volumeClaimTemplates`:
```
web-0 → pvc-www-web-0
web-1 → pvc-www-web-1
web-2 → pvc-www-web-2
```

**PVCs persist** even if Pod/StatefulSet deleted (unless `persistentVolumeReclaimPolicy: Delete`)

## Headless Service (Required)

```yaml
apiVersion: v1
kind: Service
metadata:
  name: nginx
spec:
  clusterIP: None          # Headless — no ClusterIP
  ports:
    - port: 80
  selector:
    app: nginx
```

- **No ClusterIP** — DNS returns **Pod IPs directly**
- **Pod DNS**: `<pod-name>.<service-name>.<namespace>.svc.cluster.local`
- **SRV records** for port discovery

## Scaling Behavior

### Ordered Scaling (Default: `podManagementPolicy: OrderedReady`)
```
Scale up:   web-0 ready → web-1 created → web-1 ready → web-2 created
Scale down: web-2 deleted → web-1 deleted → web-0 deleted
```

### Parallel Scaling (`podManagementPolicy: Parallel`)
```
All Pods created/deleted simultaneously
Use when: No ordering dependency (e.g., stateless replicas with stable IDs)
```

## Update Strategies

### RollingUpdate (Default)
```yaml
updateStrategy:
  type: RollingUpdate
  rollingUpdate:
    partition: 0  # Update Pods with ordinal >= partition
```
- Updates **sequentially**: `web-0` → wait ready → `web-1` → wait ready → `web-2`
- `partition`: Only update Pods with ordinal >= N (useful for canary)

### OnDelete
```yaml
updateStrategy:
  type: OnDelete
```
- **No automatic updates** — user must delete Pods manually
- Use for: manual control, complex migrations

## Common Patterns

### MySQL Primary-Replica
```yaml
# StatefulSet for MySQL
# web-0 = Primary (writes)
# web-1, web-2 = Replicas (reads)
# Use init container to configure replication based on ordinal
```

### Kafka/ZooKeeper
```yaml
# Each broker needs stable ID for cluster membership
# broker-0, broker-1, broker-2
# Stable storage for logs
```

### Redis Cluster
```yaml
# Each shard needs stable identity
# Stable storage for persistence
```

## VolumeClaimTemplates

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

- **Creates PVC per Pod**: `data-web-0`, `data-web-1`, `data-web-2`
- **PVC bound to PV** via StorageClass
- **PVCs retained** after Pod deletion (manual cleanup needed)

## Common Commands

```bash
# Create
kubectl apply -f statefulset.yaml

# View
kubectl get statefulset web -o wide
kubectl get pods -l app=nginx -o wide
# Shows: web-0, web-1, web-2 (ordered)

# Scale
kubectl scale statefulset web --replicas=5

# View PVCs
kubectl get pvc -l app=nginx

# Rolling update
kubectl set image statefulset/web nginx=nginx:1.20

# Check rollout
kubectl rollout status statefulset web

# Delete Pod (recreates with same identity)
kubectl delete pod web-1

# Delete StatefulSet (cascades to Pods, NOT PVCs by default)
kubectl delete statefulset web

# Delete with PVCs
kubectl delete statefulset web --cascade=foreground
# Or manually delete PVCs after
```

## Pod DNS Examples

```bash
# Inside cluster, from any Pod:
nslookup web-0.nginx
# Returns: web-0.nginx.default.svc.cluster.local -> 10.244.1.5

# SRV records for ports:
nslookup -type=SRV _web._tcp.nginx.default.svc.cluster.local
```

## Best Practices

1. **Always use Headless Service** — required for stable DNS
2. **Set `volumeClaimTemplates`** — for persistent storage per Pod
3. **Use `OrderedReady`** (default) — unless no ordering dependency
3. **Set `updateStrategy: RollingUpdate`** — with `partition` for canary
4. **Plan for PVC cleanup** — PVCs persist after StatefulSet deletion
5. **Use `preStop` hook** — for graceful shutdown (flush data, disconnect)
6. **Monitor PVC capacity** — set alerts on disk usage
7. **Anti-affinity** — spread Pods across nodes for HA

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| Pod stuck in Pending | PVC not bound | Check StorageClass, PV capacity |
| Pods not coming up in order | Previous not Ready | Check readiness probe, logs |
| PVC not deleted | `retain` policy | Manual cleanup or change reclaim policy |
| Update stuck | Partition / readiness | Check partition, Pod health |
| DNS not resolving | Headless Service missing | Verify `serviceName` matches Service |

## StatefulSet vs Deployment Decision Tree

```
Is the app stateless?
  ├─ Yes → Deployment
  └─ No → Does it need stable network ID + persistent storage + ordered ops?
          ├─ Yes → StatefulSet
          └─ No → Consider Deployment with PVC (if only storage needed)
```

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

## Production Checklist

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

## References

- [StatefulSets](https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/)
- [Headless Services](https://kubernetes.io/docs/concepts/services-networking/service/#headless-services)
- [Persistent Volumes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/)
- [StatefulSet Basics Tutorial](https://kubernetes.io/docs/tutorials/stateful-application/basic-stateful-set/)
- [Running ZooKeeper](https://kubernetes.io/docs/tutorials/stateful-application/zookeeper/)
- [Running Cassandra](https://kubernetes.io/docs/tutorials/stateful-application/cassandra/)