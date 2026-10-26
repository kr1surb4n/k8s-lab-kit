---
id: doc-01
title: Kubernetes objects used in this kit
section: "Concepts > Objects"
corpus_version: 2026-10-26.1
source:
  kind: authored
  snapshot: 2026-10-26
  based_on:
    - docs/runbooks.md#common-setup
    - README.md
---

A **Pod** is the smallest object Kubernetes schedules. It holds one or more
containers that share a network namespace and any volumes declared by the pod.

A **Deployment** declares the desired number of identical Pods and the strategy
used to replace them. It owns a **ReplicaSet**, and the ReplicaSet owns the Pods.
This chain matters: deleting a Pod does not delete its ReplicaSet, and deleting a
ReplicaSet does not delete its Deployment.

A **Service** gives a stable virtual IP and DNS name to a changing set of Pods.
The set is chosen by label selector, so Pods can be replaced without clients
learning new addresses.

**ConfigMaps** and **Secrets** hold configuration outside the image. A
**PersistentVolumeClaim** requests durable storage for data that must outlive a
Pod.

Every exercise in this kit runs in the **`k8s-lab` namespace**; nothing is
deployed into `default`. The scripts `lab-up.sh`, `lab-down.sh` and
`lab-status.sh` assume that namespace.
