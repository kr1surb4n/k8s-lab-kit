# paczki/k8s — what this is

Templates for the `paczek` picker (Coat, `ALT + n`). One file = one starting
point. Files ending in `.tpl` lose the suffix when copied and ask for the
`{{ VARIABLE }}` values first.

## How to use

```bash
# from any empty folder
paczek k8s          # pick one or more templates, they land in $PWD

# without Coat, copy by hand and replace the variables
cp ~/.coat/lib/paczki/k8s/deployment.yaml.tpl ./deployment.yaml
$EDITOR deployment.yaml
```

After installing the kit (`coat/install-coat.sh`) the templates are visible as
`paczek k8s`; without the install they also work from this folder directly:

```bash
PACZEK_FILLINGS="$PWD/paczki" bash -c 'source ~/.coat/modules/spells.sh; paczek k8s'
```

## Rules these templates follow

- One object per file, so `kubectl apply -f .` is predictable.
- `metadata.namespace` is never hard-coded; pass `-n` or set it in
  `kustomization.yaml`.
- `app.kubernetes.io/name` is the one selector label.
- Every template has a comment block saying what to change and what will bite.
- Values that are cluster-specific (StorageClass, LoadBalancer) are variables,
  never guesses.

## Contents

| File | Object | Use when |
|---|---|---|
| `deployment.yaml.tpl` | Deployment | any stateless workload |
| `service.yaml.tpl` | Service | expose a Deployment |
| `configmap.yaml.tpl` | ConfigMap | config file or env values |
| `secret.yaml.tpl` | Secret | demo credentials (stringData) |
| `pvc.yaml.tpl` | PersistentVolumeClaim | keep data after the pod dies |
| `ingress.yaml.tpl` | Ingress | HTTP routing by host/path |
| `values.yaml.tpl` | Helm values | override a chart |
| `kustomization.yaml.tpl` | Kustomization | group manifests, set namespace |
| `cronjob.yaml.tpl` | CronJob | recurring or one-off batch work |
| `statefulset.yaml.tpl` | StatefulSet | stable identity, ordered rollout, PVC per pod |
| `job.yaml.tpl` | Job | run-to-completion (migration, init) |
| `networkpolicy.yaml.tpl` | NetworkPolicy | default-deny, explicit allow |
| `pdb.yaml.tpl` | PodDisruptionBudget | limit voluntary disruptions |
| `rbac.yaml.tpl` | Role + RoleBinding | least-privilege namespace RBAC |
| `hpa.yaml.tpl` | HorizontalPodAutoscaler | scale on CPU / custom metrics |

`_about.md` is this file; `paczek k8s` lists it too, ignore it.
