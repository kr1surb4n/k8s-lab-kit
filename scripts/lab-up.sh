#!/usr/bin/env bash
# Bring one lab scenario up on the cluster and wait until it is ready.
#
# Examples:
#   scripts/lab-up.sh a1 --mount
#   scripts/lab-up.sh a6
#   scripts/lab-up.sh a7 --build --mount
#   scripts/lab-up.sh a2 --dry-run
set -Eeuo pipefail
trap 'printf "error: unexpected failure at line %s: %s\n" "$LINENO" "$BASH_COMMAND" >&2' ERR

# shellcheck source=lib/common.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

# Print the help text.
usage() {
  cat <<EOF
Usage: $(basename "${BASH_SOURCE[0]}") [scenario] [options]

Bring a lab scenario up: create the namespace, apply the manifests, wait.

Scenarios:
  a1  nginx serving the host folder site/ (needs --mount)
  a2  nginx serving a ConfigMap
  a3  environment variables and an init container
  a5  nginx basic auth with a Secret
  a6  three replicas behind a LoadBalancer (default)
  a7  nginx + php-fpm + postgres + sqlite (needs --mount, --build)

Options:
  -n, --namespace NS   namespace to use (default: $LAB_NAMESPACE)
  -s, --start-cluster  run minikube start first
  -m, --mount          start 'minikube mount' in the background
      --build          build the A7 PHP image (docker build)
      --no-wait        do not wait for the rollout
      --no-preflight   skip the RAM/disk warning
  -d, --dry-run        print the commands, change nothing
  -h, --help           print this help

EOF
}

scenario=a6
start_cluster=0
start_mount_flag=0
build=0
wait_flag=1
preflight=1

# Read the command line.
while [[ $# -gt 0 ]]; do
  case "$1" in
    -h | --help) usage; exit 0 ;;
    -n | --namespace) LAB_NAMESPACE=${2:?missing namespace}; shift ;;
    -s | --start-cluster) start_cluster=1 ;;
    -m | --mount) start_mount_flag=1 ;;
    --build) build=1 ;;
    --no-wait) wait_flag=0 ;;
    --no-preflight) preflight=0 ;;
    -d | --dry-run) export LAB_DRY_RUN=1 ;;
    -?*) die "unknown option: $1 (try --help)" ;;
    *) scenario=$1 ;;
  esac
  shift
done

# Fail early on a scenario that does not exist here.
scenario_dir "$scenario" >/dev/null

if [[ $start_cluster == 1 ]]; then
  if ! have minikube; then
    die "minikube not found; install it or use an existing cluster"
  fi
  # Use the same sizing as `make doctor`, not a fixed number.
  read -r cpus mem disk < <(recommend_sizing "$K8S_LAB_ROOT")
  run minikube start --driver=docker --cpus="$cpus" --memory="$mem" --disk-size="${disk}g"
fi

require_cluster

# Warn when the machine is too tight, but let the user decide.
if [[ $preflight == 1 && $LAB_DRY_RUN == 0 ]]; then
  preflight_resources
fi

# A1 and A7 read files from the host, so the mount has to exist.
if scenario_needs_host "$scenario"; then
  if [[ $start_mount_flag == 1 ]]; then
    start_mount
  else
    warn "scenario $scenario reads $LAB_MOUNT; start the mount with --mount"
    warn "without it the pod stays in ContainerCreating (hostPath does not exist)"
  fi
fi

# The A7 PHP image is not on Docker Hub, so it must be built once.
if [[ $scenario == a7 && $build == 1 ]]; then
  run docker build -t k8s-lab/php:8.3 "$K8S_LAB_ROOT/manifests/a7/php"
fi

ensure_namespace

# One apply per scenario folder keeps the order obvious.
k apply -f "$(scenario_dir "$scenario")" -n "$LAB_NAMESPACE"

if [[ $wait_flag == 1 ]]; then
  wait_available 180 || die "scenario $scenario did not become ready; run scripts/lab-status.sh $scenario"
fi

log ""
log "scenario $scenario is up in namespace $LAB_NAMESPACE"
print_access 8080
