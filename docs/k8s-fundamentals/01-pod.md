# Kubernetes Fundamentals — Pod

## What is a Pod?

A **Pod** is the smallest deployable unit in Kubernetes. It represents a single instance of a running process in your cluster.

## Key Characteristics

| Property | Description |
|----------|-------------|
| **Atomic unit** | Cannot be divided; scheduled as a whole |
| **Shared context** | Containers in a Pod share: network (localhost, ports), storage (volumes), IPC, cgroups |
| **Ephemeral** | Not durable; replaced, not repaired. Use controllers (Deployment, StatefulSet) for management |
| **Single IP** | Each Pod gets a unique cluster IP; containers communicate via `localhost` |

## Pod Lifecycle

```
Pending → Running → Succeeded / Failed / Unknown
```

- **Pending**: Accepted by API server, waiting for scheduling/image pull
- **Running**: Bound to node, all containers created, at least one running
- **Succeeded**: All containers terminated successfully (exit 0), not restarted
- **Failed**: All containers terminated, at least one failed (non-zero exit)
- **Unknown**: State cannot be determined (typically node communication issue)

## Pod Spec Key Fields

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: my-pod
  labels:
    app: my-app
spec:
  containers:
    - name: main-container
      image: nginx:latest
      ports:
        - containerPort: 80
      env:
        - name: ENV_VAR
          value: "value"
      resources:
        requests:
          memory: "64Mi"
          cpu: "250m"
        limits:
          memory: "128Mi"
          cpu: "500m"
      volumeMounts:
        - name: data
          mountPath: /data
  volumes:
    - name: data
      emptyDir: {}
  restartPolicy: Always  # Always | OnFailure | Never
```

## Init Containers

Special containers that run **before** app containers, sequentially:
- Must complete successfully before next starts
- If any fails, Pod restarts (unless `restartPolicy: Never`)
- Use for: setup scripts, DB migrations, waiting for dependencies

```yaml
spec:
  initContainers:
    - name: init-db
      image: busybox
      command: ['sh', '-c', 'until nslookup mysql; do sleep 2; done']
  containers:
    - name: app
      image: my-app
```

## Probes (Health Checks)

| Probe Type | Purpose | When Used |
|------------|---------|-----------|
| **livenessProbe** | Is app alive? If fails → kill & restart container | Detect deadlocks, crashes |
| **readinessProbe** | Is app ready for traffic? If fails → remove from Service endpoints | Startup, maintenance, overload |
| **startupProbe** | Is app started? If fails → kill container (no liveness/readiness until success) | Slow-starting apps |

```yaml
livenessProbe:
  httpGet:
    path: /healthz
    port: 8080
  initialDelaySeconds: 30
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3
```

## Common Patterns

| Pattern | Use Case |
|---------|----------|
| **Single container** | Simple apps, most common |
| **Sidecar** | Helper container (logging, proxy, sync) |
| **Adapter** | Transform output (e.g., format logs for collector) |
| **Ambassador** | Proxy outgoing connections (e.g., DB proxy) |

## Resource Management

```yaml
resources:
  requests:
    memory: "64Mi"    # Guaranteed minimum
    cpu: "250m"       # 0.25 CPU cores
  limits:
    memory: "128Mi"   # Hard limit (OOM kill if exceeded)
    cpu: "500m"       # Throttled if exceeded
```

**QoS Classes:**
- **Guaranteed**: requests = limits for all containers
- **Burstable**: requests < limits, at least one request set
- **BestEffort**: no requests/limits set (lowest priority, first evicted)

## Pod Networking

- Each Pod gets unique **Pod IP** (cluster-scoped)
- Containers in Pod share network namespace → communicate via `localhost:<port>`
- Pods communicate directly via Pod IPs (no NAT)
- **CNI plugin** (Calico, Cilium, Flannel) implements this

## Storage in Pods

| Volume Type | Lifetime | Use Case |
|-------------|----------|----------|
| `emptyDir` | Pod lifetime | Temp data, cache, inter-container sharing |
| `hostPath` | Node lifetime | Node-specific data (use sparingly) |
| `persistentVolumeClaim` | Independent | Persistent data (databases, user uploads) |
| `configMap` / `secret` | Pod lifetime | Configuration, secrets |
| `downwardAPI` | Pod lifetime | Pod metadata (name, IP, labels) |

## Common Commands

```bash
# Create from YAML
kubectl apply -f pod.yaml

# Interactive shell
kubectl exec -it my-pod -- /bin/bash

# View logs
kubectl logs my-pod -c container-name
kubectl logs -f my-pod  # follow

# Describe (events, status)
kubectl describe pod my-pod

# Delete
kubectl delete pod my-pod

# Force delete (stuck terminating)
kubectl delete pod my-pod --grace-period=0 --force

# Port forward (local access)
kubectl port-forward my-pod 8080:80
```

## Best Practices

1. **Don't manage Pods directly** — use Deployment, StatefulSet, DaemonSet, Job, CronJob
2. **One main process per container** — keep containers focused
3. **Set resource requests/limits** — prevents resource starvation
4. **Use labels** — for selection by Services, controllers
5. **Health checks** — always define liveness/readiness probes
6. **Security context** — run as non-root, drop capabilities, read-only rootfs

## References

- [Kubernetes Pods](https://kubernetes.io/docs/concepts/workloads/pods/)
- [Pod Lifecycle](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/)
- [Init Containers](https://kubernetes.io/docs/concepts/workloads/pods/init-containers/)
- [Probes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/)
- [Resource Management](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)