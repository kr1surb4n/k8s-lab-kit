# Recovery Method — Observe → Contain → Diagnose → Recover → Prevent

This is the one-page runbook for every drill. Follow the steps in order; skip
nothing. The goal is not just to fix the symptom, but to leave the system more
resilient than before.

---

## 1. Observe (what do I see?)

```bash
# Cluster health
kubectl get nodes -o wide
kubectl get pods -A --field-selector=status.phase!=Running

# The broken workload
kubectl get all -n k8s-lab
kubectl describe pod -n k8s-lab -l app.kubernetes.io/name=web
kubectl logs -n k8s-lab -l app.kubernetes.io/name=web --previous

# Events (most recent first)
kubectl get events -n k8s-lab --sort-by=.lastTimestamp
```

**Questions to answer:**
- Which pod(s) are failing?
- What is the exact error message?
- When did it start? (correlate with a deploy, config change, node issue)
- Is it one pod or all replicas?

---

## 2. Contain (stop the bleeding)

```bash
# If a runaway pod is consuming resources / flapping:
kubectl scale deploy/web -n k8s-lab --replicas=0

# If a bad rollout is in progress:
kubectl rollout undo deploy/web -n k8s-lab

# If a node is unhealthy:
kubectl cordon <node-name>
kubectl drain <node-name> --ignore-daemonsets --delete-emptydir-data
```

**Do not delete the pod yet** — its logs and state are evidence.

---

## 3. Diagnose (why did it happen?)

| Symptom | First check | Common causes |
|---|---|---|
| `CrashLoopBackOff` | `kubectl logs --previous` | App crash on start, missing config, port conflict, permission denied |
| `ImagePullBackOff` | `kubectl describe pod` → Events | Wrong image tag, no pull secret, rate limit, registry down |
| `Pending` (unschedulable) | `kubectl describe pod` → Events | Resource requests > node capacity, nodeSelector/taint mismatch, PVC unbound |
| `OOMKilled` (exit 137) | `kubectl describe pod` → Containers → Last State | Memory limit too low, memory leak, no limit set (node OOM) |
| `Readiness probe failing` | `kubectl logs` + probe path | App not listening on probe port, slow startup, wrong path |
| `Service has no endpoints` | `kubectl get endpoints` + label match | Selector mismatch, pods not Ready, wrong port name |

**Command to run for each:**
```bash
# CrashLoopBackOff
kubectl logs -n k8s-lab -l app.kubernetes.io/name=web --previous | tail -50

# ImagePullBackOff
kubectl describe pod -n k8s-lab -l app.kubernetes.io/name=web | grep -A10 Events

# Pending
kubectl describe pod -n k8s-lab -l app.kubernetes.io/name=web | grep -A5 "Warning"

# OOMKilled
kubectl describe pod -n k8s-lab -l app.kubernetes.io/name=web | grep -A3 "Last State"

# Readiness
kubectl get pod -n k8s-lab -l app.kubernetes.io/name=web -o yaml | grep -A10 readinessProbe
```

---

## 4. Recover (fix it)

| Cause | Fix | Verify |
|---|---|---|
| Missing ConfigMap/Secret | `kubectl apply -f manifests/<scenario>/` | `lab-verify.sh <scenario>` |
| Wrong image tag | `kubectl set image deploy/web web=nginx:1.27-alpine -n k8s-lab` | `kubectl rollout status` |
| Resources too low | Edit manifest: increase `resources.limits.memory` | `kubectl top pod` |
| Probe path wrong | Fix `readinessProbe.httpGet.path` | `kubectl get pod` → Ready |
| Selector mismatch | Align Service `selector` with Deployment `labels` | `kubectl get endpoints` |
| PVC unbound | Check StorageClass exists, `kubectl get pvc` | `Bound` |

**After any fix:**
```bash
kubectl rollout status deploy/web -n k8s-lab --timeout=120s
lab-verify.sh a6
```

---

## 5. Prevent (make it not happen again)

| Action | Where |
|---|---|
| Add/fix resource requests & limits | Manifest `resources:` block |
| Add/fix readiness + liveness probes | Manifest `probes:` block |
| Add PodDisruptionBudget | `paczki/k8s/pdb.yaml.tpl` |
| Add NetworkPolicy | `paczki/k8s/networkpolicy.yaml.tpl` |
| Pin image tags (no `latest`) | Manifest `image: nginx:1.27-alpine` |
| Document the failure in runbook | `docs/runbooks.md` §T1 |
| Add alert rule | `observability/alerts/lab-rules.yaml` |

**Checklist after every recovery:**
- [ ] Root cause written in `docs/runbooks.md`
- [ ] Manifest fixed and committed
- [ ] `make check` passes
- [ ] `make test` passes
- [ ] Drill script added/updated for this failure mode

---

## Quick reference: the four T1 drills

| Drill | Inject command | Expected state | Recover command |
|---|---|---|---|
| CrashLoopBackOff | `kubectl set env deploy/web BAD=1 -n k8s-lab` | `CrashLoopBackOff` | `kubectl rollout undo deploy/web -n k8s-lab` |
| ImagePullBackOff | `kubectl set image deploy/web web=nginx:does-not-exist -n k8s-lab` | `ImagePullBackOff` | `kubectl set image deploy/web web=nginx:1.27-alpine -n k8s-lab` |
| Pending | `kubectl patch deploy web -n k8s-lab -p '{"spec":{"template":{"spec":{"containers":[{"name":"web","resources":{"requests":{"cpu":"100","memory":"20Gi"}}]}}}}'` | `Pending` (unschedulable) | `kubectl rollout undo deploy/web -n k8s-lab` |
| OOMKilled | `kubectl patch deploy web -n k8s-lab -p '{"spec":{"template":{"spec":{"containers":[{"name":"web","resources":{"limits":{"memory":"1Mi"}}]}}}}'` | `OOMKilled` (exit 137) | `kubectl rollout undo deploy/web -n k8s-lab` |

**Each drill:** run inject → verify state → run recover → `lab-verify.sh a6` → green.