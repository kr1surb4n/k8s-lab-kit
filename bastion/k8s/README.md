# In-cluster jump pod

Only use this when a host bastion cannot reach ClusterIPs. It holds a
ServiceAccount token, so its RBAC is deliberately small.

## Build and load

```bash
docker build -t k8s-lab/bastion:1.0 bastion/k8s
minikube image load k8s-lab/bastion:1.0
# k3d: k3d image import k8s-lab/bastion:1.0 -c k8s-lab
# kind: kind load docker-image k8s-lab/bastion:1.0 --name k8s-lab
```

## Apply

```bash
kubectl apply -f bastion/k8s/namespace.yaml
kubectl apply -f bastion/k8s/rbac.yaml

# Put your real public key in a copy, then apply the copy (never the example).
cp bastion/k8s/secret.example.yaml /tmp/bastion-authorized-keys.yaml
$EDITOR /tmp/bastion-authorized-keys.yaml
kubectl apply -f /tmp/bastion-authorized-keys.yaml

kubectl apply -f bastion/k8s/config.yaml
kubectl apply -f bastion/k8s/deployment.yaml
kubectl apply -f bastion/k8s/service.yaml
kubectl apply -f bastion/k8s/networkpolicy.yaml

kubectl rollout status deploy/bastion -n bastion
```

## Connect

```bash
kubectl port-forward -n bastion svc/bastion 2222:22
ssh -p 2222 -i ~/.ssh/id_ed25519 labjump@127.0.0.1
# inside:
kubectl get pods -n k8s-lab
```

On k3d/k3s, skip the port-forward and use `ssh -p 30222 labjump@<node-ip>`.

## What the pod can and cannot do

- Can: list/get pods, services, endpoints, configmaps, events in `k8s-lab`,
  read logs, exec into a pod in `k8s-lab`.
- Cannot: read Secrets, change anything, see other namespaces, or create
  cluster-scoped objects.
- The token is a long-lived Secret. Delete it when the bastion is gone.

## Check the policy

```bash
kubectl get networkpolicy -n bastion
kubectl describe networkpolicy bastion -n bastion
```

If the CNI ignores NetworkPolicy (minikube default), the pod is still protected
by SSH keys and RBAC, but not by the network rules. Do not expose the NodePort
in that case.
