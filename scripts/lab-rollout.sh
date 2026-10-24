#!/usr/bin/env bash
# Do the A6 "update" part: status, history, a new image, a restart, an undo.
#
# Examples:
#   scripts/lab-rollout.sh status
#   scripts/lab-rollout.sh image nginx:1.28-alpine
#   scripts/lab-rollout.sh history
#   scripts/lab-rollout.sh undo
#   scripts/lab-rollout.sh restart
set -Eeuo pipefail
trap 'printf "error: unexpected failure at line %s: %s\n" "$LINENO" "$BASH_COMMAND" >&2' ERR

# shellcheck source=lib/common.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

# Print the help text.
usage() {
  cat <<EOF
Usage: $(basename "${BASH_SOURCE[0]}") <action> [argument] [options]

Actions:
  status            show whether the rollout finished
  history           list the revisions
  image [IMAGE]     update the container image (default: nginx:1.28-alpine)
  restart           recreate the pods without changing the spec
  undo              roll back to the previous revision

Options:
  -n, --namespace NS   namespace to use (default: $LAB_NAMESPACE)
  -d, --dry-run        print the commands, change nothing
  -h, --help           print this help

EOF
}

action=""
argument=""

# Read the command line: first non-option is the action, the next is its argument.
while [[ $# -gt 0 ]]; do
  case "$1" in
    -h | --help) usage; exit 0 ;;
    -n | --namespace) LAB_NAMESPACE=${2:?missing namespace}; shift ;;
    -d | --dry-run) export LAB_DRY_RUN=1 ;;
    -?*) die "unknown option: $1 (try --help)" ;;
    *)
      if [[ -z $action ]]; then action=$1; else argument=$1; fi
      ;;
  esac
  shift
done

[[ -n $action ]] || die "missing action (try --help)"
require_cluster

# Dispatch on the action; every branch ends with the rollout state printed.
case "$action" in
  status)
    k rollout status "deployment/$LAB_APP" -n "$LAB_NAMESPACE"
    ;;
  history)
    k rollout history "deployment/$LAB_APP" -n "$LAB_NAMESPACE"
    ;;
  image)
    image=${argument:-nginx:1.28-alpine}
    # The container inside the pod has the same name as the deployment here.
    k set image "deployment/$LAB_APP" "$LAB_APP=$image" -n "$LAB_NAMESPACE"
    wait_available 180 || die "update did not become ready; try: scripts/lab-rollout.sh undo"
    log ""
    log "now running: $image"
    k rollout status "deployment/$LAB_APP" -n "$LAB_NAMESPACE"
    ;;
  restart)
    k rollout restart "deployment/$LAB_APP" -n "$LAB_NAMESPACE"
    wait_available 180 || die "restart did not become ready; run scripts/lab-status.sh"
    ;;
  undo)
    k rollout undo "deployment/$LAB_APP" -n "$LAB_NAMESPACE"
    wait_available 180 || die "undo did not become ready; run scripts/lab-status.sh"
    log ""
    k rollout history "deployment/$LAB_APP" -n "$LAB_NAMESPACE"
    ;;
  *)
    die "unknown action '$action' (try --help)"
    ;;
esac
