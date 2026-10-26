# Kubernetes Lab Exercises — Hands-On Learning Path

> **Imported from a different repository.** Copied on 2026-10-26 from the
> abandoned `~/00___Castle/07__WorkShOps/k8s` copy (commit `db68801`). The
> `make` targets for the lab itself are real, but three commands in this sheet
> belong to the pattern Makefiles, not the root one:
> `make build`, `make deploy` and `make eval` → use
> `make -C ai/patterns/rag …`. `SCENARIO=aX` is a placeholder, not a scenario.
> The authoritative per-exercise notes are in `docs/runbooks.md`.

This guide provides step-by-step exercises to learn Kubernetes through hands-on practice. Each exercise builds on the previous one.

## Prerequisites

```bash
# Run once
make tools          # Install kubectl, minikube, helm, etc.
make doctor         # Check hardware capacity
make cluster        # Start minikube with recommended sizing
```

## Exercise 1: Static Site from Host (A1)

**Goal**: Serve files from host directory via nginx using `minikube mount`.

```bash
# 1. Deploy
make up SCENARIO=a1

# 2. Start tunnel
make tunnel

# 3. Verify
curl http://localhost:8080/
curl http://localhost:8080/images/logo.svg

# 4. Live edit test
sed -i "s/replace-me-by-hand/LIVE_EDIT_TEST/" site/index.html
curl -s http://localhost:8080/ | grep LIVE_EDIT_TEST
# Should show "LIVE_EDIT_TEST" without pod restart!

# 5. Verify
make verify SCENARIO=a1

# 6. Cleanup
make down SCENARIO=a1
```

**Key Concept**: `hostPath` + `minikube mount` = live file sync without rebuild.

---

## Exercise 2: ConfigMap with Live Updates (A2)

**Goal**: Serve content from ConfigMap, edit live without restart.

```bash
make up SCENARIO=a2
make tunnel
curl http://localhost:8080/

# Live edit via ConfigMap patch
kubectl patch configmap web-index -n k8s-lab --type json \
  -p '[{"op":"replace","path":"/data/index.html","value":"<h1>UPDATED!</h1>"}]'

# Wait ~30 seconds for kubelet sync, then verify
curl -s http://localhost:8080/ | grep UPDATED

make verify SCENARIO=a2
make down SCENARIO=a2
```

**Key Concept**: Directory-mounted ConfigMap (not `subPath`) enables live updates.

---

## Exercise 3: Environment Variables (A3)

**Goal**: Understand env var precedence and Downward API.

```bash
make up SCENARIO=a3
make tunnel
curl -s http://localhost:8080/ | grep -E "APP_ENV|LOG_LEVEL|POD_NAME|COMPOSED"

# Expected: APP_ENV=from-pod-spec (literal beats envFrom)
# COMPOSED=from-pod-spec-debug (variable expansion)

# Verify env vars in pod
kubectl exec deploy/web -n k8s-lab -- printenv | grep -E "APP_ENV|LOG_LEVEL|POD_NAME|COMPOSED"

make verify SCENARIO=a3
make down SCENARIO=a3
```

**Key Concept**: Precedence: literal `env` > `envFrom` > image `ENV`. Downward API injects pod metadata.

---

## Exercise 4: LAN Access (A4)

**Goal**: Access app from another machine on LAN.

```bash
# Deploy A6 (has LoadBalancer service)
make up SCENARIO=a6

# Start tunnel binding to all interfaces
make tunnel

# From THIS machine
curl http://127.0.0.1:8080

# From ANOTHER machine on same LAN (phone, laptop)
# Replace with your machine's LAN IP (run: hostname -I | awk '{print $1}')
curl http://192.168.1.240:8080

# If fails, check firewall:
# sudo ufw allow 8080/tcp
# (remove after: sudo ufw delete allow 8080/tcp)

# Verify
make verify SCENARIO=a6

# Note: On minikube, LoadBalancer stays <pending>
# port-forward --address 0.0.0.0 is the workaround
# For real LB, use k3d/k3s: scripts/cluster-create.sh k3d
```

---

## Exercise 5: Basic Auth with Secret (A5)

**Goal**: Secure app with HTTP Basic Auth using Secret.

```bash
make up SCENARIO=a5
make tunnel

# Without credentials → 401
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/
# Should output: 401

# With credentials (user: lab, pass: labpass)
curl -s -u lab:labpass -o /dev/null -w "%{http_code}" http://localhost:8080/
# Should output: 200

# Create your own credential
scripts/mkpasswd.sh myuser mypass > .htpasswd
kubectl create secret generic web-basic-auth --from-file=.htpasswd -n k8s-lab \
  --dry-run=client -o yaml | kubectl apply -f -

make verify SCENARIO=a5
make down SCENARIO=a5
```

**Key Concept**: Secret mounted as file (mode 0644) for nginx `auth_basic_user_file`.

---

## Exercise 6: Production Patterns (A6)

**Goal**: 3 replicas, LoadBalancer, scaling, rolling updates.

```bash
make up SCENARIO=a6
make tunnel

# Check 3 replicas
kubectl get pods -n k8s-lab -l app.kubernetes.io/name=web

# Scale up
make scale --delta 1   # 3 → 4
kubectl get pods -n k8s-lab -l app.kubernetes.io/name=web

# Scale down
make scale --delta -1  # 4 → 3

# Rolling update
make rollout          # Shows history
kubectl set image deploy/web web=nginx:1.28-alpine -n k8s-lab
kubectl rollout status deploy/web -n k8s-lab

# Rollback
kubectl rollout undo deploy/web -n k8s-lab

# Verify
make verify SCENARIO=a6
make status SCENARIO=a6

# Cleanup
make down SCENARIO=a6
```

**Key Concept**: `maxUnavailable: 0` ensures zero-downtime rolling updates.

---

## Exercise 7: Full Stack (A7)

**Goal**: nginx + PHP-FPM + PostgreSQL + SQLite on host.

```bash
# One-time: build PHP image with pdo_pgsql
make up SCENARIO=a7 --build --mount

# Or step by step:
docker build -t k8s-lab/php:8.3 manifests/a7/php
minikube image load k8s-lab/php:8.3

make up SCENARIO=a7 --mount

# Verify both DBs work
curl http://localhost:8080/ | grep -E "SQLite|PostgreSQL|row"

# Live SQLite edit from host
sqlite3 app/database/database.sqlite \
  "INSERT INTO notes (body) VALUES ('from host at $(date +%H:%M:%S)');"

curl -s http://localhost:8080/ | grep "from host"

# PostgreSQL insert
kubectl exec deploy/postgres -n k8s-lab -- \
  psql -U lab -d lab -c "INSERT INTO notes (body) VALUES ('from psql');"

curl -s http://localhost:8080/ | grep "from psql"

make verify SCENARIO=a7
make down SCENARIO=a7
```

**Key Concept**: HostPath for SQLite (live host edits), PVC for PostgreSQL (real DB).

---

## Exercise 8: Failure Drills (Phase 13)

**Goal**: Inject failures, observe, recover.

```bash
# Ensure A6 is running
make up SCENARIO=a6

# 1. CrashLoopBackOff
scripts/lab-drill.sh crashloop --inject
kubectl get pods -n k8s-lab  # See CrashLoopBackOff
scripts/lab-drill.sh crashloop --recover

# 2. ImagePullBackOff
scripts/lab-drill.sh imagepull --inject
kubectl get pods -n k8s-lab  # See ImagePullBackOff
scripts/lab-drill.sh imagepull --recover

# 3. Pending (unschedulable)
scripts/lab-drill.sh pending --inject
kubectl get pods -n k8s-lab  # See Pending
scripts/lab-drill.sh pending --recover

# 4. OOMKilled
scripts/lab-drill.sh oom --inject
kubectl get pods -n k8s-lab  # See OOMKilled
scripts/lab-drill.sh oom --recover

# Run all
make drills
```

---

## Exercise 9: Observability (Phase 15)

```bash
# Minimal: metrics + uptime + Grafana
make obs PROFILE=minimal

# Access
kubectl port-forward -n observability svc/kube-prometheus-stack-grafana 3000:80
# User: admin
# Pass: kubectl get secret -n observability kube-prometheus-stack-grafana -o jsonpath='{.data.admin-password}' | base64 -d

# Prometheus
kubectl port-forward -n observability svc/kube-prometheus-stack-prometheus 9090:9090

# Logs (Loki)
make obs PROFILE=logs

# Traces (Tempo + OTel)
make obs PROFILE=traces

# Full stack
make obs PROFILE=full
```

---

## Exercise 10: RAG Pattern (Phase 16)

```bash
cd ai/patterns/rag
make build      # Build Docker image
make deploy     # Deploy to cluster
make eval       # Run evaluation (Recall@5, latency, etc.)

# Test query
curl -X POST http://localhost:8000/v1/rag/query \
  -H "Content-Type: application/json" \
  -d '{"query": "How do I scale a deployment?", "top_k": 5, "rerank": true}'
```

---

## Exercise 11: Graph RAG (Phase 17)

```bash
cd ai/patterns/graph-rag
make build deploy eval

# Query with graph expansion
curl -X POST http://localhost:8000/v1/graph-rag/query \
  -H "Content-Type: application/json" \
  -d '{"query": "How do Deployments relate to Pods?", "graph_hops": 2}'

# Response includes graph_path showing multi-hop reasoning!
```

---

## Exercise 12: Cloud Deployment (Phase 18)

```bash
# Oracle Cloud (Always Free - recommended)
cd cloud/oracle
terraform init && terraform apply

# GKE Autopilot (free control plane)
cd ../gke
terraform init && terraform apply

# AKS
cd ../aks
terraform init && terraform apply

# Deploy lab
kubectl apply -k boilerplates/overlays/a6

# Teardown (CRITICAL)
terraform destroy
# Verify $0 bill next day!
```

---

## Complete Verification Checklist

After each exercise, run:
```bash
make verify SCENARIO=aX    # X = 1-7
make test                  # All 36 offline tests
make check                 # Syntax + shellcheck + YAML + dry-runs
```

## Cleanup

```bash
# Single scenario
make down SCENARIO=a1

# All scenarios + namespace
make down

# Full cluster
make cluster-delete
```

## Troubleshooting

| Issue | Command |
|-------|---------|
| Pod stuck | `kubectl describe pod -n k8s-lab <pod>` |
| Port forward dies | `scripts/lab-tunnel.sh --background` |
| Mount not working | `minikube mount $PWD:/mnt/lab` |
| Image not found | `minikube image load <image>` |

---

## Next Steps

1. Complete all 12 exercises
2. Run `make test` → all 36 tests pass
3. Deploy boilerplate: `cd boilerplates/stacks/node-express && make build deploy`
4. Install observability: `make obs PROFILE=minimal`
5. Try RAG: `cd ai/patterns/rag && make build deploy eval`
6. Try Graph RAG: `cd ai/patterns/graph-rag && make build deploy eval`
7. Deploy to cloud: `cd cloud/oracle && terraform apply`
8. **Teardown**: `terraform destroy` → verify $0 bill

---

**Happy Learning!** 🚀