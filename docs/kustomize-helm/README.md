# Kustomize + Helm — Study Notes & Production Boilerplates (Phase 2)

This directory contains study notes for **Phase 2** of the Kubernetes learning plan: "Na sucho – zarządzanie konfiguracjami (manifestami) na wielu środowiskach" — Config management with Kustomize and Helm.

Each file serves **dual purpose**:
1. **Study Guide** — Learn the tool from basics to advanced
2. **Production Boilerplate** — Copy-paste ready patterns for real deployments

---

## Files

| # | File | Focus | Production Boilerplate |
|---|------|-------|------------------------|
| 01 | [01-kustomize-basics.md](01-kustomize-basics.md) | Kustomize fundamentals: resources, overlays, patches, generators | Complete base + overlay structure with hardening |
| 02 | [02-kustomize-advanced.md](02-kustomize-advanced.md) | Transformers, replacements, validators, Kustomize+Helm | Full transformer set, validators, Helm integration |
| 03 | [03-helm-basics.md](03-helm-basics.md) | Helm charts, templates, values, dependencies | Complete chart structure with hardening |
| 04 | [04-helm-advanced.md](04-helm-advanced.md) | Hooks, dependencies, testing, OCI, chart testing | Full chart with dependencies, hooks, tests |
| 05 | [05-kustomize-vs-helm.md](05-kustomize-vs-helm.md) | Decision matrix, when to use which, combined patterns | Decision framework + combined architecture |
| 06 | [06-combined-workflows.md](06-combined-workflows.md) | CI/CD pipelines, ArgoCD, release process | GitHub Actions, ArgoCD, release automation |

## Learning Order

1. **Kustomize Basics** — Foundation: resources, overlays, patches
2. **Kustomize Advanced** — Transformers, validators, Helm integration
3. **Helm Basics** — Charts, templates, values, dependencies
4. **Helm Advanced** — Hooks, dependencies, testing, OCI
5. **Kustomize vs Helm** — When to use which, combined patterns
6. **Combined Workflows** — CI/CD pipelines, ArgoCD, release automation

---

## Production Boilerplate Highlights

Each file includes **copy-paste ready boilerplates** with:

### Kustomize Boilerplates
- ✅ Base + overlay structure (dev/staging/prod)
- ✅ Security patches (drop ALL capabilities, read-only rootfs, non-root)
- ✅ NetworkPolicy (default deny)
- ✅ ServiceMonitor, PDB, HPA defaults
- ✅ ConfigMap/Secret generators with checksum injection
- ✅ Validators for required labels
- ✅ Kustomize + Helm post-renderer

### Helm Boilerplates
- ✅ Complete chart structure with `values.schema.json`
- ✅ Production-ready `values.yaml` + `values-dev.yaml` + `values-prod.yaml`
- ✅ All templates: Deployment, Service, ConfigMap, Secret, HPA, PDB, ServiceMonitor, NetworkPolicy, PDB
- ✅ `_helpers.tpl` with standard labels/selectors
- ✅ Pre-install/pre-upgrade hooks (DB migrations)
- ✅ Post-install/post-upgrade hooks (smoke tests)
- ✅ Chart tests (`helm test`)
- ✅ Chart dependencies (PostgreSQL, Redis via Bitnami)
- ✅ Chart testing (ct lint, ct install, helm unittest)
- ✅ OCI registry publishing + cosign signing

### Combined Architecture
- ✅ Helm for packaging, dependencies, releases, hooks
- ✅ Kustomize for platform policies, hardening, env overlays
- ✅ GitHub Actions CI/CD pipeline
- ✅ ArgoCD integration (both Helm and Kustomize sources)
- ✅ Semantic release with chart versioning + signing
- ✅ SLSA supply chain security

---

## Quick Reference

### Kustomize Commands
```bash
# Render
kubectl kustomize overlays/prod
kustomize build overlays/prod --validate

# Apply
kubectl apply -k overlays/prod

# Diff
kustomize build overlays/prod | kubectl diff -f -

# Validate
kustomize build . | kubeval --strict
```

### Helm Commands
```bash
# Create chart
helm create my-app

# Lint & validate
helm lint ./my-app
helm template my-app ./my-app --values values-prod.yaml | kubeval --strict

# Package & sign
helm package ./my-app --sign --key keyring.gpg
helm push ./my-app-1.2.3.tgz oci://registry.example.com/charts

# Install/upgrade
helm upgrade --install my-app ./my-app -n prod --values values-prod.yaml --wait

# Test
helm test my-app -n prod

# Diff
helm diff upgrade my-app ./my-app -n prod --values values-prod.yaml
```

### Combined Workflow
```bash
# 1. Render Helm charts
helm template my-platform ./charts/my-platform -n prod --values values-prod.yaml -o rendered/prod

# 2. Apply Kustomize overlay
kustomize build kustomize/overlays/prod | kubectl apply -f -

# Or use Helm post-renderer
helm template my-platform ./charts/my-platform \
  --post-renderer ./kustomize-post-renderer.sh \
  -n prod --values values-prod.yaml | kubectl apply -f -
```

---

## Production Hardening Checklist

| Layer | Kustomize | Helm |
|-------|-----------|------|
| **Security Context** | Patches in base | Values + templates |
| **Network Policy** | Resources in base | Conditional template |
| **Monitoring** | ServiceMonitor in base | Conditional template |
| **PDB/HPA** | Resources in base | Conditional template |
| **Image Digests** | Overlay `images.digest` | Values `image.digest` |
| **Secrets** | ExternalSecretsOperator | Template + ExternalSecrets |
| **Validation** | `kustomize build --validate` | `helm lint` + `values.schema.json` |
| **Testing** | Kubeval | `helm unittest` + `ct` |
| **Signing** | Cosign on manifests | `helm package --sign` |

---

## Production-Ready Repository Structure

```
my-platform/
├── .github/workflows/
│   ├── ci.yaml
│   ├── cd-dev.yaml
│   ├── cd-staging.yaml
│   ├── cd-prod.yaml
│   └── release.yaml
├── charts/
│   ├── my-app/
│   │   ├── Chart.yaml
│   │   ├── values.yaml
│   │   ├── values-dev.yaml
│   │   ├── values-staging.yaml
│   │   ├── values-prod.yaml
│   │   ├── values.schema.json
│   │   ├── templates/
│   │   │   ├── deployment.yaml
│   │   │   ├── service.yaml
│   │   │   ├── configmap.yaml
│   │   │   ├── secret.yaml
│   │   │   ├── hpa.yaml
│   │   │   ├── pdb.yaml
│   │   │   ├── servicemonitor.yaml
│   │   │   ├── networkpolicy.yaml
│   │   │   ├── _helpers.tpl
│   │   │   ├── hooks/
│   │   │   └── tests/
│   │   └── charts/
│   ├── postgresql/
│   └── redis/
├── kustomize/
│   ├── base/
│   │   ├── kustomization.yaml
│   │   ├── networkpolicy.yaml
│   │   ├── servicemonitor.yaml
│   │   ├── pdb.yaml
│   │   ├── hpa.yaml
│   │   ├── validators/
│   │   └── patches/
│   ├── overlays/
│   │   ├── dev/
│   │   ├── staging/
│   │   └── prod/
│   └── validators/
├── scripts/
│   ├── render-charts.sh
│   ├── deploy.sh
│   └── validate.sh
├── argocd/
│   └── applications/
├── Makefile
└── README.md
```

---

## References

### Kustomize
- [Kustomize Documentation](https://kustomize.io/)
- [Kubernetes Kustomize Guide](https://kubernetes.io/docs/tasks/manage-kubernetes-objects/kustomization/)
- [Kustomize API](https://github.com/kubernetes-sigs/kustomize/blob/master/docs/api.md)

### Helm
- [Helm Documentation](https://helm.sh/docs/)
- [Chart Template Guide](https://helm.sh/docs/chart_template_guide/)
- [Chart Best Practices](https://helm.sh/docs/chart_best_practices/)
- [Sprig Functions](http://masterminds.github.io/sprig/)

### Combined
- [Helm + Kustomize](https://helm.sh/docs/topics/kustomize/)
- [ArgoCD: Helm vs Kustomize](https://argo-cd.readthedocs.io/en/stable/user-guide/helm_vs_kustomize/)
- [Google: Kustomize vs Helm](https://cloud.google.com/blog/products/containers-kubernetes/kustomize-vs-helm-template-free-customization)

### Security
- [Cosign](https://docs.sigstore.dev/cosign/overview/)
- [SLSA](https://slsa.dev/)
- [Kyverno](https://kyverno.io/)

---

## Phase 2 Status

✅ **Complete** — All 6 study notes + boilerplates created

| File | Status |
|------|--------|
| 01-kustomize-basics.md | ✅ |
| 02-kustomize-advanced.md | ✅ |
| 03-helm-basics.md | ✅ |
| 04-helm-advanced.md | ✅ |
| 05-kustomize-vs-helm.md | ✅ |
| 06-combined-workflows.md | ✅ |
| README.md | ✅ |

---

## Next Phase

**Phase 3**: Single-node Kubernetes (k3s/minikube) — nginx + Magento with Helm

See `kubernetes_plan.md` for details.