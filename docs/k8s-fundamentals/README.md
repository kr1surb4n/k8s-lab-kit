# Kubernetes Fundamentals — Study Notes (Phase 1)

This directory contains study notes for **Phase 1** of the Kubernetes learning plan: "Na sucho – przestudiowanie 30% dokumentacji do Kubernetesów".

## Files

| # | File | Topic | Plan Reference |
|---|------|-------|----------------|
| 01 | [01-pod.md](01-pod.md) | Pod — atomic unit, lifecycle, probes, resources, networking, storage | Phase 1: "Co to jest Pod?" |
| 02 | [02-service.md](02-service.md) | Service — types, discovery, exposure | Phase 1: "Co to jest Service i jakie ma warianty?" |
| 03 | [03-deployment.md](03-deployment.md) | Deployment — rolling updates, rollbacks, scaling, strategies | Phase 1: "Co to jest Deployment?" |
| 04 | [04-statefulset.md](04-statefulset.md) | StatefulSet — stable identity, per-Pod PVC, ordered ops, headless service | Phase 1: "Co to jest StatefulSet?" |
| 05 | [05-deployment-vs-statefulset.md](05-deployment-vs-statefulset.md) | **Deep comparison** — the "hard question" from the plan | Phase 1: "Czym różni się Deployment od StatefulSet?" |
| 06 | [06-cronjob.md](06-cronjob.md) | CronJob — schedule, concurrency, history, manual execution | Phase 1: "Jaki czas obowiązuje w Cron* i jak uruchamiać ręcznie?" |
| 07 | [07-ingress-exposure.md](07-ingress-exposure.md) | Service exposure — Ingress, LoadBalancer, NodePort, Gateway API, TLS | Phase 1: "Jakie są metody na udostępnienie usługi...?" |

## Learning Order

1. **Pod** — Foundation (everything runs in Pods)
2. **Service** — Networking abstraction (how Pods are reached)
3. **Deployment** — Stateless workload management
4. **StatefulSet** — Stateful workload management
5. **Deployment vs StatefulSet** — Critical comparison (the "hard question")
6. **CronJob** — Scheduled tasks
7. **Ingress/Exposure** — External access patterns

## References

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Kubernetes API Reference](https://kubernetes.io/docs/reference/kubernetes-api/)
- [kubectl Cheat Sheet](https://kubernetes.io/docs/reference/kubectl/cheatsheet/)

## Next Phase

**Phase 2**: Config management — Kustomize + Helm study