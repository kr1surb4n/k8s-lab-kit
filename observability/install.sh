#!/usr/bin/env bash
# Install observability into the lab cluster, one profile at a time.
#
# Profiles are sized for this machine:
#   minimal  metrics + uptime + Grafana   (~900 MiB)
#   logs     minimal + Loki               (~1.2 GiB)
#   traces   minimal + Tempo + collector  (~1.3 GiB)
#   full     all of the above             (~1.6 GiB)
#
# Examples:
#   observability/install.sh --profile minimal
#   observability/install.sh --profile traces --dry-run
#   observability/install.sh --uninstall
set -Eeuo pipefail
trap 'printf "error: unexpected failure at line %s: %s\n" "$LINENO" "$BASH_COMMAND" >&2' ERR

# shellcheck source=../scripts/lib/common.sh
source "$(dirname "${BASH_SOURCE[0]}")/../scripts/lib/common.sh"

profile=minimal
namespace=observability
uninstall=0
storage_class=""

usage() {
  cat <<EOF
Usage: $(basename "${BASH_SOURCE[0]}") [options]

Options:
  -p, --profile P     minimal | logs | traces | full (default: minimal)
  -n, --namespace NS  namespace (default: $namespace)
      --storage-class C  override the detected StorageClass
      --uninstall     remove the Helm releases and the namespace
  -d, --dry-run       print the commands
  -h, --help          print this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h | --help) usage; exit 0 ;;
    -p | --profile) profile=${2:?missing profile}; shift ;;
    -n | --namespace) namespace=${2:?missing namespace}; shift ;;
    --storage-class) storage_class=${2:?missing class}; shift ;;
    --uninstall) uninstall=1 ;;
    -d | --dry-run) export LAB_DRY_RUN=1 ;;
    *) printf 'unknown argument: %s\n' "$1" >&2; exit 2 ;;
  esac
  shift
done

case "$profile" in
  minimal | logs | traces | full) ;;
  *) printf 'unknown profile: %s\n' "$profile" >&2; exit 2 ;;
esac

have helm || { [[ $LAB_DRY_RUN == 1 ]] || die "helm not found; run setup/install-tools.sh"; }

values="$K8S_LAB_ROOT/observability/values"

# Remove everything this script can have installed.
if [[ $uninstall == 1 ]]; then
  for release in tempo otel-collector loki kube-prometheus-stack blackbox-exporter; do
    run helm uninstall "$release" --namespace "$namespace" --ignore-not-found
  done
  run "$LAB_KUBECTL" delete namespace "$namespace" --ignore-not-found
  exit 0
fi

# Find the StorageClass this cluster actually has.
if [[ -z $storage_class ]]; then
  for class in standard local-path; do
    if "$LAB_KUBECTL" get storageclass "$class" >/dev/null 2>&1; then
      storage_class=$class
      break
    fi
  done
fi
[[ -n $storage_class ]] || {
  if [[ $LAB_DRY_RUN == 1 ]]; then
    storage_class=standard
  else
    die "no standard/local-path StorageClass; pass --storage-class"
  fi
}

log "profile: $profile"
log "namespace: $namespace"
log "storage class: $storage_class"

# Repositories are idempotent; adding one twice is fine.
run helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
run helm repo add grafana https://grafana.github.io/helm-charts
run helm repo add open-telemetry https://open-telemetry.github.io/opentelemetry-helm-charts
run helm repo update

# Metrics, dashboards and the four symptom alerts.
run helm upgrade --install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  --namespace "$namespace" --create-namespace \
  --values "$values/kube-prometheus-stack.yaml" \
  --set "prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.storageClassName=$storage_class"

# Receiver for the Alertmanager test route; same namespace as Alertmanager.
run "$LAB_KUBECTL" apply -k "$K8S_LAB_ROOT/observability/alert-webhook" -n "$namespace"

# Uptime probes for hosts that are not in the cluster.
run helm upgrade --install blackbox-exporter prometheus-community/prometheus-blackbox-exporter \
  --namespace "$namespace" \
  --set "resources.requests.cpu=20m" \
  --set "resources.requests.memory=32Mi" \
  --set "resources.limits.memory=80Mi"

# Logs are optional and installed alone.
if [[ $profile == logs || $profile == full ]]; then
  run helm upgrade --install loki grafana/loki \
    --namespace "$namespace" \
    --values "$values/loki.yaml" \
    --set "singleBinary.persistence.storageClass=$storage_class"
fi

# Traces are optional and installed alone.
if [[ $profile == traces || $profile == full ]]; then
  run helm upgrade --install tempo grafana/tempo \
    --namespace "$namespace" \
    --values "$values/tempo.yaml" \
    --set "persistence.storageClassName=$storage_class"
  run helm upgrade --install otel-collector open-telemetry/opentelemetry-collector \
    --namespace "$namespace" \
    --values "$values/otel-collector.yaml"
fi

# The rules are a CRD object, not a chart value.
if [[ $LAB_DRY_RUN == 0 ]]; then
  run "$LAB_KUBECTL" apply -n "$namespace" -f "$K8S_LAB_ROOT/observability/alerts/lab-rules.yaml"
  run "$LAB_KUBECTL" apply -n "$namespace" -f "$K8S_LAB_ROOT/observability/probes.yaml"
fi

log ""
log "installed. next:"
log "  kubectl get pods -n $namespace"
log "  kubectl port-forward -n $namespace svc/kube-prometheus-stack-grafana 3000:80"
log "  password: kubectl get secret -n $namespace kube-prometheus-stack-grafana -o jsonpath='{.data.admin-password}' | base64 -d; echo"
log "  prometheus: kubectl port-forward -n $namespace svc/kube-prometheus-stack-prometheus 9090:9090"
log "  alertmanager: kubectl port-forward -n $namespace svc/kube-prometheus-stack-alertmanager 9093:9093"
log "  webhook: kubectl port-forward -n $namespace svc/alert-webhook 8080:80"
log "  received alerts: curl -s http://127.0.0.1:8080/alerts | python3 -m json.tool"
