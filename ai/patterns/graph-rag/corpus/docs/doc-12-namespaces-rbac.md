---
id: doc-12
title: Namespaces, service accounts, and RBAC
section: "Concepts > Cluster > Namespaces and RBAC"
corpus_version: 2026-10-26.1
source:
  kind: authored
  snapshot: 2026-10-26
  based_on:
    - docs/runbooks.md#common-setup
    - scripts/lab-up.sh
    - ai/patterns/graph-rag/k8s/rbac.yaml
---

A **Namespace** scopes names, quotas, and role bindings. The same Deployment name
can exist in two namespaces without collision. Deleting a namespace deletes
everything inside it, including PersistentVolumeClaims.

This kit uses **`k8s-lab`** for every exercise and never deploys into `default`.
The lab, observability, and graph-rag stacks each get their own namespace so that
`kubectl get pods -A` stays readable and cleanup is one command.

A **ServiceAccount** is the identity a Pod uses when it talks to the API server.
A **Role** lists verbs on resources inside one namespace; a **RoleBinding**
attaches it to a subject. A **ClusterRole** and **ClusterRoleBinding** apply
cluster-wide and should be reserved for controllers and operators.

The graph-rag Deployment runs with its own ServiceAccount and a minimal Role: it
reads ConfigMaps and Secrets in its namespace and writes nothing. It does not
mount the default token unless the app needs the API at all.

Most workloads in this kit need no API permissions. If a Pod can read every
Secret in its namespace, that is a permission bug, not a feature.
