#!/usr/bin/env bash
# Inject or recover a failure scenario for the T1 troubleshooting drills.
#
# Each drill models a real failure mode from the runbook. Run with --inject to
# break the lab, verify the failure state, then run with --recover to fix it.
#
# Examples:
#   scripts/lab-drill.sh crashloop --inject
#   scripts/lab-drill.sh crashloop --recover
#   scripts/lab-drill.sh all --inject
#   scripts/lab-drill.sh all --recover
set -Eeuo pipefail
trap 'printf "error: unexpected failure at line %s: %s\n" "$LINENO" "$BASH_COMMAND" >&2' ERR

# shellcheck source=lib/common.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

drill=""
action=""

usage() {
  cat <<EOF
Usage: $(basename "${BASH_SOURCE[0]}") <drill> <--inject|--recover>

Drills (matching runbooks.md §T1):
  crashloop   CrashLoopBackOff via bad env var
  imagepull   ImagePullBackOff via nonexistent image tag
  pending     Pending (unschedulable) via impossible resource request
  oom         OOMKilled via 1 MiB memory limit
  all         run all four in sequence

Options:
  --inject    break the lab (apply the failure)
  --recover   fix the lab (rollout undo to known-good)
  -n, --namespace NS  namespace (default: $LAB_NAMESPACE)
  -h, --help  print this help

Examples:
  scripts/lab-drill.sh crashloop --inject
  scripts/lab-drill.sh crashloop --recover
  scripts/lab-drill.sh all --inject
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h | --help) usage; exit 0 ;;
    -n | --namespace) LAB_NAMESPACE=${2:?missing namespace}; shift ;;
    --inject) action=inject ;;
    --recover) action=recover ;;
    crashloop | imagepull | pending | oom | all) drill=$1 ;;
    *) die "unknown argument: $1 (try --help)" ;;
  esac
  shift
done

[[ -n $drill ]] || { usage >&2; exit 2; }
[[ -n $action ]] || { usage >&2; exit 2; }

require_cluster

run_drill() {
  local name=$1 inject_cmd=$2 recover_cmd=$3
  log "=== $name : $action ==="
  if [[ $action == inject ]]; then
    run $inject_cmd
    log "Injected. Verify with: kubectl get pods -n $LAB_NAMESPACE"
  else
    run $recover_cmd
    log "Recovered. Waiting for rollout..."
    run "$LAB_KUBECTL" rollout status deploy/web -n "$LAB_NAMESPACE" --timeout=120s
    log "Verifying with lab-verify.sh..."
    run scripts/lab-verify.sh a6
  fi
}

case "$drill" in
  crashloop)
    patch_file=$(mktemp)
    cat >"$patch_file" <<'EOF'
[{"op":"replace","path":"/spec/template/spec/containers/0/command","value":["/bin/sh","-c","exit 1"]}]
EOF
    run_drill "CrashLoopBackOff" \
      "$LAB_KUBECTL patch deploy web -n $LAB_NAMESPACE --type=json --patch-file=$patch_file" \
      "$LAB_KUBECTL rollout undo deploy/web -n $LAB_NAMESPACE"
    rm -f "$patch_file"
    ;;
  imagepull)
    run_drill "ImagePullBackOff" \
      "$LAB_KUBECTL set image deploy/web web=nginx:does-not-exist -n $LAB_NAMESPACE" \
      "$LAB_KUBECTL set image deploy/web web=nginx:1.27-alpine -n $LAB_NAMESPACE"
    ;;
  pending)
    patch_file=$(mktemp)
    cat >"$patch_file" <<'EOF'
[{"op":"replace","path":"/spec/template/spec/containers/0/resources","value":{"requests":{"cpu":"100","memory":"20Gi"},"limits":{"cpu":"100","memory":"20Gi"}}}]
EOF
    run_drill "Pending (unschedulable)" \
      "$LAB_KUBECTL patch deploy web -n $LAB_NAMESPACE --type=json --patch-file=$patch_file" \
      "$LAB_KUBECTL rollout undo deploy/web -n $LAB_NAMESPACE"
    rm -f "$patch_file"
    ;;
  oom)
    patch_file=$(mktemp)
    cat >"$patch_file" <<'EOF'
[{"op":"replace","path":"/spec/template/spec/containers/0/resources","value":{"requests":{"cpu":"10m","memory":"1Mi"},"limits":{"cpu":"10m","memory":"1Mi"}}}]
EOF
    run_drill "OOMKilled" \
      "$LAB_KUBECTL patch deploy web -n $LAB_NAMESPACE --type=json --patch-file=$patch_file" \
      "$LAB_KUBECTL rollout undo deploy/web -n $LAB_NAMESPACE"
    rm -f "$patch_file"
    ;;
  all)
    for d in crashloop imagepull pending oom; do
      "$0" "$d" --"$action"
      [[ $action == inject ]] && sleep 10
    done
    ;;
esac

log "Drill $drill $action done."