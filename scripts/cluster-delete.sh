#!/usr/bin/env bash
# Delete a lab cluster created by cluster-create.sh.
#
# It only touches clusters whose name matches, and it says what it will delete
# before doing it. Docker volumes created by kind/k3d go with the cluster.
#
# Examples:
#   scripts/cluster-delete.sh                 # the default minikube profile
#   scripts/cluster-delete.sh kind --name k8s-lab
#   scripts/cluster-delete.sh all --yes
set -Eeuo pipefail
trap 'printf "error: unexpected failure at line %s: %s\n" "$LINENO" "$BASH_COMMAND" >&2' ERR

driver=minikube
name=minikube

usage() {
  cat <<EOF
Usage: $(basename "${BASH_SOURCE[0]}") [minikube|kind|k3d|k3s|all] [options]

Options:
  -n, --name NAME   cluster/profile name (default: minikube)
  -y, --yes         do not ask
  -d, --dry-run     print the commands
  -h, --help        print this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h | --help) usage; exit 0 ;;
    minikube | kind | k3d | k3s | all) driver=$1 ;;
    -n | --name) name=${2:?missing name}; shift ;;
    -y | --yes) assume_yes=1 ;;
    -d | --dry-run) export LAB_DRY_RUN=1 ;;
    *) printf 'unknown argument: %s\n' "$1" >&2; exit 2 ;;
  esac
  shift
done

# Run a command, or print it in dry-run mode.
run_or_print() {
  if [[ $LAB_DRY_RUN == 1 ]]; then printf '+ %s\n' "$*"; else "$@"; fi
}

# Ask once, unless --yes or dry-run.
confirm() {
  [[ ${assume_yes:-0} == 1 || $LAB_DRY_RUN == 1 ]] && return 0
  local answer
  read -r -p "$1 [y/N] " answer
  [[ $answer == [yY]* ]]
}

delete_minikube() {
  have minikube || { printf 'minikube not installed\n'; return 0; }
  printf 'minikube profile: %s\n' "$name"
  run_or_print minikube delete --profile "$name"
}

delete_kind() {
  have kind || { printf 'kind not installed\n'; return 0; }
  run_or_print kind delete cluster --name "$name"
}

delete_k3d() {
  have k3d || { printf 'k3d not installed\n'; return 0; }
  run_or_print k3d cluster delete "$name"
}

delete_k3s() {
  printf 'k3s is a host install; use the uninstall script:\n'
  printf '  /usr/local/bin/k3s-uninstall.sh   (as root)\n'
}

case "$driver" in
  minikube) delete_minikube ;;
  kind) delete_kind ;;
  k3d) delete_k3d ;;
  k3s) delete_k3s ;;
  all)
    confirm "delete every lab cluster (minikube, kind, k3d)?" || exit 0
    delete_minikube
    delete_kind
    delete_k3d
    ;;
esac
