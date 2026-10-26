# Spec: Shared-Service Hardening Manual

## Problem Statement
The repository states: "If you need a shared service, add at minimum: authentication and per-user authorization; TLS and network restrictions; per-tenant data isolation and retention rules; audit logging that does not leak document text; rate limits and request size limits; a secret manager for model/provider credentials; a packaging and migration plan; a privacy review before any remote model or provider is used."

This spec is a **practical manual** for hardening any shared service (Graph RAG API, or any other) to meet these requirements.

---

## 1. Authentication & Per-User Authorization

### Architecture
```
Client → Ingress (TLS) → oauth2-proxy (OIDC) → Backend (JWT validation + RBAC)
```

### Components

| Component | Technology | Config |
|---|---|---|
| Identity Provider | Dex, Keycloak, or cloud (Google, GitHub, Azure AD) | OIDC issuer, client ID/secret |
| Edge Auth | `oauth2-proxy` (sidecar or separate deployment) | `--provider=oidc`, `--oidc-issuer-url`, `--client-id`, `--cookie-secret` |
| Token Validation | Backend middleware (FastAPI `Depends`) | Verify JWT signature, `aud`, `exp`, `iss` |
| Authorization | Application-layer RBAC | Map JWT `groups` claim → tenant/role |

### Implementation (FastAPI Example)
```python
# auth.py
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from jwt import PyJWKClient

security = HTTPBearer(auto_error=False)
jwks_client = PyJWKClient("https://dex.k8s-lab.example.com/keys")

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(401, "Missing Authorization header")
    token = credentials.credentials
    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience="graph-rag-api",
            issuer="https://dex.k8s-lab.example.com",
        )
    except jwt.PyJWTError as e:
        raise HTTPException(401, f"Invalid token: {e}")
    return payload  # contains: sub, email, groups, tenant_id

# Per-endpoint authorization
def require_tenant(tenant_id: str):
    def checker(user: dict = Depends(get_current_user)):
        if user.get("tenant_id") != tenant_id and "admin" not in user.get("groups", []):
            raise HTTPException(403, "Tenant mismatch")
    return checker

# Usage
@app.post("/v1/ask")
async def api_ask(
    request: AskRequest,
    user: dict = Depends(get_current_user),
    _: None = Depends(require_tenant("tenant-a")),  # or from request.corpus
):
    ...
```

### Dex Configuration (IdP)
```yaml
# dex/config.yaml
issuer: https://dex.k8s-lab.example.com
storage:
  type: kubernetes
  config:
    inCluster: true
connectors:
  - type: github
    id: github
    name: GitHub
    config:
      clientID: $GITHUB_CLIENT_ID
      clientSecret: $GITHUB_CLIENT_SECRET
      redirectURI: https://dex.k8s-lab.example.com/callback
      orgs:
        - name: my-org
          teams:
            - tenant-a-users
            - tenant-b-users
            - admins
oauth2:
  skipApprovalScreen: true
staticClients:
  - id: graph-rag-api
    redirectURIs:
      - https://graph-rag.lab.example.com/oauth2/callback
    name: Graph RAG API
    secret: $OAUTH2_PROXY_CLIENT_SECRET
```

---

## 2. TLS & Network Restrictions

### TLS Everywhere

| Layer | Implementation |
|---|---|
| **Ingress** | cert-manager + Let's Encrypt (prod) / self-signed CA (lab) |
| **Service-to-service** | mTLS via service mesh (Linkerd/Istio) or manual certs |
| **Database** | Postgres `sslmode=verify-full` + client certs |
| **Object Storage** | HTTPS only (S3/OCI/GCS) |

### Ingress TLS (cert-manager)
```yaml
# ClusterIssuer (Let's Encrypt prod)
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: ops@example.com
    privateKeySecretRef:
      name: letsencrypt-prod-key
    solvers:
      - http01:
          ingress:
            class: nginx
---
# Certificate (auto-created by Ingress annotation)
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
    - hosts: [graph-rag.lab.example.com]
      secretName: graph-rag-api-tls
```

### Network Restrictions (NetworkPolicy)
```yaml
# Default deny all
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
---
# Allow specific ingress
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: graph-rag-api-ingress
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: graph-rag-api
  policyTypes: [Ingress]
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: ingress-nginx
      ports:
        - protocol: TCP
          port: 8000
---
# Allow specific egress
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: graph-rag-api-egress
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: graph-rag-api
  policyTypes: [Egress]
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: default
      ports:
        - protocol: UDP
          port: 53  # DNS
    - to:
        - podSelector:
            matchLabels:
              app.kubernetes.io/name: postgres-age
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

---

## 3. Per-Tenant Data Isolation & Retention

### Database-Level Isolation (Preferred)
```sql
-- One database per tenant (physical isolation)
CREATE DATABASE graphrag_tenant_a;
CREATE DATABASE graphrag_tenant_b;
-- Each gets own user, own connection pool
```

### Schema-Level Isolation (If Shared DB)
```sql
-- One schema per tenant
CREATE SCHEMA tenant_a AUTHORIZATION graphrag;
CREATE SCHEMA tenant_b AUTHORIZATION graphrag;
-- Row-level security
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON documents
  USING (current_setting('app.current_tenant') = tenant_id);
-- Set via: SET LOCAL app.current_tenant = 'tenant_a';
```

### Application-Level Isolation (Graph RAG Pattern)
```python
# In retrieval.py search()/answer()
def dsn_for_tenant(tenant_id: str) -> str:
    return settings.databases[f"tenant_{tenant_id}"]  # separate DSN per tenant

# Or filter by corpus column (current lab pattern)
corpus = f"tenant_{tenant_id}_notes"
# CLI/API rejects cross-tenant corpus access
```

### Retention Rules
| Data Type | Retention | Implementation |
|---|---|---|
| Documents/chunks | Per-tenant config (default 1 year) | TTL column + nightly cron `DELETE WHERE created_at < now() - interval` |
| Embeddings | Same as documents | Cascading delete via FK |
| Graph edges | Same as documents | Cascading delete via FK |
| Query logs (audit) | 90 days | Loki retention + compaction |
| Metrics | 15 days (Prometheus), 1 year (downsampled) | Thanos/Cortex retention |

---

## 4. Audit Logging (No Document Text Leakage)

### Principles
- **Never log**: question text, answer text, passage text, document content
- **Always log**: user ID, tenant ID, trace ID, timestamps, counts, decisions
- **Structured JSON** for parsing/alerting

### Implementation
```python
# telemetry.py / retrieval.py _log()
AUDIT_LOGGER = logging.getLogger("graphrag.audit")

def audit_log(event: str, user: dict, **fields):
    AUDIT_LOGGER.info(json.dumps({
        "event": event,
        "timestamp": time.time(),
        "trace_id": current_trace_id() or "",
        "user_id": user.get("sub"),
        "tenant_id": user.get("tenant_id"),
        "groups": user.get("groups", []),
        **fields,  # counts, latency, refused, etc.
    }, ensure_ascii=False))

# Usage in answer()
audit_log(
    "query_answered",
    user,
    corpus=corpus,
    latency_ms=latency,
    citations_count=len(citations),
    graph_path_count=len(graph_path),
    refused=refused,
    graph_error=response.get("graph_error"),
    # NO: question, answer, passage text, chunk text
)
```

### Log Forwarding (Loki)
```yaml
# promtail config
clients:
  - url: http://loki.observability:3100/loki/api/v1/push
scrape_configs:
  - job_name: graphrag-audit
    static_configs:
      - targets: [localhost]
        labels:
          job: graphrag-audit
          __path__: /var/log/graphrag/audit.log
    pipeline_stages:
      - json:
          expressions:
            trace_id: trace_id
            user_id: user_id
            tenant_id: tenant_id
            event: event
```

---

## 5. Rate Limits & Request Size Limits

### Ingress Level (NGINX)
```yaml
annotations:
  nginx.ingress.kubernetes.io/rate-limit: "100"
  nginx.ingress.kubernetes.io/rate-limit-window: "1m"
  nginx.ingress.kubernetes.io/limit-connections: "50"
  nginx.ingress.kubernetes.io/proxy-body-size: "1m"  # max request body
```

### Application Level (FastAPI + slowapi)
```python
# main.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(
    key_func=lambda r: r.headers.get("X-Forwarded-User", get_remote_address(r)),
    default_limits=["100/minute", "1000/hour"],
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Per-endpoint limits
@app.post("/v1/ask")
@limiter.limit("30/minute;100/hour")
async def api_ask(request: Request, ...):
    ...

@app.post("/v1/search")
@limiter.limit("60/minute;500/hour")
async def api_search(request: Request, ...):
    ...

@app.post("/v1/graph-rag/ingest")
@limiter.limit("10/minute;50/hour")
async def api_ingest(request: Request, ...):
    ...
```

### Tenant-Aware Limits (Redis-backed)
```python
# For distributed rate limiting across replicas
import redis.asyncio as redis
from slowapi import Limiter
from slowapi.util import get_remote_address

redis_client = redis.from_url("redis://redis.k8s-lab:6379")

def tenant_key_func(request: Request) -> str:
    user = request.state.user  # set by auth middleware
    return f"ratelimit:{user['tenant_id']}:{user['sub']}"

limiter = Limiter(key_func=tenant_key_func, storage_uri="redis://redis.k8s-lab:6379")
```

---

## 6. Secret Manager for Model/Provider Credentials

### External Secrets Operator (Recommended)
```yaml
# ClusterSecretStore (cluster-scoped)
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
---
# ExternalSecret (namespace-scoped)
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: graph-rag-secrets
  namespace: k8s-lab
spec:
  refreshInterval: 1h
  secretStoreRef:
    kind: ClusterSecretStore
    name: vault-backend
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
    - secretKey: OIDC_CLIENT_SECRET
      remoteRef:
        key: oauth2-proxy/prod
        property: client_secret
    - secretKey: OIDC_COOKIE_SECRET
      remoteRef:
        key: oauth2-proxy/prod
        property: cookie_secret
```

### Vault Path Structure
```
secret/
├── graph-rag/
│   ├── prod/
│   │   ├── pgvector_dsn
│   │   ├── hf_token
│   │   └── jwt_secret
│   └── staging/
├── oauth2-proxy/
│   ├── prod/
│   │   ├── client_secret
│   │   └── cookie_secret
│   └── staging/
└── observability/
    ├── grafana_admin_password
    └── alertmanager_webhook_url
```

### Rotation
- `refreshInterval: 1h` in ExternalSecret
- Vault TTL on dynamic secrets (DB creds: 1h)
- Manual rotation: `kubectl delete secret graph-rag-secrets -n k8s-lab` → ESO recreates

---

## 7. Packaging & Migration Plan

### Packaging: Helm Chart from Kustomize
```bash
# Convert Kustomize base to Helm chart
mkdir -p helm/graph-rag-api/{templates,values}
kubectl kustomize k8s/bases --output helm/graph-rag-api/templates/
# Edit templates: replace hardcoded values with {{ .Values.xxx }}
# Create values.yaml with defaults
# Create values-{dev,staging,prod}.yaml
```

### Helm Chart Structure
```
helm/graph-rag-api/
├── Chart.yaml
├── values.yaml              # defaults
├── values-dev.yaml
├── values-staging.yaml
├── values-prod.yaml
├── templates/
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── configmap.yaml
│   ├── secret.yaml          # only if not using ESO
│   ├── rbac.yaml
│   ├── hpa.yaml
│   ├── networkpolicy.yaml
│   ├── pdb.yaml
│   ├── ingress.yaml
│   ├── servicemonitor.yaml
│   ├── externalsecret.yaml
│   └── _helpers.tpl
└── charts/                  # dependencies (postgres, redis, etc.)
```

### Migration Plan (Schema + Data)
```sql
-- schema_migrations table tracks version
-- Each migration: up.sql / down.sql in db/migrations/
-- Versioned: V001__initial.sql, V002__add_page_numbers.sql

-- Migration runner (in app startup or init container)
-- 1. Check current version
-- 2. Apply pending migrations in order
-- 3. Record version
-- 4. Fail fast on error (no partial apply)

-- Example migration:
-- V003__add_tenant_id.sql
ALTER TABLE documents ADD COLUMN tenant_id text;
CREATE INDEX idx_documents_tenant ON documents(tenant_id);
-- Backfill existing rows
UPDATE documents SET tenant_id = 'legacy' WHERE tenant_id IS NULL;
ALTER TABLE documents ALTER COLUMN tenant_id SET NOT NULL;
```

### Rollback Procedure
```bash
# Helm rollback
helm rollback graph-rag-api 3 -n k8s-lab

# Database rollback (if migration has down.sql)
psql -f db/migrations/V003__add_tenant_id.down.sql

# Full disaster recovery
velero restore create --from-backup graph-rag-daily-2026-10-25
```

---

## 8. Privacy Review Before Remote Model/Provider

### Checklist (Run Before Any Remote Call)

| Question | Yes/No | Evidence |
|---|---|---|
| Does the remote model receive **document text**? | | |
| Does the remote model receive **user questions**? | | |
| Is there a **Data Processing Agreement (DPA)**? | | |
| Is data **encrypted in transit** (TLS 1.2+)? | | |
| Is data **encrypted at rest** by provider? | | |
| Can you **opt out of training**? | | |
| Is there a **data residency** guarantee? | | |
| What is the **retention period** for logs/prompts? | | |
| Can you **delete data** on demand? | | |
| Is the provider **SOC2/ISO27001** certified? | | |

### Decision Matrix

| Use Case | Local Model OK? | Remote Model Allowed? | Conditions |
|---|---|---|---|
| Private notes Q&A | ✅ | ❌ | Never — data leaves machine |
| Public docs Q&A | ✅ | ⚠️ | Only with DPA, opt-out, EU residency |
| Embeddings for public corpus | ✅ | ⚠️ | Same as above |
| Reranking public candidates | ✅ | ⚠️ | Same as above |
| Code generation (no private context) | ✅ | ✅ | If no private data in prompt |

### Enforcement in Code
```python
# config.py - model registry with privacy tags
MODEL_REGISTRY = {
    "bge-m3-local": {"privacy": "local", "type": "embed"},
    "granite3.3-8b-local": {"privacy": "local", "type": "generate"},
    "qwen3-8b-local": {"privacy": "local", "type": "generate"},
    "gpt-4o": {"privacy": "remote", "type": "generate", "allowed_corpora": ["public"]},
    "text-embedding-3-large": {"privacy": "remote", "type": "embed", "allowed_corpora": ["public"]},
}

def validate_model_corpus(model: str, corpus: str) -> None:
    info = MODEL_REGISTRY.get(model, {"privacy": "unknown"})
    if info["privacy"] == "remote" and corpus in PRIVATE_CORPORA:
        raise ValueError(f"Remote model {model} cannot be used with private corpus {corpus}")
```

---

## Hardening Checklist (Per Service)

| Control | Graph RAG API | Postgres | Prometheus | Grafana | Loki | Tempo |
|---|---|---|---|---|---|---|
| Auth (OIDC) | ✅ oauth2-proxy | ❌ (internal) | ✅ oauth2-proxy | ✅ built-in | ❌ (internal) | ❌ (internal) |
| TLS (mTLS) | ✅ Ingress + mesh | ✅ sslmode=verify-full | ✅ mesh | ✅ Ingress | ✅ mesh | ✅ mesh |
| NetworkPolicy | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| PDB | ✅ | ⚠️ (Patroni) | ✅ | ✅ | ✅ | ✅ |
| Secret Manager | ✅ ESO | ✅ ESO | ✅ ESO | ✅ ESO | ✅ ESO | ✅ ESO |
| Audit Logging | ✅ (no text) | ✅ pgAudit | ✅ | ✅ | ✅ | ✅ |
| Rate Limits | ✅ (ingress + app) | ❌ | ❌ | ✅ | ❌ | ❌ |
| Image Digest | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| PodSecurity | ✅ restricted | ✅ restricted | ✅ restricted | ✅ restricted | ✅ restricted | ✅ restricted |
| Backup | ❌ (stateless) | ✅ pg_dump + PVC snap | ✅ Velero | ✅ Velero | ✅ Velero | ✅ Velero |
| Image Verify | ✅ cosign | ✅ cosign | ✅ cosign | ✅ cosign | ✅ cosign | ✅ cosign |

---

## Acceptance Criteria
- Manual exists at `docs/shared-service-hardening.md`
- Each of the 8 requirements has: explanation, architecture, manifests, code snippets
- Graph RAG API demonstrates all 8 controls
- Checklist can be copied for new services
- Privacy review checklist is enforced in CI (model registry validation)

## References
- `specs/05-hardened-manifests.md` — manifest implementations
- `specs/06-cloud-provider-template.md` — cloud deployment with these controls
- OAuth2-Proxy: <https://oauth2-proxy.github.io/oauth2-proxy/>
- External Secrets Operator: <https://external-secrets.io/>
- cert-manager: <https://cert-manager.io/>
- Kyverno policies: <https://kyverno.io/policies/>
- SlowAPI (rate limiting): <https://github.com/laursen/slowapi>