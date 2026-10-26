# Provenance — imported scaffold

This directory was **imported from a different repository**, not written here.

| Field | Value |
|---|---|
| Source path | `/home/kris/00___Castle/07__WorkShOps/k8s` (capital `S` in `WorkShOps`) |
| Source commit | `db68801 feat: Complete Kubernetes Lab Kit - All phases complete` |
| Imported on | 2026-10-26 |
| Imported by | the session working in `07__WorkShops/k8s` (lowercase `s`) |
| Status | **scaffold only** — not wired into the test suite, not verified on a cluster |

## What was taken

- `README.md`, `contracts/openapi.yaml`, `failure-modes/failure-modes.md`
- `eval/eval.py` and `eval/golden_qa.jsonl`
- `mockup/` (FastAPI mock, Dockerfile, requirements)
- `k8s/` manifests and `Makefile`

## What was changed during the import

- Removed a duplicated block of FastAPI routes (the source defined `/healthz`,
  `/v1/graph-rag/ingest` and `/v1/graph-rag/query` twice).
- Removed two no-op entity loops that did nothing.
- Replaced the random uuid in the response with the live OpenTelemetry span id,
  and added `X-Trace-ID` to the response.
- Moved tracing setup before application startup and pointed the default OTLP
  endpoint at the collector in the `observability` namespace.
- Removed the duplicate `boilerplates/base` include from the kustomization; the
  standalone Deployment is complete.

## Known limitations (Phase 17 work, not import defects)

- The mockup keeps documents and relations in memory. There is no pgvector
  table and no Apache AGE query; the graph is a Python list.
- Embeddings and generation are keyword mocks, not real models. The current
  Phase 17 decision is real models only.
- `k8s/secret.yaml` contains placeholder credentials (`changeme`). Replace them
  with generated values before applying anything.
- The manifests request a GPU and are written for the full deployment; the local
  minikube overlay still has to be written.
- The evaluation harness scores graph-path accuracy but its faithfulness is a
  placeholder, same as the Phase 16 baseline.

The current, authoritative plan for Phase 17 lives in
`analysis/07-what-to-do.md` §3. Treat this directory as raw material.
