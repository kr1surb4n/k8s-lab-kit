#!/usr/bin/env bash
# Show what the lab looks like right now: pods, deployment, service, endpoints,
# storage, and the latest events. Read-only.
#
# Examples:
#   scripts/lab-status.sh
#   scripts/lab-status.sh a7
#   scripts/lab-status.sh a6 --namespace demo
set -Eeuo pipefail
trap 'printf "error: unexpected failure at line %s: %s\n" "$LINENO" "$BASH_COMMAND" >&2' ERR

# shellcheck source=lib/common.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

# Print the help text.
usage() {
  cat <<EOF
Usage: $(basename "${BASH_SOURCE[0]}") [scenario] [options]

Print the state of the lab. Never changes anything.

Options:
  -n, --namespace NS   namespace to use (default: $LAB_NAMESPACE)
  -d, --dry-run        print the commands instead of running them
  -h, --help           print this help

EOF
}

scenario=${1:-a6}
[[ $scenario == -h || $scenario == --help ]] && { usage; exit 0; }
[[ $scenario == -* ]] && scenario=a6

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h | --help) usage; exit 0 ;;
    -n | --namespace) LAB_NAMESPACE=${2:?missing namespace}; shift ;;
    -d | --dry-run) export LAB_DRY_RUN=1 ;;
    -?*) die "unknown option: $1 (try --help)" ;;
    *) scenario=$1 ;;
  esac
  shift
done

require_cluster

# Print a section title, then run the kubectl command under it.
section() {
  local title=$1
  shift
  log ""
  log "== $title"
  k "$@" || true
}

section "pods" get pods -n "$LAB_NAMESPACE" -o wide
section "deployment" get deployment -n "$LAB_NAMESPACE" -o wide
section "replicas" rollout status "deployment/$LAB_APP" -n "$LAB_NAMESPACE"
section "service" get service -n "$LAB_NAMESPACE" -o wide
section "endpoints" get endpoints -n "$LAB_NAMESPACE"
section "ingress" get ingress -n "$LAB_NAMESPACE"
section "storage" get pvc -n "$LAB_NAMESPACE"
section "config" get configmap -n "$LAB_NAMESPACE"
section "secrets" get secret -n "$LAB_NAMESPACE"

# Events explain most of the failures that the tables only hint at.
log ""
log "== recent events"
k get events -n "$LAB_NAMESPACE" --sort-by=.lastTimestamp 2>/dev/null | tail -n 15 || true

# Point at the next step instead of leaving the reader with raw output.
log ""
log "next: scripts/lab-tunnel.sh $scenario --background   # then open the LAN URL"
