# Spec: Missing Controls Inventory

## Problem Statement
The teaching manifests in this repository intentionally omit production controls for clarity. This spec inventories every missing control, maps it to the manifests that need it, and defines what "adding it" means.

## Source of Truth
The following statements in repo documents list missing controls:

| Source | Missing Controls Listed |
|---|---|
| `analysis/07-what-to-do.md` §3 (Phase 17.7) | NetworkPolicy, Secrets via `Secret` (`envFrom`), non-root, probes, resource requests/limits |
| `docs/REPO-STATE.md` row 9 | no TLS, no auth, no backup, no NetworkPolicy, no PDB |
| `docs/REPO-STATE.md` row 10 | no Ingress, no NetworkPolicy, no PDB, no HPA, no securityContext, no image digest, no secret manager |
| `docs/REPO-STATE.md` row 11 | no policy objects, no production secrets, no backup |
| `docs/REPO-STATE.md` row 12 | no multi-user isolation, no TLS, no rate limits, private data |
| `analysis/06-scope-expansion.md` R18 | no highly available monitoring, durable long-term storage, tenant isolation |
| `guides/real-world-use.md` | hardened bastion, multiple namespaces |

## Consolidated Missing Controls Inventory

| # | Control | Category | Manifest(s) to Update | Notes |
|---|---|---|---|---|
| 1 | **TLS (mTLS + ingress certs)** | Security | `service.yaml`, new `ingress.yaml`, `cert-manager` resources | cert-manager + Let's Encrypt or self-signed CA |
| 2 | **Authentication (OIDC/JWT)** | Security | `deployment.yaml` (env), new `oauth2-proxy` or `auth-service` | Integrate with Dex/Keycloak or cloud IAP |
| 3 | **Authorization (RBAC per user/tenant)** | Security | `rbac.yaml` (expand), new `ClusterRole`/`RoleBinding` per tenant | Current RBAC is service-account only |
| 4 | **NetworkPolicy (default-deny + explicit allow)** | Network | `networkpolicy.yaml` (extend), per-namespace policies | Phase 17 base has one; need per-app + ingress/egress |
| 5 | **PodDisruptionBudget (PDB)** | Availability | New `pdb.yaml` per Deployment | `minAvailable: 1` or `maxUnavailable: 25%` |
| 6 | **Ingress (external access + TLS termination)** | Network | New `ingress.yaml` per service | NGINX or Traefik ingress controller |
| 7 | **HPA (HorizontalPodAutoscaler)** | Scaling | `hpa.yaml` (extend metrics) | Phase 17 has CPU/memory + custom; need Prometheus Adapter |
| 8 | **securityContext (non-root, readOnlyRootFs, caps drop)** | Security | `deployment.yaml` (pod + container) | Phase 17 base has this; apply to all Deployments |
| 9 | **Image digest pinning (sha256)** | Supply Chain | All `deployment.yaml` | `image: repo/app@sha256:...` not `:tag` |
| 10 | **Secret manager (External Secrets / SealedSecrets)** | Secrets | `secret.yaml` (replace), new `ExternalSecret`/`SealedSecret` | No plaintext secrets in git |
| 11 | **Backup/Restore (Velero, pg_dump, PVC snapshots)** | Data Protection | New `backup.yaml`, schedules, restore docs | Per-resource + cluster-level |
| 12 | **Multi-user / multi-tenant isolation** | Tenancy | Namespace per tenant, `ResourceQuota`, `LimitRange`, `NetworkPolicy` | Current lab is single-namespace (`k8s-lab`) |
| 13 | **Rate limiting (ingress / API gateway)** | Reliability | `ingress.yaml` (annotations), or `EnvoyFilter` / `APISIX` | Per-tenant / per-IP / per-user |
| 14 | **Audit logging (kube-apiserver + app-level)** | Observability | `audit-policy.yaml`, log forwarding | No document text in audit logs |
| 15 | **Durable long-term storage (PVC + StorageClass + snapshot)** | Storage | `pvc.yaml` per stateful app, `VolumeSnapshotClass` | Current: hostPath / emptyDir only |
| 16 | **HA monitoring (Prometheus HA, Alertmanager HA, Tempo HA)** | Observability | Multiple replicas, remote write, object storage | Current: single replica each |
| 17 | **Hardened bastion (SSH CA, MFA, session recording, just-in-time access)** | Access | `bastion/` manifests, `sshd_config`, `teleport`/`boundary` | Current: basic SSH key only |
| 18 | **Multiple namespaces (dev/staging/prod or per-tenant)** | Tenancy | `namespace.yaml`, per-ns `NetworkPolicy`, `ResourceQuota` | Current: `k8s-lab` only |
| 19 | **Image signature verification (cosign, sigstore)** | Supply Chain | `admission-controller` (Kyverno/OTEL), `ImagePolicy` | Prevent unsigned images |
| 20 | **PodSecurityPolicy / PodSecurity Standards (restricted)** | Security | Namespace labels `pod-security.kubernetes.io/enforce: restricted` | Replace PSP (deprecated) |

## Mapping to Existing Manifests

| Manifest | Currently Has | Missing (from above) |
|---|---|---|
| `ai/patterns/graph-rag/k8s/deployment.yaml` | non-root, probes, resources, readOnlyRootFs, caps drop | image digest, HPA custom metrics, PodSecurity labels |
| `ai/patterns/graph-rag/k8s/networkpolicy.yaml` | DNS, OTel egress; ingress from same ns | Postgres egress (when real service), per-tenant policies |
| `ai/patterns/graph-rag/k8s/secret.yaml` | placeholder `stringData` | ExternalSecrets/SealedSecrets, rotation |
| `ai/patterns/graph-rag/k8s/hpa.yaml` | CPU, memory, custom queue metric | Prometheus Adapter, scaling behaviors |
| `boilerplates/*/deployment.yaml` | varies | all of the above |
| `boilerplates/stacks/*/` | base only | all of the above |

## Implementation Approach
Each control becomes a **separate PR/commit** following the pattern:
1. Add the control to the Graph RAG base (`ai/patterns/graph-rag/k8s/`) as reference implementation
2. Propagate to boilerplates and stacks
3. Document in `docs/hardening-guide.md` (new file)
4. Add to `make test` validation (dry-run, kubeval, conftest)

## Acceptance Criteria
- Inventory is complete (no control mentioned in repo docs is missing from this table)
- Each control has a clear "manifest(s) to update" column
- Graph RAG base demonstrates all controls that apply to a stateless API
- `make test` includes manifest validation for new controls

## References
- `analysis/07-what-to-do.md` §3.17.7 (Kubernetes packaging)
- `docs/REPO-STATE.md` rows 9–12
- `guides/real-world-use.md` (hardening checklist)
- `analysis/06-scope-expansion.md` R18