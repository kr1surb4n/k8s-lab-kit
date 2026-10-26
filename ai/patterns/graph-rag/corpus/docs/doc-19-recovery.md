---
id: doc-19
title: Recovery drills and the evidence rule
section: "Operations > Recovery"
corpus_version: 2026-10-26.1
source:
  kind: authored
  snapshot: 2026-10-26
  based_on:
    - recovery/method.md
    - recovery/decision-tree.md
    - docs/runbooks.md#t1
---

The recovery method is five steps in order: **Observe, Contain, Diagnose,
Recover, Prevent**.

Observing means `kubectl get pods -A`, `describe`, `logs --previous`, and sorted
events. Containing means scaling to zero, undoing a rollout, or cordoning and
draining a node; the failing Pod is not deleted yet, because its logs and state
are evidence. Diagnosing uses the symptom table: CrashLoopBackOff, ImagePullBackOff,
Pending, OOMKilled, failing readiness, or a Service with no endpoints.

A **backup that has never been restored is decoration**, so every backup change
comes with a restore drill and a measured recovery time. The drills under
`recovery/` are deliberately destructive: they delete a Pod, delete a Deployment,
drain a node, or break a probe, and then require the operator to explain what
recovered automatically and what did not.

Deleting a Pod managed by a Deployment is not an outage; the ReplicaSet replaces
it. Deleting the Deployment is an outage, and deleting the namespace also
destroys its PVCs. Those three actions look similar in the shell and have very
different consequences.
