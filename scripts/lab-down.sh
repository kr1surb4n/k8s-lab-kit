#!/usr/bin/env bash
# Tear one scenario down, or the whole lab namespace, or the cluster.
#
# Examples:
#   scripts/lab-down.sh a6
#   scripts/lab-down.sh all --yes
#   scripts/lab-down.sh --cluster --yes
#   scripts/lab-down.sh a6 --dry-run
set -Eeuo pipefail
trap 'printf "error: unexpected failure at line %s: %s\n" "$LINENO" "$BASH_COMMAND" >&2' ERR

# shellcheck source=lib/common.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

# Print the help text.
usage() {
  cat <<EOF
Usage: $(basename "${BASH_SOURCE[0]}") [scenario|all] [options]

Remove what lab-up.sh created. Nothing else in the cluster is touched.

Arguments:
  <scenario>   delete the manifests of a1, a2, a3, a5, a6 or a7
  all          delete the whole namespace $LAB_NAMESPACE

Options:
  -n, --namespace NS   namespace to use (default: $LAB_NAMESPACE)
      --cluster        delete the minikube cluster as well
  -y, --yes            do not ask for confirmation
  -d, --dry-run        print the commands, change nothing
  -h, --help           print this help

EOF
}

target=all
delete_cluster=0
assume_yes=0

# Read the command line.
while [[ $# -gt 0 ]]; do
  case "$1" in
    -h | --help) usage; exit 0 ;;
    -n | --namespace) LAB_NAMESPACE=${2:?missing namespace}; shift ;;
    --cluster) delete_cluster=1 ;;
    -y | --yes) assume_yes=1 ;;
    -d | --dry-run) export LAB_DRY_RUN=1 ;;
    -?*) die "unknown option: $1 (try --help)" ;;
    *) target=$1 ;;
  esac
  shift
done

# Ask before deleting, unless the caller already said yes.
confirm() {
  local question=$1 answer
  if [[ $assume_yes == 1 || $LAB_DRY_RUN == 1 ]]; then
    return 0
  fi
  read -r -p "$question [y/N] " answer </dev/tty || true
  [[ $answer == [yY]* ]]
}

require_cluster

# A scenario means "remove its manifests"; the folder is the source of truth.
if [[ $target != all ]]; then
  scenario_dir "$target" >/dev/null
  k delete -f "$(scenario_dir "$target")" -n "$LAB_NAMESPACE" --ignore-not-found
  log "scenario $target removed"
else
  if confirm "delete namespace $LAB_NAMESPACE and everything in it?"; then
    k delete namespace "$LAB_NAMESPACE" --ignore-not-found
    log "namespace $LAB_NAMESPACE removed"
  else
    log "kept namespace $LAB_NAMESPACE"
  fi
fi

# The cluster is a separate, bigger decision: always ask.
if [[ $delete_cluster == 1 ]]; then
  if ! have minikube; then
    die "minikube not found, cannot delete the cluster"
  fi
  if confirm "delete the minikube cluster (all labs and images inside it)?"; then
    run minikube delete
  else
    log "kept the minikube cluster"
  fi
fi
