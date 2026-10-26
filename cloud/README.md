# Cloud Free Tier Deployment

> **Imported from a different repository.** Copied on 2026-10-26 from the
> abandoned `~/00___Castle/07__WorkShOps/k8s` copy (commit `db68801`). This is
> provider research, not a validated plan: the bootstrap-script URL below is a
> placeholder and there is no Terraform yet. The current Phase 18 plan (Oracle
> first, `terraform validate`/`plan` only, teardown checklist before
> provisioning) is in `analysis/07-what-to-do.md` §5.

Deploy the lab stacks to cloud free tiers for production-like experience.

## Providers Comparison

| Provider | Free Tier | Best For | Caveats |
|----------|-----------|----------|---------|
| **Oracle Cloud** | 4 OCPU Ampere + 24GB RAM (Always Free) | Long-running labs, ARM workloads | Capacity often unavailable; verify at signup |
| **Google Cloud** | 1 zonal cluster free (control plane) | Real LB, Ingress, GCS, Workload Identity | Nodes + LB billed; free tier = control plane only |
| **Azure AKS** | Free tier control plane | Enterprise defaults, Entra ID | Node VMs + LBs billed |
| **AWS EKS** | **Paid** (~$0.10/h control plane) | IAM/RBAC depth, AWS integration | Most expensive for learning basics |

## Quick Start: Oracle Cloud (Recommended)

```bash
# 1. Create Oracle Cloud account (verify Always Free eligibility)
# 2. Create VCN with public subnet
# 3. Create compute instance (VM.Standard.A1.Flex, 4 OCPU, 24GB)
# 3. SSH and run bootstrap:
curl -sSL https://raw.githubusercontent.com/your-repo/k8s-lab/main/scripts/bootstrap-oracle.sh | bash
# 4. Deploy lab:
kubectl apply -k boilerplates/overlays/a6
```

## Quick Start: GKE Autopilot (Free Control Plane)

```bash
# 1. gcloud auth login && gcloud config set project YOUR_PROJECT
# 2. Enable APIs: container, compute, iam
# 3. Create cluster:
gcloud container clusters create-auto lab \
  --region=us-central1 \
  --release-channel=regular
# 4. Get credentials:
gcloud container clusters get-credentials lab --region=us-central1
# 5. Deploy:
kubectl apply -k boilerplates/overlays/a6
```

## Quick Start: AKS Free Tier

```bash
# 1. az login && az group create -n lab-rg -l eastus
# 2. Create cluster:
az aks create -g lab-rg -n lab \
  --node-count 1 --node-vm-size Standard_B2s \
  --enable-managed-identity --generate-ssh-keys
# 3. Get credentials:
az aks get-credentials -g lab-rg -n lab
# 4. Deploy:
kubectl apply -k boilerplates/overlays/a6
```

## Terraform Modules

```bash
# Oracle
cd cloud/oracle && terraform init && terraform apply

# GKE
cd cloud/gke && terraform init && terraform apply

# AKS
cd cloud/aks && terraform init && terraform apply
```

## Teardown Checklist (CRITICAL)

- [ ] `kubectl delete -k .` all namespaces
- [ ] `terraform destroy` infrastructure
- [ ] Verify $0 next bill
- [ ] Delete SSH keys / IAM roles
- [ ] Remove DNS records

## Cost Monitoring

```bash
# Set budget alerts
gcloud billing budgets create --billing-account=BILLING_ID --display-name="Lab Budget" --budget-amount=5USD
az consumption budget create --budget-name LabBudget --amount 5 --time-grain Monthly
```

## Lab-Specific Notes

| Lab | Cloud Notes |
|-----|-------------|
| A1-A3 | Work on any cluster; no special requirements |
| A4 | Needs real LoadBalancer (GKE/AKS/Oracle); minikube tunnel doesn't work |
| A5 | Works everywhere |
| A6 | Needs LoadBalancer for real external IP |
| A7 | Needs GPU node for PHP build; Oracle Ampere has no GPU |
| Graph RAG | Needs PostgreSQL + AGE; use managed PG (Cloud SQL, RDS, Azure DB) |
| Observability | Managed Prometheus/Grafana available (GMP, Azure Monitor, CloudWatch) |

## Budget Rules

1. **Write teardown BEFORE create** - document `teardown.md` first
2. **One cluster, one namespace, one experiment** - no "while I'm here"
3. **Turn off same day** - `gcloud container clusters delete`, `az aks delete`, `terraform destroy`
4. **No real secrets/data** in trial accounts
5. **Check bill next day** - $0 bill is the only proof