# kind skeleton

kind runs a Kubernetes node as a Docker container. It is the cheapest way to
get an "ingress-ready" cluster with published host ports.

```bash
scripts/cluster-create.sh kind
# or directly:
kind create cluster --name k8s-lab --config clusters/kind/config.yaml

kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=180s
```

The mapping in `config.yaml` publishes host `8080` to node port `80` and host
`8443` to node port `443`. The ingress controller still has to listen on those
node ports: the provider manifest above does that with a DaemonSet on the
control-plane node, which is why the node is labelled `ingress-ready=true`.

Try the lab:

```bash
scripts/lab-up.sh a6
curl -s -H 'Host: app.example.com' http://127.0.0.1:8080/ | head -3
```

Notes:

- `kind` keeps its images inside the node. To use a locally built image, run
  `kind load docker-image k8s-lab/php:8.3 --name k8s-lab`.
- Storage is `standard` (local-path provisioner).
- Delete with `kind delete cluster --name k8s-lab`; the Docker volumes go too.
