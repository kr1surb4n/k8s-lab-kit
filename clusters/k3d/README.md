# k3d skeleton

k3d runs k3s inside Docker. It is the middle ground: no host changes, but the
load balancer can publish real host ports.

```bash
scripts/cluster-create.sh k3d --name k8s-lab
# or directly:
k3d cluster create --config clusters/k3d/config.yaml
```

What the skeleton gives you:

- 1 server + 1 agent (two containers, ~1 GiB of Docker memory).
- host `8080` → load balancer `80`, host `8443` → `443`.
- Traefik disabled, so install ingress-nginx if you want the N1 exercise:

```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/cloud/deploy.yaml
```

Notes:

- StorageClass is `local-path`, not `standard`. Change the PVC manifest or use
  the overlay when a scenario hard-codes `standard`.
- Images built on the host must be imported:
  `k3d image import k8s-lab/php:8.3 -c k8s-lab`.
- The API server is at `https://0.0.0.0:6443` by default; k3d writes the
  kubeconfig and switches the context (`k3d-k8s-lab`).
- Delete with `k3d cluster delete k8s-lab`.
