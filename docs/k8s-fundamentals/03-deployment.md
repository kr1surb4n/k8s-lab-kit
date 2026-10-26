# Kubernetes Fundamentals — Deployment

## What is a Deployment?

A **Deployment** is a controller that provides **declarative updates** for Pods and ReplicaSets. It manages:
- **Rolling updates** (zero-downtime)
- **Rollbacks** (to previous versions)
- **Scaling** (horizontal)
- **Self-healing** (replaces failed Pods)

## Deployment vs ReplicaSet vs Pod

| Level | Responsibility |
|-------|----------------|
| **Pod** | Runs containers (atomic unit) |
| **ReplicaSet** | Ensures N Pods running (replaces failed) |
| **Deployment** | Manages ReplicaSets (updates, rollbacks, history) |

**Never manage ReplicaSets directly** — Deployment owns them.

## Deployment Spec

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
  labels:
    app: my-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      containers:
        - name: my-app
          image: my-app:v1
          ports:
            - containerPort: 8080
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 25%
      maxUnavailable: 25%
  # minReadySeconds: 10  # Pod must be ready this long before considered available
  # progressDeadlineSeconds: 600  # Timeout for rollout
  # revisionHistoryLimit: 10  # Number of old ReplicaSets to keep
```

## Key Fields

| Field | Purpose |
|-------|---------|
| `replicas` | Desired Pod count |
| `selector` | **Must match** `template.metadata.labels` |
| `template` | Pod template (same as Pod spec) |
| `strategy` | Update strategy (RollingUpdate / Recreate) |
| `minReadySeconds` | Delay before Pod considered available |
| `progressDeadlineSeconds` | Max time for rollout (default 600s) |
| `revisionHistoryLimit` | Old ReplicaSets to retain (default 10) |

## Update Strategies

### RollingUpdate (Default)
- **Gradually replaces** old Pods with new ones
- **maxSurge**: Extra Pods above replicas during rollout (default 25%)
- **maxUnavailable**: Pods unavailable during rollout (default 25%)
- **Zero-downtime** if readiness probes configured

```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxSurge: 1           # Can be int or %
    maxUnavailable: 0     # 0 = no downtime (need readiness probe)
```

### Recreate
- **Kills all old Pods first**, then creates new ones
- **Downtime** guaranteed
- Use for: apps that can't run multiple versions (e.g., single-writer DB)

```yaml
strategy:
  type: Recreate
```

## Rolling Update Process

```
1. Create new ReplicaSet (v2) with 0 replicas
2. Scale up v2 to maxSurge (e.g., +1)
3. Wait for new Pods ready (readiness probe)
4. Scale down old ReplicaSet (v1) by maxUnavailable
5. Repeat until v2 = replicas, v1 = 0
```

## Rollback

```bash
# See rollout history
kubectl rollout history deployment my-app

# Rollback to previous
kubectl rollout undo deployment my-app

# Rollback to specific revision
kubectl rollout undo deployment my-app --to-revision=3

# Check rollout status
kubectl rollout status deployment my-app
```

## Scaling

```bash
# Manual scale
kubectl scale deployment my-app --replicas=5

# Auto-scale (HPA)
kubectl autoscale deployment my-app --cpu-percent=70 --min=3 --max=10
```

## Deployment Status & Conditions

```bash
kubectl get deploy my-app -o wide
kubectl describe deploy my-app
```

**Conditions:**
- **Progressing**: Rollout in progress / complete / stuck
- **Available**: Minimum replicas ready
- **ReplicaFailure**: Failed to create Pods

## Pausing & Resuming

```bash
# Pause rollout (make changes, then resume)
kubectl rollout pause deployment my-app

# Resume
kubectl rollout resume deployment my-app
```

## Deployment Internals

### Label Selector Mechanics
- `spec.selector.matchLabels` must be subset of `template.metadata.labels`
- Changing selector = new Deployment (can't update in place)

### ReplicaSet Ownership
- Deployment creates ReplicaSet with `ownerReference`
- Deleting Deployment → cascades to ReplicaSets → Pods
- Orphaned ReplicaSets cleaned up by garbage collector

### Revision History
- Each rollout creates new ReplicaSet
- `revisionHistoryLimit` controls retention
- Rollback = scale up old ReplicaSet, scale down current

## Common Patterns

### Blue-Green (via Service selector switch)
```yaml
# Deploy v2 with different label
# Switch Service selector to v2 label
# Instant switch, easy rollback
```

### Canary (via multiple Deployments)
```yaml
# Deploy v2 with 10% replicas
# Same Service selector (both Deployments match)
# Gradually increase v2 replicas
```

### Feature Flags
```yaml
# Deploy with env var FEATURE_NEW_UI=false
# Toggle via ConfigMap/env without redeploy
```

## Common Commands

```bash
# Create
kubectl apply -f deployment.yaml

# View
kubectl get deploy my-app -o wide
kubectl get rs -l app=my-app  # ReplicaSets
kubectl get pods -l app=my-app

# Scale
kubectl scale deploy my-app --replicas=5

# Update image
kubectl set image deploy/my-app my-app=my-app:v2

# Edit live
kubectl edit deploy my-app

# Rollout
kubectl rollout status deploy my-app
kubectl rollout history deploy my-app
kubectl rollout undo deploy my-app
kubectl rollout pause deploy my-app
kubectl rollout resume deploy my-app

# Delete (cascades to Pods)
kubectl delete deploy my-app
```

## Best Practices

1. **Always set resource requests/limits** — prevents scheduling issues
2. **Use readiness probes** — essential for zero-downtime rolling updates
3. **Set `maxUnavailable: 0`** — with readiness probe, ensures no downtime
4. **Set `revisionHistoryLimit`** — keep enough history for rollback
5. **Use labels consistently** — app, version, tier, environment
6. **Don't mix manual Pod changes** — Deployment owns Pods
7. **ProgressDeadlineSeconds** — set to detect stuck rollouts
8. **MinReadySeconds** — avoid flapping Pods counted as available

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| Rollout stuck | Pods not ready | Check readiness probe, Pod events |
| Pods CrashLoopBackOff | App crash | `kubectl logs` previous container |
| ImagePullBackOff | Wrong image/registry | Check image name, credentials |
| Rollout timeout | ProgressDeadlineSeconds | Increase or fix underlying issue |
| Old ReplicaSets not cleaned | revisionHistoryLimit | Set or increase limit |

## References

- [Deployments](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/)
- [Rolling Updates](https://kubernetes.io/docs/tutorials/k8s/rolling-update/)
- [Rollbacks](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/#rolling-back-a-deployment)
- [Scaling](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)
- [Deployment Strategies](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/#strategy)