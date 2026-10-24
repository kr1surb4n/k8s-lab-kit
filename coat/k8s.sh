#!/usr/bin/env bash
# Coat module for the Kubernetes lab kit.
#
# Loaded from ~/.coatrc AFTER coat.sh, because COAT_MODULE_ORDER lives inside
# coat.sh and this module is not part of that list.
#
# It only wraps the scripts in this kit; the logic stays in scripts/.

# Kit root, resolved from this file (installed as a symlink in ~/.coat/modules).
K8S_LAB_KIT=${K8S_LAB_KIT:-$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd -P)}
export K8S_LAB_KIT

# Print the klab help.
klab_help() {
  cat <<'EOF'
klab <command> [args]

  up [scenario]       bring a scenario up (default a6, add --mount for a1/a7)
  down [scenario|all] remove a scenario or the namespace
  status [scenario]   pods, deployment, service, endpoints, events
  scale [--delta N]   scale the app (+1 by default)
  rollout <action>    status|history|image TAG|restart|undo
  tunnel [--port N]   expose on 0.0.0.0 for the LAN
  verify [scenario]   checks, non-zero exit on failure
  doctor              tools, RAM, disk, ports, GPU
  env                 the host-side environment variable demo
  ns [namespace]      show or switch the lab namespace
  url                 LAN URL of the current forward

Scenarios: a1 a2 a3 a5 a6 a7
EOF
}

# Dispatch to the task scripts in the kit.
klab() {
  local cmd=${1:-help}
  shift || true
  local scripts="$K8S_LAB_KIT/scripts"

  case "$cmd" in
    up) "$scripts/lab-up.sh" "$@" ;;
    down) "$scripts/lab-down.sh" "$@" ;;
    status) "$scripts/lab-status.sh" "$@" ;;
    scale) "$scripts/lab-scale.sh" "$@" ;;
    rollout) "$scripts/lab-rollout.sh" "$@" ;;
    tunnel) "$scripts/lab-tunnel.sh" "$@" ;;
    verify) "$scripts/lab-verify.sh" "$@" ;;
    doctor) "$scripts/lab-doctor.sh" "$@" ;;
    env) "$scripts/env-demo.sh" "$@" ;;
    ns)
      # With an argument, switch the namespace for this shell only.
      if [[ -n ${1:-} ]]; then
        export LAB_NAMESPACE=$1
        echo "LAB_NAMESPACE=$LAB_NAMESPACE"
      else
        echo "${LAB_NAMESPACE:-k8s-lab}"
      fi
      ;;
    url) echo "http://$(hostname -I 2>/dev/null | awk '{print $1}'):8080" ;;
    help | -h | --help) klab_help ;;
    *) echo "klab: unknown command '$cmd' (try: klab help)" >&2; return 2 ;;
  esac
}

# Namespace of the current lab.
k8s_ns() { echo "${LAB_NAMESPACE:-k8s-lab}"; }

# Pods with their node and IP.
k8s_pods() { kubectl get pods -n "$(k8s_ns)" -o wide "$@"; }

# Everything in the lab namespace.
k8s_all() { kubectl get all,pvc,configmap,secret -n "$(k8s_ns)" "$@"; }

# Recent events, newest last.
k8s_events() { kubectl get events -n "$(k8s_ns)" --sort-by=.lastTimestamp | tail -20; }

# Logs of the lab app, following by default.
k8s_logs() { kubectl logs -n "$(k8s_ns)" -l app.kubernetes.io/name=web --tail=50 -f "$@"; }

# Shell inside the lab app.
k8s_shell() { kubectl exec -it -n "$(k8s_ns)" deploy/web -- /bin/sh "$@"; }

# Describe the lab pods.
k8s_desc() { kubectl describe pod -n "$(k8s_ns)" -l app.kubernetes.io/name=web "$@"; }

# Show the current context and the lab namespace.
k8s_ctx() {
  echo "context:   $(kubectl config current-context 2>/dev/null)"
  echo "namespace: $(k8s_ns)"
}

# Follow the pods while something changes.
k8s_watch() { watch -n 2 "kubectl get pods -n $(k8s_ns) -o wide"; }

# When curl is not installed inside the app image, use this instead.
k8s_curl() { kubectl run "curl-$RANDOM" --rm -it --restart=Never --image=curlimages/curl -- "$@"; }

# kubectl shortcuts, deliberately short and boring.
alias kgp='kubectl get pods'
alias kgs='kubectl get svc'
alias kgd='kubectl get deploy'
alias kga='kubectl get all'
alias kgn='kubectl get nodes -o wide'
alias kge='kubectl get events --sort-by=.lastTimestamp'
alias kdp='kubectl describe pod'
alias kaf='kubectl apply -f'
alias kdel='kubectl delete'
alias kctx='kubectl config use-context'
alias klab-up='klab up'
alias klab-status='klab status'
