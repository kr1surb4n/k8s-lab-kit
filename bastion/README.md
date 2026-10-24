# Bastion host

A bastion is the one machine allowed to reach the lab network from outside. It
is not a magic security device: it is a small, boring host with keys, logs and
a short list of things it may forward.

There are two shapes here. Use the first unless you have a reason.

| Shape | Where | What it protects | Complexity |
|---|---|---|---|
| **Host bastion** (default) | a small VM or the lab host itself | SSH access to hosts and the kubeconfig | low |
| **In-cluster jump pod** | a pod in the cluster | access to ClusterIP services and the API from inside | medium, and it holds a token |

## Host bastion

```text
laptop --ssh--> bastion (public or LAN) --ssh--> lab hosts
                              \--kubectl--> API :6443
```

Files:

| Path | What |
|---|---|
| `host/sshd_config.d/10-bastion.conf` | the hardening drop-in |
| `host/setup.sh` | creates the user, installs keys, applies ufw, validates sshd |
| `host/audit.sh` | logs every command to journald under the `bastion` tag |
| `client/ssh_config` | ProxyJump on the laptop |

```bash
bastion/host/setup.sh --dry-run
sudo bastion/host/setup.sh --user labjump --key ~/.ssh/id_ed25519.pub
```

Rules that matter more than the config file:

- **Keys only, one user, no root login.** `PermitRootLogin no`,
  `PasswordAuthentication no`, `AllowUsers labjump`.
- **Forward only what is needed.** `AllowTcpForwarding local` (not `remote`),
  `PermitOpen` a short list, no agent forwarding unless you need it.
- **Log the session.** `audit.sh` writes commands to journald; `sshd` logs to
  the same place. Ship them somewhere else if the bastion is the only door.
- **Patch it like a server, not like a pet.** The bastion is the box an attacker
  will try first; unattended-upgrades and a reboot window are part of the design.
- **No kubeconfig with cluster-admin.** Give the bastion a read-only context for
  day-to-day work; keep the admin kubeconfig on the laptop.

## In-cluster jump pod

Only for reaching ClusterIPs and the API from a pod network that has no route
out. It holds a ServiceAccount token; keep it read-only and namespace-scoped.

```bash
kubectl apply -f bastion/k8s/
kubectl port-forward -n bastion svc/bastion 2222:22
ssh -p 2222 -i ~/.ssh/id_ed25519 labjump@127.0.0.1
```

The manifests:

| File | What |
|---|---|
| `k8s/namespace.yaml` | `bastion` namespace |
| `k8s/rbac.yaml` | read-only Role + RoleBinding + long-lived token Secret |
| `k8s/config.yaml` | sshd config and the authorized_keys placeholder |
| `k8s/deployment.yaml` | Alpine + openssh + kubectl, one replica |
| `k8s/service.yaml` | ClusterIP (port-forward) and an optional NodePort |
| `k8s/networkpolicy.yaml` | ingress only from the LAN, egress only DNS + API |

Build the image once:

```bash
docker build -t k8s-lab/bastion:1.0 bastion/k8s
minikube image load k8s-lab/bastion:1.0
```

## What not to do

- Do not expose the kube API directly to the internet and call it a bastion.
- Do not put a private key in a Secret "for convenience".
- Do not enable `GatewayPorts yes` unless you can explain who reaches it.
- Do not make the bastion the only place with logs.
