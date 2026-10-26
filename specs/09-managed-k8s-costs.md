# Spec: Managed Kubernetes Cost Model

## Problem Statement
"Managed Kubernetes has costs that the lab does not model: load balancers, storage, egress, logging, and idle control planes." This spec documents, explains, and quantifies these costs so users can budget realistically when moving from minikube to a managed service (EKS, GKE, AKS, OKE).

---

## Cost Categories the Lab Ignores

| Category | Lab (minikube) | Managed Kubernetes | Why It Matters |
|---|---|---|---|
| **Control Plane** | Free (local process) | $0–$730/mo (per cluster) | EKS: $0.10/hr = $73/mo; GKE: free zonal; AKS: free; OKE: free |
| **Worker Nodes** | Your laptop RAM/CPU | $0.03–$0.50/hr per node | Pay for VMs, not just pods |
| **Load Balancers** | `port-forward` (free) | $18–$25/mo per LB | Each `Service type=LoadBalancer` = 1 LB |
| **Block Storage (PVC)** | hostPath/emptyDir (free) | $0.10–$0.17/GiB/mo | gp3: $0.08/GiB; pd-ssd: $0.17/GiB |
| **Object Storage** | Local filesystem | $0.02–$0.026/GiB/mo | Backups, Loki/Tempo storage, Terraform state |
| **Egress (Internet)** | Free (local) | $0.08–$0.12/GiB | First 1 GiB free on some clouds |
| **Logging/Metrics** | Local (Prometheus/Loki) | $0.50–$2.50/GiB ingested | CloudWatch, Cloud Logging, Azure Monitor |
| **Managed Services** | Self-hosted everything | Per-service pricing | RDS, ElastiCache, Cloud SQL, etc. |
| **Snapshot/Backup** | Manual `pg_dump` | $0.05–$0.12/GiB/mo | Automated, cross-region |

---

## Detailed Breakdown by Provider (2026 Pricing)

### AWS EKS
| Component | Cost (US-East-1) | Notes |
|---|---|---|
| EKS Control Plane | $0.10/hr = **$73/mo** | Per cluster |
| EC2 t3.medium (2 vCPU, 4 GiB) | $0.0416/hr = **$30/mo** | 1 node; need 3 for HA = $90 |
| EC2 t3.large (2 vCPU, 8 GiB) | $0.0832/hr = **$61/mo** | 3 nodes = $183 |
| Application Load Balancer | $0.0225/hr = **$16.50/mo** | Per ALB; NLB cheaper ($0.0225) |
| EBS gp3 (20 GiB) | $0.08/GiB/mo = **$1.60/mo** | Per volume |
| S3 Standard (100 GiB) | $0.023/GiB/mo = **$2.30/mo** | Backups, Loki/Tempo |
| Data Transfer Out | $0.09/GiB (first 10 TB) | After 100 GiB free |
| CloudWatch Logs | $0.50/GiB ingested | + $0.03/GiB archived |
| **Estimated Monthly (dev, 1 node)** | **~$125/mo** | |
| **Estimated Monthly (prod HA, 3 nodes)** | **~$350/mo** | |

### Google Cloud GKE
| Component | Cost (us-central1) | Notes |
|---|---|---|
| GKE Zonal Control Plane | **Free** | Autopilot: $0.10/hr per cluster |
| GKE Standard (you manage nodes) | Node VM pricing only | e2-medium: $0.024/hr = $17.50/mo |
| e2-standard-4 (4 vCPU, 16 GiB) | $0.136/hr = **$99/mo** | 3 nodes = $297 |
| Cloud Load Balancing | $0.025/hr = **$18/mo** | Per forwarding rule |
| Persistent Disk SSD (20 GiB) | $0.17/GiB/mo = **$3.40/mo** | Per disk |
| Cloud Storage (100 GiB) | $0.026/GiB/mo = **$2.60/mo** | |
| VPC Egress | $0.12/GiB (first 1 TB) | |
| Cloud Logging | $0.50/GiB ingested | |
| **Estimated Monthly (dev, 1 node)** | **~$40/mo** | Free control plane helps |
| **Estimated Monthly (prod HA, 3 nodes)** | **~$340/mo** | |

### Azure AKS
| Component | Cost (East US) | Notes |
|---|---|---|
| AKS Control Plane | **Free** | |
| Standard_B2s (2 vCPU, 4 GiB) | $0.0416/hr = **$30/mo** | 3 nodes = $90 |
| Standard_D4s_v3 (4 vCPU, 16 GiB) | $0.187/hr = **$136/mo** | 3 nodes = $408 |
| Azure Load Balancer Standard | Free (first 5 rules) | Then $0.008/hr per rule |
| Managed Disk SSD P10 (128 GiB) | $15.21/mo | Min size; smaller = same tier |
| Blob Storage (100 GiB) | $0.0184/GiB/mo = **$1.84/mo** | Cool tier cheaper |
| Bandwidth Egress | $0.087/GiB (first 5 TB) | |
| Azure Monitor Logs | $2.30/GiB ingested | Expensive! |
| **Estimated Monthly (dev, 1 node)** | **~$50/mo** | |
| **Estimated Monthly (prod HA, 3 nodes)** | **~$300/mo** | |

### Oracle Cloud OKE (Always Free Tier)
| Component | Cost | Notes |
|---|---|---|
| OKE Control Plane | **Free** | |
| Ampere A1.Flex (4 OCPU, 24 GiB) | **Free** | 4 OCPU + 24 GiB total across all VMs |
| Block Volume (200 GiB) | **Free** | 200 GiB total |
| Object Storage (10 TiB) | **Free** | |
| Load Balancer (1 Flexible, 10 Mbps) | **Free** | 1 LB free |
| Data Transfer | **Free** | 10 TB/mo free |
| **Estimated Monthly (within free tier)** | **$0** | If you stay within limits |
| **Beyond Free Tier** | Pay-as-you-go | Ampere: $0.015/OCPU/hr |

---

## Cost Model for This Lab's Components

### Current Lab Stack (What Runs on minikube)

| Component | Replicas | Resources (req/limit) | PVC | LB | Managed Equivalent |
|---|---|---|---|---|---|
| Graph RAG API | 2 | 500m/1Gi → 1000m/2Gi | — | 1 (ingress) | 2× t3.medium pods |
| Postgres (Graph RAG) | 1 | 1Gi/2Gi | 20 GiB | — | RDS/Cloud SQL / self-managed |
| Prometheus | 1 | 512Mi/1Gi | 10 GiB | — | AMP / self-managed |
| Grafana | 1 | 256Mi/512Mi | 1 GiB | — | Grafana Cloud / self-managed |
| Loki | 1 | 512Mi/1Gi | 20 GiB | — | Grafana Cloud / self-managed |
| Tempo | 1 | 512Mi/1Gi | 10 GiB | — | Grafana Cloud / self-managed |
| Alertmanager | 1 | 64Mi/128Mi | — | — | Self-managed |
| Ingress NGINX | 2 | 100m/256Mi | — | 1 | Cloud LB + controller |
| cert-manager | 1 | 64Mi/128Mi | — | — | Self-managed |
| oauth2-proxy | 2 | 64Mi/128Mi | — | — | Self-managed |
| **Total (dev)** | | **~4 vCPU, 8 GiB** | **~61 GiB** | **1–2** | |
| **Total (prod HA)** | | **~12 vCPU, 24 GiB** | **~150 GiB** | **2–3** | |

### Monthly Cost Estimates (US-East-1, On-Demand)

| Scenario | Compute | Storage | LB | Egress/Logs | Total |
|---|---|---|---|---|---|
| **Dev (1 node, single-AZ)** | $60 | $8 | $18 | $10 | **~$96/mo** |
| **Staging (2 nodes, single-AZ)** | $120 | $15 | $18 | $20 | **~$173/mo** |
| **Prod HA (3 nodes, multi-AZ)** | $360 | $45 | $50 | $50 | **~$505/mo** |
| **Oracle Free Tier (dev/staging)** | $0 | $0 | $0 | $0 | **$0** |
| **GKE Autopilot (prod)** | $400 | $30 | $20 | $30 | **~$480/mo** |

---

## Cost Optimization Strategies

### 1. Use Free Tiers Aggressively
- **Oracle Always Free**: Best for dev/staging (4 OCPU, 24 GiB, 200 GiB, 1 LB)
- **GKE Free Zonal**: Free control plane; pay only for nodes
- **AWS EKS**: No free control plane ($73/mo fixed)

### 2. Right-Size Nodes
```yaml
# Instead of 3× t3.large ($183/mo), use 3× t3.medium ($90/mo) + HPA
# Lab needs: 4 vCPU / 8 GiB total → 2× t3.medium covers it
# With HPA scaling to 3 nodes only under load
```

### 3. Spot/Preemptible for Fault-Tolerant Workloads
| Workload | Spot Safe? | Savings |
|---|---|---|
| Graph RAG API (stateless, HPA) | ✅ Yes | 60–90% |
| Prometheus (HA pair) | ⚠️ One replica | 50% |
| Loki/Tempo (replicated) | ⚠️ One replica | 50% |
| Postgres (primary) | ❌ No | — |
| Ingress controller | ❌ No | — |

### 4. Storage Tiering
```yaml
# Loki/Tempo: use object storage (S3/GCS/OCI) not PVC
# Prometheus: remote write to Cortex/Mimir/Thanos on object storage
# Only keep 2h local; ship rest to S3 ($0.023/GiB vs $0.08/GiB for EBS)
```

### 5. Logging/Metrics Sampling
```yaml
# Prometheus: scrape_interval: 30s (not 15s) → 50% fewer samples
# Loki: drop debug logs, keep only warn/error for long-term
# Tempo: tail sampling (keep only error traces) → 90% reduction
```

### 6. Idle Control Plane Avoidance
- **Dev clusters**: Spin down at night (`aws eks update-cluster-config --resources-vpc-config ...` + scale node group to 0)
- **GitOps**: `flux`/`argo` can pause reconciliation
- **Weekend shutdown**: Cron to scale node group to 0 Fri 20:00, up Mon 08:00

---

## Budget Template (Spreadsheet-Ready)

| Item | Unit | Qty (Dev) | Unit Cost/Mo | Monthly Dev | Qty (Prod) | Monthly Prod |
|---|---|---|---|---|---|---|
| Control Plane | cluster | 1 | $73 (EKS) / $0 (GKE/AKS/OKE) | $73 | 1 | $73 |
| Worker Nodes (t3.medium) | node | 1 | $30 | $30 | 3 | $90 |
| Worker Nodes (t3.large) | node | 0 | $61 | $0 | 0 | $0 |
| Load Balancer (ALB/NLB) | LB | 1 | $18 | $18 | 2 | $36 |
| EBS gp3 (20 GiB) | volume | 3 | $1.60 | $4.80 | 6 | $9.60 |
| EBS gp3 (100 GiB) | volume | 1 | $8 | $8 | 2 | $16 |
| S3/Object Storage (100 GiB) | GiB | 100 | $0.023 | $2.30 | 500 | $11.50 |
| Data Egress (10 GiB) | GiB | 10 | $0.09 | $0.90 | 100 | $9 |
| CloudWatch/Logging (5 GiB) | GiB | 5 | $0.50 | $2.50 | 20 | $10 |
| **Subtotal** | | | | **$139.50** | | **$255.10** |
| **Spot Discount (API nodes)** | | | -60% | **-$18** | -60% | **-$54** |
| **Total Estimated** | | | | **~$122/mo** | | **~$201/mo** |

---

## Cost Monitoring & Alerts

### AWS Budgets + Alerts
```hcl
# terraform/aws_budget.tf
resource "aws_budgets_budget" "monthly" {
  name              = "k8s-lab-monthly"
  budget_type       = "COST"
  limit_amount      = "150"
  limit_unit        = "USD"
  time_unit         = "MONTHLY"
  cost_filters = {
    "LinkedAccount" = [var.aws_account_id]
  }
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = ["ops@example.com"]
  }
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = ["ops@example.com"]
  }
}
```

### Kubecost (In-Cluster Cost Visibility)
```yaml
# kubecost/values.yaml
kubecostToken: "your-token"
prometheus:
  server:
    global:
      scrape_interval: 60s
```

---

## Decision Guide: Which Managed K8s?

| Priority | Recommendation |
|---|---|
| **$0 dev/staging** | Oracle Cloud Always Free (OKE) |
| **Lowest prod cost (AWS)** | EKS + Spot nodes + S3 for observability |
| **Lowest prod cost (GCP)** | GKE Standard (free control plane) + e2 instances |
| **Easiest ops** | GKE Autopilot (pay per pod, no node mgmt) |
| **Enterprise/Compliance** | EKS (most mature) or AKS (Azure integration) |
| **Multi-cloud** | Rancher / Cluster API + Terraform |

---

## Acceptance Criteria
- Document exists at `docs/managed-k8s-cost-model.md`
- Tables cover all 5 hidden cost categories (LB, storage, egress, logging, control plane)
- Per-provider breakdown (AWS, GCP, Azure, Oracle) with 2026 pricing
- Lab component mapping shows what each piece costs in cloud
- Optimization strategies with concrete savings estimates
- Budget template + Terraform budget alert example
- Decision guide for choosing a provider

## References
- AWS EKS Pricing: <https://aws.amazon.com/eks/pricing/>
- GKE Pricing: <https://cloud.google.com/kubernetes-engine/pricing>
- AKS Pricing: <https://azure.microsoft.com/pricing/details/kubernetes-service/>
- OCI Always Free: <https://www.oracle.com/cloud/free/>
- Kubecost: <https://www.kubecost.com/>
- FinOps Foundation: <https://www.finops.org/>