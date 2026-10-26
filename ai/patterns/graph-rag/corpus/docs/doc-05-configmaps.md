---
id: doc-05
title: ConfigMaps as files and as environment variables
section: "Concepts > Configuration > ConfigMaps"
corpus_version: 2026-10-26.1
source:
  kind: authored
  snapshot: 2026-10-26
  based_on:
    - docs/runbooks.md#a2
    - docs/runbooks.md#a5
    - manifests/a2/web.yaml
---

A ConfigMap stores UTF-8 key/value data. Its total data is capped at 1 MiB, so a
binary file or a large asset belongs on a volume, not in a ConfigMap.

There are two ways to consume one, and they behave differently:

- **Directory mount**: every key becomes a file. The kubelet syncs the projected
  volume periodically, so an edit appears in the running Pod after roughly 30–60
  seconds, with no restart. A2 uses this for `index.html` and `style.css`.
- **Environment variables** (`envFrom` or `configMapKeyRef`): values are fixed
  when the container starts. Editing the ConfigMap has no effect until the Pod is
  recreated.

A `subPath` mount defeats the update: it becomes a bind mount of a single file and
never sees later ConfigMap changes.

A5 mounts two ConfigMaps as directories: one holds the nginx server block, the
other the page. Both stay editable without a restart.

Secrets use the same mechanics. The difference is handling: a Secret is excluded
from routine dumps and can be mounted with restrictive permissions.
