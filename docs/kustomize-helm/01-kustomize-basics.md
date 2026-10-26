# Kustomize Basics — Study Notes + Production Boilerplate

> **Dual Purpose**: Study guide for learning Kustomize + Production-ready boilerplate patterns.
> Copy the "Production Boilerplate" sections directly into your projects.

---

## What is Kustomize?

Kustomize is a **template-free** way to customize Kubernetes manifests. It works by:
- **Bases**: Common manifests shared across environments
- **Overlays**: Environment-specific customizations (dev, staging, prod)
- **Patches**: Surgical modifications without forking bases
- **Generators**: ConfigMaps/Secrets from files/literals
- **Transformers**: Global modifications (labels, annotations, prefixes)

**Key Philosophy**: "Configuration as data, not code" — no templating language, just YAML merging.

---

## Study: Core Concepts

### 1. `kustomization.yaml` — The Heart

Every Kustomize directory has a `kustomization.yaml`:

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

# 1. Resources — base manifests to include
resources:
  - deployment.yaml
  - service.yaml
  - configmap.yaml
  - ../base              # Can reference other kustomization dirs

# 2. Common metadata applied to ALL resources
commonLabels:
  app: my-app
  managed-by: kustomize
commonAnnotations:
  gitops.example.com/sync: "true"

# 3. Namespace for all resources
namespace: my-app

# 4. Name prefix/suffix for all resources
namePrefix: dev-
# nameSuffix: -v1

# 4. Images — override image tags globally
images:
  - name: my-app
    newTag: v1.2.3
  - name: postgres
    newTag: 15-alpine

# 5. Patches — surgical changes to resources
patches:
  - path: patches/deployment-replicas.yaml
    target:
      kind: Deployment
      name: my-app

# 6. ConfigMap/Secret generators
configMapGenerator:
  - name: app-config
    files:
      - config.yaml=config/app.yaml
    literals:
      - LOG_LEVEL=info
      - FEATURE_FLAG=new-ui=true

secretGenerator:
  - name: app-secrets
    literals:
      - DB_PASSWORD=changeme
    # Or from files:
    # files:
    #   - tls.crt=certs/tls.crt
    #   - tls.key=certs/tls.key

# 7. Transformers — global modifications
# (labels, annotations, prefixes, etc. — see advanced)

# 8. Validators — custom validation (see advanced)
```

---

## Study: Bases + Overlays Pattern

### Directory Structure

```
my-app/
├── base/
│   ├── kustomization.yaml
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── configmap.yaml
│   └── secrets.yaml          # Template only (no real secrets!)
├── overlays/
│   ├── dev/
│   │   ├── kustomization.yaml
│   │   └── patches/
│   │       └── replicas.yaml
│   ├── staging/
│   │   ├── kustomization.yaml
│   │   └── patches/
│   │       └── resources.yaml
│   └── prod/
│       ├── kustomization.yaml
│       └── patches/
│           ├── replicas.yaml
│           ├── resources.yaml
│           └── security.yaml
```

### Base (`base/kustomization.yaml`)

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - deployment.yaml
  - service.yaml
  - configmap.yaml
  - secrets.yaml

commonLabels:
  app: my-app
  version: v1

# Base images (overridden in overlays)
images:
  - name: my-app
    newTag: "latest"
  - name: postgres
    newTag: "15-alpine"

# ConfigMap with defaults
configMapGenerator:
  - name: app-config
    literals:
      - LOG_LEVEL=info
      - ENVIRONMENT=base

# Secrets template (no real values!)
secretGenerator:
  - name: app-secrets
    literals:
      - DB_PASSWORD=CHANGEME_IN_OVERLAY
      - API_KEY=CHANGEME_IN_OVERLAY
```

### Overlay Example: Dev (`overlays/dev/kustomization.yaml`)

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - ../../base

namespace: my-app-dev

namePrefix: dev-

images:
  - name: my-app
    newTag: "dev-latest"

commonLabels:
  environment: development

# Override ConfigMap
configMapGenerator:
  - name: app-config
    behavior: merge
    literals:
      - LOG_LEVEL=debug
      - ENVIRONMENT=development
      - FEATURE_NEW_UI=enabled

# Override secrets with dev values
secretGenerator:
  - name: app-secrets
    behavior: merge
    literals:
      - DB_PASSWORD=dev-password
      - API_KEY=dev-api-key

# Patch replicas
patches:
  - path: patches/replicas.yaml
    target:
      kind: Deployment
      name: my-app

# Dev-specific resources
resources:
  - ../../base
  - dev-only-resources.yaml
```

### Dev Patch (`overlays/dev/patches/replicas.yaml`)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
spec:
  replicas: 1
```

---

## Production Boilerplate: Complete Base Structure

> **Copy this entire structure** for a new production-ready service.

### `base/kustomization.yaml` — Production Base

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

# === RESOURCES ===
resources:
  - deployment.yaml
  - service.yaml
  - configmap.yaml
  - servicemonitor.yaml      # Prometheus monitoring
  - networkpolicy.yaml       # Network isolation
  - pdb.yaml                 # PodDisruptionBudget
  - hpa.yaml                 # HorizontalPodAutoscaler

# === COMMON METADATA ===
commonLabels:
  app.kubernetes.io/name: "{{APP_NAME}}"
  app.kubernetes.io/version: "{{VERSION}}"
  app.kubernetes.io/managed-by: kustomize
  app.kubernetes.io/part-of: "{{PLATFORM_NAME}}"

commonAnnotations:
  gitops.example.com/managed-by: "kustomize"
  gitops.example.com/sync-wave: "10"

# === NAMESPACE ===
# Set in overlay, not here (base is namespace-agnostic)

# === IMAGES (overridden in overlay) ===
images:
  - name: "{{APP_IMAGE}}"
    newTag: "{{IMAGE_TAG}}"
  - name: "{{SIDECARE_IMAGE}}"
    newTag: "{{SIDECAR_TAG}}"

# === CONFIGMAP GENERATOR ===
configMapGenerator:
  - name: "{{APP_NAME}}-config"
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

# === SECRET GENERATOR (TEMPLATE ONLY!) ===
# Real secrets injected via ExternalSecretsOperator in overlay
secretGenerator:
  - name: "{{APP_NAME}}-secrets"
    behavior: merge
    literals:
      - DB_PASSWORD=CHANGEME_VIA_EXTERNAL_SECRETS
      - JWT_SECRET=CHANGEME_VIA_EXTERNAL_SECRETS
      - API_KEY=CHANGEME_VIA_EXTERNAL_SECRETS
    options:
      disableNameSuffixHash: true
      labels:
        app.kubernetes.io/component: secrets
    # Type is Opaque by default; for TLS use:
    # type: kubernetes.io/tls

# === COMMON TRANSFORMERS (see advanced) ===
# Applied in overlay for environment-specific transforms
```

### `base/deployment.yaml` — Production Deployment Template

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{APP_NAME}}
  labels:
    app.kubernetes.io/name: {{APP_NAME}}
    app.kubernetes.io/component: application
spec:
  replicas: 3
  revisionHistoryLimit: 10
  selector:
    matchLabels:
      app.kubernetes.io/name: {{APP_NAME}}
      app.kubernetes.io/component: application
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 25%
      maxUnavailable: 0
  minReadySeconds: 10
  progressDeadlineSeconds: 600
  template:
    metadata:
      labels:
        app.kubernetes.io/name: {{APP_NAME}}
        app.kubernetes.io/component: application
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "9090"
        prometheus.io/path: /metrics
        # Checksum annotations for rolling restarts on config change
        checksum/config: "{{CONFIG_CHECKSUM}}"
        checksum/secrets: "{{SECRETS_CHECKSUM}}"
    spec:
      serviceAccountName: {{APP_NAME}}
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        runAsGroup: 1000
        fsGroup: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: {{APP_NAME}}
          image: {{APP_IMAGE}}:{{IMAGE_TAG}}
          imagePullPolicy: IfNotPresent
          ports:
            - name: http
              containerPort: 8080
              protocol: TCP
            - name: metrics
              containerPort: 9090
              protocol: TCP
          envFrom:
            - configMapRef:
                name: {{APP_NAME}}-config
            - secretRef:
                name: {{APP_NAME}}-secrets
          resources:
            requests:
              cpu: "250m"
              memory: "256Mi"
            limits:
              cpu: "1000m"
              memory: "1Gi"
          livenessProbe:
            httpGet:
              path: /healthz
              port: http
            initialDelaySeconds: 30
            periodSeconds: 10
            timeoutSeconds: 5
            failureThreshold: 3
          readinessProbe:
            httpGet:
              path: /ready
              port: http
            initialDelaySeconds: 10
            periodSeconds: 5
            timeoutSeconds: 3
            failureThreshold: 3
          startupProbe:
            httpGet:
              path: /healthz
              port: http
            initialDelaySeconds: 5
            periodSeconds: 5
            timeoutSeconds: 3
            failureThreshold: 30
          securityContext:
            allowPrivilegeEscalation: false
            capabilities:
              drop: ["ALL"]
            readOnlyRootFilesystem: true
          volumeMounts:
            - name: tmp
              mountPath: /tmp
            - name: cache
              mountPath: /app/cache
      volumes:
        - name: tmp
          emptyDir:
            sizeLimit: 100Mi
        - name: cache
          emptyDir:
            sizeLimit: 500Mi
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              podAffinityTerm:
                labelSelector:
                  matchExpressions:
                    - key: app.kubernetes.io/name
                      operator: In
                      values: ["{{APP_NAME}}"]
                topologyKey: kubernetes.io/hostname
```

### `base/service.yaml` — Production Service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: {{APP_NAME}}
  labels:
    app.kubernetes.io/name: {{APP_NAME}}
    app.kubernetes.io/component: service
spec:
  type: ClusterIP
  ports:
    - name: http
      port: 80
      targetPort: http
      protocol: TCP
    - name: metrics
      port: 9090
      targetPort: metrics
      protocol: TCP
  selector:
    app.kubernetes.io/name: {{APP_NAME}}
    app.kubernetes.io/component: application
```

### `base/servicemonitor.yaml` — Prometheus Monitoring

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: {{APP_NAME}}
  labels:
    app.kubernetes.io/name: {{APP_NAME}}
    release: prometheus
spec:
  selector:
    matchLabels:
      app.kubernetes.io/name: {{APP_NAME}}
  endpoints:
    - port: metrics
      interval: 30s
      path: /metrics
```

### `base/networkpolicy.yaml` — Network Isolation

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: {{APP_NAME}}
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: {{APP_NAME}}
  policyTypes:
    - Ingress
    - Egress
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
          port: 4318  # OTel collector
```

### `base/pdb.yaml` — Pod Disruption Budget

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: {{APP_NAME}}
spec:
  minAvailable: 50%
  selector:
    matchLabels:
      app.kubernetes.io/name: {{APP_NAME}}
      app.kubernetes.io/component: application
```

### `base/hpa.yaml` — Horizontal Pod Autoscaler

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: {{APP_NAME}}
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: {{APP_NAME}}
  minReplicas: 3
  maxReplicas: 20
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
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
```

---

## Production Overlay: `overlays/prod/kustomization.yaml`

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - ../../base

namespace: my-app-prod

namePrefix: prod-

images:
  - name: my-app
    newTag: "v1.2.3"
    digest: sha256:abc123...  # Pin by digest for supply chain security
  - name: postgres
    newTag: "15-alpine"

commonLabels:
  environment: production

# Production ConfigMap overrides
configMapGenerator:
  - name: my-app-config
    behavior: merge
    literals:
      - LOG_LEVEL=warn
      - LOG_FORMAT=json
      - METRICS_ENABLED=true
      - RATE_LIMIT_ENABLED=true

# Production secrets via ExternalSecretsOperator (no literal values!)
# secretGenerator removed — managed by ExternalSecretsOperator

# Production patches
patches:
  - path: patches/replicas.yaml
    target:
      kind: Deployment
      name: my-app
  - path: patches/resources.yaml
    target:
      kind: Deployment
      name: my-app
  - path: patches/security.yaml
    target:
      kind: Deployment
      name: my-app

# Production-only resources
resources:
  - ../../base
  - prod-only-resources.yaml

# Transformers for production
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
```

### `overlays/prod/patches/replicas.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
spec:
  replicas: 5
```

### `overlays/prod/patches/resources.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
spec:
  template:
    spec:
      containers:
        - name: my-app
          resources:
            requests:
              cpu: "500m"
              memory: "512Mi"
            limits:
              cpu: "2000m"
              memory: "2Gi"
```

### `overlays/prod/patches/security.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
spec:
  template:
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        runAsGroup: 1000
        fsGroup: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: my-app
          securityContext:
            allowPrivilegeEscalation: false
            capabilities:
              drop: ["ALL"]
            readOnlyRootFilesystem: true
            runAsNonRoot: true
            runAsUser: 1000
            runAsGroup: 1000
```

---

## Production Hardening Checklist (from specs/05-hardened-manifests.md)

| Control | Implemented in Boilerplate | Location |
|---------|---------------------------|----------|
| Non-root user | ✅ | deployment.yaml `securityContext` |
| Read-only root filesystem | ✅ | deployment.yaml `readOnlyRootFilesystem: true` |
| Drop ALL capabilities | ✅ | deployment.yaml `capabilities.drop: ["ALL"]` |
| Resource requests/limits | ✅ | deployment.yaml `resources` |
| Readiness/Liveness/Startup probes | ✅ | deployment.yaml probes |
| PodDisruptionBudget | ✅ | pdb.yaml |
| HorizontalPodAutoscaler | ✅ | hpa.yaml |
| NetworkPolicy (default deny) | ✅ | networkpolicy.yaml |
| ServiceMonitor for Prometheus | ✅ | servicemonitor.yaml |
| SecurityContext (pod + container) | ✅ | deployment.yaml |
| Image digest pinning | ✅ | overlay `images.digest` |
| Anti-affinity for HA | ✅ | deployment.yaml `podAntiAffinity` |
| Checksum annotations for config reload | ✅ | deployment.yaml annotations |
| RBAC (ServiceAccount) | ⬜ Add to base | deployment.yaml `serviceAccountName` |
| ExternalSecretsOperator integration | ✅ | overlay removes secretGenerator |
| Checksum-based rolling restarts | ✅ | deployment.yaml annotations |
| PodSecurity Standards (restricted) | ⬜ Namespace label | Namespace manifest |

---

## Common Commands

```bash
# Render manifests (dry-run)
kubectl kustomize overlays/prod

# Apply to cluster
kubectl apply -k overlays/prod

# Preview changes (diff)
kubectl kustomize overlays/prod | kubectl diff -f -

# Validate manifests
kubectl kustomize overlays/prod | kubeval --strict

# Build and save to file
kubectl kustomize overlays/prod > /tmp/prod-manifests.yaml

# View all resources that would be created
kubectl kustomize overlays/prod | kubectl get -f - -o wide
```

---

## Production Deployment Workflow

```bash
# 1. Update overlay with new image tag/digest
cd overlays/prod
# Edit kustomization.yaml: newTag + digest

# 2. Preview changes
kubectl kustomize . | kubectl diff -f -

# 3. Apply
kubectl apply -k .

# 4. Monitor rollout
kubectl rollout status deployment/my-app -n my-app-prod

# 5. Verify
kubectl get pods -n my-app-prod -l app.kubernetes.io/name=my-app
kubectl logs -n my-app-prod -l app.kubernetes.io/name=my-app -f
```

---

## Key References

- [Kustomize Documentation](https://kustomize.io/)
- [Kubernetes Kustomize Guide](https://kubernetes.io/docs/tasks/manage-kubernetes-objects/kustomization/)
- [Kustomize API Reference](https://github.com/kubernetes-sigs/kustomize/blob/master/docs/api.md)
- [specs/05-hardened-manifests.md](../specs/05-hardened-manifests.md) — Full hardening checklist
- [specs/08-shared-service-hardening.md](../specs/08-shared-service-hardening.md) — Shared service requirements

---

> **Next**: [02-kustomize-advanced.md](02-kustomize-advanced.md) — Transformers, validators, Kustomize + Helm integration