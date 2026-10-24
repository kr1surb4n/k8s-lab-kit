# minikube skeleton

The default. One Docker container, no host changes, `minikube mount` for the
host-file exercises.

```bash
# the doctor prints these numbers for this machine
minikube start --driver=docker --cpus=6 --memory=6144 --disk-size=20g

minikube addons enable metrics-server   # kubectl top
minikube addons enable ingress          # optional, N1
minikube mount "$PWD:/mnt/lab"          # A1 and A7
```

Why these numbers rather than the PDF's 4 CPU / 8 GiB / 20 GiB:

- 8 GiB leaves the host swapping during a PHP build or an observability install.
- 20 GiB is only safe while the disk has more than ~40 GiB free; `make doctor`
  drops it to 15 GiB otherwise.
- 6 CPU is plenty for three nginx replicas, PHP-FPM, PostgreSQL and a small
  metrics stack.

Known limits, all of them exercises rather than bugs:

| Limit | Consequence | Workaround |
|---|---|---|
| node IP is inside Docker | LAN cannot reach a NodePort | `kubectl port-forward --address 0.0.0.0` |
| LoadBalancer has no controller | `EXTERNAL-IP` stays `<pending>` | port-forward, or k3d for the real thing |
| `minikube mount` is a foreground process | pods using hostPath stay `ContainerCreating` | `scripts/lab-up.sh a1 --mount` detaches it |
| images live inside the node | a host build is not visible | `minikube image load` |

Useful:

```bash
minikube ssh                  # inside the node
minikube dashboard            # needs the dashboard addon
minikube service web -n k8s-lab --url   # binds 127.0.0.1 only
minikube delete --profile minikube
```
