# Spec: Hardened Manifests — Production Controls

## Problem Statement
The teaching manifests intentionally omit production controls. This spec defines the **complete set of hardened manifests** for each missing control, using the Graph RAG base (`ai/patterns/graph-rag/k8s/`) as the reference implementation, then propagated to boilerplates and stacks.

## Reference Implementation: Graph RAG Base (Current vs. Hardened)

### Current `ai/patterns/graph-rag/k8s/` (Teaching Grade)
```
k8s/
├── kustomization.yaml
├── deployment.yaml       # non-root, probes, resources, readOnlyRootFs, caps drop
├── service.yaml          # ClusterIP + headless
├── configmap.yaml        # APP_* env vars
├── secret.yaml           # placeholder stringData
├── rbac.yaml             # ServiceAccount, Role, RoleBinding
├── hpa.yaml              # CPU, memory, custom queue metric
└── networkpolicy.yaml    # DNS + OTel egress, same-ns ingress
```

### Hardened Target (Production Grade)
```
k8s/
├── kustomization.yaml
├── bases/
│   ├── deployment.yaml           # + image digest, PodSecurity labels, topology spread
│   ├── service.yaml              # unchanged
│   ├── configmap.yaml            # unchanged
│   ├── secret.yaml               # → ExternalSecret reference only
│   ├── rbac.yaml                 # + PodSecurityPolicy migration (restricted)
│   ├── hpa.yaml                  # + Prometheus Adapter, VPA
│   ├── networkpolicy.yaml        # + Postgres egress, per-tenant isolation
│   ├── pdb.yaml                  # NEW: PodDisruptionBudget
│   ├── ingress.yaml              # NEW: TLS, auth, rate limiting
│   ├── servicemonitor.yaml       # NEW: Prometheus scrape config
│   ├── podmonitor.yaml           # NEW: if needed
│   └── externalsecret.yaml       # NEW: ExternalSecretsOperator reference
├── overlays/
│   ├── minikube/                 # reduced resources, no GPU, no TLS
│   ├── staging/                  # 2 replicas, staging certs, staging secrets
│   └── production/               # 3+ replicas, prod certs, prod secrets, HA
└── policies/                     # Kyverno/OPA policies
    ├── require-image-digest.yaml
    ├── require-security-context.yaml
    ├── require-networkpolicy.yaml
    └── require-pdb.yaml
```

---

## Control-by-Control Hardening Specs

### 1. TLS (mTLS + Ingress Certs)

**Manifest: `bases/ingress.yaml`**
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: graph-rag-api
  namespace: k8s-lab
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/auth-type: "external"
    nginx.ingress.kubernetes.io/auth-url: "https://oauth2-proxy.k8s-lab/oauth2/auth"
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/rate-limit-window: "1m"
    nginx.ingress.kubernetes.io/limit-connections: "50"
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - graph-rag.lab.example.com
      secretName: graph-rag-api-tls
  rules:
    - host: graph-rag.lab.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: graph-rag-api
                port:
                  number: 80
```

**Requirements:**
- `cert-manager` installed with `ClusterIssuer` (Let's Encrypt or self-signed CA)
- `oauth2-proxy` deployed for authentication (see #2)
- Ingress controller (NGINX/Traefik) with rate-limit support

---

### 2. Authentication (OIDC/JWT via oauth2-proxy)

**Manifest: `oauth2-proxy/deployment.yaml` (separate component)**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: oauth2-proxy
  namespace: k8s-lab
spec:
  replicas: 2
  template:
    spec:
      containers:
        - name: oauth2-proxy
          image: quay.io/oauth2-proxy/oauth2-proxy:v7.8.0@sha256:...
          args:
            - --provider=oidc
            - --oidc-issuer-url=https://dex.k8s-lab.example.com
            - --client-id=graph-rag-api
            - --client-secret=$(OAUTH2_PROXY_CLIENT_SECRET)
            - --cookie-secret=$(OAUTH2_PROXY_COOKIE_SECRET)
            - --upstream=file:///dev/null  # auth only, no proxy
            - --http-address=0.0.0.0:4180
            - --authenticated-emails-file=/etc/oauth2-proxy/allowed-emails.txt
          envFrom:
            - secretRef:
                name: oauth2-proxy-secrets
```

**Integration:** Ingress `auth-url` points to `oauth2-proxy`; valid JWT → `X-Forwarded-User` header passed to backend.

---

### 3. Authorization (Per-Tenant RBAC)

**Manifest: `bases/rbac.yaml` (extended)**
```yaml
# Per-tenant Role (example for tenant-a)
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: graph-rag-api-tenant-a
  namespace: k8s-lab
rules:
  - apiGroups: [""]
    resources: ["configmaps", "secrets"]
    verbs: ["get", "list", "watch"]
    resourceNames: ["tenant-a-*"]  # name-prefix scoping
  - apiGroups: [""]
    resources: ["pods"]
    verbs: ["get", "list", "watch"]
    resourceNames: ["graph-rag-api-tenant-a-*"]
---
# RoleBinding per tenant
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: graph-rag-api-tenant-a-binding
  namespace: k8s-lab
subjects:
  - kind: Group
    name: "tenant-a-users"  # from OIDC groups claim
    apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: graph-rag-api-tenant-a
  apiGroup: rbac.authorization.k8s.io
```

**Pattern:** Namespace-per-tenant is cleaner; this shows in-namespace tenancy via name prefixes + RBAC.

---

### 4. NetworkPolicy (Default-Deny + Explicit Allow)

**Manifest: `bases/networkpolicy.yaml` (hardened)**
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: graph-rag-api-deny-all
  namespace: k8s-lab
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
  # No ingress/egress rules = default deny
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: graph-rag-api-allow
  namespace: k8s-lab
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: graph-rag-api
  policyTypes: [Ingress, Egress]
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: ingress-nginx
      ports:
        - protocol: TCP
          port: 8000
    - from:
        - podSelector:
            matchLabels:
              app.kubernetes.io/name: prometheus
      ports:
        - protocol: TCP
          port: 8000
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: default
      ports:
        - protocol: UDP
          port: 53
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: observability
      ports:
        - protocol: TCP
          port: 4318
    - to:
        - podSelector:
            matchLabels:
              app.kubernetes.io/name: postgres-age
      ports:
        - protocol: TCP
          port: 5432
```

---

### 5. PodDisruptionBudget (PDB)

**Manifest: `bases/pdb.yaml`**
```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: graph-rag-api
  namespace: k8s-lab
spec:
  minAvailable: 1  # or maxUnavailable: 25%
  selector:
    matchLabels:
      app.kubernetes.io/name: graph-rag-api
```

**Rule:** Every Deployment with `replicas > 1` must have a PDB.

---

### 6. Ingress (see TLS above)

---

### 7. HPA + VPA (Vertical Pod Autoscaler)

**Manifest: `bases/hpa.yaml` (extended)**
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: graph-rag-api
  namespace: k8s-lab
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: graph-rag-api
  minReplicas: 2
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
    - type: Pods
      pods:
        metric:
          name: graph_rag_queue_depth
        target:
          type: AverageValue
          averageValue: "10"
```

**VPA Manifest: `bases/vpa.yaml`**
```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: graph-rag-api
  namespace: k8s-lab
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: graph-rag-api
  updatePolicy:
    updateMode: "Auto"  # or "Initial" for restart-only
  resourcePolicy:
    containerPolicies:
      - containerName: graph-rag-api
        minAllowed:
          cpu: "100m"
          memory: "256Mi"
        maxAllowed:
          cpu: "2000m"
          memory: "4Gi"
        controlledResources: ["cpu", "memory"]
```

---

### 8. securityContext (Already in Graph RAG base — propagate)

**Checklist for all Deployments:**
- [ ] `podSecurityContext.runAsNonRoot: true`
- [ ] `podSecurityContext.runAsUser: 1000`
- [ ] `podSecurityContext.runAsGroup: 1000`
- [ ] `podSecurityContext.fsGroup: 1000`
- [ ] `containerSecurityContext.allowPrivilegeEscalation: false`
- [ ] `containerSecurityContext.capabilities.drop: ["ALL"]`
- [ ] `containerSecurityContext.readOnlyRootFilesystem: true`
- [ ] `containerSecurityContext.runAsNonRoot: true`

---

### 9. Image Digest Pinning

**Manifest: `bases/deployment.yaml` (patch)**
```yaml
# In kustomization.yaml patches:
- op: replace
  path: /spec/template/spec/containers/0/image
  value: boilerplate/graph-rag-api@sha256:a1b2c3d4e5f6...
```

**Automation:** CI pipeline computes digest on build and updates kustomization.

---

### 10. Secret Manager (External Secrets Operator)

**Manifest: `bases/externalsecret.yaml`**
```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: graph-rag-secrets
  namespace: k8s-lab
spec:
  refreshInterval: 1h
  secretStoreRef:
    kind: ClusterSecretStore
    name: vault-backend  # or aws-secretsmanager, gcp-secretsmanager
  target:
    name: graph-rag-secrets
    creationPolicy: Owner
  data:
    - secretKey: PGVECTOR_DSN
      remoteRef:
        key: graph-rag/prod
        property: pgvector_dsn
    - secretKey: HF_TOKEN
      remoteRef:
        key: graph-rag/prod
        property: hf_token
    - secretKey: JWT_SECRET
      remoteRef:
        key: graph-rag/prod
        property: jwt_secret
```

**ClusterSecretStore (cluster-scoped):**
```yaml
apiVersion: external-secrets.io/v1beta1
kind: ClusterSecretStore
metadata:
  name: vault-backend
spec:
  provider:
    vault:
      server: "https://vault.k8s-lab.example.com"
      path: "secret"
      version: "v2"
      auth:
        kubernetes:
          mountPath: "kubernetes"
          role: "external-secrets"
```

---

### 11. Backup/Restore

**Velero Backup (cluster-level):**
```yaml
# velero/backup-schedule.yaml
apiVersion: velero.io/v1
kind: Schedule
metadata:
  name: graph-rag-daily
  namespace: velero
spec:
  schedule: "0 2 * * *"  # daily 02:00
  template:
    includedNamespaces:
      - k8s-lab
    labelSelector:
      matchLabels:
        app.kubernetes.io/name: graph-rag-api
    ttl: 720h  # 30 days
```

**Postgres Backup (app-level):**
```yaml
# postgres/backup-cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: postgres-backup
  namespace: k8s-lab
spec:
  schedule: "0 3 * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
            - name: pgdump
              image: postgres:16@sha256:...
              env:
                - name: PGPASSWORD
                  valueFrom:
                    secretKeyRef:
                      name: graph-rag-secrets
                      key: POSTGRES_PASSWORD
              command:
                - /bin/sh
                - -c
                - |
                  pg_dump -h postgres-age -U graph_rag graph_rag \
                    | gzip > /backups/graph_rag-$(date +%F).sql.gz
                  # Upload to S3/GCS/Azure Blob
          restartPolicy: OnFailure
          volumes:
            - name: backups
              persistentVolumeClaim:
                claimName: backup-pvc
```

---

### 12. Multi-User / Multi-Tenant Isolation

**Pattern: Namespace per Tenant**
```
tenant-a/
├── namespace.yaml
├── networkpolicy.yaml      # deny all, allow only tenant-a pods
├── resourcequota.yaml      # CPU, memory, PVC, secrets limits
├── limitrange.yaml         # default requests/limits
├── rbac.yaml               # tenant-a Role + RoleBinding
└── graph-rag-api/          # tenant-specific deployment (or shared with authZ)
```

**Shared Service with Tenancy:** Graph RAG API runs once; tenancy enforced at application layer (JWT claims → namespace/db filtering).

---

### 13. Rate Limiting

**In Ingress (see TLS/Ingress above):**
```yaml
annotations:
  nginx.ingress.kubernetes.io/rate-limit: "100"
  nginx.ingress.kubernetes.io/rate-limit-window: "1m"
  nginx.ingress.kubernetes.io/limit-connections: "50"
```

**Application-level (Graph RAG API):**
```python
# In FastAPI app
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/v1/ask")
@limiter.limit("30/minute")
async def api_ask(request: Request, ...):
    ...
```

---

### 14. Audit Logging

**Kube-apiserver Audit Policy:**
```yaml
# audit-policy.yaml
apiVersion: audit.k8s.io/v1
kind: Policy
rules:
  - level: Metadata
    resources:
      - group: ""
        resources: ["secrets", "configmaps"]
  - level: RequestResponse
    resources:
      - group: ""
        resources: ["pods/exec", "pods/portforward"]
  - level: None
    users: ["system:kube-scheduler", "system:kube-controller-manager"]
```

**App-level Audit (Graph RAG):**
```python
# Structured log, NO document text
LOGGER.info(json.dumps({
    "event": "query",
    "trace_id": trace_id,
    "user": user_id,  # from JWT
    "corpus": corpus,
    "latency_ms": latency,
    "refused": refused,
    "citations_count": len(citations),
    # NO question text, NO answer text, NO passage text
}))
```

---

### 15. Durable Long-Term Storage

**PVC with StorageClass + VolumeSnapshot:**
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-data
  namespace: k8s-lab
spec:
  accessModes: ["ReadWriteOnce"]
  storageClassName: "fast-rwo"  # CSI driver with snapshots
  resources:
    requests:
      storage: 20Gi
---
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshotClass
metadata:
  name: csi-snapshot-class
driver: pd.csi.storage.gke.io  # or ebs.csi.aws.com, disk.csi.azure.com
deletionPolicy: Delete
```

---

### 16. HA Monitoring

**Prometheus HA (remote write to object storage):**
```yaml
# prometheus/remote-write.yaml
apiVersion: monitoring.coreos.com/v1
kind: Prometheus
spec:
  replicas: 2
  remoteWrite:
    - url: https://cortex.k8s-lab.example.com/api/prom/push
      # or Thanos receive, Mimir, S3
```

**Alertmanager HA:**
```yaml
# alertmanager/ha.yaml
apiVersion: monitoring.coreos.com/v1
kind: Alertmanager
spec:
  replicas: 3
  # gossip mesh for deduplication
```

---

### 17. Hardened Bastion

**Components:**
- **Teleport** or **Boundary** for certificate-based SSH, MFA, session recording
- **Just-in-time access** via `teleport request` / `boundary connect`
- **Audit log** of all sessions (stored in immutable bucket)
- **No long-lived SSH keys** — short-lived certs only

**Manifest: `bastion/teleport.yaml` (simplified)**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: teleport
  namespace: k8s-lab
spec:
  replicas: 2
  template:
    spec:
      containers:
        - name: teleport
          image: goteleport/teleport:16@sha256:...
          command: ["teleport", "start", "--roles=proxy,auth,node"]
          env:
            - name: TELEPORT_CLUSTER_NAME
              value: k8s-lab
          volumeMounts:
            - name: data
              mountPath: /var/lib/teleport
      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: teleport-data
```

---

### 18. Multiple Namespaces

**Structure:**
```
namespaces/
├── k8s-lab.yaml           # lab workloads
├── observability.yaml     # Prometheus, Grafana, Loki, Tempo
├── ingress-nginx.yaml     # ingress controller
├── cert-manager.yaml      # cert-manager
├── external-secrets.yaml  # ESO
├── velero.yaml            # backup
├── tenant-a.yaml          # tenant A
├── tenant-b.yaml          # tenant B
└── platform.yaml          # operators, CRDs, shared services
```

**Each namespace gets:**
- `ResourceQuota`
- `LimitRange`
- `NetworkPolicy` (default deny)
- `PodSecurity` labels (`enforce: restricted`)

---

### 19. Image Signature Verification (cosign + Kyverno)

**Kyverno Policy:**
```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-image-signature
spec:
  validationFailureAction: Enforce
  rules:
    - name: verify-cosign-signature
      match:
        any:
          - resources:
              kinds: ["Pod"]
      verifyImages:
        - image: "*"
          key: |-
            -----BEGIN PUBLIC KEY-----
            ...
            -----END PUBLIC KEY-----
          annotations:
            - "sigstore.dev/cert-identity=*"
            - "sigstore.dev/cert-identity-regexp=.*"
```

---

### 20. PodSecurity Standards (Restricted)

**Namespace Labels:**
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: k8s-lab
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

**Effect:** Blocks any pod that doesn't meet `restricted` profile (non-root, no priv caps, read-only rootfs, etc.).

---

## Propagation Plan

| Target | Action |
|---|---|
| `ai/patterns/graph-rag/k8s/` | Implement all 20 controls as reference |
| `boilerplates/base/` | Add base hardened manifests |
| `boilerplates/stacks/*/` | Each stack gets overlay with its specifics |
| `paczki/k8s/` | Package templates include hardened base |
| `docs/hardening-guide.md` | New document: how to apply, customize, validate |

## Validation (Added to `make test`)

```makefile
# New targets
hardened-lint:
	kubectl kustomize ai/patterns/graph-rag/k8s/bases | kubeval --strict
	kubectl kustomize ai/patterns/graph-rag/k8s/bases | conftest test -p policies/
	kubectl kustomize ai/patterns/graph-rag/k8s/overlays/production | kubeval --strict

test: hardened-lint ...
```

## Acceptance Criteria
- Graph RAG base (`bases/`) passes `kubeval`, `conftest`, `kubectl apply --dry-run=client`
- Each control has a manifest in `bases/` or `policies/`
- Overlays (`minikube/`, `staging/`, `production/`) demonstrate environment-specific values
- `make test` includes manifest validation
- Documentation in `docs/hardening-guide.md` explains each control and how to adopt

## References
- `specs/02-missing-controls.md` — inventory source
- `ai/patterns/graph-rag/k8s/` — current teaching base
- `boilerplates/` — templates to propagate to
- Kubernetes PodSecurity Standards: <https://kubernetes.io/docs/concepts/security/pod-security-standards/>
- Kyverno policies: <https://kyverno.io/policies/>
- External Secrets Operator: <https://external-secrets.io/>
- cert-manager: <https://cert-manager.io/>