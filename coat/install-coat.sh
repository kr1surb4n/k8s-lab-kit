#!/usr/bin/env bash
# Install the kit into Coat: the module, the paczki loot table, the spells.
#
# It creates symlinks (so the kit stays the single source of truth), and adds one
# source line to ~/.coatrc if it is missing. It never touches an existing file.
#
# Examples:
#   coat/install-coat.sh --dry-run
#   coat/install-coat.sh
#   coat/install-coat.sh --yes      # no prompts
set -Eeuo pipefail
trap 'printf "error: unexpected failure at line %s: %s\n" "$LINENO" "$BASH_COMMAND" >&2' ERR

kit=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)
coat_dir=${PATH_TO_COAT:-$HOME/.coat}
coatrc=${COATRC:-$HOME/.coatrc}
paczek_dir=${PACZEK_FILLINGS:-$coat_dir/lib/paczki}
spells_dir=${SPELLS:-$HOME/.dotfiles/spells}

dry_run=0
assume_yes=0

# Print the help text.
usage() {
  cat <<EOF
Usage: $(basename "${BASH_SOURCE[0]}") [options]

Install the Kubernetes lab kit into Coat.

  module  -> $coat_dir/modules/k8s.sh
  paczki  -> $paczek_dir/k8s
  spells  -> $spells_dir/kubernetes
  .coatrc -> one source line, after the existing coat.sh line

Options:
  -y, --yes       do not ask for confirmation
  -d, --dry-run   print what would happen, change nothing
  -h, --help      print this help
EOF
}

# Read the command line.
while [[ $# -gt 0 ]]; do
  case "$1" in
    -h | --help) usage; exit 0 ;;
    -y | --yes) assume_yes=1 ;;
    -d | --dry-run) dry_run=1 ;;
    *) printf 'unknown option: %s\n' "$1" >&2; exit 2 ;;
  esac
  shift
done

# Run a command, or only print it in dry-run mode.
doit() {
  if [[ $dry_run == 1 ]]; then printf '+ %s\n' "$*"; else "$@"; fi
}

# Ask a yes/no question; --yes answers it in advance.
confirm() {
  local answer
  [[ $assume_yes == 1 ]] && return 0
  read -r -p "$1 [y/N] " answer </dev/tty || true
  [[ $answer == [yY]* ]]
}

# Link a path into place, refusing to replace a foreign file.
link() {
  local source=$1 target=$2
  if [[ -L $target ]]; then
    if [[ $(readlink -f "$target") == "$(readlink -f "$source")" ]]; then
      echo "already linked: $target"
      return 0
    fi
    echo "warning: $target points elsewhere, leaving it alone" >&2
    return 0
  fi
  if [[ -e $target ]]; then
    echo "warning: $target exists and is not a symlink, leaving it alone" >&2
    return 0
  fi
  if [[ $dry_run == 1 ]]; then
    echo "would link: $target -> $source"
    return 0
  fi
  mkdir -p "$(dirname "$target")"
  ln -sfn "$source" "$target"
  echo "linked: $target -> $source"
}

echo "kit:    $kit"
echo "coat:   $coat_dir"
echo "paczek: $paczek_dir"
echo "spells: $spells_dir"
echo ""

# 1. The module. It is sourced from .coatrc, not from COAT_MODULE_ORDER.
link "$kit/coat/k8s.sh" "$coat_dir/modules/k8s.sh"

# 2. The paczki loot table, so `paczek k8s` works from anywhere.
link "$kit/paczki/k8s" "$paczek_dir/k8s"

# 3. The spells, so they show up in the spellbooks.
link "$kit/coat/spells/k8s" "$spells_dir/kubernetes"

# 4. One line in .coatrc, after `source .../coat.sh`.
line='[ -f "$PATH_TO_COAT/modules/k8s.sh" ] && source "$PATH_TO_COAT/modules/k8s.sh"'
if [[ $dry_run == 1 ]]; then
  echo "+ append to $coatrc: $line"
elif grep -Fq 'modules/k8s.sh' "$coatrc" 2>/dev/null; then
  echo "already in $coatrc: $line"
else
  if confirm "add one source line to $coatrc (a backup is made)?"; then
    cp -a "$coatrc" "$coatrc.bak.$(date +%Y%m%d%H%M%S)"
    printf '\n# k8s lab kit (added by %s)\n%s\n' "$(basename "$0")" "$line" >>"$coatrc"
    echo "updated: $coatrc"
  else
    echo "skipped: $coatrc"
    echo "add manually: $line"
  fi
fi

echo ""
echo "next: open a new shell, then: klab help"
