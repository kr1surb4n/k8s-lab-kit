# k3s skeleton (real host node)

k3s is a single binary that runs a real node: containerd, kubelet, the API
server and the scheduler, all under systemd. Unlike the other skeletons it
changes the host, so it is a deliberate step, not the default.

```bash
clusters/k3s/install.sh --dry-run
sudo clusters/k3s/install.sh
export KUBECONFIG=$HOME/.kube/config-k3s
kubectl get nodes -o wide
```

What you get:

- API on `https://<host>:6443`, reachable from the LAN.
- `NodePort` services reachable from the LAN (the A4 lesson without a tunnel).
- StorageClass `local-path`.
- Traefik disabled; install ingress-nginx for the N1 exercise.
- Config in `/etc/rancher/k3s/config.yaml`, data in `/var/lib/rancher/k3s`.

The lab then works unchanged, except:

| Thing | minikube | k3s |
|---|---|---|
| StorageClass | `standard` | `local-path` |
| LoadBalancer | `<pending>` | `klipper-lb` gives a node IP |
| LAN access | port-forward | NodePort or ingress |

Host impact to remember:

- `systemctl status k3s`, `journalctl -u k3s`.
- It writes iptables rules and a CNI config; Docker still works, but the two
  container runtimes are separate.
- Uninstall: `sudo /usr/local/bin/k3s-uninstall.sh` (and `k3s-agent-uninstall.sh`
  on workers). The data directory is removed, so back up anything you care about.

This is the honest answer to "would another distribution solve the LAN problem":
yes, because the node is the host. The cost is that cleanup is no longer one
command.
