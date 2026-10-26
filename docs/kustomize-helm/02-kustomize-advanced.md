# Kustomize Advanced — Study Notes + Production Boilerplate

> **Dual Purpose**: Deep dive into advanced Kustomize features + Production boilerplate patterns.

---

## Study: Advanced Transformers

### 1. Label/Annotation Transformers

Apply labels/annotations to **all** resources globally:

```yaml
# In kustomization.yaml
labels:
  - includeSelectors: true
    pairs:
      app.kubernetes.io/managed-by: kustomize
      app.kubernetes.io/part-of: my-platform
      cost-center: engineering
    includeTemplates: true  # Apply to generated ConfigMaps/Secrets too

annotations:
  - includeSelectors: true
    pairs:
      gitops.example.com/managed-by: "kustomize"
      gitops.example.com/sync-wave: "10"
    includeTemplates: true
```

### 2. Name Prefix/Suffix

```yaml
namePrefix: prod-
# nameSuffix: -v1

# Result: deployment "my-app" → "prod-my-app"
# Works with namePrefix + namespace for full isolation
```

### 3. Namespace Transformer

```yaml
namespace: my-app-prod
# Adds namespace to all namespaced resources
# Cluster-scoped resources (ClusterRole, PV, etc.) unchanged
```

### 4. Image Transformer (Beyond Basics)

```yaml
images:
  - name: my-app
    newName: registry.example.com/my-app
    newTag: v1.2.3
    digest: sha256:abc123...
  - name: postgres
    newTag: 15-alpine
  - name: redis
    newName: my-registry/redis
    newTag: 7-alpine
```

**Advanced**: Use `newName` for registry migration, `digest` for immutable deployments.

### 5. Replacement Transformer (Cross-Resource References)

Inject values from one resource into another:

```yaml
replacements:
  # Inject ConfigMap checksum into Deployment annotation
  - source:
      kind: ConfigMap
      name: my-app-config
      fieldPath: data.CONFIG_CHECKSUM
    targets:
      - select:
          kind: Deployment
          name: my-app
        fieldPaths:
          - spec.template.metadata.annotations.checksum/config

  # Inject Secret checksum
  - source:
      kind: Secret
      name: my-app-secrets
      fieldPath: data.SECRETS_CHECKSUM
    targets:
      - select:
          kind: Deployment
          name: my-app
        fieldPaths:
          - spec.template.metadata.annotations.checksum/secrets

  # Inject Service name into ConfigMap
  - source:
      kind: Service
      name: my-app
      fieldPath: metadata.name
    targets:
      - select:
          kind: ConfigMap
          name: my-app-config
        fieldPaths:
          - data.SERVICE_NAME

  # Inject Namespace into resources
  - source:
      kind: Namespace
      name: my-namespace
      fieldPath: metadata.name
    targets:
      - select:
          kind: Deployment
        fieldPaths:
          - spec.template.spec.containers[0].env[0].value
        options:
          create: true
```

### 6. Variable Reference (Kustomize 4.5+)

Define variables once, use everywhere:

```yaml
vars:
  - name: APP_NAME
    objref:
      kind: Deployment
      name: my-app
      apiVersion: apps/v1
    fieldref:
      fieldpath: metadata.name
  - name: NAMESPACE
    objref:
      kind: Namespace
      name: my-namespace
      apiVersion: v1
    fieldref:
      fieldpath: metadata.name

# Use in patches with $(VAR_NAME)
patches:
  - patch: |-
      - op: add
        path: /spec/template/spec/containers/0/env/-
        value:
          name: APP_NAME
          value: $(APP_NAME)
    target:
      kind: Deployment
      name: my-app
```

---

## Study: ConfigMap/Secret Generators (Advanced)

### ConfigMapGenerator Options

```yaml
configMapGenerator:
  - name: app-config
    behavior: merge           # merge | replace (default: replace)
    files:
      - config.yaml=config/app.yaml
      - nginx.conf=config/nginx.conf
    literals:
      - LOG_LEVEL=info
      - FEATURE_FLAG=true
    envs:
      - config/.env           # Load from .env file
    options:
      disableNameSuffixHash: true    # Stable name (no hash suffix)
      labels:
        app.kubernetes.io/component: config
      annotations:
        gitops.example.com/sync: "true"
      disableNameSuffixHash: true
```

### SecretGenerator Options

```yaml
secretGenerator:
  - name: app-secrets
    behavior: merge
    type: Opaque              # Opaque | kubernetes.io/tls | kubernetes.io/dockerconfigjson
    files:
      - tls.crt=certs/tls.crt
      - tls.key=certs/tls.key
    literals:
      - DB_PASSWORD=changeme
    envs:
      - secrets/.env
    options:
      disableNameSuffixHash: true
      labels:
        app.kubernetes.io/component: secrets
      annotations:
        gitops.example.com/sync: "true"
```

### Generator Behavior: `merge` vs `replace`

| Behavior | Use Case |
|----------|----------|
| `replace` (default) | Overlay completely replaces base generator |
| `merge` | Overlay adds/updates literals/files, keeps base ones |

---

## Study: Patches (Advanced)

### 1. Strategic Merge Patch (Native Kubernetes)

```yaml
patches:
  - path: patches/deployment-replicas.yaml
    target:
      kind: Deployment
      name: my-app
```

```yaml
# patches/deployment-replicas.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
spec:
  replicas: 5
  template:
    spec:
      containers:
        - name: my-app
          resources:
            limits:
              memory: "2Gi"
```

### 2. JSON Patch (RFC 6902) — Surgical Precision

```yaml
patches:
  - patch: |-
      - op: replace
        path: /spec/replicas
        value: 10
      - op: add
        path: /spec/template/spec/containers/0/env/-
        value:
          name: NEW_FEATURE
          value: "enabled"
      - op: remove
        path: /spec/template/spec/containers/0/env/1
    target:
      kind: Deployment
      name: my-app
```

**JSON Patch Operations**: `add`, `remove`, `replace`, `move`, `copy`, `test`

### 3. Inline Patch (No External File)

```yaml
patches:
  - patch: |-
      - op: replace
        path: /spec/template/spec/containers/0/resources/limits/memory
        value: "4Gi"
    target:
      kind: Deployment
      name: my-app
```

### 3. Target Selectors (Multiple Resources)

```yaml
patches:
  - patch: |-
      - op: add
        path: /metadata/labels/app.kubernetes.io/managed-by
        value: kustomize
    target:
      kind: Deployment
    # Applies to ALL Deployments!
  - patch: |-
      - op: add
        path: /metadata/annotations/prometheus.io/scrape
        value: "true"
    target:
      kind: Service
      labelSelector: "app.kubernetes.io/name=my-app"
```

---

## Production Boilerplate: Advanced Transformers

### `base/kustomization.yaml` — Full Transformer Set

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - deployment.yaml
  - service.yaml
  - configmap.yaml
  - servicemonitor.yaml
  - networkpolicy.yaml
  - pdb.yaml
  - hpa.yaml

# === COMMON TRANSFORMERS ===

# Labels applied to ALL resources (including generated)
labels:
  - includeSelectors: true
    pairs:
      app.kubernetes.io/managed-by: kustomize
      app.kubernetes.io/part-of: my-platform
      cost-center: engineering
      security.tier: standard
    includeTemplates: true

annotations:
  - includeSelectors: true
    pairs:
      gitops.example.com/managed-by: "kustomize"
      gitops.example.com/sync-wave: "10"
      gitops.example.com/sync-prune: "true"
    includeTemplates: true

# Name prefix (set in overlay)
# namePrefix: prod-

# Namespace (set in overlay)
# namespace: my-app-prod

# Images (set in overlay)
images:
  - name: my-app
    newTag: "latest"

# === CONFIGMAP GENERATOR ===
configMapGenerator:
  - name: app-config
    behavior: merge
    literals:
      - LOG_LEVEL=info
      - LOG_FORMAT=json
      - METRICS_ENABLED=true
      - HEALTH_CHECK_PATH=/healthz
      - READINESS_PATH=/ready
    options:
      disableNameSuffixHash: true
      labels:
        app.kubernetes.io/component: config

# === SECRET GENERATOR (TEMPLATE) ===
secretGenerator:
  - name: app-secrets
    behavior: merge
    type: Opaque
    literals:
      - DB_PASSWORD=CHANGEME_VIA_EXTERNAL_SECRETS
      - JWT_SECRET=CHANGEME_VIA_EXTERNAL_SECRETS
      - API_KEY=CHANGEME_VIA_EXTERNAL_SECRETS
    options:
      disableNameSuffixHash: true
      labels:
        app.kubernetes.io/component: secrets

# === REPLACEMENTS (Checksum Injection) ===
replacements:
  # Inject ConfigMap checksum into Deployment annotation
  - source:
      kind: ConfigMap
      name: app-config
      fieldPath: data.CONFIG_CHECKSUM
    targets:
      - select:
          kind: Deployment
          name: my-app
        fieldPaths:
          - spec.template.metadata.annotations.checksum/config

  # Inject Secret checksum
  - source:
      kind: Secret
      name: app-secrets
      fieldPath: data.SECRETS_CHECKSUM
    targets:
      - select:
          kind: Deployment
          name: my-app
        fieldPaths:
          - spec.template.metadata.annotations.checksum/secrets

  # Inject Service name into ConfigMap
  - source:
      kind: Service
      name: my-app
      fieldPath: metadata.name
    targets:
      - select:
          kind: ConfigMap
          name: app-config
        fieldPaths:
          - data.SERVICE_NAME

# === VARIABLES (Kustomize 4.5+) ===
vars:
  - name: APP_NAME
    objref:
      kind: Deployment
      name: my-app
      apiVersion: apps/v1
    fieldref:
      fieldpath: metadata.name
  - name: SERVICE_NAME
    objref:
      kind: Service
      name: my-app
      apiVersion: v1
    fieldref:
      fieldpath: metadata.name

# === PATCHES ===
patches:
  # Replicas (overridden in overlay)
  - path: patches/replicas.yaml
    target:
      kind: Deployment
      name: my-app

  # Resources (overridden in overlay)
  - path: patches/resources.yaml
    target:
      kind: Deployment
      name: my-app

  # Security hardening (overridden in overlay)
  - path: patches/security.yaml
    target:
      kind: Deployment
      name: my-app

  # Global label patch (applies to all Deployments)
  - patch: |-
      - op: add
        path: /metadata/labels/app.kubernetes.io/managed-by
        value: kustomize
    target:
      kind: Deployment

# === VALIDATORS (see below) ===
# validators:
#   - ./validators/required-labels.yaml
```

---

## Study: Validators (Kustomize 5.0+)

Validate manifests **before** they hit the cluster:

### Custom Validator

```yaml
# validators/required-labels.yaml
apiVersion: kustomize.config.k8s.io/v1alpha1
kind: Validator
metadata:
  name: required-labels
spec:
  rules:
    - name: require-app-label
      message: "All resources must have app.kubernetes.io/name label"
      condition: |
        has(object.metadata.labels["app.kubernetes.io/name"])
    - name: require-version-label
      message: "All resources must have app.kubernetes.io/version label"
      condition: |
        has(object.metadata.labels["app.kubernetes.io/version"])
    - name: require-managed-by
      message: "All resources must have app.kubernetes.io/managed-by label"
      condition: |
        has(object.metadata.labels["app.kubernetes.io/managed-by"])
```

### Register in kustomization.yaml

```yaml
validators:
  - ./validators/required-labels.yaml
```

### Run Validation

```bash
# Validate manifests
kubectl kustomize . | kustomize validate

# Or with kustomize binary
kustomize build . --validate
```

---

## Study: Kustomize + Helm Integration

### Pattern: Helm for Packaging, Kustomize for Environment

```
my-app/
├── helm-chart/              # Helm chart (packaging)
│   ├── Chart.yaml
│   ├── values.yaml
│   └── templates/
│       ├── deployment.yaml
│       └── service.yaml
├── base/                    # Kustomize base (from helm template)
│   └── kustomization.yaml
└── overlays/
    ├── dev/
    │   └── kustomization.yaml
    ├── staging/
    │   └── kustomization.yaml
    └── prod/
        └── kustomization.yaml
```

### Workflow

```bash
# 1. Render Helm chart to base/
helm template my-app ./helm-chart \
  --namespace my-app \
  --values ./helm-chart/values.yaml \
  --output-dir ./base

# 2. Create base/kustomization.yaml from rendered files
# (or use helm-post-renderer)

# 3. Customize per environment with overlays
kubectl apply -k overlays/prod
```

### Helm Post-Renderer (Native Integration)

```yaml
# helm-chart/values.yaml
postRenderer:
  executable: kustomize
  args:
    - build
    - overlays/prod
```

```bash
# Render with Kustomize post-processing
helm template my-app ./helm-chart \
  --post-renderer ./kustomize-post-renderer.sh \
  --namespace my-app-prod
```

### Kustomize Post-Renderer Script (`kustomize-post-renderer.sh`)

```bash
#!/bin/bash
# stdin: Helm rendered manifests
# stdout: Kustomized manifests

cat <&0 | kustomize build overlays/prod
```

```bash
# Usage
helm template my-app ./helm-chart \
  --post-renderer ./kustomize-post-renderer.sh \
  --namespace my-app-prod | kubectl apply -f -
```

---

## Production Boilerplate: Kustomize + Helm Workflow

### Directory Structure

```
my-platform/
├── charts/                    # Helm charts (shared)
│   ├── my-app/
│   │   ├── Chart.yaml
│   │   ├── values.yaml
│   │   ├── values-dev.yaml
│   │   ├── values-prod.yaml
│   │   └── templates/
│   │       ├── deployment.yaml
│   │       ├── service.yaml
│   │       └── _helpers.tpl
│   ├── postgres/
│   └── redis/
├── kustomize/
│   ├── base/                  # Kustomize base (from helm template)
│   │   ├── kustomization.yaml
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   ├── configmap.yaml
│   │   ├── servicemonitor.yaml
│   │   ├── networkpolicy.yaml
│   │   ├── pdb.yaml
│   │   └── hpa.yaml
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
└── deploy.sh                  # Deployment script
```

### Deployment Script (`deploy.sh`)

```bash
#!/bin/bash
set -euo pipefail

ENV="${1:-dev}"
NAMESPACE="my-app-${ENV}"
CHART="charts/my-app"
OVERLAY="kustomize/overlays/${ENV}"

echo "Deploying to ${ENV} (namespace: ${NAMESPACE})"

# 1. Render Helm chart to temporary directory
TMP_DIR=$(mktemp -d)
helm template my-app "${CHART}" \
  --namespace "${NAMESPACE}" \
  --values "${CHART}/values-${ENV}.yaml" \
  --output-dir "${TMP_DIR}"

# 2. Create kustomization.yaml from rendered files
cat > "${TMP_DIR}/my-app/kustomization.yaml" <<EOF
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - deployment.yaml
  - service.yaml
  - configmap.yaml
  - servicemonitor.yaml
  - networkpolicy.yaml
  - pdb.yaml
  - hpa.yaml
commonLabels:
  app.kubernetes.io/name: my-app
  app.kubernetes.io/managed-by: helm+kustomize
EOF

# 3. Apply overlay on top
cd "${OVERLAY}"
kustomize build . --load-restrictor=LoadRestrictionsNone | kubectl apply -f -

# 4. Wait for rollout
kubectl rollout status deployment/my-app -n "${NAMESPACE}" --timeout=300s

echo "Deployment to ${ENV} complete"
```

---

## Production Hardening: Kustomize-Specific

| Hardening | Implementation |
|-----------|----------------|
| **Pin kustomize version** | Use `kustomize/v5.4.3` in CI/CD |
| **Validate before apply** | `kustomize build . --validate` in CI |
| **Pin image digests** | `images.digest` in overlay |
| **Disable name suffix hash** | `disableNameSuffixHash: true` for stable names |
| **Use `behavior: merge`** | For ConfigMap/Secret generators |
| **Validate with kubeval** | `kustomize build . | kubeval --strict` |
| **Sign manifests** | `cosign sign-blob` + verify in admission controller |
| **Limit resources in base** | Set sensible defaults, override in overlay |

---

## Common Commands Reference

```bash
# Build and validate
kustomize build . --validate

# Build with specific load restrictor
kustomize build . --load-restrictor=LoadRestrictionsNone

# Output to file
kustomize build . > manifests.yaml

# Diff against cluster
kustomize build . | kubectl diff -f -

# Apply with server-side apply
kustomize build . | kubectl apply --server-side -f -

# List all resources that would be created
kustomize build . | kubectl get -f - -o wide

# Edit live resource (creates patch)
kubectl kustomize . | kubectl edit -f -

# Generate ConfigMap from files
kustomize edit add configmap my-config --from-file=config/

# Generate Secret from literals
kustomize edit add secret my-secret --from-literal=key=value

# Add resource to kustomization
kustomize edit add resource deployment.yaml

# Add patch
kustomize edit add patch --path patches/replicas.yaml --kind Deployment --name my-app

# Set image
kustomize edit set image my-app=my-app:v1.2.3

# Set namespace
kustomize edit set namespace my-app-prod

# Set name prefix
kustomize edit add prefix prod-

# View current kustomization
kustomize edit view
```

---

## Key References

- [Kustomize Transformers](https://kubectl.docs.kubernetes.io/references/kustomize/kustomization/transformers/)
- [Kustomize Patches](https://kubectl.docs.kubernetes.io/references/kustomize/kustomization/patches/)
- [Kustomize Generators](https://kubectl.docs.kubernetes.io/references/kustomize/kustomization/generators/)
- [Kustomize Validators](https://github.com/kubernetes-sigs/kustomize/blob/master/docs/validators.md)
- [Kustomize + Helm](https://kustomize.io/helm/)
- [Kustomize Post-Renderer](https://helm.sh/docs/chart_template_guide/post_renderer/)

---

> **Next**: [03-helm-basics.md](03-helm-basics.md) — Helm chart structure, templates, values, dependencies