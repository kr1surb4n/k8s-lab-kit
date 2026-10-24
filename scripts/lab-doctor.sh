#!/usr/bin/env bash
# Check what this machine can actually run: tools, RAM, disk, ports, GPU,
# and whether a cluster is reachable. Prints a recommended minikube command.
#
# Examples:
#   scripts/lab-doctor.sh
#   scripts/lab-doctor.sh --strict   # non-zero when something blocking is missing
set -Eeuo pipefail
trap 'printf "error: unexpected failure at line %s: %s\n" "$LINENO" "$BASH_COMMAND" >&2' ERR

# shellcheck source=lib/common.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

strict=0
[[ ${1:-} == --strict ]] && strict=1

problems=0
warnings=0

# Print a passing line.
ok() { printf 'ok    %s\n' "$*"; }

# Print a warning that does not block the lab.
warn() {
  printf 'warn  %s\n' "$*"
  warnings=$((warnings + 1))
}

# Print a blocking problem.
fail() {
  printf 'FAIL  %s\n' "$*"
  problems=$((problems + 1))
}

# Check that a tool exists and print its version when it is cheap.
tool() {
  local name=$1 cmd=${2:-}
  if have "$name"; then
    if [[ -n $cmd ]]; then ok "$name ($(eval "$cmd" 2>/dev/null | head -n1 || true))"; else ok "$name"; fi
  else
    warn "$name is not installed"
  fi
}

# Print a size in GiB from a value in KiB.
gib() { awk -v k="$1" 'BEGIN { printf "%.1f", k / 1048576 }'; }

printf '== host\n'
ok "$(uname -srm)"

# CPU count is what the scheduler will actually see.
cpus=$(nproc)
ok "$cpus CPUs"

# Memory: total matters for minikube, available matters for running it now.
mem_total_kb=$(awk '/MemTotal/ {print $2}' /proc/meminfo)
mem_avail_kb=$(awk '/MemAvailable/ {print $2}' /proc/meminfo)
ok "memory: $(gib "$mem_total_kb") GiB total, $(gib "$mem_avail_kb") GiB available"

# Disk: the kit, the docker data root and the home folder can be the same.
free_kb=$(df -Pk "$K8S_LAB_ROOT" | awk 'NR==2 {print $4}')
ok "disk free at the kit: $(gib "$free_kb") GiB"

# A minikube docker cluster needs room for the VM image plus app images.
if (( free_kb < 20 * 1048576 )); then
  fail "less than 20 GiB free: minikube + app images will not fit safely"
elif (( free_kb < 40 * 1048576 )); then
  warn "less than 40 GiB free: keep --disk-size small and prune images"
fi

# Available RAM decides which scenarios can run next to a browser.
if (( mem_avail_kb < 4 * 1048576 )); then
  fail "less than 4 GiB RAM available right now: stop other work before minikube"
elif (( mem_avail_kb < 8 * 1048576 )); then
  warn "less than 8 GiB available: use --memory=6144 and run one scenario at a time"
fi

printf '\n== tools\n'
tool docker 'docker --version'
tool kubectl 'kubectl version --client'
tool minikube 'minikube version'
tool helm 'helm version --short'
tool sqlite3 'sqlite3 --version'
tool htpasswd 'htpasswd -h 2>&1 | head -n1'
tool jq 'jq --version'
tool curl 'curl --version'
tool python3 'python3 --version'
tool shellcheck 'shellcheck --version | head -n2'
tool git 'git --version'

printf '\n== container runtime\n'
if have docker && docker info >/dev/null 2>&1; then
  ok "docker daemon answers"
  driver=$(docker info --format '{{.Driver}}' 2>/dev/null)
  cgroup=$(docker info --format '{{.CgroupVersion}}' 2>/dev/null)
  server=$(docker info --format '{{.ServerVersion}}' 2>/dev/null)
  ok "docker $server, storage driver $driver, cgroup v$cgroup"
  # The docker driver of minikube needs a local, reachable daemon.
  ok "running as: $(id -un) (no sudo needed for docker)"
else
  warn "docker daemon not reachable: minikube --driver=docker will fail"
fi

printf '\n== ports\n'
for port in 80 8080 8443; do
  if ss -ltn "( sport = :$port )" 2>/dev/null | grep -q LISTEN; then
    warn "port $port is already in use ($(ss -ltnp "( sport = :$port )" 2>/dev/null | awk 'NR==2 {print $6}'))"
  else
    ok "port $port is free"
  fi
done

printf '\n== accelerator\n'
if have nvidia-smi; then
  gpu=$(nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader 2>/dev/null | head -n1 || true)
  if [[ -n $gpu ]]; then
    ok "GPU: $gpu"
    # 8 GB is enough for local embeddings and a small chat model, not for 70B.
    vram=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2>/dev/null | head -n1 || echo 0)
    if (( vram >= 8000 )); then
      ok "GPU tier: local 7-8B quantised models and embeddings are realistic"
    else
      warn "GPU has ${vram} MiB: keep models small or use the CPU"
    fi
  else
    warn "nvidia-smi present but no GPU answered"
  fi
else
  warn "no nvidia-smi: GPU workloads (local LLM, embeddings) are CPU-only"
fi

printf '\n== cluster\n'
if have kubectl && kubectl cluster-info >/dev/null 2>&1; then
  ok "cluster reachable: $(kubectl config current-context 2>/dev/null)"
  kubectl get nodes -o wide 2>/dev/null | sed 's/^/      /'
else
  warn "no cluster reachable (run: minikube start --driver=docker)"
fi

printf '\n== recommendation\n'
# Size the cluster from what is present, not from a fixed number.
read -r cpus_for_cluster mem_for_cluster_mb disk_for_cluster < <(recommend_sizing "$K8S_LAB_ROOT")
# Keep the GiB value for the tier wording below.
mem_for_cluster=$(( mem_for_cluster_mb / 1024 ))

printf '  minikube start --driver=docker --cpus=%s --memory=%s --disk-size=%sg\n' \
  "$cpus_for_cluster" "$mem_for_cluster_mb" "$disk_for_cluster"

# Say plainly which parts of the kit this machine can host.
if (( problems > 0 )); then
  printf '  tier: BLOCKED, fix the FAIL lines first\n'
elif (( mem_for_cluster < 4 )); then
  printf '  tier: LIGHT, A1-A5 only, one pod at a time\n'
elif (( mem_for_cluster < 6 )); then
  printf '  tier: STANDARD, A1-A6, A7 with care\n'
else
  printf '  tier: FULL, A1-A7 plus a small observability stack\n'
fi

# Heavier tracks from the scope plan need a budget check, not a guess.
printf '  heavier tracks: one at a time; a full kube-prometheus-stack needs ~2 GiB\n'
printf '  local AI: use the GPU outside the cluster, not inside a pod\n'

printf '\n'
if (( problems > 0 )); then
  printf '%s blocking problem(s), %s warning(s)\n' "$problems" "$warnings"
  (( strict == 1 )) && exit 1
  exit 0
fi
printf 'no blocking problems, %s warning(s)\n' "$warnings"
