# Combined Workflows — Kustomize + Helm Production Pipelines

> **Dual Purpose**: End-to-end production deployment workflows using both tools together.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        CI/CD PIPELINE                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │   SOURCE     │───▶│    BUILD     │───▶│   DEPLOY     │      │
│  │   CONTROL    │    │              │    │              │      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
│         │                   │                   │                │
│         ▼                   ▼                   ▼                │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │ Git Commit   │    │ Helm Package │    │ Kustomize    │      │
│  │ PR/Tag       │    │ + Sign       │    │ Overlay +    │      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Workflow 1: Monorepo with Helm Charts + Kustomize Overlays

### Repository Structure

```
my-platform/
├── .github/
│   ├── workflows/
│   │   ├── ci.yaml              # CI pipeline
│   │   ├── cd-dev.yaml          # Deploy to dev
│   │   ├── cd-staging.yaml      # Deploy to staging
│   │   └── cd-prod.yaml         # Deploy to prod (manual approval)
│   └── dependabot.yml
├── charts/                       # Helm charts (packaging)
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
│   │   │   ├── tests/
│   │   │   └── hooks/
│   │   ├── charts/              # Subcharts (postgresql, redis)
│   │   └── .helmignore
│   ├── postgresql/              # Or use upstream
│   └── redis/
├── kustomize/                   # Platform hardening + env overlays
│   ├── base/                    # Platform-wide policies
│   │   ├── kustomization.yaml
│   │   ├── networkpolicy.yaml
│   │   ├── servicemonitor.yaml
│   │   ├── pdb.yaml
│   │   ├── hpa.yaml
│   │   ├── validators/
│   │   └── patches/
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
├── scripts/
│   ├── render-charts.sh         # Render Helm → base
│   ├── deploy.sh                # Deploy with Kustomize
│   └── validate.sh              # Validate manifests
├── Makefile
├── .helmignore
└── README.md
```

---

## Workflow 2: CI Pipeline (GitHub Actions)

### `.github/workflows/ci.yaml`

```yaml
name: CI
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

env:
  HELM_VERSION: "3.14.0"
  KUSTOMIZE_VERSION: "5.4.3"
  KUBEVAL_VERSION: "0.16.1"

jobs:
  lint-and-test:
    name: Lint & Test
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Set up Helm
        uses: azure/setup-helm@v4
        with:
          version: ${{ env.HELM_VERSION }}

      - name: Set up Kustomize
        run: |
          curl -sSL "https://github.com/kubernetes-sigs/kustomize/releases/download/kustomize/v${KUSTOMIZE_VERSION}/kustomize_v${KUSTOMIZE_VERSION}_linux_amd64.tar.gz" | tar xz
          sudo mv kustomize /usr/local/bin/

      - name: Set up kubeval
        run: |
          curl -sSL "https://github.com/instrumenta/kubeval/releases/download/${KUBEVAL_VERSION}/kubeval-linux-amd64.tar.gz" | tar xz
          sudo mv kubeval /usr/local/bin/

      - name: Set up chart-testing
        uses: helm/chart-testing-action@v2.6.1

      - name: Run ct lint
        run: ct lint --all --config .github/ct.yaml

      - name: Helm lint all charts
        run: |
          for chart in charts/*/; do
            helm lint "$chart"
          done

      - name: Helm unittest
        run: |
          for chart in charts/*/; do
            if [ -d "$chart/tests" ]; then
              helm unittest "$chart"
            fi
          done

      - name: Validate Kustomize bases
        run: |
          for base in kustomize/base/; do
            kustomize build "$base" --validate
            kustomize build "$base" | kubeval --strict --ignore-missing-schemas
          done

      - name: Validate Kustomize overlays
        run: |
          for overlay in kustomize/overlays/*/; do
            kustomize build "$overlay" --validate
            kustomize build "$overlay" | kubeval --strict --ignore-missing-schemas
          done

  package-and-sign:
    name: Package & Sign Charts
    needs: lint-and-test
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    permissions:
      contents: write
      packages: write
      id-token: write
    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Set up Helm
        uses: azure/setup-helm@v4

      - name: Set up cosign
        uses: sigstore/cosign-installer@v3

      - name: Package charts
        run: |
          mkdir -p dist/charts
          for chart in charts/*/; do
            helm dependency build "$chart"
            helm package "$chart" --destination dist/charts --sign --key "${{ secrets.COSIGN_PRIVATE_KEY }}"
          done

      - name: Create repo index
        run: |
          helm repo index dist/charts --url https://example.github.io/charts

      - name: Upload charts
        uses: actions/upload-artifact@v4
        with:
          name: helm-charts
          path: dist/charts/
          retention-days: 30

      - name: Publish to OCI Registry
        run: |
          for chart in dist/charts/*.tgz; do
            helm chart save "$chart" oci://ghcr.io/${{ github.repository_owner }}/charts/$(basename "$chart" .tgz)
          done
          helm chart push oci://ghcr.io/${{ github.repository_owner }}/charts --all

  build-images:
    name: Build Container Images
    needs: lint-and-test
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: |
            ghcr.io/${{ github.repository }}/my-app:${{ github.sha }}
            ghcr.io/${{ github.repository }}/my-app:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max

  deploy-dev:
    name: Deploy to Dev
    needs: [package-and-sign, build-images]
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: dev
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up kubectl
        uses: azure/k8s-set-context@v4
        with:
          kubeconfig: ${{ secrets.KUBECONFIG_DEV }}

      - name: Deploy to Dev
        run: |
          ./scripts/deploy.sh dev

  deploy-staging:
    name: Deploy to Staging
    needs: [package-and-sign, build-images]
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    environment: staging
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up kubectl
        uses: azure/k8s-set-context@v4
        with:
          kubeconfig: ${{ secrets.KUBECONFIG_STAGING }}

      - name: Deploy to Staging
        run: |
          ./scripts/deploy.sh staging

  deploy-prod:
    name: Deploy to Prod
    needs: [package-and-sign, build-images]
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    environment: production
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up kubectl
        uses: azure/k8s-set-context@v4
        with:
          kubeconfig: ${{ secrets.KUBECONFIG_PROD }}

      - name: Deploy to Prod
        run: |
          ./scripts/deploy.sh prod
```

---

## Workflow 3: Render + Deploy Scripts

### `scripts/render-charts.sh`

```bash
#!/bin/bash
set -euo pipefail

ENV="${1:-dev}"
CHART_DIR="charts/my-platform"
OUTPUT_DIR="kustomize/rendered/${ENV}"
VALUES_FILE="charts/my-platform/values-${ENV}.yaml"

echo "Rendering Helm charts for ${ENV}..."

# Clean and create output directory
rm -rf "${OUTPUT_DIR}"
mkdir -p "${OUTPUT_DIR}"

# Render Helm chart
helm template my-platform "${CHART_DIR}" \
  --namespace "my-platform-${ENV}" \
  --values "${VALUES_FILE}" \
  --output-dir "${OUTPUT_DIR}"

# Create kustomization.yaml from rendered files
cat > "${OUTPUT_DIR}/my-platform/kustomization.yaml" <<EOF
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - deployment.yaml
  - service.yaml
  - configmap.yaml
  - secret.yaml
  - hpa.yaml
  - pdb.yaml
  - servicemonitor.yaml
  - networkpolicy.yaml
  - serviceaccount.yaml

commonLabels:
  app.kubernetes.io/managed-by: helm
  app.kubernetes.io/instance: my-platform-${ENV}

# Security patches applied to all Deployments
patches:
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

# Include platform base (network policies, monitoring, etc.)
resources:
  - ../../kustomize/base
EOF

echo "Rendered to ${OUTPUT_DIR}/my-platform/"
```

### `scripts/deploy.sh`

```bash
#!/bin/bash
set -euo pipefail

ENV="${1:-dev}"
NAMESPACE="my-platform-${ENV}"
OVERLAY_DIR="kustomize/overlays/${ENV}"

echo "Deploying to ${ENV} (namespace: ${NAMESPACE})"

# 1. Render charts
./scripts/render-charts.sh "${ENV}"

# 2. Apply Kustomize overlay (includes base + rendered charts)
echo "Applying Kustomize overlay..."
cd "kustomize/overlays/${ENV}"
kustomize build . --load-restrictor=LoadRestrictionsNone | kubectl apply -f -

# 3. Wait for rollout
echo "Waiting for rollout..."
kubectl rollout status deployment/my-app -n "my-platform-${ENV}" --timeout=300s

# 4. Verify
echo "Verifying deployment..."
kubectl get pods -n "my-platform-${ENV}" -l app.kubernetes.io/name=my-app

# 5. Run smoke tests
echo "Running smoke tests..."
kubectl run smoke-test-${RANDOM} \
  --image=curlimages/curl:8.6 \
  --rm -i --restart=Never \
  -n "my-platform-${ENV}" \
  -- curl -sf "http://my-app:80/healthz"

echo "Deployment to ${ENV} complete!"
```

### `scripts/validate.sh`

```bash
#!/bin/bash
set -euo pipefail

echo "Validating all manifests..."

# Validate Kustomize base
echo "Validating base..."
kustomize build kustomize/base --validate
kustomize build kustomize/base | kubeval --strict --ignore-missing-schemas

# Validate each overlay
for overlay in kustomize/overlays/*/; do
  echo "Validating ${overlay}..."
  kustomize build "${overlay}" --validate
  kustomize build "${overlay}" | kubeval --strict --ignore-missing-schemas
done

# Validate Helm charts
for chart in charts/*/; do
  echo "Validating ${chart}..."
  helm lint "${chart}"
  helm template test "${chart}" | kubeval --strict --ignore-missing-schemas
done

echo "All validations passed!"
```

---

## Workflow 4: Makefile for Local Development

```makefile
.PHONY: help lint test render deploy-dev deploy-staging deploy-prod validate clean

HELM_VERSION := 3.14.0
KUSTOMIZE_VERSION := 5.4.3

help:
	@echo "Available targets:"
	@echo "  make lint           - Lint all charts and Kustomize"
	@echo "  make test           - Run unit tests"
	@echo "  make render ENV=dev - Render charts for environment"
	@echo "  make deploy ENV=dev - Deploy to environment"
	@echo "  make validate       - Validate all manifests"
	@echo "  make clean          - Clean rendered artifacts"

lint:
	@for chart in charts/*/; do helm lint $$chart; done
	kustomize build kustomize/base --validate
	@for overlay in kustomize/overlays/*/; do kustomize build $$overlay --validate; done

test:
	@for chart in charts/*/; do if [ -d "$$chart/tests" ]; then helm unittest $$chart; fi; done

render:
	@if [ -z "$(ENV)" ]; then echo "Usage: make render ENV=dev"; exit 1; fi
	./scripts/render-charts.sh $(ENV)

deploy:
	@if [ -z "$(ENV)" ]; then echo "Usage: make deploy ENV=dev"; exit 1; fi
	./scripts/deploy.sh $(ENV)

deploy-dev:
	make deploy ENV=dev

deploy-staging:
	make deploy ENV=staging

deploy-prod:
	make deploy ENV=prod

validate:
	./scripts/validate.sh

clean:
	rm -rf kustomize/rendered/
```

---

## Workflow 5: ArgoCD Integration

### ArgoCD Application (Helm + Kustomize)

```yaml
# argocd/applications/my-platform.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: my-platform
  namespace: argocd
spec:
  project: production
  source:
    repoURL: https://github.com/example/my-platform
    targetRevision: main
    path: kustomize/overlays/prod
    kustomize:
      version: v5.4.3
  destination:
    server: https://kubernetes.default.svc
    namespace: my-platform-prod
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
      allowEmpty: false
    syncOptions:
      - CreateNamespace=true
      - PrunePropagationPolicy=foreground
    retry:
      limit: 5
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 3m
```

### ArgoCD with Helm Chart Source

```yaml
# argocd/applications/my-app-helm.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: my-app
  namespace: argocd
spec:
  project: production
  source:
    repoURL: https://github.com/example/my-platform
    targetRevision: main
    path: charts/my-app
    helm:
      valueFiles:
        - values-prod.yaml
      parameters:
        - name: image.tag
          value: "v2.0.0"
      skipCrds: false
  destination:
    server: https://kubernetes.default.svc
    namespace: my-app-prod
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
```

---

## Workflow 6: Release Process

### Semantic Release + Chart Versioning

```yaml
# .github/workflows/release.yaml
name: Release
on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      packages: write
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Set up Helm
        uses: azure/setup-helm@v4

      - name: Set up cosign
        uses: sigstore/cosign-installer@v3

      - name: Extract version
        id: version
        run: echo "VERSION=${GITHUB_REF#refs/tags/v}" >> $GITHUB_OUTPUT

      - name: Update chart versions
        run: |
          for chart in charts/*/; do
            yq eval ".version = \"${{ steps.version.outputs.VERSION }}\"" -i "$chart/Chart.yaml"
            yq eval ".appVersion = \"${{ steps.version.outputs.VERSION }}\"" -i "$chart/Chart.yaml"
          done

      - name: Commit version bump
        run: |
          git config user.name "github-actions"
          git config user.email "github-actions@github.com"
          git add charts/*/Chart.yaml
          git commit -m "chore: release ${{ steps.version.outputs.VERSION }}"
          git push

      - name: Package and sign charts
        run: |
          mkdir -p dist/charts
          for chart in charts/*/; do
            helm dependency build "$chart"
            helm package "$chart" --destination dist/charts \
              --sign --key "${{ secrets.COSIGN_PRIVATE_KEY }}"
          done
          helm repo index dist/charts --url https://example.github.io/charts

      - name: Create GitHub Release
        uses: softprops/action-gh-release@v1
        with:
          files: dist/charts/*.tgz
          generate_release_notes: true

      - name: Publish to OCI
        run: |
          for chart in dist/charts/*.tgz; do
            helm chart save "$chart" oci://ghcr.io/${{ github.repository_owner }}/charts/$(basename "$chart" .tgz)
          done
          helm chart push oci://ghcr.io/${{ github.repository_owner }}/charts --all
```

---

## Production Hardening: Pipeline Security

| Stage | Security Measure |
|-------|------------------|
| **Source** | Signed commits, branch protection, CODEOWNERS |
| **Build** | SLSA Level 3, reproducible builds, SBOM (Syft) |
| **Test** | Unit tests, integration tests, contract tests |
| **Package** | Cosign signing, SBOM attestation, provenance |
| **Deploy** | ArgoCD sync windows, manual approval for prod |
| **Runtime** | Admission controllers (Kyverno), runtime security (Falco) |

### Supply Chain Security (SLSA)

```yaml
# .github/workflows/slsa.yaml
name: SLSA Build
on:
  push:
    tags: ['v*']
jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: actions/checkout@v4
      - uses: slsa-framework/slsa-github-generator/.github/workflows/generator_generic_slsa3.yml@v1.9.0
        with:
          base64-subjects: "true"
```

---

## Key References

- [Helm CI/CD](https://helm.sh/docs/topics/ci_cd/)
- [Kustomize in CI/CD](https://kustomize.io/ci/)
- [ArgoCD Helm](https://argo-cd.readthedocs.io/en/stable/user-guide/helm/)
- [ArgoCD Kustomize](https://argo-cd.readthedocs.io/en/stable/user-guide/kustomize/)
- [Cosign Signing](https://docs.sigstore.dev/cosign/overview/)
- [SLSA Framework](https://slsa.dev/)
- [Chart Testing](https://github.com/helm/chart-testing)

---

> **Phase 2 Complete** — All 6 study notes + README created.
> 
> **Files Created:**
> - `01-kustomize-basics.md` — Kustomize fundamentals + production boilerplate
> - `02-kustomize-advanced.md` — Transformers, validators, Kustomize+Helm
> - `03-helm-basics.md` — Helm charts, templates, values + production boilerplate
> - `04-helm-advanced.md` — Hooks, dependencies, testing, OCI + production patterns
> - `05-kustomize-vs-helm.md` — Decision matrix + combined architecture
> - `06-combined-workflows.md` — CI/CD pipelines, ArgoCD, release process
> - `README.md` — Index for all Phase 2 notes