# Spec: Cloud Provider Research Template — Terraform Prerequisites

## Problem Statement
The repository has "Notes and provider research only. There is no Terraform implementation." This spec defines the **requirements, elements, and template structure** for a Terraform implementation that provisions a free-tier Kubernetes cluster (Oracle Cloud Always Free preferred, GKE fallback) and deploys the A6 stack unchanged.

## Target Cloud: Oracle Cloud Always Free (Primary)

| Resource | Free Tier Limit | Notes |
|---|---|---|
| Compute | 4 OCPU Ampere (A1.Flex) + 24 GiB RAM | Can be 1×4OCPU or 4×1OCPU VMs |
| Block Storage | 200 GiB total | Boot + data volumes |
| Object Storage | 10 TiB | For backups, Terraform state |
| Load Balancer | 1 Flexible LB (10 Mbps) | For ingress |
| VCN | 1 VCN + subnets, gateways | Network foundation |
| Kubernetes (OKE) | Managed control plane free | Worker nodes use free compute |

**Alternative:** GKE Free Zonal (1 zonal cluster, 744 hrs/mo, egress costs apply)

## Terraform Implementation Requirements

### 1. Repository Structure
```
terraform/
├── main.tf                 # Root module, calls submodules
├── providers.tf            # Provider config (OCI, Helm, Kubernetes, TLS)
├── variables.tf            # Input variables
├── outputs.tf              # Outputs (kubeconfig, LB IP, etc.)
├── versions.tf             # Required provider versions
├── backend.tf              # Remote state (OCI Object Storage)
├── modules/
│   ├── vcn/                # VCN, subnets, IGW, NAT GW, route tables, security lists
│   ├── oke/                # OKE cluster + node pool (Ampere)
│   ├── k8s-providers/      # Kubernetes, Helm providers (depend on oke)
│   ├── ingress-nginx/      # NGINX ingress controller (LB service)
│   ├── cert-manager/       # cert-manager + ClusterIssuer (Let's Encrypt)
│   ├── observability/      # Prometheus, Grafana, Loki, Tempo (Helm)
│   ├── graph-rag/          # Graph RAG API (Helm/Kustomize)
│   └── bastion/            # Teleport/Boundary (optional)
└── environments/
    ├── dev/                # dev.tfvars
    ├── staging/            # staging.tfvars
    └── prod/               # prod.tfvars
```

### 2. Provider Configuration
```hcl
# providers.tf
terraform {
  required_version = ">= 1.6"
  required_providers {
    oci = {
      source  = "oracle/oci"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.30"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.10"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
  backend "oci" {
    # Configured in backend.tf or via env vars
  }
}

provider "oci" {
  region = var.oci_region
  # Auth via ~/.oci/config or env vars (OCI_CLI_*)
}

provider "kubernetes" {
  host                   = oci_containerengine_cluster.main.endpoint_config[0].public_endpoint
  cluster_ca_certificate = base64decode(oci_containerengine_cluster.main.endpoint_config[0].certificate_authority)
  exec {
    api_version = "client.authentication.k8s.io/v1beta1"
    command     = "oci"
    args        = ["ce", "cluster", "generate-kubeconfig", "--cluster-id", oci_containerengine_cluster.main.id, "--region", var.oci_region, "--token-version", "2.0.0"]
  }
}

provider "helm" {
  kubernetes {
    host                   = provider.kubernetes.host
    cluster_ca_certificate = provider.kubernetes.cluster_ca_certificate
    exec {
      api_version = provider.kubernetes.exec[0].api_version
      command     = provider.kubernetes.exec[0].command
      args        = provider.kubernetes.exec[0].args
    }
  }
}
```

### 3. Core Modules

#### `modules/vcn/` — Network Foundation
```hcl
# Creates:
# - VCN (10.0.0.0/16)
# - Public subnet (10.0.0.0/24) — LB, bastion
# - Private subnet (10.0.1.0/24) — OKE workers
# - Internet Gateway + NAT Gateway
# - Route tables + security lists (or NSGs)
# - Service gateway (for Object Storage, Vault)
```

#### `modules/oke/` — OKE Cluster + Ampere Node Pool
```hcl
# Creates:
# - OKE cluster (managed control plane, free)
# - Node pool: Ampere A1.Flex, 4 OCPU / 24 GiB total
#   - Can be 1 node (4 OCPU) or 2 nodes (2 OCPU each) for HA
#   - Pod subnet = private subnet
#   - Image: Oracle Linux 8 or Ubuntu 22.04
#   - Shape: VM.Standard.A1.Flex
#   - OCPU / Memory configurable via var.node_pool_shape
# - Kubeconfig output
```

#### `modules/ingress-nginx/` — External Access
```hcl
# Helm release: ingress-nginx
# Service type: LoadBalancer → provisions OCI Flexible LB (free tier: 1)
# Annotations for OCI LB:
#   service.beta.kubernetes.io/oci-load-balancer-shape: "flexible"
#   service.beta.kubernetes.io/oci-load-balancer-shape-flex-min: "10"
#   service.beta.kubernetes.io/oci-load-balancer-shape-flex-max: "100"
```

#### `modules/cert-manager/` — TLS
```hcl
# Helm release: cert-manager
# ClusterIssuer: Let's Encrypt (staging + prod)
# Requires: public DNS zone delegated to OCI DNS (or external)
```

#### `modules/observability/` — Monitoring Stack
```hcl
# Helm releases (in order):
# 1. prometheus-stack (Prometheus + Alertmanager + Grafana)
#    - remoteWrite to OCI Object Storage (or Cortex/Mimir)
#    - persistent volumes for local retention (2h)
# 2. loki (logs)
#    - storage: filesystem (PVC) or S3 (OCI Object Storage)
# 3. tempo (traces)
#    - storage: filesystem (PVC) or S3
# 4. grafana dashboards + datasources
```

#### `modules/graph-rag/` — Application
```hcl
# Option A: Helm chart (create one from k8s/ base)
# Option B: kubectl apply -k via null_resource + local-exec (simpler for Kustomize)
# Uses: Kustomize overlay for environment (dev/staging/prod)
```

#### `modules/bastion/` — Secure Access
```hcl
# Option: Teleport (Helm) or Boundary (Helm)
# Requires: public subnet access, TLS cert, OIDC connector
```

### 4. State Management
```hcl
# backend.tf
terraform {
  backend "oci" {
    bucket_name = "terraform-state"
    namespace   = "ociateam"
    key         = "k8s-lab-kit/terraform.tfstate"
    region      = "us-ashburn-1"
    # Auth via OCI_CLI_* env vars or ~/.oci/config
  }
}
```

**Locking:** OCI Object Storage supports native locking (no DynamoDB needed).

### 5. Variables Template (`variables.tf`)
```hcl
variable "oci_region" {
  type        = string
  default     = "us-ashburn-1"
  description = "OCI region for all resources"
}

variable "compartment_ocid" {
  type        = string
  description = "OCID of compartment to create resources in"
}

variable "ssh_public_key" {
  type        = string
  description = "SSH public key for node pool access (bastion/debug)"
}

variable "dns_zone_name" {
  type        = string
  description = "DNS zone for ingress (e.g., lab.example.com)"
  default     = ""
}

variable "letsencrypt_email" {
  type        = string
  description = "Email for Let's Encrypt registration"
  default     = ""
}

variable "environment" {
  type        = string
  default     = "dev"
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "node_pool_config" {
  type = object({
    shape       = string  # "VM.Standard.A1.Flex"
    ocpus       = number  # 1-4 per node
    memory_gb   = number  # 6-24 per node
    node_count  = number  # 1-3
  })
  default = {
    shape      = "VM.Standard.A1.Flex"
    ocpus      = 4
    memory_gb  = 24
    node_count = 1
  }
}
```

### 6. Outputs (`outputs.tf`)
```hcl
output "kubeconfig" {
  description = "Kubeconfig for cluster access"
  value       = oci_containerengine_cluster.main.kubeconfig_content
  sensitive   = true
}

output "ingress_lb_ip" {
  description = "Public IP of ingress LoadBalancer"
  value       = kubernetes_service.ingress_nginx.status[0].load_balancer[0].ingress[0].ip
}

output "grafana_url" {
  description = "Grafana URL"
  value       = "https://grafana.${var.dns_zone_name}"
}

output "graph_rag_url" {
  description = "Graph RAG API URL"
  value       = "https://graph-rag.${var.dns_zone_name}"
}
```

### 7. Deployment Script (`deploy.sh`)
```bash
#!/usr/bin/env bash
# deploy.sh — one-command deploy for a given environment
set -euo pipefail

ENV=${1:-dev}
TF_DIR="terraform/environments/${ENV}"

if [[ ! -f "${TF_DIR}/terraform.tfvars" ]]; then
  echo "Create ${TF_DIR}/terraform.tfvars from template"
  exit 1
fi

cd terraform
terraform init
terraform workspace select ${ENV} || terraform workspace new ${ENV}
terraform plan -var-file="${TF_DIR}/terraform.tfvars" -out=tfplan
terraform apply tfplan

# Post-deploy: wait for ingress LB, print URLs
terraform output -json | jq -r '.ingress_lb_ip.value'
```

### 8. Teardown Checklist (Budget Safety)
```bash
# teardown.sh — destroys everything, verifies zero cost
terraform destroy -var-file=environments/prod/terraform.tfvars -auto-approve
# Verify in OCI Console:
# - Compute: 0 instances
# - Block Storage: 0 volumes (or only boot if kept)
# - Load Balancer: 0 LBs
# - Object Storage: only terraform-state bucket remains
# - OKE: 0 clusters
```

## Prerequisites Checklist (Before Running Terraform)

| Prerequisite | How to Satisfy |
|---|---|
| OCI Account | Sign up at cloud.oracle.com (Always Free) |
| OCI CLI configured | `oci setup config` → `~/.oci/config` |
| Compartment created | Root compartment or dedicated compartment OCID |
| SSH key pair | `ssh-keygen -t ed25519 -f ~/.ssh/oci_lab` |
| DNS zone (optional) | Delegate subdomain to OCI DNS or use external DNS |
| Let's Encrypt email | For cert-manager ClusterIssuer |
| Terraform ≥ 1.6 | `brew install terraform` / `apt install terraform` |
| kubectl, helm, kustomize | For post-deploy validation |

## Free-Tier Guardrails (Terraform-Level)

```hcl
# In variables.tf validation or pre-commit hook
variable "node_pool_config" {
  validation {
    condition     = var.node_pool_config.ocpus * var.node_pool_config.node_count <= 4
    error_message = "Total OCPUs must not exceed 4 (Always Free limit)"
  }
  validation {
    condition     = var.node_pool_config.memory_gb * var.node_pool_config.node_count <= 24
    error_message = "Total memory must not exceed 24 GiB (Always Free limit)"
  }
}
```

## Acceptance Criteria
- `terraform init && terraform plan` succeeds with `dev.tfvars`
- `terraform apply` provisions: VCN, OKE cluster, Ampere node pool, ingress LB, cert-manager, observability stack, Graph RAG API
- `kubectl get pods -A` shows all components healthy
- `curl https://graph-rag.lab.example.com/healthz` returns 200
- `./teardown.sh` destroys all resources; OCI Console shows $0 estimated cost
- State stored in OCI Object Storage (not local)

## References
- Oracle Cloud Always Free: <https://www.oracle.com/cloud/free/>
- OCI Terraform Provider: <https://registry.terraform.io/providers/oracle/oci/latest/docs>
- OKE Terraform Module: <https://registry.terraform.io/modules/oracle-terraform-modules/oke/oci/latest>
- cert-manager on OCI: <https://cert-manager.io/docs/configuration/acme/dns01/oci/>
- OCI Load Balancer annotations: <https://docs.oracle.com/en-us/iaas/Content/ContEng/Tasks/contengloadbalancer.htm>
- Graph RAG Kustomize base: `ai/patterns/graph-rag/k8s/`