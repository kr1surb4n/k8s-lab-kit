#!/usr/bin/env bash
# Expose the lab app, including to another machine on the LAN (exercise A4).
#
# The default is a port-forward bound to 0.0.0.0: the only mechanism that works
# the same on minikube, k3d and a bare cluster. `minikube tunnel` and
# `minikube service --url` are kept for comparison; both are host-only.
#
# Examples:
#   scripts/lab-tunnel.sh              # foreground, 0.0.0.0:8080
#   scripts/lab-tunnel.sh --background
#   scripts/lab-tunnel.sh --mode url   # what minikube suggests
#   scripts/lab-tunnel.sh --mode minikube-tunnel
set -Eeuo pipefail
trap 'printf "error: unexpected failure at line %s: %s\n" "$LINENO" "$BASH_COMMAND" >&2' ERR

# shellcheck source=lib/common.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

# Print the help text.
usage() {
  cat <<EOF
Usage: $(basename "${BASH_SOURCE[0]}") [options]

Expose deployment/$LAB_APP on port 8080 and print the LAN URL.

Options:
      --port N           local port (default: 8080)
      --address ADDR     bind address for port-forward (default: 0.0.0.0)
      --target TARGET    kubectl port-forward target (default: svc/$LAB_APP)
      --mode MODE        port-forward (default), url, minikube-tunnel
  -b, --background       detach the forward and record its pid
  -n, --namespace NS     namespace to use (default: $LAB_NAMESPACE)
  -d, --dry-run          print the commands, change nothing
  -h, --help             print this help

Notes:
  --mode url              runs 'minikube service --url' (binds 127.0.0.1)
  --mode minikube-tunnel  runs 'minikube tunnel' (needs sudo, IP is host-only)

EOF
}

port=8080
address=0.0.0.0
target="svc/$LAB_APP"
mode="port-forward"
background=0

# Read the command line.
while [[ $# -gt 0 ]]; do
  case "$1" in
    -h | --help) usage; exit 0 ;;
    --port) port=${2:?missing port}; shift ;;
    --address) address=${2:?missing address}; shift ;;
    --target) target=${2:?missing target}; shift ;;
    --mode) mode=${2:?missing mode}; shift ;;
    -b | --background) background=1 ;;
    -n | --namespace) LAB_NAMESPACE=${2:?missing namespace}; shift ;;
    -d | --dry-run) export LAB_DRY_RUN=1 ;;
    -?*) die "unknown option: $1 (try --help)" ;;
    *) die "unexpected argument: $1 (try --help)" ;;
  esac
  shift
done

require_cluster

# Print the address the other machine should try.
show_urls() {
  log ""
  log "from this machine: http://127.0.0.1:$port"
  log "from the LAN:      http://$(lan_ip):$port"
  log "if it does not answer from another machine, open the port:"
  log "  sudo ufw allow $port/tcp"
}

case "$mode" in
  port-forward)
    if [[ $background == 1 ]]; then
      pid_file=${TMPDIR:-/tmp}/k8s-lab-forward-$port.pid
      log_file=${TMPDIR:-/tmp}/k8s-lab-forward-$port.log
      if [[ $LAB_DRY_RUN == 1 ]]; then
        printf '+ %s port-forward --address %s %s %s:%s &\n' \
          "$LAB_KUBECTL" "$address" "$target" "$port" 80
        exit 0
      fi
      # Detach, because the forward blocks the terminal.
      nohup "$LAB_KUBECTL" port-forward --address "$address" "$target" "$port:80" \
        -n "$LAB_NAMESPACE" >"$log_file" 2>&1 &
      echo $! >"$pid_file"
      log "forward started (pid $!, log $log_file)"
      show_urls
    else
      log "forwarding $target $port -> 80 (Ctrl+C to stop)"
      show_urls
      run "$LAB_KUBECTL" port-forward --address "$address" "$target" "$port:80" -n "$LAB_NAMESPACE"
    fi
    ;;
  url)
    have minikube || die "minikube not found"
    run minikube service "$LAB_APP" -n "$LAB_NAMESPACE" --url
    warn "that URL is bound to 127.0.0.1; another machine cannot use it"
    ;;
  minikube-tunnel)
    have minikube || die "minikube not found"
    warn "minikube tunnel asks for sudo and assigns a host-only IP"
    run minikube tunnel
    ;;
  *)
    die "unknown mode '$mode' (try --help)"
    ;;
esac
