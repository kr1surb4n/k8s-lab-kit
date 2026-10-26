# Helm Advanced — Study Notes + Production Boilerplate

> **Dual Purpose**: Deep dive into advanced Helm features + Production boilerplate patterns.

---

## Study: Helm Hooks

Hooks allow you to execute operations at specific points in a release lifecycle.

### Hook Types

| Hook | When It Runs | Use Case |
|------|--------------|----------|
| `pre-install` | Before any resources created | DB migrations, setup |
| `post-install` | After all resources created | Smoke tests, notifications |
| `pre-delete` | Before resources deleted | Cleanup, data export |
| `post-delete` | After resources deleted | Cleanup |
| `pre-upgrade` | Before upgrade | DB migrations, backup |
| `post-upgrade` | After upgrade | Smoke tests |
| `pre-rollback` | Before rollback | Prepare rollback |
| `post-rollback` | After rollback | Verification |
| `test` | `helm test` | Integration tests |

### Hook Implementation

```yaml
# templates/migration-job.yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: {{ include "my-app.fullname" . }}-migration
  namespace: {{ .Release.Namespace }}
  labels:
    {{- include "my-app.labels" . | nindent 4 }}
  annotations:
    "helm.sh/hook": pre-install,pre-upgrade
    "helm.sh/hook-weight": "-5"  # Run first (lower = earlier)
    "helm.sh/hook-delete-policy": hook-succeeded,hook-failed
spec:
  backoffLimit: 3
  template:
    spec:
      restartPolicy: OnFailure
      containers:
        - name: migration
          image: {{ .Values.image.repository }}:{{ .Values.image.tag }}
          command: ["/app/migrate"]
          envFrom:
            - configMapRef:
                name: {{ include "my-app.fullname" . }}-config
            - secretRef:
                name: {{ include "my-app.fullname" . }}-secrets
```

### Hook Weights & Delete Policies

```yaml
# Weight: lower runs first (negative = earlier)
"helm.sh/hook-weight": "-10"

# Delete policies:
# hook-succeeded — delete after success (default)
# hook-failed — delete after failure
# before-hook-creation — delete before new hook runs
"helm.sh/hook-delete-policy": hook-succeeded,hook-failed
```

---

## Study: Chart Dependencies

### Declaration in Chart.yaml

```yaml
dependencies:
  - name: postgresql
    version: "12.x.x"
    repository: "https://charts.bitnami.com/bitnami"
    condition: postgresql.enabled
    tags:
      - database
      - infra
  - name: redis
    version: "18.x.x"
    repository: "https://charts.bitnami.com/bitnami"
    condition: redis.enabled
    tags:
      - cache
      - infra
  - name: ingress-nginx
    version: "4.x.x"
    repository: "https://kubernetes.github.io/ingress-nginx"
    condition: ingress-nginx.enabled
    import-values:
      - data: controller.config
```

### Using Subchart Values

```yaml
# values.yaml
postgresql:
  enabled: true
  auth:
    username: myapp
    password: changeme
    database: myapp
  primary:
    persistence:
      size: 10Gi

redis:
  enabled: true
  auth:
    enabled: true
    password: changeme
  master:
    persistence:
      size: 5Gi
```

### Accessing Subchart Outputs

```yaml
# In your templates, access subchart resources:
# Postgres Service: {{ .Release.Name }}-postgresql
# Redis Service: {{ .Release.Name }}-redis-master
```

---

## Study: Chart Testing

### Chart Testing (ct) - Lint + Install Test

```yaml
# .github/workflows/chart-testing.yml
name: Chart Testing
on:
  pull_request:
    paths:
      - 'charts/**'
jobs:
  chart-testing:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - name: Set up Helm
        uses: azure/setup-helm@v4
      - name: Set up chart-testing
        uses: helm/chart-testing-action@v2.6.1
      - name: Run chart-testing (lint)
        run: ct lint --all --config .github/ct.yaml
      - name: Run chart-testing (install)
        run: ct install --config .github/ct.yaml
```

```yaml
# .github/ct.yaml
remote: origin
target-branch: main
chart-dirs:
  - charts
validate-maintainers: true
validate-yaml: true
excluded-charts: []
lint-conf: .github/lintconf.yaml
```

```yaml
# .github/lintconf.yaml
# Chart linting configuration
ignore:
  - "CHARTNAME"
```

### Helm Unit Tests (helm-unittest)

```yaml
# tests/unittest_values.yaml
replicaCount: 2
image:
  repository: my-app
  tag: test
autoscaling:
  enabled: true
```

```yaml
# tests/unittest_snapshot.yaml
- name: Deployment should have correct replicas
  template: deployment.yaml
  asserts:
    - matchRegex:
        path: spec.replicas
        pattern: "^2$"
```

```bash
# Run unit tests
helm unittest ./my-chart
```

---

## Study: Chart Repositories

### Local Repository (GitHub Pages)

```bash
# 1. Package charts
helm package ./charts/my-app --destination ./docs/charts
helm package ./charts/postgresql --destination ./docs/charts

# 2. Create index.yaml
helm repo index ./docs/charts --url https://example.github.io/charts

# 3. Commit docs/ to gh-pages branch
git add docs/
git commit -m "Update Helm repo"
git push origin gh-pages
```

### OCI Registry (Modern)

```bash
# Push to OCI registry
helm chart save ./charts/my-app oci://registry.example.com/charts/my-app:1.2.3
helm push oci://registry.example.com/charts/my-app:1.2.3

# Pull from OCI
helm pull oci://registry.example.com/charts/my-app --version 1.2.3

# List tags
helm chart list oci://registry.example.com/charts/my-app
```

### Repository Configuration

```yaml
# ~/.config/helm/repositories.yaml
repositories:
  - name: my-repo
    url: https://example.github.io/charts
    username: ""
    password: ""
    certFile: ""
    keyFile: ""
    caFile: ""
    passCredentialsAll: false
```

---

## Production Boilerplate: Complete Chart with Dependencies

### `Chart.yaml` — Full Production Chart

```yaml
apiVersion: v2
name: my-platform
description: Production-ready platform stack with app, database, and cache
type: application
version: 2.0.0
appVersion: "2.0.0"
kubeVersion: ">=1.25.0-0"
maintainers:
  - name: Platform Team
    email: platform@example.com
    url: https://github.com/example/platform
keywords:
  - platform
  - microservices
  - production
home: https://github.com/example/platform
sources:
  - https://github.com/example/platform
dependencies:
  # Application
  - name: my-app
    version: "1.x.x"
    repository: "file://../my-app"
    condition: my-app.enabled
    tags:
      - application
  # Database
  - name: postgresql
    version: "12.x.x"
    repository: "https://charts.bitnami.com/bitnami"
    condition: postgresql.enabled
    tags:
      - database
      - infra
  - name: redis
    version: "18.x.x"
    repository: "https://charts.bitnami.com/bitnami"
    condition: redis.enabled
    tags:
      - cache
      - infra
  # Ingress
  - name: ingress-nginx
    version: "4.x.x"
    repository: "https://kubernetes.github.io/ingress-nginx"
    condition: ingress-nginx.enabled
    import-values:
      - data: controller.config
    tags:
      - networking
```

### `values.yaml` — Platform Values

```yaml
# Global settings
global:
  platformName: my-platform
  environment: production
  domain: example.com

# Application
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
  config:
    LOG_LEVEL: warn
    LOG_FORMAT: json
    RATE_LIMIT_ENABLED: "true"
  ingress:
    enabled: true
    className: nginx
    hosts:
      - host: app.example.com
        paths:
          - path: /
            pathType: Prefix
    tls:
      - secretName: app-tls
        hosts:
          - app.example.com

# PostgreSQL (Bitnami)
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
    resources:
      limits:
        cpu: 2000m
        memory: 4Gi
      requests:
        cpu: 500m
        memory: 1Gi
    podSecurityContext:
      runAsUser: 1000
      fsGroup: 1000
    networkPolicy:
      enabled: true
  backup:
    enabled: true
    schedule: "0 2 * * *"
    retention: 30

# Redis (Bitnami)
redis:
  enabled: true
  auth:
    enabled: true
    password: ""
  master:
    persistence:
      size: 10Gi
      storageClass: fast-ssd
    resources:
      limits:
        cpu: 1000m
        memory: 2Gi
      requests:
        cpu: 250m
        memory: 512Mi
    podSecurityContext:
      runAsUser: 1000
      fsGroup: 1000

# Ingress NGINX
ingress-nginx:
  enabled: true
  controller:
    replicaCount: 2
    admissionWebhooks:
      enabled: true
    metrics:
      enabled: true
    service:
      type: LoadBalancer
    config:
      proxy-body-size: "10m"
      rate-limit: "100"
      rate-limit-window: "1m"
    resources:
      limits:
        cpu: 500m
        memory: 512Mi
      requests:
        cpu: 100m
        memory: 128Mi

# Platform-wide settings
global:
  platformName: my-platform
  environment: production
  domain: example.com
  storageClass: fast-ssd
  monitoring:
    enabled: true
  logging:
    enabled: true
```

---

## Production Boilerplate: Hooks for Database Migrations

### `templates/hooks/pre-upgrade-migration.yaml`

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: {{ include "my-platform.fullname" . }}-db-migration
  namespace: {{ .Release.Namespace }}
  labels:
    {{- include "my-platform.labels" . | nindent 4 }}
  annotations:
    "helm.sh/hook": pre-install,pre-upgrade
    "helm.sh/hook-weight": "-10"
    "helm.sh/hook-delete-policy": hook-succeeded,hook-failed
spec:
  backoffLimit: 3
  activeDeadlineSeconds: 300
  template:
    spec:
      serviceAccountName: {{ include "my-platform.serviceAccountName" . }}
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        runAsGroup: 1000
        fsGroup: 1000
      restartPolicy: OnFailure
      containers:
        - name: migration
          image: {{ .Values.my-app.image.repository }}:{{ .Values.my-app.image.tag }}
          command: ["/app/migrate", "--auto-approve"]
          envFrom:
            - configMapRef:
                name: {{ include "my-platform.fullname" . }}-my-app-config
            - secretRef:
                name: {{ include "my-platform.fullname" . }}-my-app-secrets
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 512Mi
          securityContext:
            allowPrivilegeEscalation: false
            capabilities:
              drop: ["ALL"]
            readOnlyRootFilesystem: true
            runAsNonRoot: true
            runAsUser: 1000
            runAsGroup: 1000
```

### `templates/hooks/post-install-smoke-test.yaml`

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: {{ include "my-platform.fullname" . }}-smoke-test
  namespace: {{ .Release.Namespace }}
  labels:
    {{- include "my-platform.labels" . | nindent 4 }}
  annotations:
    "helm.sh/hook": post-install,post-upgrade
    "helm.sh/hook-weight": "10"
    "helm.sh/hook-delete-policy": hook-succeeded,hook-failed
spec:
  backoffLimit: 1
  activeDeadlineSeconds: 120
  template:
    spec:
      serviceAccountName: {{ include "my-platform.serviceAccountName" . }}
      restartPolicy: OnFailure
      containers:
        - name: smoke-test
          image: curlimages/curl:8.6
          command:
            - /bin/sh
            - -c
            - |
              set -e
              echo "Waiting for service..."
              for i in $(seq 1 30); do
                if curl -sf http://{{ include "my-platform.fullname" . }}-my-app:80/healthz; then
                  echo "Health check passed"
                  exit 0
                fi
                sleep 2
              done
              echo "Health check failed"
              exit 1
          resources:
            requests:
              cpu: 10m
              memory: 16Mi
            limits:
              cpu: 50m
              memory: 32Mi
```

---

## Production Boilerplate: Chart Tests

### `templates/tests/test-connection.yaml`

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: "{{ include "my-platform.fullname" . }}-test-connection"
  namespace: {{ .Release.Namespace }}
  labels:
    {{- include "my-platform.labels" . | nindent 4 }}
  annotations:
    "helm.sh/hook": test
spec:
  containers:
    - name: test-db
      image: postgres:15-alpine
      command:
        - pg_isready
        - -h
        - {{ include "my-platform.fullname" . }}-postgresql
        - -U
        - {{ .Values.postgresql.auth.username }}
        - -d
        - {{ .Values.postgresql.auth.database }}
      env:
        - name: PGPASSWORD
          valueFrom:
            secretKeyRef:
              name: {{ include "my-platform.fullname" . }}-postgresql
              key: password
    - name: test-redis
      image: redis:7-alpine
      command:
        - redis-cli
        - -h
        - {{ include "my-platform.fullname" . }}-redis-master
        - -a
        - {{ .Values.redis.auth.password }}
        - ping
    - name: test-app
      image: curlimages/curl:8.6
      command:
        - /bin/sh
        - -c
        - |
          curl -sf http://{{ include "my-platform.fullname" . }}-my-app:80/healthz
  restartPolicy: Never
```

---

## Study: Helm 3.13+ Features

### OCI Registry Support (Native)

```bash
# Save chart as OCI artifact
helm chart save ./my-chart oci://registry.example.com/charts/my-app:1.2.3

# Push to registry
helm push oci://registry.example.com/charts/my-app:1.2.3

# Install from OCI
helm install my-app oci://registry.example.com/charts/my-app --version 1.2.3

# List tags
helm chart list oci://registry.example.com/charts/my-app
```

### Library Charts (Reusable Templates)

```yaml
# Chart.yaml for library chart
apiVersion: v2
name: my-lib
description: Shared library templates
type: library
version: 1.0.0
```

```yaml
# In consumer Chart.yaml
dependencies:
  - name: my-lib
    version: "1.x.x"
    repository: "https://charts.example.com"
```

```go
// Use library templates
{{- include "my-lib.common.labels" . }}
```

### Post-Renderer (Kustomize Integration)

```bash
# kustomize-post-renderer.sh
#!/bin/bash
cat <&0 | kustomize build overlays/prod
```

```bash
# Usage
helm template my-app ./my-chart \
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

## Production Hardening Checklist (Helm Advanced)

| Hardening | Implementation |
|-----------|----------------|
| **Hook delete policies** | `hook-succeeded,hook-failed` on all hooks |
| **Hook weights** | Order: -10 (migrations) → 0 (default) → 10 (smoke tests) |
| **Subchart conditions** | Use `condition` + `tags` for optional deps |
| **Values schema** | `values.schema.json` for validation |
| **Chart signing** | `helm package --sign --key keyring.gpg` |
| **Chart verification** | `helm verify my-chart-1.2.3.tgz` |
| **Dependency locking** | `helm dependency build` → commit `charts/` |
| **Unit tests** | `helm unittest` in CI |
| **Integration tests** | `ct install` in CI |
| **Chart linting** | `helm lint` + `ct lint` in CI |
| **Values validation** | `values.schema.json` + `--validate` |
| **OCI registry** | Push/pull charts as OCI artifacts |

---

## Key References

- [Helm Hooks](https://helm.sh/docs/topics/charts_hooks/)
- [Chart Dependencies](https://helm.sh/docs/topics/charts/#chart-dependencies)
- [Chart Testing](https://github.com/helm/chart-testing)
- [Helm Unit Tests](https://github.com/helm-unittest/helm-unittest)
- [OCI Registry Support](https://helm.sh/docs/topics/registries/)
- [Library Charts](https://helm.sh/docs/topics/library_charts/)
- [Post-Renderer](https://helm.sh/docs/chart_template_guide/post_renderer/)

---

> **Next**: [05-kustomize-vs-helm.md](05-kustomize-vs-helm.md) — When to use which, decision matrix