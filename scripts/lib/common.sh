# shellcheck shell=bash
# Shared helpers for the k8s lab scripts. Source this file, never run it.
#
#   source "$(dirname "$0")/lib/common.sh"
#
# Every helper prints what it is about to do, so a transcript is readable.

# Kit root, resolved from this file: scripts/lib/../..
K8S_LAB_ROOT=${K8S_LAB_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)}

# Defaults; command-line flags override them.
LAB_NAMESPACE=${LAB_NAMESPACE:-k8s-lab}
LAB_APP=${LAB_APP:-web}
LAB_KUBECTL=${LAB_KUBECTL:-kubectl}
LAB_DRY_RUN=${LAB_DRY_RUN:-0}
# Where the host folder appears inside the minikube node.
LAB_MOUNT=${LAB_MOUNT:-/mnt/lab}
# Scenarios that read files from the host.
LAB_HOST_SCENARIOS=${LAB_HOST_SCENARIOS:-"a1 a7"}

# Print a normal message to stderr, keeping stdout clean for data.
log() { printf '%s\n' "$*" >&2; }

# Print a warning.
warn() { printf 'warning: %s\n' "$*" >&2; }

# Print an error and stop.
die() {
  printf 'error: %s\n' "$*" >&2
  exit "${2:-1}"
}

# Fail loudly on any uncaught error, with the line that caused it.
lab_set_error_trap() {
  trap 'printf "error: unexpected failure at line %s: %s\n" "$LINENO" "$BASH_COMMAND" >&2' ERR
}

# True when a command exists.
have() { command -v "$1" >/dev/null 2>&1; }

# Print a command and run it, or only print it in dry-run mode.
run() {
  if [[ $LAB_DRY_RUN == 1 ]]; then
    printf '+ %s\n' "$*"
    return 0
  fi
  printf '+ %s\n' "$*" >&2
  "$@"
}

# Run kubectl through run(), so --dry-run covers it too.
k() { run "$LAB_KUBECTL" "$@"; }

# Refuse to continue without the client and a reachable cluster.
require_cluster() {
  if [[ $LAB_DRY_RUN == 1 ]]; then
    have "$LAB_KUBECTL" || log "dry-run: $LAB_KUBECTL not installed, printing commands only"
    log "dry-run: skipping the cluster check"
    return 0
  fi
  have "$LAB_KUBECTL" || die "kubectl not found; install it or set LAB_KUBECTL"
  # cluster-info is the cheapest call that proves the API server answers.
  if ! "$LAB_KUBECTL" cluster-info >/dev/null 2>&1; then
    die "no cluster reachable; run: minikube start --driver=docker"
  fi
}

# Return the manifest folder for a scenario, or fail if it is unknown.
scenario_dir() {
  local scenario=$1
  local dir="$K8S_LAB_ROOT/manifests/$scenario"
  [[ -d $dir ]] || die "unknown scenario '$scenario' (looked in $dir)"
  printf '%s\n' "$dir"
}

# True when a scenario has manifests here.
scenario_exists() { [[ -d "$K8S_LAB_ROOT/manifests/$1" ]]; }

# True when the scenario needs the host folder mounted into the node.
scenario_needs_host() {
  local s
  for s in $LAB_HOST_SCENARIOS; do
    [[ $s == "$1" ]] && return 0
  done
  return 1
}

# Create the lab namespace unless it is already there.
ensure_namespace() {
  if [[ $LAB_DRY_RUN == 1 ]]; then
    log "dry-run: would ensure namespace $LAB_NAMESPACE"
    return 0
  fi
  if "$LAB_KUBECTL" get namespace "$LAB_NAMESPACE" >/dev/null 2>&1; then
    log "namespace $LAB_NAMESPACE already exists"
    return 0
  fi
  k create namespace "$LAB_NAMESPACE"
}

# Print the number of desired replicas for the app, 0 when unknown.
desired_replicas() {
  "$LAB_KUBECTL" get deployment "$LAB_APP" -n "$LAB_NAMESPACE" \
    -o jsonpath='{.spec.replicas}' 2>/dev/null || printf '0'
}

# Print the number of ready replicas for the app, 0 when unknown.
ready_replicas() {
  "$LAB_KUBECTL" get deployment "$LAB_APP" -n "$LAB_NAMESPACE" \
    -o jsonpath='{.status.readyReplicas}' 2>/dev/null || printf '0'
}

# Block until the deployment reports success, or explain what to inspect.
wait_available() {
  local timeout=${1:-180}
  if [[ $LAB_DRY_RUN == 1 ]]; then
    log "dry-run: would wait for deployment/$LAB_APP"
    return 0
  fi
  if ! "$LAB_KUBECTL" rollout status "deployment/$LAB_APP" -n "$LAB_NAMESPACE" --timeout="${timeout}s"; then
    warn "deployment did not become ready; try: scripts/lab-status.sh"
    return 1
  fi
}

# Print the first non-loopback IPv4 address, used to build a LAN URL.
lan_ip() {
  hostname -I 2>/dev/null | awk '{print $1}'
}

# Warn when this machine is too tight for a scenario, without blocking it.
preflight_resources() {
  local mem_avail_kb free_kb
  mem_avail_kb=$(awk '/MemAvailable/ {print $2}' /proc/meminfo 2>/dev/null || echo 0)
  free_kb=$(df -Pk "$K8S_LAB_ROOT" 2>/dev/null | awk 'NR==2 {print $4}')
  if [[ -n $free_kb ]] && (( free_kb < 20 * 1048576 )); then
    warn "less than 20 GiB free: pull fewer images and prune before the next stack"
  fi
  if (( mem_avail_kb > 0 && mem_avail_kb < 3 * 1048576 )); then
    warn "less than 3 GiB RAM available: close something before starting pods"
  fi
}

# Print "CPUS MEMORY_MB DISK_GB" sized to the RAM and disk this machine has now.
recommend_sizing() {
  local path=${1:-$K8S_LAB_ROOT}
  local mem_avail_kb free_kb cpus mem disk
  mem_avail_kb=$(awk '/MemAvailable/ {print $2}' /proc/meminfo 2>/dev/null || echo 0)
  free_kb=$(df -Pk "$path" 2>/dev/null | awk 'NR==2 {print $4}')
  cpus=$(nproc)
  # 6 GiB is enough for A1-A6 and a small observability stack.
  if (( mem_avail_kb >= 10 * 1048576 )); then
    mem=6
  elif (( mem_avail_kb >= 7 * 1048576 )); then
    mem=4
  elif (( mem_avail_kb >= 5 * 1048576 )); then
    mem=3
  else
    mem=2
  fi
  cpus=$(( cpus / 4 ))
  (( cpus > 6 )) && cpus=6
  (( cpus < 2 )) && cpus=2
  disk=15
  (( free_kb > 120 * 1048576 )) && disk=20
  printf '%s %s %s\n' "$cpus" "$(( mem * 1024 ))" "$disk"
}

# Print the URLs a human can try, depending on the service type.
print_access() {
  local port=${1:-8080}
  log ""
  log "try it:"
  log "  host:    http://127.0.0.1:$port"
  log "  LAN:     http://$(lan_ip):$port  (run scripts/lab-tunnel.sh)"
  log "  in pod:  $LAB_KUBECTL exec deploy/$LAB_APP -n $LAB_NAMESPACE -- curl -s localhost"
}

# Start `minikube mount` in the background for the host-file scenarios.
# The mount must stay alive, so it is detached and its pid is recorded.
start_mount() {
  local log_file=${TMPDIR:-/tmp}/k8s-lab-mount.log
  local pid_file=${TMPDIR:-/tmp}/k8s-lab-mount.pid
  if [[ -f $pid_file ]] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
    log "mount already running (pid $(cat "$pid_file"))"
    return 0
  fi
  if [[ $LAB_DRY_RUN == 1 ]]; then
    printf '+ minikube mount %s:%s > %s 2>&1 &\n' "$K8S_LAB_ROOT" "$LAB_MOUNT" "$log_file"
    return 0
  fi
  # 9p mount: host folder on the left, path inside the node on the right.
  nohup minikube mount "$K8S_LAB_ROOT:$LAB_MOUNT" >"$log_file" 2>&1 &
  echo $! >"$pid_file"
  log "mount started (pid $!, log $log_file)"
}
