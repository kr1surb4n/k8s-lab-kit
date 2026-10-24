# Managed clusters and free tiers

The lab manifests are written for a local single node, but they run on a managed
cluster with three changes: a real `LoadBalancer`, a cloud `StorageClass`, and an
image registry the nodes can pull from.

| Provider | Control plane | Nodes | Best use | Watch out |
|---|---|---|---|---|
| **Oracle OKE / Always Free** | free | 4 OCPU Ampere + 24 GiB (always free, if capacity exists) | the only long-lived free lab | capacity is often unavailable; verify at signup |
| **Google GKE** | one free zonal cluster | paid | real LB, ingress, GCS, Workload Identity | the free control plane is not a free cluster |
| **Azure AKS** | free tier control plane | paid | enterprise defaults, Entra ID | node VMs and LBs are billed |
| **AWS EKS** | **paid** (~$0.10/h) | paid | IAM/RBAC depth | the most expensive way to learn the basics |

Rules that keep a free tier free:

1. Write the teardown **before** the create: `cloud/<provider>/teardown.md`.
2. One cluster, one namespace, one experiment. No "while I am here".
3. Turn off the control plane the same day (`gcloud container clusters delete`,
   `az aks delete`, `eksctl delete cluster`, OCI console).
4. Never put real secrets or data in a trial account.
5. Check the bill the next day. A zero bill is the only proof.

## Commands, for reference

```bash
# GKE (needs gcloud auth and a project)
gcloud container clusters create lab --zone europe-west1-b --num-nodes 1 \
  --machine-type e2-small --disk-size 20GB
gcloud container clusters get-credentials lab --zone europe-west1-b
# ... run the lab ...
gcloud container clusters delete lab --zone europe-west1-b

# AKS
az aks create -g lab-rg -n lab --node-count 1 --node-vm-size Standard_B2s \
  --enable-managed-identity --generate-ssh-keys
az aks get-credentials -g lab-rg -n lab
az group delete -n lab-rg --yes --no-wait

# EKS (the control plane is billed)
eksctl create cluster --name lab --region eu-west-1 --nodes 1 \
  --node-type t3.small
eksctl delete cluster --name lab --region eu-west-1
```

Oracle's Always Free Ampere shape is the only one that stays up without a trial
clock; it is also the one where `kubectl` sees a normal node, so it is the best
place to practise `NodePort` and a real bastion (see `bastion/`).

Verify the current terms before signing up. Every table on the internet,
including this one, goes stale.
