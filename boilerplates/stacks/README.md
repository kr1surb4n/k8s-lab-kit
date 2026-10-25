# Stack Boilerplates

Production-ready Kubernetes overlays for common application stacks. Each stack
extends `boilerplates/base` and adds runtime-specific configuration.

## Stacks

| Stack | Runtime | Port | Key Features |
|-------|---------|------|--------------|
| `node-express/` | Node 22 + Express | 3000 | Multi-stage build, health checks, graceful shutdown |
| `python-fastapi/` | Python 3.12 + FastAPI | 8000 | Pydantic settings, lifespan, uvicorn workers |
| `go-http/` | Go 1.23 + Gin | 8080 | Distroless image, structured JSON logging |
| `java-spring/` | Java 21 + Spring Boot 3 | 8080 | **startupProbe**, actuator health, layered jars |
| `worker-cronjob/` | Python + Redis | N/A | Worker Deployment + CronJob + Redis |
| `stateful-postgres/` | PostgreSQL 16 | 5432 | StatefulSet, PVC per replica, headless service |
| `stateful-redis/` | Redis 7 | 6379 | StatefulSet, AOF persistence, headless + client service |
| `stateful-minio/` | MinIO | 9000/9001 | StatefulSet, S3 API, console, 10Gi PVC |

## Quick Start

```bash
# Build images (from each stack directory)
docker build -t boilerplate/node-express:1.0 boilerplates/stacks/node-express
docker build -t boilerplate/python-fastapi:1.0 boilerplates/stacks/python-fastapi
docker build -t boilerplate/go-http:1.0 boilerplates/stacks/go-http
docker build -t boilerplate/java-spring:1.0 boilerplates/stacks/java-spring
docker build -t boilerplate/worker-cron:1.0 boilerplates/stacks/worker-cronjob

# Load into minikube
minikube image load boilerplate/node-express:1.0
minikube image load boilerplate/python-fastapi:1.0
# ... etc

# Deploy
kubectl apply -k boilerplates/stacks/node-express
kubectl apply -k boilerplates/stacks/python-fastapi
# ... etc

# Verify
kubectl get pods -n k8s-lab -l app.kubernetes.io/name=node-express
kubectl port-forward -n k8s-lab svc/node-express 3000:80
curl http://localhost:3000/healthz
```

## Design Principles

1. **Extend base boilerplate** — Each stack is a kustomize overlay on `boilerplates/base`
2. **Non-root containers** — All images run as non-root users
2. **Health endpoints** — `/healthz` (liveness) and `/ready` (readiness) on every stack
3. **Structured logging** — JSON output with timestamp, level, message, extra fields
4. **Graceful shutdown** — SIGTERM handling, connection draining
5. **Resource limits** — CPU/memory requests and limits set per stack
4. **Security** — Non-root, read-only rootfs where possible, distroless for Go
5. **Observability** — Health endpoints compatible with Prometheus/k8s probes
5. **Config via env** — All configuration via environment variables

## Special Notes

- **Java/Spring**: Uses `startupProbe` with 60s initial delay (Spring Boot cold start)
- **PostgreSQL/Redis/MinIO**: StatefulSets with PVC templates for persistence
- **Worker/CronJob**: Separate worker Deployment + CronJob sharing Redis queue
- **MinIO**: Console on port 9001, S3 API on 9000

## Customization

Each stack accepts env vars for configuration:
```yaml
env:
  - name: APP_NAME
    value: "my-app"
  - name: APP_ENV
    value: "production"
  - name: VERSION
    value: "v1.2.3"
```
Override in the overlay's `kustomization.yaml` or via `kustomize edit set env`.