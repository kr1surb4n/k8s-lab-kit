#!/usr/bin/env bash
# Offline test suite for the kit. No cluster, no network, no root.
#
# It runs the scripts against the fake kubectl and checks their output and exit
# codes, then runs the artifact checks (syntax, YAML).
#
#   tests/run.sh
#   tests/run.sh --filter scale
set -Eeuo pipefail

kit=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)
filter=${TEST_FILTER:-}

# Parse --filter NAME.
while [[ $# -gt 0 ]]; do
  case "$1" in
    --filter) filter=${2:?missing filter}; shift ;;
    -h | --help) printf 'Usage: %s [--filter NAME]\n' "$(basename "$0")"; exit 0 ;;
    *) printf 'unknown argument: %s\n' "$1" >&2; exit 2 ;;
  esac
  shift
done

pass=0
fail=0
skip=0

# Print a passing test.
ok() { printf 'ok   %s\n' "$1"; pass=$((pass + 1)); }

# Print a failing test and the reason.
bad() {
  printf 'FAIL %s\n' "$1"
  [[ -n ${2:-} ]] && printf '     %s\n' "$2"
  fail=$((fail + 1))
}

# Skip a test that this machine cannot run.
skip_test() { printf 'skip %s (%s)\n' "$1" "$2"; skip=$((skip + 1)); }

# Run one test unless the filter says otherwise.
wanted() {
  [[ -z $filter ]] && return 0
  [[ $1 == *"$filter"* ]]
}

# Run a command with the fake kubectl and a throwaway state file.
fake() {
  PATH="$kit/scripts/demo:$PATH" \
    FAKE_KUBECTL_STATE="$state" \
    FAKE_KUBECTL_LOG="$state.log" \
    "$@"
}

state=$(mktemp "${TMPDIR:-/tmp}/k8s-lab-test.XXXXXX")
trap 'rm -f "$state" "$state.log"' EXIT

# Every script must exist and be executable.
test_scripts_present() {
  local s
  for s in lab-up lab-down lab-status lab-scale lab-rollout lab-tunnel lab-verify lab-doctor env-demo mkpasswd cluster-create cluster-delete; do
    if [[ -x $kit/scripts/$s.sh ]]; then ok "scripts/$s.sh is executable"; else bad "scripts/$s.sh is not executable"; fi
  done
}

# Every script must survive bash -n.
test_syntax() {
  if bash -n "$kit"/scripts/*.sh "$kit"/scripts/lib/common.sh "$kit"/scripts/demo/kubectl 2>/dev/null; then
    ok "bash -n on every script"
  else
    bad "bash -n on every script"
  fi
}

# Every manifest, values file and cluster config must be valid YAML.
test_yaml() {
  if python3 -c '
import glob, sys, yaml
patterns = ("manifests/**/*.yaml", "observability/**/*.yaml", "observability/**/*.yml",
            "clusters/**/*.yaml", "bastion/**/*.yaml")
try:
    files = [f for p in patterns for f in glob.glob(sys.argv[1] + "/" + p, recursive=True)]
    docs = [d for f in files for d in yaml.safe_load_all(open(f)) if d]
except Exception as exc:
    print(exc, file=sys.stderr)
    sys.exit(1)
sys.exit(0 if docs else 1)
' "$kit"; then
    ok "manifests and values parse as YAML"
  else
    bad "manifests and values parse as YAML"
  fi
}

# The fake kubectl must answer the calls the scripts make.
test_fake_kubectl() {
  local out
  out=$(PATH="$kit/scripts/demo:$PATH" kubectl cluster-info 2>&1)
  [[ $out == *"control plane"* ]] && ok "fake kubectl answers cluster-info" || bad "fake kubectl cluster-info" "$out"
}

# lab-up must apply the scenario and print the access hints.
test_up() {
  local out
  out=$(fake "$kit/scripts/lab-up.sh" a6 2>&1) || { bad "lab-up a6" "$out"; return; }
  [[ $out == *"applied"* ]] && ok "lab-up applies manifests" || bad "lab-up apply" "$out"
  [[ $out == *"LAN:"* ]] && ok "lab-up prints the LAN hint" || bad "lab-up LAN hint" "$out"
}

# lab-status must show the pods and the LoadBalancer.
test_status() {
  local out
  out=$(fake "$kit/scripts/lab-status.sh" a6 2>&1) || { bad "lab-status a6" "$out"; return; }
  [[ $out == *"Running"* ]] && ok "lab-status shows running pods" || bad "lab-status pods" "$out"
  [[ $out == *"LoadBalancer"* ]] && ok "lab-status shows the service type" || bad "lab-status service" "$out"
}

# lab-scale must add one replica and report it.
test_scale() {
  fake "$kit/scripts/lab-up.sh" a6 >/dev/null 2>&1
  local out
  out=$(fake "$kit/scripts/lab-scale.sh" --delta 1 2>&1) || { bad "lab-scale +1" "$out"; return; }
  [[ $out == *"3 -> 4"* ]] && ok "lab-scale adds one replica" || bad "lab-scale arithmetic" "$out"
  [[ $out == *"4/4"* ]] && ok "lab-scale reports ready replicas" || bad "lab-scale readiness" "$out"
}

# lab-scale must refuse to go below zero.
test_scale_floor() {
  fake "$kit/scripts/lab-up.sh" a6 >/dev/null 2>&1
  if fake "$kit/scripts/lab-scale.sh" --to -1 >/dev/null 2>&1; then
    bad "lab-scale accepts a negative count"
  else
    ok "lab-scale refuses a negative count"
  fi
}

# lab-verify must pass on a healthy fake cluster.
test_verify_ok() {
  fake "$kit/scripts/lab-up.sh" a6 >/dev/null 2>&1
  local out
  out=$(fake "$kit/scripts/lab-verify.sh" a6 2>&1)
  [[ $out == *"all checks passed"* ]] && ok "lab-verify passes a healthy lab" || bad "lab-verify healthy" "$out"
}

# lab-verify must fail when the object is missing.
test_verify_missing() {
  rm -f "$state"
  local out
  out=$(fake "$kit/scripts/lab-verify.sh" a5 2>&1) || true
  [[ $out == *"FAIL"* ]] && ok "lab-verify fails on a missing lab" || bad "lab-verify missing" "$out"
}

# lab-verify must fail when endpoints are empty.
test_verify_endpoints() {
  fake "$kit/scripts/lab-up.sh" a6 >/dev/null 2>&1
  # Point at a service that does not exist.
  local out
  out=$(LAB_APP=nothing fake "$kit/scripts/lab-verify.sh" a6 2>&1) || true
  [[ $out == *"missing"* || $out == *"FAIL"* ]] && ok "lab-verify detects a missing deployment" || bad "lab-verify missing deployment" "$out"
}

# lab-down must delete the namespace only when asked.
test_down() {
  local out
  out=$(fake "$kit/scripts/lab-down.sh" a6 2>&1) || { bad "lab-down a6" "$out"; return; }
  [[ $out == *"scenario a6 removed"* ]] && ok "lab-down removes a scenario" || bad "lab-down scenario" "$out"
  out=$(fake "$kit/scripts/lab-down.sh" all --yes 2>&1) || { bad "lab-down all" "$out"; return; }
  [[ $out == *"namespace k8s-lab removed"* ]] && ok "lab-down all removes the namespace" || bad "lab-down namespace" "$out"
}

# The doctor must run without a cluster and print a recommendation.
test_doctor() {
  local out
  out=$("$kit/scripts/lab-doctor.sh" 2>&1) || true
  [[ $out == *"minikube start"* ]] && ok "lab-doctor prints a recommendation" || bad "lab-doctor recommendation" "$out"
  [[ $out == *"tier:"* ]] && ok "lab-doctor prints a tier" || bad "lab-doctor tier" "$out"
}


# mkpasswd must print a line nginx can use, with or without htpasswd.
test_mkpasswd() {
  local out
  out=$("$kit/scripts/mkpasswd.sh" lab labpass 2>&1)
  [[ $out == 'lab:$apr1$'* ]] && ok "mkpasswd prints an apr1 line" || bad "mkpasswd output" "$out"
}

# cluster-create must size the cluster and only print in dry-run.
test_cluster_dryrun() {
  local out
  out=$("$kit/scripts/cluster-create.sh" --dry-run 2>&1)
  [[ $out == *"minikube start"* && $out == *"--cpus="* ]] && ok "cluster-create sizes minikube" || bad "cluster-create dry-run" "$out"
  [[ $out == *"tier"* || $out == *"cluster minikube is up"* ]] && ok "cluster-create reports the result" || bad "cluster-create report" "$out"
}

# The observability installer must be previewable without a cluster.
test_observability_dryrun() {
  local out
  out=$("$kit/observability/install.sh" --dry-run 2>&1) || true
  [[ $out == *"kube-prometheus-stack"* ]] && ok "observability plan includes Prometheus" || bad "observability plan" "$out"
  [[ $out == *"storage class"* ]] && ok "observability picks a StorageClass" || bad "observability storage" "$out"
}

# The bastion setup must be safe to preview as a normal user.
test_bastion_dryrun() {
  local out
  out=$("$kit/bastion/host/setup.sh" --dry-run 2>&1) || true
  [[ $out == *"sshd_config.d"* ]] && ok "bastion setup shows the sshd drop-in" || bad "bastion drop-in" "$out"
  [[ $out == *"ufw"* ]] && ok "bastion setup shows the firewall step" || bad "bastion firewall" "$out"
}

# Run a test when the filter matches.
run() {
  local name=$1
  if wanted "$name"; then "$name"; else skip_test "$name" "filtered out"; fi
}

test_scripts_present
run test_syntax
run test_yaml
run test_fake_kubectl
run test_up
run test_status
run test_scale
run test_scale_floor
run test_verify_ok
run test_verify_missing
run test_verify_endpoints
run test_down
run test_doctor
run test_mkpasswd
run test_cluster_dryrun
run test_observability_dryrun
run test_bastion_dryrun

printf '\n%s passed, %s failed, %s skipped\n' "$pass" "$fail" "$skip"
(( fail == 0 ))
