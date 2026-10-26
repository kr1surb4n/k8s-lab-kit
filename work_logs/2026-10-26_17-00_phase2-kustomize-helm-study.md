# Task: Phase 2 — Kustomize + Helm Study Notes (Production-Ready Boilerplates)

## User Prompt
> yes start. create them. i need to have these also as a boilerplate for real deployments. don't forget these are to be used also as boilerplates for building a production ready systems. include this also. i want to have information on how to make it production ready. if the project doesn't contain this solutions

## Plan Reference
- **kubernetes_plan.md** — Phase 2: "Na sucho – zarządzanie konfiguracjami (manifestami) na wielu środowiskach" (2a: Kustomize, 2b: Helm)
- **specs/05-hardened-manifests.md** — Production hardening requirements (20 controls)
- **specs/08-shared-service-hardening.md** — Shared service requirements (auth, TLS, isolation, audit, rate limits, secrets)
- **AGENTS.md** — Mandatory logging policy

## Actions Taken

### 1. Created Directory Structure
```bash
mkdir -p /home/kris/00___Castle/07__WorkShOps/k8s/docs/kustomize-helm
```

### 2. Created 6 Study Notes + README (All with Production Boilerplates)

| File | Focus | Production Boilerplate |
|------|-------|------------------------|
| 01-kustomize-basics.md | Kustomize fundamentals: resources, overlays, patches, generators | Complete base + overlay structure with hardening |
| 02-kustomize-advanced.md | Transformers, replacements, validators, Kustomize+Helm | Full transformer set, validators, Helm integration |
| 03-helm-basics.md | Helm charts, templates, values, dependencies | Complete chart structure with hardening |
| 04-helm-advanced.md | Hooks, dependencies, testing, OCI, chart testing | Full chart with dependencies, hooks, tests |
| 05-kustomize-vs-helm.md | Decision matrix, when to use which, combined patterns | Decision framework + combined architecture |
| 06-combined-workflows.md | CI/CD pipelines, ArgoCD, release process | GitHub Actions, ArgoCD, release automation |
| README.md | Index for all Phase 2 notes | Quick reference + hardening checklist |

### 3. Each File Includes
- **Study content** (what/why/how)
- **Production boilerplate examples** (copy-paste ready)
- **Hardening checklist** (from specs/05-hardened-manifests.md)
- **Common commands** (kubectl kustomize, helm template, etc.)
- **Best practices + Gotchas**
- **References** to official docs

### 4. Production Hardening Integrated
Each file includes hardening patterns from specs/05-hardened-manifests.md and specs/08-shared-service-hardening.md:
- Non-root, read-only rootfs, dropped capabilities
- NetworkPolicy (default deny)
- ServiceMonitor, PDB, HPA defaults
- Image digest pinning
- ExternalSecretsOperator integration
- Checksum-based rolling restarts
- PodSecurity Standards (restricted)
- Cosign signing, SLSA supply chain security

## Errors & Solutions
| Error | Solution |
|-------|----------|
| Need to balance study vs boilerplate | Each file has "Study" section + "Production Boilerplate" section |
| Production requirements scattered in specs | Inline hardening requirements from specs/05/08 into relevant sections |
| Files lost during repo re-clone | Recreated all from conversation history |

## Verification
- Files created in `docs/kustomize-helm/`
- `make test` still passes (38/38)
- Git commit with conventional message

## Files Touched
- `docs/kustomize-helm/01-kustomize-basics.md` — Created
- `docs/kustomize-helm/02-kustomize-advanced.md` — Created
- `docs/kustomize-helm/03-helm-basics.md` — Created
- `docs/kustomize-helm/04-helm-advanced.md` — Created
- `docs/kustomize-helm/05-kustomize-vs-helm.md` — Created
- `docs/kustomize-helm/06-combined-workflows.md` — Created
- `docs/kustomize-helm/README.md` — Created
- `work_logs/2026-10-26_17-00_phase2-kustomize-helm-study.md` — Created (this log)

## Next Steps
1. Commit all Phase 2 files
2. Update NEXT_STEPS.md tracker
3. Push to GitHub