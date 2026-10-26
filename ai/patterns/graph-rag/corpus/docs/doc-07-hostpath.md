---
id: doc-07
title: hostPath volumes and the minikube mount
section: "Concepts > Storage > hostPath"
corpus_version: 2026-10-26.1
source:
  kind: authored
  snapshot: 2026-10-26
  based_on:
    - docs/runbooks.md#a1
    - manifests/a1/web.yaml
    - manifests/a7/app.yaml
---

A **hostPath** volume binds a directory on the node into a Pod. It is the
simplest way to make host files visible in a container, and it is the mechanism
behind A1 and A7.

With minikube, the node is a container, so the host directory must first be
mounted into the node:

```bash
minikube mount "$PWD:/mnt/lab"
```

That is a foreground process. `scripts/lab-up.sh a1 --mount` starts it detached
and records the pid. When the mount stops, the Pods keep running but no longer
see host changes.

A1 mounts `/mnt/lab/site` read-only at `/usr/share/nginx/html`. The content is
not in the image, so editing `site/index.html` on the host changes the page on
the next request, with no restart and no rebuild. The volume type is `Directory`,
which requires the path to exist on the node.

A7 uses the same mount at `/mnt/lab/app`. hostPath is a single-node demo
mechanism: it does not follow a Pod to another node, and it should not be used
for data that must survive the node.
