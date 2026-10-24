#!/usr/bin/env bash
# Change the replica count of the lab deployment and wait for the result.
#
# Examples:
#   scripts/lab-scale.sh            # +1 (A6 asks for exactly this)
#   scripts/lab-scale.sh --delta -1 # -1
#   scripts/lab-scale.sh --to 5     # absolute value
set -Eeuo pipefail
trap 'printf "error: unexpected failure at line %s: %s\n" "$LINENO" "$BASH_COMMAND" >&2' ERR

# shellcheck source=lib/common.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

# Print the help text.
usage() {
  cat <<EOF
Usage: $(basename "${BASH_SOURCE[0]}") [options]

Scale deployment/$LAB_APP by one, by a delta, or to an absolute count.

Options:
      --delta N        add N replicas (may be negative; default: +1)
      --to N           set the replica count to N
  -n, --namespace NS   namespace to use (default: $LAB_NAMESPACE)
  -d, --dry-run        print the commands, change nothing
  -h, --help           print this help

EOF
}

delta=1
to=""

# Read the command line.
while [[ $# -gt 0 ]]; do
  case "$1" in
    -h | --help) usage; exit 0 ;;
    --delta) delta=${2:?missing delta}; shift ;;
    --to) to=${2:?missing count}; shift ;;
    -n | --namespace) LAB_NAMESPACE=${2:?missing namespace}; shift ;;
    -d | --dry-run) export LAB_DRY_RUN=1 ;;
    -?*) die "unknown option: $1 (try --help)" ;;
    *) die "unexpected argument: $1 (try --help)" ;;
  esac
  shift
done

require_cluster

current=$(desired_replicas)
[[ -z $current ]] && current=0

# Prefer the absolute value when given, otherwise do the arithmetic.
if [[ -n $to ]]; then
  target=$to
else
  target=$((current + delta))
fi

if (( target < 0 )); then
  die "refusing to scale below zero (current=$current, delta=$delta)"
fi

log "replicas: $current -> $target"
k scale "deployment/$LAB_APP" --replicas="$target" -n "$LAB_NAMESPACE"
wait_available 120 || die "scale did not settle; run scripts/lab-status.sh"

log ""
log "ready replicas: $(ready_replicas)/$target"
