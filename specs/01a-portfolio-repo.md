# Spec: Portfolio GitHub Repository

## Problem Statement
The entire Kubernetes Lab Kit (Phases 0–18) lives in a local directory. It needs to be published as a portfolio project on GitHub with a professional name, description, and structure so it can be shown to employers/collaborators.

## Requirements
- Choose a clear, memorable repository name
- Write a compelling description (1–2 sentences + bullet highlights)
- Include: README, LICENSE, CONTRIBUTING, CODE_OF_CONDUCT, SECURITY.md
- Topics/tags for discoverability
- GitHub Pages or docs site (optional but recommended)
- Clean commit history (already satisfied by conventional commits)
- No secrets, keys, or local paths in the repo

## Proposed Repository Metadata

| Field | Value |
|---|---|
| **Name** | `k8s-lab-kit` (or `kubernetes-lab-kit`) |
| **Description** | A hands-on Kubernetes learning kit: core lab (A1–A7), boilerplates, recovery drills, observability stack, stack overlays, and a local Graph RAG pattern — all runnable on a 6–8 GiB minikube. |
| **Visibility** | Public |
| **Topics** | `kubernetes`, `learning`, `lab`, `observability`, `graph-rag`, `postgresql`, `prometheus`, `grafana`, `minikube`, `portfolio` |
| **License** | MIT (or Apache-2.0) |
| **Default branch** | `main` |

## Implementation Steps
1. Decide on final name (check availability on GitHub)
2. Create repository on GitHub (web UI or `gh repo create`)
3. Add required files:
   - `LICENSE` (MIT)
   - `CONTRIBUTING.md` (brief: conventional commits, `make test` green)
   - `CODE_OF_CONDUCT.md` (Contributor Covenant 2.1)
   - `SECURITY.md` (report via GitHub Security Advisories)
   - `.github/PULL_REQUEST_TEMPLATE.md`
   - `.github/ISSUE_TEMPLATE/` (bug, feature, question)
4. Push existing `main` branch
5. Enable GitHub Pages from `docs/` (optional) or publish `mkdocs` site
6. Add repository description, website, topics in GitHub settings

## Acceptance Criteria
- `gh repo view kris/<name>` shows the repo with description, topics, license
- `git clone https://github.com/kris/<name>.git` works and `make test` passes
- No `.env`, `config.yaml`, or local paths committed
- README renders with badges (build, test, license)

## References
- Current repo root: `/home/kris/00___Castle/07__WorkShops/k8s`
- `docs/REPO-STATE.md` has the component inventory
- `analysis/07-what-to-do.md` has the phase summary