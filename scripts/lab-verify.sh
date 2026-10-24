#!/usr/bin/env bash
# Check a scenario against its definition of done. Exit 0 only when every
# check passes, so it can be used as a lab "test".
#
# Examples:
#   scripts/lab-verify.sh a6
#   scripts/lab-verify.sh a5 --url http://127.0.0.1:8080 --expect 401
#   scripts/lab-verify.sh a7 --no-http
set -Eeuo pipefail
trap 'printf "error: unexpected failure at line %s: %s\n" "$LINENO" "$BASH_COMMAND" >&2' ERR

# shellcheck source=lib/common.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

# Print the help text.
usage() {
  cat <<EOF
Usage: $(basename "${BASH_SOURCE[0]}") [scenario] [options]

Checks the objects that the scenario promises exist and are ready, and
optionally fetches a URL.

Options:
      --url URL        also fetch this URL
      --expect CODE    expected HTTP status (default: 200)
  -n, --namespace NS   namespace to use (default: $LAB_NAMESPACE)
  -d, --dry-run        print the checks, run none
  -h, --help           print this help

EOF
}

scenario=${1:-a6}
[[ $scenario == -h || $scenario == --help ]] && { usage; exit 0; }

url=""
expect=200

# Read the command line.
while [[ $# -gt 0 ]]; do
  case "$1" in
    -h | --help) usage; exit 0 ;;
    --url) url=${2:?missing url}; shift ;;
    --expect) expect=${2:?missing code}; shift ;;
    -n | --namespace) LAB_NAMESPACE=${2:?missing namespace}; shift ;;
    -d | --dry-run) export LAB_DRY_RUN=1 ;;
    -?*) die "unknown option: $1 (try --help)" ;;
    *) scenario=$1 ;;
  esac
  shift
done

scenario_dir "$scenario" >/dev/null
require_cluster

# A dry run has no data to check, so describe the plan and stop.
if [[ $LAB_DRY_RUN == 1 ]]; then
  log "dry-run: would check in namespace $LAB_NAMESPACE"
  printf '+ %s get deployment/%s -o jsonpath={.status.readyReplicas}\n' "$LAB_KUBECTL" "$LAB_APP"
  printf '+ %s get endpoints/%s -o jsonpath={.subsets[0].addresses[0].ip}\n' "$LAB_KUBECTL" "$LAB_APP"
  printf '+ %s get deployment/web -o jsonpath={.spec.template.spec.volumes[0].hostPath.path}\n' "$LAB_KUBECTL"
  [[ -n $url ]] && printf '+ curl -s -o /dev/null -w %%{http_code} %s\n' "$url"
  exit 0
fi

failures=0

# Record a passing check.
ok() { printf 'ok   %s\n' "$*"; }

# Record a failing check and keep going, so one run shows every problem.
bad() {
  printf 'FAIL %s\n' "$*"
  failures=$((failures + 1))
}

# Read one value through kubectl without aborting on error.
value() { "$LAB_KUBECTL" "$@" 2>/dev/null || true; }

# Compare an actual value with the expected one.
check_eq() {
  local name=$1 want=$2 got=$3
  if [[ $got == "$want" ]]; then ok "$name = $want"; else bad "$name: want '$want', got '$got'"; fi
}

# Check that a named object exists in the namespace.
check_exists() {
  local kind=$1 name=$2
  if value get "$kind" "$name" -n "$LAB_NAMESPACE" >/dev/null && \
     [[ -n $(value get "$kind" "$name" -n "$LAB_NAMESPACE" -o jsonpath='{.metadata.name}') ]]; then
    ok "$kind/$name exists"
  else
    bad "$kind/$name is missing"
  fi
}

log "verifying scenario $scenario in namespace $LAB_NAMESPACE"
log ""

# Every scenario must have a deployment that is fully ready.
desired=$(value get deployment "$LAB_APP" -n "$LAB_NAMESPACE" -o jsonpath='{.spec.replicas}')
ready=$(value get deployment "$LAB_APP" -n "$LAB_NAMESPACE" -o jsonpath='{.status.readyReplicas}')

if [[ -n $desired && $desired != 0 ]]; then
  ok "deployment/$LAB_APP exists (desired $desired)"
else
  bad "deployment/$LAB_APP is missing"
fi
check_eq "ready replicas" "$desired" "${ready:-0}"

# The service must have at least one backend, otherwise the selector is wrong.
endpoint=$(value get endpoints "$LAB_APP" -n "$LAB_NAMESPACE" -o jsonpath='{.subsets[0].addresses[0].ip}')
if [[ -n $endpoint ]]; then
  ok "service/$LAB_APP has endpoints ($endpoint)"
else
  bad "service/$LAB_APP has no endpoints (selector or readiness)"
fi

# Per-scenario objects that carry the lesson.
case "$scenario" in
  a1)
    check_eq "hostPath" "$LAB_MOUNT/site" \
      "$(value get deployment "$LAB_APP" -n "$LAB_NAMESPACE" -o jsonpath='{.spec.template.spec.volumes[0].hostPath.path}')"
    ;;
  a2)
    check_exists configmap web-index
    ;;
  a3)
    check_exists configmap web-config
    ;;
  a5)
    check_exists secret web-basic-auth
    check_exists configmap web-auth-config
    ;;
  a6)
    check_eq "service type" "LoadBalancer" \
      "$(value get service "$LAB_APP" -n "$LAB_NAMESPACE" -o jsonpath='{.spec.type}')"
    ;;
  a7)
    check_exists pvc postgres-data
    check_eq "pvc phase" "Bound" \
      "$(value get pvc postgres-data -n "$LAB_NAMESPACE" -o jsonpath='{.status.phase}')"
    check_exists service postgres
    check_eq "postgres ready" "1" \
      "$(value get deployment postgres -n "$LAB_NAMESPACE" -o jsonpath='{.status.readyReplicas}')"
    ;;
esac

# Optional HTTP check: the only proof that the whole chain works.
if [[ -n $url ]]; then
  if [[ $LAB_DRY_RUN == 1 ]]; then
    printf '+ curl -s -o /dev/null -w %%{http_code} %s\n' "$url"
  else
    code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "$url" || true)
    check_eq "HTTP $url" "$expect" "$code"
  fi
fi

log ""
if (( failures == 0 )); then
  log "all checks passed"
  exit 0
fi
log "$failures check(s) failed"
exit 1
