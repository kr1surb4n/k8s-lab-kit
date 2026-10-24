#!/usr/bin/env bash
# Install the CLI tools this lab needs, without root by default.
#
# Debian has kubectl but not minikube or helm, so the supported path here is
# user-space: download the official binaries into ~/.local/bin. The two packages
# that really want apt (sqlite3, apache2-utils) are fetched as .deb files and
# unpacked into the same prefix when sudo is not available.
#
# Examples:
#   setup/install-tools.sh --check          # what is installed, what is missing
#   setup/install-tools.sh                  # core tools into ~/.local/bin
#   setup/install-tools.sh --extras         # core plus k9s, stern, linters
#   setup/install-tools.sh --apt            # also apt-get install sqlite3 apache2-utils
#   setup/install-tools.sh --all --extras   # everything, prompts for sudo once
#   setup/install-tools.sh --dry-run
set -Eeuo pipefail
trap 'printf "error: unexpected failure at line %s: %s\n" "$LINENO" "$BASH_COMMAND" >&2' ERR

BIN=${BIN:-$HOME/.local/bin}
KUBECTL_VERSION=${KUBECTL_VERSION:-stable}
MINIKUBE_VERSION=${MINIKUBE_VERSION:-latest}
HELM_VERSION=${HELM_VERSION:-v3.22.1}
K3D_VERSION=${K3D_VERSION:-latest}
KIND_VERSION=${KIND_VERSION:-latest}
YQ_VERSION=${YQ_VERSION:-latest}
ARCH=${ARCH:-amd64}

mode=user
do_extras=0
dry_run=0
verify=1
apt_packages=(sqlite3 apache2-utils)

# Print the help text.
usage() {
  cat <<EOF
Usage: $(basename "${BASH_SOURCE[0]}") [options]

Install the Kubernetes lab CLI tools into $BIN (no root by default).

Options:
  --user          user-space binaries only (default)
  --apt           also run apt-get for: ${apt_packages[*]}
  --all           --user and --apt
  --extras        also install k9s, stern, kubectx/kubens, kubeconform,
                  kube-linter, popeye, helmfile, argocd
  --check         report versions, change nothing
  --no-verify     skip sha256 checks where a checksum exists
  --dry-run       print what would happen
  -h, --help      print this help

Environment:
  BIN=$BIN
  HELM_VERSION=$HELM_VERSION
  KUBECTL_VERSION=$KUBECTL_VERSION
EOF
}

# Print a step.
log() { printf '==> %s\n' "$*"; }

# Print a warning.
warn() { printf 'warning: %s\n' "$*" >&2; }

# Print an error and stop.
die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

# Read the command line.
while [[ $# -gt 0 ]]; do
  case "$1" in
    -h | --help) usage; exit 0 ;;
    --user) mode=user ;;
    --apt) mode=apt ;;
    --all) mode=all ;;
    --extras) do_extras=1 ;;
    --check) mode=check ;;
    --no-verify) verify=0 ;;
    --dry-run) dry_run=1 ;;
    *) die "unknown option: $1 (try --help)" ;;
  esac
  shift
done

# Run a command, or print it in dry-run mode.
doit() {
  if [[ $dry_run == 1 ]]; then printf '+ %s\n' "$*"; else "$@"; fi
}

# Stop unless the basic download tools exist.
need_tools() {
  local t
  for t in curl tar install; do
    command -v "$t" >/dev/null 2>&1 || die "$t is required"
  done
}

# Report the version of one installed tool.
report_one() {
  local name=$1 version_cmd=$2
  if command -v "$name" >/dev/null 2>&1; then
    printf 'ok    %-10s %s\n' "$name" "$(eval "$version_cmd" 2>&1 | head -n1)"
  else
    printf 'MISS  %-10s\n' "$name"
  fi
}

# Report every tool this script can install.
report() {
  printf '== installed ==\n'
  report_one kubectl 'kubectl version --client -o json 2>/dev/null | jq -r .clientVersion.gitVersion'
  report_one minikube 'minikube version --short'
  report_one helm 'helm version --short'
  report_one k3d 'k3d version | head -n1'
  report_one kind 'kind version'
  report_one yq 'yq --version'
  report_one sqlite3 'sqlite3 --version'
  report_one htpasswd 'htpasswd -h 2>&1 | head -n1'
  printf '\n== optional ==\n'
  report_one k9s 'k9s version --short'
  report_one stern 'stern --version'
  report_one kubectx 'kubectx --version 2>&1 | head -n1'
  report_one kubens 'kubens --version 2>&1 | head -n1'
  report_one kubeconform 'kubeconform -v'
  report_one kube-linter 'kube-linter version'
  report_one popeye 'popeye version'
  report_one helmfile 'helmfile --version'
  report_one argocd 'argocd version --client --short'
  printf '\nBIN=%s\n' "$BIN"
  case ":$PATH:" in
    *":$BIN:"*) printf 'PATH contains BIN: yes\n' ;;
    *) printf 'PATH contains BIN: NO, add: export PATH="%s:$PATH"\n' "$BIN" ;;
  esac
}

[[ $mode == check ]] && { report; exit 0; }

need_tools
doit mkdir -p "$BIN"

# Download a file, retrying a few times.
download() {
  local url=$1 dest=$2
  if [[ $dry_run == 1 ]]; then
    printf '+ curl -fsSL %s -o %s\n' "$url" "$dest"
    return 0
  fi
  curl -fsSL --retry 3 --retry-delay 2 -o "$dest" "$url"
}

# Verify a sha256 file next to the download, when one is published.
sha_check() {
  local file=$1 sums_url=$2
  [[ $verify == 1 ]] || return 0
  if [[ $dry_run == 1 ]]; then
    printf '+ sha256sum -c <(curl %s)\n' "$sums_url"
    return 0
  fi
  local sums expected actual
  sums=$(curl -fsSL "$sums_url" 2>/dev/null || true)
  if [[ -z $sums ]]; then
    warn "no checksum published at $sums_url, skipping"
    return 0
  fi
  # The published file may be "hash  name" or just "hash".
  expected=$(printf '%s\n' "$sums" | awk 'NR==1 {print $1}')
  actual=$(sha256sum "$file" | awk '{print $1}')
  if [[ ${expected,,} != "${actual,,}" ]]; then
    die "checksum mismatch for $file"
  fi
  printf '    sha256 ok\n'
}

# Install a single binary from a URL.
install_binary() {
  local name=$1 url=$2 tmp=$3
  download "$url" "$tmp/$name"
  doit install -m 0755 "$tmp/$name" "$BIN/$name"
  printf '    %s -> %s\n' "$name" "$BIN/$name"
}

# Extract one member from a tar.gz and install it.
install_tarball() {
  local name=$1 url=$2 member=$3 tmp=$4
  download "$url" "$tmp/$name.tar.gz"
  if [[ $dry_run == 1 ]]; then
    printf '+ tar -xzf %s -C %s %s\n' "$tmp/$name.tar.gz" "$tmp" "$member"
    printf '+ install -m 0755 %s/%s %s/%s\n' "$tmp" "$member" "$BIN" "$name"
    return 0
  fi
  tar -xzf "$tmp/$name.tar.gz" -C "$tmp" --strip-components=1 "$member" 2>/dev/null ||
    tar -xzf "$tmp/$name.tar.gz" -C "$tmp" "$member"
  local found base
  base=$(basename "$member")
  found=$(find "$tmp" -type f -name "$base" -perm -u+x | head -n1)
  [[ -n $found ]] || found=$(find "$tmp" -type f -name "$base" | head -n1)
  [[ -n $found ]] || die "could not find $member in $url"
  install -m 0755 "$found" "$BIN/$name"
  printf '    %s -> %s\n' "$name" "$BIN/$name"
}

# Install a GitHub release asset that is a plain binary.
gh_binary() {
  local name=$1 repo=$2 asset=$3 tmp=$4
  install_binary "$name" "https://github.com/$repo/releases/latest/download/$asset" "$tmp"
}

# Install a GitHub release asset that is a tarball.
gh_tarball() {
  local name=$1 repo=$2 asset=$3 member=$4 tmp=$5
  install_tarball "$name" "https://github.com/$repo/releases/latest/download/$asset" "$member" "$tmp"
}

# Fetch the core Kubernetes clients.
install_core() {
  local tmp=$1
  local kver=$KUBECTL_VERSION
  if [[ $kver == stable ]]; then
    kver=$(curl -fsSL https://dl.k8s.io/release/stable.txt)
  fi

  log "kubectl $kver"
  install_binary kubectl "https://dl.k8s.io/release/$kver/bin/linux/$ARCH/kubectl" "$tmp"
  sha_check "$tmp/kubectl" "https://dl.k8s.io/release/$kver/bin/linux/$ARCH/kubectl.sha256"

  log "minikube ($MINIKUBE_VERSION)"
  if [[ $MINIKUBE_VERSION == latest ]]; then
    install_binary minikube "https://storage.googleapis.com/minikube/releases/latest/minikube-linux-$ARCH" "$tmp"
    sha_check "$tmp/minikube" "https://storage.googleapis.com/minikube/releases/latest/minikube-linux-$ARCH.sha256"
  else
    install_binary minikube "https://storage.googleapis.com/minikube/releases/$MINIKUBE_VERSION/minikube-linux-$ARCH" "$tmp"
  fi

  log "helm $HELM_VERSION"
  # Helm is pinned to 3.x: the workshop charts and plugins assume it.
  install_tarball helm "https://get.helm.sh/helm-$HELM_VERSION-linux-$ARCH.tar.gz" "linux-$ARCH/helm" "$tmp"
  sha_check "$tmp/helm.tar.gz" "https://get.helm.sh/helm-$HELM_VERSION-linux-$ARCH.tar.gz.sha256sum"

  log "k3d ($K3D_VERSION)"
  gh_binary k3d k3d-io/k3d "k3d-linux-$ARCH" "$tmp"

  log "kind ($KIND_VERSION)"
  install_binary kind "https://kind.sigs.k8s.io/dl/$KIND_VERSION/kind-linux-$ARCH" "$tmp"

  log "yq ($YQ_VERSION)"
  gh_binary yq mikefarah/yq "yq_linux_$ARCH" "$tmp"
}

# Install sqlite3 from the official static build.
install_sqlite() {
  local tmp=$1 page name rel sha url
  log "sqlite3"
  page=$(curl -fsSL https://sqlite.org/download.html) || die "sqlite.org is not reachable"
  name=$(printf '%s\n' "$page" | grep -o "sqlite-tools-linux-x64-[0-9]*\.zip" | head -n1 || true)
  [[ -n $name ]] || die "could not find the sqlite tools zip on sqlite.org"
  rel=$(printf '%s\n' "$page" | grep -o "[0-9]\{4\}/$name" | head -n1 || true)
  # The PRODUCT line is: PRODUCT,version,path,size,sha256
  sha=$(printf '%s\n' "$page" | awk -F, -v n="$name" '$1 == "PRODUCT" && $3 ~ n {print $5; exit}')
  url="https://sqlite.org/$rel"
  download "$url" "$tmp/sqlite.zip"
  # sqlite.org publishes SHA3-256 on that page, not SHA-256.
  if [[ -n $sha && $verify == 1 && $dry_run == 0 ]]; then
    if command -v openssl >/dev/null 2>&1; then
      local actual
      actual=$(openssl dgst -sha3-256 "$tmp/sqlite.zip" | awk '{print $NF}')
      [[ ${sha,,} == "${actual,,}" ]] || die "checksum mismatch for sqlite tools"
      printf '    sha3-256 ok\n'
    else
      warn "openssl missing, cannot verify the sqlite sha3-256"
    fi
  fi
  if [[ $dry_run == 1 ]]; then
    printf '+ unzip -j %s sqlite3 -d %s\n' "$tmp/sqlite.zip" "$tmp"
    return 0
  fi
  unzip -o -j "$tmp/sqlite.zip" sqlite3 -d "$tmp" >/dev/null
  install -m 0755 "$tmp/sqlite3" "$BIN/sqlite3"
  printf '    sqlite3 -> %s\n' "$BIN/sqlite3"
}

# Install htpasswd from the Debian package without root.
# The libraries it needs are already present on a normal desktop.
install_htpasswd() {
  local tmp=$1 deb
  log "htpasswd (from apache2-utils .deb)"
  if [[ $dry_run == 1 ]]; then
    printf '+ apt-get download apache2-utils (in %s)\n' "$tmp"
    printf '+ dpkg-deb -x apache2-utils*.deb %s/apache\n' "$tmp"
    return 0
  fi
  (
    cd "$tmp"
    apt-get download apache2-utils >/dev/null 2>&1
  ) || {
    warn "could not download apache2-utils; use openssl instead: scripts/mkpasswd.sh"
    return 0
  }
  deb=$(find "$tmp" -maxdepth 1 -name 'apache2-utils_*.deb' | head -n1)
  [[ -n $deb ]] || { warn "apache2-utils .deb not found"; return 0; }
  dpkg-deb -x "$deb" "$tmp/apache"
  install -m 0755 "$tmp/apache/usr/bin/htpasswd" "$BIN/htpasswd"
  # -h prints the usage and exits non-zero, so test it by hashing a dummy value.
  if ! "$BIN/htpasswd" -nb test test >/dev/null 2>&1; then
    warn "htpasswd needs a library that is missing; use scripts/mkpasswd.sh"
    rm -f "$BIN/htpasswd"
    return 0
  fi
  printf '    htpasswd -> %s\n' "$BIN/htpasswd"
}

# Install the optional day-2 tools.
install_extras() {
  local tmp=$1
  log "extras: k9s, stern, kubectx/kubens, kubeconform, kube-linter, popeye, helmfile, argocd"
  gh_tarball k9s derailed/k9s "k9s_Linux_${ARCH}.tar.gz" k9s "$tmp"
  gh_tarball stern stern/stern "stern_linux_${ARCH}.tar.gz" stern "$tmp"
  gh_binary kubectx ahmetb/kubectx kubectx "$tmp"
  gh_binary kubens ahmetb/kubectx kubens "$tmp"
  gh_tarball kubeconform yannh/kubeconform "kubeconform-linux-${ARCH}.tar.gz" kubeconform "$tmp"
  gh_tarball kube-linter stackrox/kube-linter "kube-linter-linux.tar.gz" kube-linter "$tmp"
  gh_tarball popeye derailed/popeye "popeye_Linux_x86_64.tar.gz" popeye "$tmp"
  gh_binary helmfile helmfile/helmfile "helmfile_linux_${ARCH}" "$tmp"
  gh_binary argocd argoproj/argo-cd "argocd-linux-${ARCH}" "$tmp"

  # helm-diff is what makes "helm diff upgrade" possible.
  if command -v helm >/dev/null 2>&1; then
    log "helm-diff plugin"
    doit helm plugin install https://github.com/databus23/helm-diff --verify=false || \
      warn "helm-diff install failed; optional"
  fi
}

# Install the two packages that want apt, when the user asked for it.
install_apt() {
  log "apt: ${apt_packages[*]}"
  if [[ $dry_run == 1 ]]; then
    printf '+ sudo apt-get update\n+ sudo apt-get install -y %s\n' "${apt_packages[*]}"
    return 0
  fi
  if [[ $EUID -eq 0 ]]; then
    apt-get update && apt-get install -y "${apt_packages[@]}"
  elif sudo -n true 2>/dev/null; then
    sudo apt-get update && sudo apt-get install -y "${apt_packages[@]}"
  elif [[ -t 0 ]]; then
    sudo apt-get update && sudo apt-get install -y "${apt_packages[@]}"
  else
    warn "sudo needs a password and there is no terminal; skipping apt"
    warn "run: sudo apt-get install -y ${apt_packages[*]}"
  fi
}

tmp=$(mktemp -d "${TMPDIR:-/tmp}/k8s-lab-tools.XXXXXX")
trap 'rm -rf "$tmp"' EXIT

case "$mode" in
  user) install_core "$tmp" ;;
  apt) install_apt ;;
  all) install_core "$tmp"; install_sqlite "$tmp"; install_htpasswd "$tmp"; install_apt ;;
esac

# sqlite3 and htpasswd are part of the core expectations for the lab.
if [[ $mode == user ]]; then
  install_sqlite "$tmp"
  install_htpasswd "$tmp"
fi

[[ $do_extras == 1 ]] && install_extras "$tmp"

printf '\n'
report
printf '\nnext: make doctor\n'
