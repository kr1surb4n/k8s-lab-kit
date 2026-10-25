# Decision Tree — Symptom → Command → Cause → Fix

Use this when a pod is unhealthy. Start at the symptom, run the command, read the
output, follow the arrow.

---

```text
POD NOT READY
    │
    ├─► kubectl get pod -n k8s-lab -l app.kubernetes.io/name=web
    │       │
    │       ├─ STATUS = CrashLoopBackOff
    │       │   ├─► kubectl logs -n k8s-lab <pod> --previous
    │       │   │       │
    │       │   │       ├─ "exit 1" / app error → bad command / code bug
    │       │   │       │       └─► Fix image or command, `kubectl rollout undo`
    │       │   │       │
    │       │   │       ├─ "permission denied" / "no such file" → volume/secret mount
    │       │   │       │       └─► Check mountPath, defaultMode, Secret exists
    │       │   │       │
    │       │   │       ├─ "address already in use" → port conflict
    │       │   │       │       └─► Change containerPort or fix existing process
    │       │   │       │
    │       │   │       └─ OOM → memory limit too low
    │       │   │               └─► Increase limits.memory
    │       │   │
    │       ├─ STATUS = ImagePullBackOff / ErrImagePull
    │       │   ├─► kubectl describe pod -n k8s-lab <pod> | grep -A5 Events
    │       │   │       │
    │       │   │       ├─ "repository does not exist" / "manifest unknown" → wrong tag
    │       │   │       │       └─► `kubectl set image deploy/web web=nginx:1.27-alpine`
    │       │   │       │
    │       │   │       ├─ "pull access denied" / "unauthorized" → private registry
    │       │   │       │       └─► Add imagePullSecret, `kubectl create secret docker-registry`
    │       │   │       │
    │       │   │       └─ "rate limit" / "toomanyrequests" → Docker Hub limit
    │       │   │               └─► Use mirror / authenticated pull / local registry
    │       │   │
    │       ├─ STATUS = Pending
    │       │   ├─► kubectl describe pod -n k8s-lab <pod> | grep -A5 Warning
    │       │   │       │
    │       │   │       ├─ "Insufficient cpu/memory" → requests > node capacity
    │       │   │       │       └─► Reduce requests, or add node, or `kubectl rollout undo`
    │       │   │       │
    │       │   │       ├─ "PersistentVolumeClaim is not bound" → PVC issue
    │       │   │       │       └─► Check PVC status, StorageClass exists, `kubectl get pvc`
    │       │   │       │
    │       │   │       ├─ "node(s) didn't match node selector/affinity" → scheduling
    │       │   │       │       └─► Remove nodeSelector / add toleration / label node
    │       │   │       │
    │       │   │       └─ "0/1 nodes are available" → node full / tainted
    │       │   │               └─► `kubectl describe node` / `kubectl cordon/uncordon`
    │       │   │
    │       ├─ STATUS = OOMKilled (exit 137)
    │       │   ├─► kubectl describe pod -n k8s-lab <pod> | grep -A3 "Last State"
    │       │   │       │
    │       │   │       └─ Exit Code 137 → memory limit exceeded
    │       │   │               └─► Increase limits.memory, check for leaks, add livenessProbe
    │       │   │
    │       ├─ STATUS = ContainerCreating (stuck > 1 min)
    │       │   ├─► kubectl describe pod -n k8s-lab <pod> | tail -20
    │       │   │       │
    │       │   │       ├─ "MountVolume.SetUp failed" → volume mount issue
    │       │   │       │       └─► Check PV/PVC, Secret/ConfigMap exists, mountPath
    │       │   │       │
    │       │   │       ├─ "rpc error: code = DeadlineExceeded" → CNI / disk slow
    │       │   │       │       └─► Check CNI pods, `kubectl get pods -n kube-system`
    │       │   │       │
    │       │   │       └─ "FailedCreatePodSandBox" → CNI / runtime issue
    │       │   │               └─► Restart kubelet / CNI pods, reboot node
    │       │   │
    │       └─ STATUS = Running but Readiness failing
    │           ├─► kubectl get pod -n k8s-lab <pod> -o yaml | grep -A10 readinessProbe
    │           │       │
    │           │       ├─ Wrong path/port → fix probe httpGet.path/port
    │           │       │
    │           │       ├─ App not listening yet → increase initialDelaySeconds
    │           │       │
    │           │       └─ App crashes before probe → check CrashLoopBackOff above
    │           │
    └─► If all else fails: `kubectl rollout undo deploy/web -n k8s-lab`
```

---

## Quick Reference Card

| Symptom | First Command | Likely Fix |
|---|---|---|
| CrashLoopBackOff | `kubectl logs --previous` | Fix command / config / memory |
| ImagePullBackOff | `kubectl describe pod \| grep Events` | Fix image tag / add pull secret |
| Pending | `kubectl describe pod \| grep Warning` | Reduce requests / fix PVC / node selector |
| OOMKilled | `kubectl describe pod \| grep "Last State"` | Increase memory limit |
| Readiness fail | `kubectl get pod -o yaml \| grep readinessProbe` | Fix path/port / increase delay |
| No endpoints | `kubectl get endpoints` + `kubectl get svc` | Fix selector / port name |

---

## Runbook Links

- Full method: `recovery/method.md`
- Drill scripts: `scripts/lab-drill.sh crashloop|imagepull|pending|oom --inject|--recover`
- Run all: `make drills`
- Verify after fix: `lab-verify.sh a6`