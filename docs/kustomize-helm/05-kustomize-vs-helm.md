# Kustomize vs Helm — Decision Matrix + Production Patterns

> **Dual Purpose**: Compare both tools for different scenarios + Production-ready decision framework.

---

## The Core Philosophy Difference

| Aspect | Kustomize | Helm |
|--------|-----------|------|
| **Paradigm** | **Overlay/Transform** — Modify existing YAML | **Template** — Generate YAML from templates |
| **Input** | Existing Kubernetes manifests | Template files + values |
| **Output** | Modified manifests | Rendered manifests |
| **Abstraction** | None — raw K8s API | Charts abstract complexity |
| **Learning Curve** | Low (pure YAML) | Medium (Go templates + Sprig) |
| **Customization** | Patches, transformers, generators | Values files, conditionals, loops |

---

## When to Use Kustomize

### ✅ Best For

| Scenario | Why |
|----------|-----|
| **Environment-specific configs** (dev/staging/prod) | Native overlays pattern |
| **Patching upstream manifests** | No forking needed |
| **GitOps with ArgoCD/Flux** | Native integration |
| **Simple customizations** | Labels, annotations, replicas, images |
| **Multi-cluster deployments** | Cluster-specific overlays |
| **No templating needed** | Pure YAML, no logic |
| **Validating raw manifests** | `kustomize build \| kubeval` |

### ❌ Avoid When

| Scenario | Better Alternative |
|----------|-------------------|
| **Complex conditional logic** | Helm templates |
| **Repeating similar resources** | Helm loops |
| **Packaging for distribution** | Helm charts |
| **Complex value transformations** | Helm Sprig functions |
| **Chart dependencies** | Helm dependencies |

---

## When to Use Helm

### ✅ Best For

| Scenario | Why |
|----------|-----|
| **Packaging applications** | Chart format + versioning |
| **Distributing to users** | Repo/OCI registry |
| **Complex conditionals** | Go templates + Sprig |
| **Repeating resources** | `range` loops in templates |
| **Chart dependencies** | Subcharts with conditions |
| **Release management** | Install/upgrade/rollback |
| **User-facing configuration** | Values files as API |

### ❌ Avoid When

| Scenario | Better Alternative |
|----------|-------------------|
| **Simple env overlays** | Kustomize |
| **Patching CRDs/operators** | Kustomize patches |
| **No templating needed** | Kustomize |
| **Validating raw YAML** | Kustomize |

---

## Decision Matrix

### Choose Kustomize If:

```
☐ You have existing K8s manifests to customize
☐ You need dev/staging/prod overlays
☐ You use ArgoCD/Flux for GitOps
☐ Customizations are simple (replicas, images, labels)
☐ You want to validate raw YAML before apply
☐ Team knows YAML but not Go templates
```

### Choose Helm If:

```
☐ You're packaging an app for distribution
☐ You need complex conditionals/loops
☐ You have chart dependencies (PostgreSQL, Redis, etc.)
☐ You need release management (rollback, history)
☐ Users configure via values.yaml
☐ You need hooks (pre-install, post-upgrade)
☐ You publish to Helm/OCI registries
```

### Choose Both If:

```
☐ Package with Helm → customize with Kustomize
☐ Helm for packaging, Kustomize for env overlays
☐ Helm for dependencies, Kustomize for platform config
☐ Helm charts as "base" → Kustomize for platform hardening
```

---

## Production Pattern: Helm + Kustomize Together

### Recommended Architecture

```
my-platform/
├── charts/                          # Helm charts (packaging)
│   ├── my-app/
│   │   ├── Chart.yaml
│   │   ├── values.yaml
│   │   ├── values-dev.yaml
│   │   ├── values-staging.yaml
│   │   ├── values-prod.yaml
│   │   └── templates/
│   ├── postgresql/                  # Or use Bitnami
│   └── redis/
├── kustomize/                       # Kustomize (platform config)
│   ├── base/                        # Platform-wide base
│   │   ├── kustomization.yaml
│   │   ├── networkpolicy.yaml       # Default deny
│   │   ├── servicemonitor.yaml      # Monitoring defaults
│   │   ├── pdb.yaml                 # PDB defaults
│   │   └── hpa.yaml                 # HPA defaults
│   ├── overlays/
│   │   ├── dev/
│   │   │   ├── kustomization.yaml
│   │   │   └── patches/
│   │   ├── staging/
│   │   │   ├── kustomization.yaml
│   │   │   └── patches/
│   │   └── prod/
│   │       ├── kustomization.yaml
│   │       └── patches/
│   └── validators/
│       └── required-labels.yaml
├── deploy.sh                        # Deployment script
└── Makefile
```

### Workflow

```bash
# 1. Render Helm charts to temporary directory
helm template my-platform ./charts/my-platform \
  --namespace my-platform-prod \
  --values ./charts/my-platform/values-prod.yaml \
  --output-dir /tmp/rendered

# 2. Apply Kustomize overlay on top
cd kustomize/overlays/prod
kustomize build . --load-restrictor=LoadRestrictionsNone \
  | kubectl apply -f -

# Or use Helm post-renderer:
helm template my-platform ./charts/my-platform \
  --post-renderer ./kustomize-post-renderer.sh \
  --namespace my-platform-prod \
  --values values-prod.yaml | kubectl apply -f -
```

### Kustomize Post-Renderer Script

```bash
#!/bin/bash
# kustomize-post-renderer.sh
# stdin: Helm rendered manifests
# stdout: Kustomized manifests

cat <&0 | kustomize build kustomize/overlays/prod
```

---

## Production Boilerplate: Combined Chart + Kustomize

### `charts/my-platform/Chart.yaml`

```yaml
apiVersion: v2
name: my-platform
description: Complete platform stack
type: application
version: 1.0.0
appVersion: "1.0.0"
kubeVersion: ">=1.25.0-0"
dependencies:
  - name: my-app
    version: "1.x.x"
    repository: "file://../my-app"
    condition: my-app.enabled
  - name: postgresql
    version: "12.x.x"
    repository: "https://charts.bitnami.com/bitnami"
    condition: postgresql.enabled
  - name: redis
    version: "18.x.x"
    repository: "https://charts.bitnami.com/bitnami"
    condition: redis.enabled
```

### `charts/my-platform/values-prod.yaml`

```yaml
global:
  platformName: my-platform
  environment: production
  domain: example.com

my-app:
  enabled: true
  replicaCount: 5
  image:
    repository: my-app
    tag: "v2.0.0"
    digest: sha256:abc123...
  autoscaling:
    enabled: true
    minReplicas: 5
    maxReplicas: 50

postgresql:
  enabled: true
  auth:
    username: myapp
    password: ""
    database: myapp
  primary:
    persistence:
      size: 50Gi
      storageClass: fast-ssd

redis:
  enabled: true
  auth:
    enabled: true
    password: ""
  master:
    persistence:
      size: 10Gi
```

### `kustomize/base/kustomization.yaml` — Platform Hardening

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

# Resources rendered from Helm charts
resources:
  - ../../charts/my-app/templates/deployment.yaml
  - ../../charts/my-app/templates/service.yaml
  - ../../charts/my-app/templates/configmap.yaml
  - ../../charts/my-app/templates/servicemonitor.yaml
  - ../../charts/postgresql/templates/statefulset.yaml
  - ../../charts/postgresql/templates/service.yaml
  - ../../charts/redis/templates/statefulset.yaml
  - ../../charts/redis/templates/service.yaml

# Platform-wide hardening (applied to ALL resources)
commonLabels:
  platform.example.com/managed-by: "helm+kustomize"
  platform.example.com/environment: "production"
  cost-center: engineering

commonAnnotations:
  gitops.example.com/managed-by: "kustomize"
  gitops.example.com/sync-wave: "10"

# Security hardening patches
patches:
  # Drop capabilities on ALL containers
  - patch: |-
      - op: add
        path: /spec/template/spec/containers/0/securityContext/capabilities/drop
        value: ["ALL"]
    target:
      kind: Deployment
  - patch: |-
      - op: add
        path: /spec/template/spec/containers/0/securityContext/readOnlyRootFilesystem
        value: true
    target:
      kind: Deployment
  - patch: |-
      - op: add
        path: /spec/template/spec/containers/0/securityContext/allowPrivilegeEscalation
        value: false
    target:
      kind: Deployment
  - patch: |-
      - op: add
        path: /spec/template/spec/containers/0/securityContext/runAsNonRoot
        value: true
    target:
      kind: Deployment
  - patch: |-
      - op: add
        path: /spec/template/spec/containers/0/securityContext/runAsUser
        value: 1000
    target:
      kind: Deployment
  - patch: |-
      - op: add
        path: /spec/template/spec/containers/0/securityContext/runAsGroup
        value: 1000
    target:
      kind: Deployment

# Network policies (default deny)
resources:
  - networkpolicy.yaml

# Monitoring defaults
resources:
  - servicemonitor.yaml

# PDB defaults
resources:
  - pdb.yaml

# HPA defaults
resources:
  - hpa.yaml

# Validators
validators:
  - ./validators/required-labels.yaml
```

### `kustomize/overlays/prod/kustomization.yaml`

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - ../../base

namespace: my-platform-prod

namePrefix: prod-

images:
  - name: my-app
    newTag: "v2.0.0"
    digest: sha256:abc123...

commonLabels:
  environment: production

# Production resource overrides
patches:
  - path: patches/replicas.yaml
  - path: patches/resources.yaml

# Production-only resources
resources:
  - ../../base
  - prod-only.yaml
```

---

## Comparison: Feature by Feature

| Feature | Kustomize | Helm | Winner |
|---------|-----------|------|--------|
| **Environment overlays** | Native (bases/overlays) | Values files | Kustomize |
| **Conditionals** | Limited (patches) | Full Go templates | Helm |
| **Loops** | No | `range` in templates | Helm |
| **Chart packaging** | No | Native | Helm |
| **Dependencies** | Manual | Native (subcharts) | Helm |
| **Release management** | No | Native (history, rollback) | Helm |
| **Hooks** | No | Native | Helm |
| **GitOps (ArgoCD/Flux)** | Native | Via helm plugin | Kustomize |
| **Validation** | `kustomize build \| kubeval` | `helm lint`, schema | Tie |
| **DRY (Don't Repeat Yourself)** | Bases + patches | Templates + values | Tie |
| **Learning curve** | Low (YAML) | Medium (templates) | Kustomize |
| **Debugging** | `kustomize build` | `helm template` | Tie |

---

## Production Decision Framework

### For Each Component, Ask:

```
1. Is this a reusable application package?
   → YES: Helm chart
   → NO: Continue

2. Does it need complex conditionals/loops?
   → YES: Helm
   → NO: Continue

3. Does it need release management (rollback)?
   → YES: Helm
   → NO: Continue

4. Is it platform-wide config (policies, monitoring, networking)?
   → YES: Kustomize base + overlays
   → NO: Continue

5. Is it environment-specific customization?
   → YES: Kustomize overlay
   → NO: Plain manifests
```

### Component Classification Example

| Component | Tool | Reason |
|-----------|------|--------|
| My Application | Helm | Packaging, deps, release mgmt |
| PostgreSQL | Helm (Bitnami) | Complex, mature chart |
| Redis | Helm (Bitnami) | Complex, mature chart |
| Ingress NGINX | Helm | Complex, mature chart |
| Platform NetworkPolicies | Kustomize | Platform-wide, patches |
| Platform ServiceMonitors | Kustomize | Platform-wide, patches |
| Platform PDBs | Kustomize | Platform-wide, patches |
| Platform HBAs | Kustomize | Platform-wide, patches |
| Dev environment config | Kustomize overlay | Env-specific |
| Prod environment config | Kustomize overlay | Env-specific |
| Staging environment config | Kustomize overlay | Env-specific |

---

## Migration Path: From One to Both

### If You Have Helm Only → Add Kustomize

```bash
# 1. Keep Helm charts for packaging
# 2. Render to base/
helm template my-app ./charts/my-app --output-dir ./kustomize/base

# 2. Create base/kustomization.yaml
# 3. Move env-specific values to overlays/
# 4. Use Kustomize for platform hardening
```

### If You Have Kustomize Only → Add Helm

```bash
# 1. Extract common patterns into Helm chart
# 2. Create Chart.yaml + templates/
# 3. Move env-specific to values-dev.yaml/values-prod.yaml
# 4. Use Kustomize for platform-wide policies
```

---

## Production Hardening: Combined Approach

| Layer | Tool | Responsibility |
|-------|------|----------------|
| **Application Packaging** | Helm | Chart, deps, release, hooks |
| **Platform Policies** | Kustomize | NetworkPolicy, PDB, HPA, ServiceMonitor |
| **Security Hardening** | Kustomize | Patches for securityContext, capabilities |
| **Environment Config** | Kustomize | Overlays (dev/staging/prod) |
| **Image Management** | Both | Helm: default tags; Kustomize: prod digests |
| **Secrets** | Helm + ExternalSecrets | Helm: template; ExternalSecrets: inject |

---

## Decision Checklist for New Projects

```markdown
# New Project Decision

## Application Type
- [ ] Microservice → Helm chart
- [ ] Platform service → Helm chart + Kustomize base
- [ ] Infrastructure (DB, cache) → Upstream Helm chart
- [ ] Policy/Config → Kustomize only

## Distribution
- [ ] Internal only → Kustomize sufficient
- [ ] Shared across teams → Helm chart
- [ ] Open source / public → Helm chart + OCI registry

## Team Skills
- [ ] Strong Go template skills → Helm
- [ ] YAML-only preference → Kustomize
- [ ] Mixed → Both (Helm for apps, Kustomize for platform)

## GitOps
- [ ] ArgoCD/Flux → Both work, Kustomize native
- [ ] Custom GitOps → Helm releases tracked

## Complexity
- [ ] Simple (1-3 resources) → Kustomize
- [ ] Medium (5-15 resources) → Helm
- [ ] Complex (20+ resources, deps) → Helm + Kustomize
```

---

## Key Takeaways

1. **Not mutually exclusive** — Best production setups use both
2. **Helm for packaging** — Charts, dependencies, releases, hooks
3. **Kustomize for platform** — Policies, hardening, env overlays
4. **ArgoCD/Flux** — Works with both, but Kustomize is native
4. **Validation** — Both support `kubeval` / schema validation
5. **Security** — Kustomize patches excel at platform-wide hardening

---

## Quick Reference: Which Tool for What

| Task | Tool | Command |
|------|------|---------|
| Create new app package | Helm | `helm create my-app` |
| Add PostgreSQL dependency | Helm | Edit Chart.yaml |
| Patch securityContext on all deployments | Kustomize | `patches` in base |
| Create dev/staging/prod envs | Kustomize | `overlays/` |
| Rollback failed release | Helm | `helm rollback` |
| Validate manifests pre-apply | Both | `helm lint` / `kustomize build \| kubeval` |
| Distribute to other teams | Helm | `helm package` + OCI registry |
| Run DB migration before deploy | Helm | `pre-install` hook |
| Apply platform-wide NetworkPolicy | Kustomize | `resources: networkpolicy.yaml` |

---

## References

- [Kustomize vs Helm](https://www.cncf.io/blog/2020/01/14/helm-and-kustomize/)
- [Using Helm with Kustomize](https://helm.sh/docs/topics/kustomize/)
- [ArgoCD: Helm vs Kustomize](https://argo-cd.readthedocs.io/en/stable/user-guide/helm_vs_kustomize/)
- [Google: Kustomize vs Helm](https://cloud.google.com/blog/products/containers-kubernetes/kustomize-vs-helm-template-free-customization)

---

> **Next**: [06-combined-workflows.md](06-combined-workflows.md) — Production deployment pipelines with both tools