#!/usr/bin/env bash
# Install k3s on this host, using clusters/k3s/config.yaml.
#
# This is the only skeleton that changes the host: systemd units, containerd,
# iptables rules and /etc/rancher. Read the script before running it with sudo.
#
#   clusters/k3s/install.sh --dry-run
#   sudo clusters/k3s/install.sh
#
# The PDF uses SH_K3S_EXEC, which does nothing; the installer reads
# INSTALL_K3S_EXEC. That is the variable used here.
set -Eeuo pipefail

config_src=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/config.yaml
config_dir=/etc/rancher/k3s
dry_run=0

case "${1:-}" in
  -h | --help)
    printf 'Usage: sudo %s [--dry-run]\n' "$(basename "$0")"
    exit 0
    ;;
  --dry-run) dry_run=1 ;;
  "") ;;
  *) printf 'unknown argument: %s\n' "$1" >&2; exit 2 ;;
esac

step() { printf '==> %s\n' "$*"; }

if [[ $dry_run == 1 ]]; then
  step "would install $config_src to $config_dir/config.yaml"
  step "would run: curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC='server --config $config_dir/config.yaml' sh -"
  step "would wait for the node, then copy the kubeconfig to the invoking user"
  step "would print the StorageClass (local-path) and the ingress class (none)"
  exit 0
fi

[[ $EUID -eq 0 ]] || { printf 'error: run with sudo\n' >&2; exit 1; }

# Keep the config where k3s looks for it.
step "installing $config_dir/config.yaml"
mkdir -p "$config_dir"
install -m 0644 "$config_src" "$config_dir/config.yaml"

# The official installer is the supported path; INSTALL_K3S_EXEC adds our config.
step "running the k3s installer"
curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="server --config $config_dir/config.yaml" sh -

# Wait for the API to answer before declaring success.
step "waiting for the node"
for _ in $(seq 1 60); do
  if k3s kubectl get node >/dev/null 2>&1; then break; fi
  sleep 2
done
k3s kubectl get nodes -o wide

# Give the human who ran sudo a kubeconfig they can read.
if [[ -n ${SUDO_USER:-} ]]; then
  home=$(getent passwd "$SUDO_USER" | cut -d: -f6)
  if [[ -n $home ]]; then
    install -d -m 0700 -o "$SUDO_USER" -g "$SUDO_USER" "$home/.kube"
    install -m 0600 -o "$SUDO_USER" -g "$SUDO_USER" \
      /etc/rancher/k3s/k3s.yaml "$home/.kube/config-k3s"
    step "wrote $home/.kube/config-k3s"
    step "use it with: export KUBECONFIG=$home/.kube/config-k3s"
  fi
fi

step "done; uninstall with /usr/local/bin/k3s-uninstall.sh"
