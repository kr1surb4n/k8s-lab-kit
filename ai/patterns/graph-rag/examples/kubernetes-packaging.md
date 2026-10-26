# Example: Kubernetes packaging (offline rendering & validation)

The Graph RAG API includes a Kustomize base in `ai/patterns/graph-rag/k8s/`
that can be rendered and validated without a running cluster. Minikube is not
required for this step.

## What the base contains

| Manifest | Purpose |
|---|---|
| `deployment.yaml` | Non-root Deployment with probes, resource limits, read-only root filesystem |
| `service.yaml` | ClusterIP Service + headless Service for pod-to-pod communication |
| `configmap.yaml` | Application settings (`APP_NAME`, `OTLP_ENDPOINT`, `LOG_LEVEL`, …) |
| `secret.yaml` | Placeholder credentials (`PGVECTOR_DSN`, `HF_TOKEN`, `JWT_SECRET`) |
| `rbac.yaml` | ServiceAccount, Role, RoleBinding scoped to the namespace |
| `hpa.yaml` | HorizontalPodAutoscaler on CPU, memory, and optional queue-depth metric |
| `networkpolicy.yaml` | Default-deny egress; allow DNS, OTel collector; ingress from same namespace |

## Offline validation

```bash
cd ai/patterns/graph-rag

# 1. Render the manifests
kubectl kustomize k8s > /tmp/graph-rag-rendered.yaml

# 2. Validate against the Kubernetes API schema (no cluster needed)
kubectl apply --dry-run=client -f /tmp/graph-rag-rendered.yaml

# 3. Check specific fields
yq '.spec.template.spec.securityContext.runAsNonRoot' /tmp/graph-rag-rendered.yaml
# → true
yq '.spec.template.spec.containers[0].securityContext.readOnlyRootFilesystem' /tmp/graph-rag-rendered.yaml
# → true
yq '.spec.template.spec.containers[0].securityContext.capabilities.drop' /tmp/graph-rag-rendered.yaml
# → [ALL]
yq '.spec.template.spec.containers[0].resources.requests.memory' /tmp/graph-rag-rendered.yaml
# → 1Gi
yq '.spec.template.spec.containers[0].resources.limits.memory' /tmp/graph-rag-rendered.yaml
# → 2Gi
```

Expected output of the dry-run:

```console
$ kubectl apply --dry-run=client -f /tmp/graph-rag-rendered.yaml
serviceaccount/graph-rag-api created (dry-run)
role.rbac.authorization.k8s.io/graph-rag-api created (dry-run)
rolebinding.rbac.authorization.k8s.io/graph-rag-api created (dry-run)
configmap/graph-rag-config created (dry-run)
secret/graph-rag-secrets created (dry-run)
service/graph-rag-api created (dry-run)
service/graph-rag-api-headless created (dry-run)
deployment.apps/graph-rag-api created (dry-run)
horizontalpodautoscaler.autoscaling/graph-rag-api-hpa created (dry-run)
networkpolicy.networking.k8s.io/graph-rag-api created (dry-run)
```

## Secrets handling

The Secret contains **placeholders only** (`changeme`). Before applying to a
real cluster:

```bash
# Generate a real JWT secret
openssl rand -base64 32

# Update the secret (or use SealedSecrets / External Secrets Operator)
kubectl -n k8s-lab create secret generic graph-rag-secrets \
  --from-literal=JWT_SECRET="$(openssl rand -base64 32)" \
  --from-literal=HF_TOKEN="your-hf-token" \
  --from-literal=PGVECTOR_DSN="postgresql://user:pass@host:5432/db" \
  --dry-run=client -o yaml | kubectl apply -f -
```

The ConfigMap and Secret are mounted via `envFrom` in the Deployment, so the
container sees them as environment variables.

## NetworkPolicy explained

```yaml
egress:
  - to:
      - namespaceSelector:
          matchLabels:
            kubernetes.io/metadata.name: default
    ports:
      - protocol: UDP
        port: 53          # DNS resolution
  - to:
      - namespaceSelector:
          matchLabels:
            kubernetes.io/metadata.name: observability
    ports:
      - protocol: TCP
        port: 4318        # OTLP/HTTP traces to the collector
```

The app runs without a database (the mockup uses in-memory data), so no
Postgres egress rule is included. When the Phase 17 retrieval service is
containerised, add an egress rule for the Postgres service/namespace.

## Resource profile for minikube (6 GiB)

The Deployment requests `500m CPU / 1Gi memory` and limits `1000m CPU / 2Gi
memory` per replica. With two replicas the base footprint is ~2 GiB, leaving
room for:

- Prometheus + Grafana + Loki + Tempo (observability stack) ~2–3 GiB
- A small Postgres instance if co-located ~1 GiB
- System daemons and kubelet overhead ~1 GiB

No GPU is requested; the mockup is CPU-only. When the real Phase 17 service is
built, add `nvidia.com/gpu: "1"` to requests/limits and a node-affinity
requiring the GPU label.

## Verify the Kustomize base is complete

```bash
# List all resources in the base
kubectl kustomize k8s | grep '^kind:' | sort | uniq -c
# Expected:
#       1 ConfigMap
#       1 Deployment
#       1 HorizontalPodAutoscaler
#       1 NetworkPolicy
#       1 Role
#       1 RoleBinding
#       1 Secret
#       1 Service
#       1 Service
#       1 ServiceAccount

# Ensure no duplicates
kubectl kustomize k8s | yq 'select(.metadata.name=="graph-rag-api") | .kind' | sort | uniq -c
# Each name should appear once per kind
```

## Next step: minikube overlay (not done)

A minikube overlay would:

- Reduce replicas to 1
- Reduce memory requests/limits
- Point `OTLP_ENDPOINT` at a local collector or disable it
- Remove the custom-metric HPA line (no Prometheus Adapter in minikube)
- Use a local image pull policy (`IfNotPresent`)

Create it as `k8s/overlays/minikube/kustomization.yaml` when you are ready to
test on the cluster.