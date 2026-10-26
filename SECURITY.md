# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| main    | ✅ Current         |

This is a learning kit; security patches are applied to `main` only.

## Reporting a Vulnerability

**Do not open a public issue.** Use GitHub Security Advisories instead:

1. Go to the repository **Security** tab
2. Click **Report a vulnerability**
3. Fill in the details (affected component, impact, reproduction steps)
4. Submit — maintainers will be notified privately

We aim to acknowledge within 48 hours and provide a remediation timeline within 5 business days.

## Scope

This policy covers:

- The Kubernetes manifests and Helm/Kustomize bases in this repository
- The Graph RAG application (`ai/patterns/graph-rag/app/`)
- The evaluation and ingestion pipelines
- The recovery drill scripts

**Out of scope:**
- Your local minikube cluster configuration
- Your private `~/.config/graphrag/config.yaml`
- Upstream dependencies (Ollama, Postgres, Prometheus, etc.) — report there

## What to Include

- Component (e.g., `graph-rag-api`, `ingress-nginx`, `postgres-age`)
- Vulnerability type (injection, auth bypass, info leak, etc.)
- Steps to reproduce (minimal PoC)
- Impact assessment (CVSS if known)
- Suggested fix (if you have one)

## Disclosure Timeline

1. **Day 0** — Report received via Security Advisory
2. **Day 1–2** — Acknowledgment + initial triage
3. **Day 3–10** — Investigation, fix development, testing
4. **Day 10–14** — Fix merged to `main`, advisory published with CVE (if applicable)
5. **Day 14+** — Users notified via release notes / GitHub release

## Safe Harbor

We consider good-faith security research aligned with this policy to be
authorized. We will not pursue legal action against researchers who:

- Make a good-faith effort to avoid privacy violations, data destruction, or service disruption
- Only interact with their own test accounts/systems
- Report findings promptly via Security Advisories
- Give us reasonable time to remediate before public disclosure

## Security-Related Configuration

If you deploy this kit, **you are responsible for**:

- Replacing all `changeme` secrets in `k8s/secret.yaml` and `compose.yaml`
- Enabling TLS (cert-manager + Let's Encrypt or self-signed CA)
- Configuring authentication (oauth2-proxy + OIDC provider)
- Applying NetworkPolicies (see `specs/05-hardened-manifests.md`)
- Setting up audit logging and log forwarding
- Regular dependency updates (`dependabot` / `renovate` recommended)

The teaching manifests in this repo **are not production-ready** without these steps.