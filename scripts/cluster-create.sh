#!/usr/bin/env bash
# Create a lab cluster with one of the skeletons in clusters/.
#
# minikube is the default: no host changes, one command up and down. kind and
# k3d are for the LAN/NodePort comparison, k3s for a real node.
#
# Examples:
#   scripts/cluster-create.sh                       # minikube, doctor sizing
#   scripts/cluster-create.sh minikube --ingress
#   scripts/cluster-create.sh kind
#   scripts/cluster-create.sh k3d --name lab
#   scripts/cluster-create.sh k3s --dry-run         # prints the root commands
#   scripts/cluster-create.sh minikube --profile minimal
set -Eeuo pipefail
trap 'printf "error: unexpected failure at line %s: %s\n" "$LINENO" "$BASH_COMMAND" >&2' ERR

# shellcheck source=lib/common.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

driver=minikube
name=""
profile=standard
ingress=0
metrics=1

usage() {
  cat <<EOF
Usage: $(basename "${BASH_SOURCE[0]}") [driver] [options]

Drivers:
  minikube   default, docker driver, no host changes
  kind       Kubernetes in Docker, needs port mappings for ingress
  k3d        k3s in Docker, publishes ports to the host
  k3s        real node, needs root and systemd (prints the commands)

Options:
  -n, --name NAME       cluster/profile name (default: minikube or k8s-lab)
  -p, --profile P       minimal | standard | full (default: standard)
      --ingress         enable the ingress addon (minikube) or print the hint
      --no-metrics      do not enable metrics-server
  -d, --dry-run         print the commands
  -y, --yes             allow the k3s installer to run (root)
  -h, --help            print this help

Examples:
  scripts/cluster-create.sh
  scripts/cluster-create.sh k3d --name lab
  scripts/cluster-create.sh minikube --profile minimal
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h | --help) usage; exit 0 ;;
    minikube | kind | k3d | k3s) driver=$1 ;;
    -n | --name) name=${2:?missing name}; shift ;;
    -p | --profile) profile=${2:?missing profile}; shift ;;
    --ingress) ingress=1 ;;
    --no-metrics) metrics=0 ;;
    -d | --dry-run) export LAB_DRY_RUN=1 ;;
    -y | --yes) assume_yes=1 ;;
    *) die "unknown argument: $1 (try --help)" ;;
  esac
  shift
done

case "$profile" in
  minimal | standard | full) ;;
  *) die "unknown profile '$profile' (minimal|standard|full)" ;;
esac

[[ -n $name ]] || { [[ $driver == minikube ]] && name=minikube || name=k8s-lab; }

# Read the machine and adjust for the requested profile.
read -r cpus mem disk < <(recommend_sizing "$K8S_LAB_ROOT")
case "$profile" in
  minimal)
    cpus=$(( cpus / 2 )); (( cpus < 2 )) && cpus=2
    mem=$(( mem / 2 )); (( mem < 2048 )) && mem=2048
    disk=15
    ;;
  full)
    cpus=$(( cpus + 2 )); (( cpus > 8 )) && cpus=8
    mem=$(( mem + 2048 )); (( mem > 8192 )) && mem=8192
    disk=$(( disk + 5 ))
    ;;
esac

case "$driver" in
  minikube)
    if ! have minikube; then
      die "minikube not found; run: setup/install-tools.sh"
    fi
    run minikube start --driver=docker --cpus="$cpus" --memory="$mem" \
      --disk-size="${disk}g" --profile "$name"
    [[ $LAB_DRY_RUN == 1 ]] || run kubectl config use-context "$name"
    if [[ $metrics == 1 ]]; then
      run minikube addons enable metrics-server --profile "$name"
    fi
    if [[ $ingress == 1 ]]; then
      run minikube addons enable ingress --profile "$name"
    fi
    log ""
    log "cluster $name is up (docker driver, ${cpus} CPU, ${mem} MiB, ${disk} GiB)"
    log "next: scripts/lab-up.sh a6"
    ;;

  kind)
    have kind || die "kind not found; run: setup/install-tools.sh"
    config="$K8S_LAB_ROOT/clusters/kind/config.yaml"
    run kind create cluster --name "$name" --config "$config"
    log ""
    log "cluster $name is up; ingress ports 8080/8443 are published"
    log "to use them: kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml"
    ;;

  k3d)
    have k3d || die "k3d not found; run: setup/install-tools.sh"
    config="$K8S_LAB_ROOT/clusters/k3d/config.yaml"
    # The skeleton carries a default name; replace it with the requested one.
    tmp=$(mktemp "${TMPDIR:-/tmp}/k3d-config.XXXXXX")
    sed "s/^  name: k8s-lab$/  name: $name/" "$config" >"$tmp"
    if [[ $LAB_DRY_RUN == 1 ]]; then
      printf '+ k3d cluster create --config %s\n' "$tmp"
      rm -f "$tmp"
    else
      k3d cluster create --config "$tmp"
      rm -f "$tmp"
      kubectl config use-context "k3d-$name"
    fi
    log ""
    log "cluster $name is up; http://127.0.0.1:8080 reaches the load balancer"
    ;;

  k3s)
    installer="$K8S_LAB_ROOT/clusters/k3s/install.sh"
    [[ -x $installer ]] || die "missing $installer"
    log "k3s changes the host (systemd, containerd, iptables); it is not a container."
    if [[ ${assume_yes:-0} == 1 || $LAB_DRY_RUN == 1 ]]; then
      "$installer" --dry-run
    else
      log "re-run with --yes to actually install it, or read clusters/k3s/README.md"
      "$installer" --dry-run
    fi
    ;;
esac
