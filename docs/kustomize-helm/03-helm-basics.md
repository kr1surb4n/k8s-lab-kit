# Helm Basics — Study Notes + Production Boilerplate

> **Dual Purpose**: Study guide for learning Helm + Production-ready boilerplate patterns.
> Copy the "Production Boilerplate" sections directly into your projects.

---

## What is Helm?

Helm is the **package manager for Kubernetes**. It provides:
- **Charts**: Packages of pre-configured Kubernetes resources
- **Templating**: Go templates for generating manifests
- **Release Management**: Install, upgrade, rollback, uninstall
- **Dependencies**: Chart dependencies with version locking
- **Repositories**: Share charts via HTTP/OCI registries

**Key Concept**: Helm separates **chart structure** (templates) from **configuration** (values).

---

## Study: Core Concepts

### 1. Chart Structure

```
my-chart/
├── Chart.yaml              # Chart metadata (required)
├── values.yaml             # Default configuration values
├── values.schema.json      # JSON schema for values validation
├── README.md               # Documentation
├── LICENSE                 # License
├── templates/              # Template files (required)
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── configmap.yaml
│   ├── secret.yaml
│   ├── _helpers.tpl        # Named templates (partials)
│   ├── hpa.yaml
│   ├── pdb.yaml
│   ├── servicemonitor.yaml
│   ├── networkpolicy.yaml
│   └── NOTES.txt           # Post-install notes
├── charts/                 # Chart dependencies (subcharts)
│   └── postgresql-12.0.0.tgz
├── .helmignore             # Files to ignore
└── .github/
    └── workflows/
        └── chart-testing.yml
```

### 2. Chart.yaml — Metadata

```yaml
apiVersion: v2
name: my-app
description: A production-ready Helm chart for my-app
type: application
version: 1.2.3              # Chart version (SemVer)
appVersion: "1.2.3"         # Application version (informational)
kubeVersion: ">=1.25.0-0"   # Kubernetes version constraint
maintainers:
  - name: Platform Team
    email: platform@example.com
    url: https://example.com
keywords:
  - web
  - api
  - microservice
home: https://github.com/example/my-app
sources:
  - https://github.com/example/my-app
dependencies:
  - name: postgresql
    version: "12.x.x"
    repository: "https://charts.bitnami.com/bitnami"
    condition: postgresql.enabled
  - name: redis
    version: "18.x.x"
    repository: "https://charts.bitnami.com/bitnami"
    condition: redis.enabled
```

### 3. values.yaml — Default Configuration

```yaml
# values.yaml — Default configuration (overridden by user)
replicaCount: 3

image:
  repository: my-app
  tag: "latest"
  pullPolicy: IfNotPresent
  pullSecrets: []

nameOverride: ""
fullnameOverride: ""

serviceAccount:
  create: true
  annotations: {}
  name: ""

podAnnotations:
  prometheus.io/scrape: "true"
  prometheus.io/port: "9090"
  prometheus.io/path: /metrics

podLabels: {}

podSecurityContext:
  runAsNonRoot: true
  runAsUser: 1000
  runAsGroup: 1000
  fsGroup: 1000
  seccompProfile:
    type: RuntimeDefault

securityContext:
  allowPrivilegeEscalation: false
  capabilities:
    drop:
      - ALL
  readOnlyRootFilesystem: true
  runAsNonRoot: true
  runAsUser: 1000
  runAsGroup: 1000

service:
  type: ClusterIP
  port: 80
  targetPort: http

ingress:
  enabled: true
  className: "nginx"
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/rate-limit: "100"
  hosts:
    - host: my-app.example.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: my-app-tls
      hosts:
        - my-app.example.com

resources:
  limits:
    cpu: 1000m
    memory: 1Gi
  requests:
    cpu: 250m
    memory: 256Mi

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 20
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80

nodeSelector: {}

tolerations: []

affinity:
  podAntiAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 100
        podAffinityTerm:
          labelSelector:
            matchExpressions:
              - key: app.kubernetes.io/name
                operator: In
                values:
                  - {{ .Release.Name }}
          topologyKey: kubernetes.io/hostname

# Application configuration
config:
  LOG_LEVEL: info
  LOG_FORMAT: json
  METRICS_ENABLED: "true"
  HEALTH_CHECK_PATH: /healthz
  READINESS_PATH: /ready

# Secrets (use ExternalSecretsOperator in production!)
secrets:
  DB_PASSWORD: ""
  JWT_SECRET: ""
  API_KEY: ""

# Monitoring
serviceMonitor:
  enabled: true
  interval: 30s
  path: /metrics

# Network policy
networkPolicy:
  enabled: true
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: ingress-nginx
      ports:
        - protocol: TCP
          port: 8080
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: default
      ports:
        - protocol: UDP
          port: 53

# Pod Disruption Budget
pdb:
  enabled: true
  minAvailable: "50%"

# Extra deploy/statefulset/daemonset config
extraVolumes: []
extraVolumeMounts: []
extraContainers: []
initContainers: []

# Tests
tests:
  enabled: true
```

---

## Study: Template Language (Go Templates + Sprig)

### Basic Syntax

```yaml
# Variable substitution
replicas: {{ .Values.replicaCount }}

# String quoting
image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"

# Conditionals
{{- if .Values.ingress.enabled }}
# ... ingress resources
{{- end }}

# Loops
{{- range .Values.extraVolumes }}
  - name: {{ .name }}
    {{- if .persistentVolumeClaim }}
    persistentVolumeClaim:
      claimName: {{ .claimName }}
    {{- else }}
    emptyDir: {}
    {{- end }}
{{- end }}

# Helpers (from _helpers.tpl)
{{- include "my-app.fullname" . }}
{{- include "my-app.labels" . | nindent 4 }}

# Sprig functions
{{ .Values.image.tag | default "latest" | quote }}
{{ .Release.Name | trunc 24 }}
{{ now | date "2006-01-02" }}
{{ randAlphaNum 10 | lower }}
```

### Control Structures

```yaml
# if/else
{{- if .Values.autoscaling.enabled }}
  # HPA config
{{- else }}
  # No HPA
{{- end }}

# with (scopes to object)
{{- with .Values.image }}
repository: {{ .repository }}
tag: {{ .tag }}
{{- end }}

# range with index
{{- range $index, $item := .Values.extraContainers }}
  - name: extra-{{ $index }}
    image: {{ $item.image }}
{{- end }}

# default values
{{ .Values.config.LOG_LEVEL | default "info" }}

# required (fail if not set)
{{ .Values.secrets.DB_PASSWORD | required "DB_PASSWORD is required" }}

# ternary
{{ ternary "enabled" "disabled" .Values.featureFlag }}
```

---

## Study: Template Files

### `templates/deployment.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "my-app.fullname" . }}
  namespace: {{ .Release.Namespace }}
  labels:
    {{- include "my-app.labels" . | nindent 4 }}
  annotations:
    checksum/config: {{ include (print $.Template.BasePath "/configmap.yaml") . | sha256sum }}
    checksum/secrets: {{ include (print $.Template.BasePath "/secret.yaml") . | sha256sum }}
spec:
  replicas: {{ .Values.replicaCount }}
  selector:
    matchLabels:
      {{- include "my-app.selectorLabels" . | nindent 6 }}
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 25%
      maxUnavailable: 0
  minReadySeconds: 10
  progressDeadlineSeconds: 600
  revisionHistoryLimit: 10
  template:
    metadata:
      labels:
        {{- include "my-app.selectorLabels" . | nindent 8 }}
      annotations:
        checksum/config: {{ include (print $.Template.BasePath "/configmap.yaml") . | sha256sum }}
        checksum/secrets: {{ include (print $.Template.BasePath "/secret.yaml") . | sha256sum }}
        prometheus.io/scrape: "true"
        prometheus.io/port: "9090"
        prometheus.io/path: /metrics
    spec:
      serviceAccountName: {{ include "my-app.serviceAccountName" . }}
      securityContext:
        {{- toYaml .Values.podSecurityContext | nindent 8 }}
      containers:
        - name: {{ .Chart.Name }}
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag | default .Chart.AppVersion }}"
          imagePullPolicy: {{ .Values.image.pullPolicy }}
          ports:
            - name: http
              containerPort: 8080
              protocol: TCP
            - name: metrics
              containerPort: 9090
              protocol: TCP
          envFrom:
            - configMapRef:
                name: {{ include "my-app.fullname" . }}-config
            - secretRef:
                name: {{ include "my-app.fullname" . }}-secrets
          resources:
            {{- toYaml .Values.resources | nindent 12 }}
          livenessProbe:
            httpGet:
              path: {{ .Values.config.HEALTH_CHECK_PATH }}
              port: http
            initialDelaySeconds: 30
            periodSeconds: 10
            timeoutSeconds: 5
            failureThreshold: 3
          readinessProbe:
            httpGet:
              path: {{ .Values.config.READINESS_PATH }}
              port: http
            initialDelaySeconds: 10
            periodSeconds: 5
            timeoutSeconds: 3
            failureThreshold: 3
          startupProbe:
            httpGet:
              path: {{ .Values.config.HEALTH_CHECK_PATH }}
              port: http
            initialDelaySeconds: 5
            periodSeconds: 5
            timeoutSeconds: 3
            failureThreshold: 30
          securityContext:
            {{- toYaml .Values.securityContext | nindent 12 }}
          volumeMounts:
            - name: tmp
              mountPath: /tmp
            {{- range .Values.extraVolumeMounts }}
            - name: {{ .name }}
              mountPath: {{ .mountPath }}
            {{- end }}
      volumes:
        - name: tmp
          emptyDir:
            sizeLimit: 100Mi
        {{- range .Values.extraVolumes }}
        - name: {{ .name }}
          {{- if .persistentVolumeClaim }}
          persistentVolumeClaim:
            claimName: {{ .claimName }}
          {{- else }}
          emptyDir: {}
          {{- end }}
        {{- end }}
      affinity:
        {{- toYaml .Values.affinity | nindent 8 }}
      nodeSelector:
        {{- toYaml .Values.nodeSelector | nindent 8 }}
      tolerations:
        {{- toYaml .Values.tolerations | nindent 8 }}
      serviceAccountName: {{ include "my-app.serviceAccountName" . }}
      {{- with .Values.initContainers }}
      initContainers:
        {{- toYaml . | nindent 8 }}
      {{- end }}
```

---

## Study: `_helpers.tpl` — Named Templates

```go
{{/*
Expand the name of the chart.
*/}}
{{- define "my-app.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "my-app.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "my-app.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "my-app.labels" -}}
helm.sh/chart: {{ include "my-app.chart" . }}
{{ include "my-app.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "my-app.selectorLabels" -}}
app.kubernetes.io/name: {{ include "my-app.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Service account name
*/}}
{{- define "my-app.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "my-app.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}
```

---

## Study: Common Commands

```bash
# Create new chart
helm create my-app

# Validate chart
helm lint ./my-app

# Render templates (dry-run)
helm template my-app ./my-app --namespace my-namespace --values values.yaml

# Install
helm install my-app ./my-app --namespace my-namespace --create-namespace

# Upgrade
helm upgrade my-app ./my-app --namespace my-namespace --values values-prod.yaml

# Rollback
helm rollback my-app 1 --namespace my-namespace

# Uninstall
helm uninstall my-app --namespace my-namespace

# List releases
helm list --namespace my-namespace

# Get release status
helm status my-app --namespace my-namespace

# Get release values
helm get values my-app --namespace my-namespace

# Get manifest
helm get manifest my-app --namespace my-namespace

# Package chart
helm package ./my-app

# Push to OCI registry
helm push ./my-app-1.2.3.tgz oci://registry.example.com/charts

# Pull from OCI
helm pull oci://registry.example.com/charts/my-app --version 1.2.3

# Show chart info
helm show chart ./my-app
helm show values ./my-app
helm show readme ./my-app

# Dependency management
helm dependency update ./my-app
helm dependency build ./my-app

# Test chart
helm test my-app --namespace my-namespace

# Show diff before upgrade
helm diff upgrade my-app ./my-app --namespace my-namespace --values values-prod.yaml
```

---

## Production Boilerplate: Complete Chart Structure

### `Chart.yaml` — Production Chart Metadata

```yaml
apiVersion: v2
name: my-app
description: Production-ready Helm chart for my-app microservice
type: application
version: 1.2.3
appVersion: "1.2.3"
kubeVersion: ">=1.25.0-0"
maintainers:
  - name: Platform Team
    email: platform@example.com
    url: https://github.com/example/platform
keywords:
  - web
  - api
  - microservice
  - production
home: https://github.com/example/my-app
sources:
  - https://github.com/example/my-app
dependencies:
  - name: postgresql
    version: "12.x.x"
    repository: "https://charts.bitnami.com/bitnami"
    condition: postgresql.enabled
    tags:
      - database
  - name: redis
    version: "18.x.x"
    repository: "https://charts.bitnami.com/bitnami"
    condition: redis.enabled
    tags:
      - cache
```

### `values.yaml` — Production Defaults (Full)

```yaml
# Production-ready values.yaml
replicaCount: 3

image:
  repository: my-app
  tag: "v1.2.3"
  pullPolicy: IfNotPresent
  pullSecrets: []

nameOverride: ""
fullnameOverride: ""

serviceAccount:
  create: true
  annotations:
    eks.amazonaws.com/role-arn: ""  # For IRSA
  name: ""

podAnnotations:
  prometheus.io/scrape: "true"
  prometheus.io/port: "9090"
  prometheus.io/path: /metrics
  # For kube-prometheus-stack
  # prometheus.io/scrape: "true"

podLabels: {}

podSecurityContext:
  runAsNonRoot: true
  runAsUser: 1000
  runAsGroup: 1000
  fsGroup: 1000
  seccompProfile:
    type: RuntimeDefault

securityContext:
  allowPrivilegeEscalation: false
  capabilities:
    drop:
      - ALL
  readOnlyRootFilesystem: true
  runAsNonRoot: true
  runAsUser: 1000
  runAsGroup: 1000

service:
  type: ClusterIP
  port: 80
  targetPort: http

ingress:
  enabled: true
  className: "nginx"
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/rate-limit-window: "1m"
    nginx.ingress.kubernetes.io/limit-connections: "50"
  hosts:
    - host: my-app.example.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: my-app-tls
      hosts:
        - my-app.example.com

resources:
  limits:
    cpu: 1000m
    memory: 1Gi
  requests:
    cpu: 250m
    memory: 256Mi

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 20
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
        - type: Percent
          value: 10
          periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
        - type: Percent
          value: 100
          periodSeconds: 15
        - type: Pods
          value: 4
          periodSeconds: 15
      selectPolicy: Max

nodeSelector: {}

tolerations: []

affinity:
  podAntiAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 100
        podAffinityTerm:
          labelSelector:
            matchExpressions:
              - key: app.kubernetes.io/name
                operator: In
                values:
                  - {{ .Release.Name }}
          topologyKey: kubernetes.io/hostname

config:
  LOG_LEVEL: info
  LOG_FORMAT: json
  METRICS_ENABLED: "true"
  HEALTH_CHECK_PATH: /healthz
  READINESS_PATH: /ready

# Secrets (use ExternalSecretsOperator in production!)
secrets:
  DB_PASSWORD: ""
  JWT_SECRET: ""
  API_KEY: ""

serviceMonitor:
  enabled: true
  interval: 30s
  path: /metrics

networkPolicy:
  enabled: true
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: ingress-nginx
        - podSelector:
            matchLabels:
              app.kubernetes.io/name: prometheus
      ports:
        - protocol: TCP
          port: 8080
        - protocol: TCP
          port: 9090
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: default
      ports:
        - protocol: UDP
          port: 53
    - to:
        - podSelector:
            matchLabels:
              app.kubernetes.io/name: postgres
      ports:
        - protocol: TCP
          port: 5432
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: observability
      ports:
        - protocol: TCP
          port: 4318

pdb:
  enabled: true
  minAvailable: "50%"

extraVolumes: []
extraVolumeMounts: []
extraContainers: []
initContainers: []

tests:
  enabled: true
```

---

## Production Boilerplate: Template Files

### `templates/configmap.yaml`

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: {{ include "my-app.fullname" . }}-config
  namespace: {{ .Release.Namespace }}
  labels:
    {{- include "my-app.labels" . | nindent 4 }}
  annotations:
    checksum/config: {{ .Files.Get "config.yaml" | sha256sum }}
data:
  {{- range $key, $value := .Values.config }}
  {{ $key }}: {{ $value | quote }}
  {{- end }}
  CONFIG_CHECKSUM: {{ include (print $.Template.BasePath "/configmap.yaml") . | sha256sum }}
```

### `templates/secret.yaml`

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: {{ include "my-app.fullname" . }}-secrets
  namespace: {{ .Release.Namespace }}
  labels:
    {{- include "my-app.labels" . | nindent 4 }}
  annotations:
    checksum/secrets: {{ .Files.Get "secret.yaml" | sha256sum }}
type: Opaque
stringData:
  {{- range $key, $value := .Values.secrets }}
  {{ $key }}: {{ $value }}
  {{- end }}
  SECRETS_CHECKSUM: {{ include (print $.Template.BasePath "/secret.yaml") . | sha256sum }}
```

### `templates/servicemonitor.yaml`

```yaml
{{- if .Values.serviceMonitor.enabled }}
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: {{ include "my-app.fullname" . }}
  namespace: {{ .Release.Namespace }}
  labels:
    {{- include "my-app.labels" . | nindent 4 }}
    release: prometheus
spec:
  selector:
    matchLabels:
      {{- include "my-app.selectorLabels" . | nindent 6 }}
  endpoints:
    - port: metrics
      interval: {{ .Values.serviceMonitor.interval | default "30s" }}
      path: {{ .Values.serviceMonitor.path | default "/metrics" }}
{{- end }}
```

### `templates/networkpolicy.yaml`

```yaml
{{- if .Values.networkPolicy.enabled }}
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: {{ include "my-app.fullname" . }}
  namespace: {{ .Release.Namespace }}
  labels:
    {{- include "my-app.labels" . | nindent 4 }}
spec:
  podSelector:
    matchLabels:
      {{- include "my-app.selectorLabels" . | nindent 6 }}
  policyTypes:
    - Ingress
    - Egress
  ingress:
    {{- toYaml .Values.networkPolicy.ingress | nindent 4 }}
  egress:
    {{- toYaml .Values.networkPolicy.egress | nindent 4 }}
{{- end }}
```

### `templates/pdb.yaml`

```yaml
{{- if .Values.pdb.enabled }}
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: {{ include "my-app.fullname" . }}
  namespace: {{ .Release.Namespace }}
  labels:
    {{- include "my-app.labels" . | nindent 4 }}
spec:
  minAvailable: {{ .Values.pdb.minAvailable }}
  selector:
    matchLabels:
      {{- include "my-app.selectorLabels" . | nindent 6 }}
{{- end }}
```

### `templates/hpa.yaml`

```yaml
{{- if .Values.autoscaling.enabled }}
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: {{ include "my-app.fullname" . }}
  namespace: {{ .Release.Namespace }}
  labels:
    {{- include "my-app.labels" . | nindent 4 }}
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: {{ include "my-app.fullname" . }}
  minReplicas: {{ .Values.autoscaling.minReplicas }}
  maxReplicas: {{ .Values.autoscaling.maxReplicas }}
  {{- if .Values.autoscaling.behavior }}
  behavior:
    {{- toYaml .Values.autoscaling.behavior | nindent 4 }}
  {{- end }}
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: {{ .Values.autoscaling.targetCPUUtilizationPercentage }}
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: {{ .Values.autoscaling.targetMemoryUtilizationPercentage | default 80 }}
{{- end }}
```

### `templates/tests/test-connection.yaml`

```yaml
{{- if .Values.tests.enabled }}
apiVersion: v1
kind: Pod
metadata:
  name: "{{ include "my-app.fullname" . }}-test-connection"
  namespace: {{ .Release.Namespace }}
  labels:
    {{- include "my-app.labels" . | nindent 4 }}
  annotations:
    "helm.sh/hook": test
spec:
  containers:
    - name: wget
      image: busybox
      command: ['wget', '--spider', '--timeout=5', 'http://{{ include "my-app.fullname" . }}:80/healthz']
  restartPolicy: Never
{{- end }}
```

---

## Production Hardening Checklist (Helm-Specific)

| Hardening | Implementation |
|-----------|----------------|
| **Schema validation** | `values.schema.json` + `helm lint` + `helm install --dry-run` |
| **Image digest pinning** | Use `image.digest` in values-prod.yaml |
| **Non-root, read-only rootfs** | `securityContext` in values.yaml |
| **Drop ALL capabilities** | `capabilities.drop: ["ALL"]` |
| **Resource requests/limits** | Required in values.yaml |
| **Probes (liveness/readiness/startup)** | Defined in deployment template |
| **PodDisruptionBudget** | Conditional template with `pdb.enabled` |
| **HPA with behavior** | Full `behavior` config in values |
| **NetworkPolicy** | Conditional template with `networkPolicy.enabled` |
| **ServiceMonitor** | Conditional template with `serviceMonitor.enabled` |
| **Image pull secrets** | Support via `image.pullSecrets` |
| **Checksum annotations** | Auto-reload on config/secret change |
| **Anti-affinity** | `podAntiAffinity` in values |
| **Tests** | `helm test` with hook annotations |
| **Schema validation** | `values.schema.json` + `helm lint` |
| **Dependencies locked** | `helm dependency build` → `charts/` |
| **Signed charts** | `helm package --sign` + `helm verify` |

---

## Environment-Specific Values Files

### `values-dev.yaml`

```yaml
replicaCount: 1

image:
  tag: "dev-latest"

resources:
  limits:
    cpu: 500m
    memory: 512Mi
  requests:
    cpu: 100m
    memory: 128Mi

autoscaling:
  enabled: false

config:
  LOG_LEVEL: debug
  LOG_FORMAT: text

ingress:
  enabled: true
  hosts:
    - host: my-app-dev.example.com
      paths:
        - path: /
          pathType: Prefix

networkPolicy:
  enabled: false

pdb:
  enabled: false
```

### `values-prod.yaml`

```yaml
replicaCount: 5

image:
  tag: "v1.2.3"
  digest: sha256:abc123...

resources:
  limits:
    cpu: 2000m
    memory: 2Gi
  requests:
    cpu: 500m
    memory: 512Mi

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
  hosts:
    - host: my-app.example.com
      paths:
        - path: /
          pathType: Prefix

networkPolicy:
  enabled: true

pdb:
  enabled: true
  minAvailable: "50%"
```

---

## Deployment Commands

```bash
# Install/Upgrade with environment values
helm upgrade --install my-app ./my-app \
  --namespace my-app-prod \
  --create-namespace \
  --values values-prod.yaml \
  --wait \
  --timeout 5m

# Dry-run to preview
helm upgrade --install my-app ./my-app \
  --namespace my-app-prod \
  --values values-prod.yaml \
  --dry-run \
  --debug

# Diff before upgrade
helm diff upgrade my-app ./my-app \
  --namespace my-app-prod \
  --values values-prod.yaml

# Rollback
helm rollback my-app 1 --namespace my-app-prod

# Test
helm test my-app --namespace my-app-prod

# Verify chart
helm lint ./my-app
helm template my-app ./my-app --values values-prod.yaml | kubeval --strict
```

---

## Key References

- [Helm Documentation](https://helm.sh/docs/)
- [Helm Chart Template Guide](https://helm.sh/docs/chart_template_guide/)
- [Helm Chart Best Practices](https://helm.sh/docs/chart_best_practices/)
- [Sprig Functions](http://masterminds.github.io/sprig/)
- [Chart Testing](https://github.com/helm/chart-testing)
- [Helm Diff Plugin](https://github.com/databus23/helm-diff)

---

> **Next**: [04-helm-advanced.md](04-helm-advanced.md) — Hooks, tests, dependencies, Helm + Kustomize integration