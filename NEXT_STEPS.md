# Next Steps — Portfolio & Hardening Tracker

This file tracks the remaining work items for turning the Kubernetes Lab Kit into a
portfolio-ready, production-hardened reference. Each item links to a detailed
specification file.

## Items

| # | Title | Spec file | Status |
|---|---|---|---|
| 1a | Portfolio GitHub repository — name, description, create/push | `specs/01a-portfolio-repo.md` | ✅ Done — https://github.com/kr1surb4n/k8s-lab-kit |
| 1b | Databases with persistent storage — Postgres access for other projects | `specs/01b-persistent-databases.md` | ✅ Spec created |
| 2  | Missing controls inventory — what to add to teaching manifests | `specs/02-missing-controls.md` | ✅ Spec created |
| 3  | On-call process boilerplate — extensible runbook framework | `specs/03-oncall-process.md` | ✅ Spec created |
| 4  | HA definition — what "High Availability" means here | `specs/04-ha-definition.md` | ✅ Spec created |
| 5  | Hardened manifests — TLS, auth, backup, NetworkPolicy, PDB, Ingress, HPA, securityContext, image digest, secret manager, multi-user isolation, rate limits, tenant isolation | `specs/05-hardened-manifests.md` | ✅ Spec created |
| 6  | Cloud provider research template — Terraform prerequisites | `specs/06-cloud-provider-template.md` | ✅ Spec created |
| 7  | Phase 17 Graph RAG optional increments | `specs/07-graphrag-increments.md` | ✅ Done (6 commits) |
| 8  | Shared-service hardening manual — auth, TLS, isolation, audit, rate limits, secrets, packaging, privacy review | `specs/08-shared-service-hardening.md` | ✅ Spec created |
| 9  | Managed Kubernetes cost model — LB, storage, egress, logging, idle control planes | `specs/09-managed-k8s-costs.md` | ✅ Spec created |
| 10 | Phase 2: Kustomize + Helm study notes + production boilerplates | `docs/kustomize-helm/` | ✅ Done (7 files) |

## Conventions

- Each spec file contains: **Problem Statement**, **Requirements**, **Implementation Steps**, **Acceptance Criteria**, **References**.
- Work proceeds one spec at a time; commit after each with message `feat|docs|chore(scope): ...`.
- `make test` must stay green (38/38) after every commit.

---

*Created: 2026-10-26*