#!/usr/bin/env bash
# Exercise A3 on the host side: where environment variables live, who sees
# them, and how a shell turns a file into exported variables.
#
# This script needs no cluster. It writes only to a temporary folder.
#
# Examples:
#   scripts/env-demo.sh
set -Eeuo pipefail
trap 'printf "error: unexpected failure at line %s: %s\n" "$LINENO" "$BASH_COMMAND" >&2' ERR

work=${TMPDIR:-/tmp}/k8s-lab-env-demo

# Print a section title.
title() { printf '\n== %s\n' "$*"; }

# Print a command as a human would type it, then run it.
demo() {
  printf '$ %s\n' "$*"
  "$@"
}

# Show the value of a variable, or "(unset)" when it has no value at all.
show() {
  local name=$1
  if [[ -v $name ]]; then
    printf '  %-14s = %s\n' "$name" "${!name}"
  else
    printf '  %-14s = (unset)\n' "$name"
  fi
}

mkdir -p "$work"

title "1. a shell variable is local to the shell"
# shellcheck disable=SC2034  # read through show()
LOCAL_ONLY="visible here"
show LOCAL_ONLY
# A child process does not inherit it, because it was never exported.
printf '$ bash -c "echo \\${LOCAL_ONLY:-(unset)}"\n'
bash -c 'echo "  child sees    = ${LOCAL_ONLY:-(unset)}"'

title "2. export makes it part of the environment"
export EXPORTED="visible everywhere"
show EXPORTED
printf '$ bash -c "echo \\${EXPORTED:-(unset)}"\n'
bash -c 'echo "  child sees    = ${EXPORTED:-(unset)}"'

title "3. a .env file is only text until you export it"
cat >"$work/lab.env" <<EOF
APP_ENV=lab
LOG_LEVEL=debug
GREETING="hello from the file"
EOF
printf '$ cat lab.env\n'
sed 's/^/  /' "$work/lab.env"
printf '$ set -a; . lab.env; set +a\n'
set -a
# shellcheck disable=SC1091
. "$work/lab.env"
set +a
show APP_ENV
show GREETING

title "4. envsubst renders a file from the environment"
printf 'APP_ENV=%s LOG_LEVEL=%s\n' '${APP_ENV}' '${LOG_LEVEL}' >"$work/template.txt"
printf '$ cat template.txt\n'
sed 's/^/  /' "$work/template.txt"
printf '$ envsubst < template.txt\n'
envsubst <"$work/template.txt" | sed 's/^/  /'

title "5. defaults, empty values and unset"
EMPTY=""
show EMPTY
printf '  ${EMPTY:-fallback}   = %s   (empty triggers the default)\n' "${EMPTY:-fallback}"
printf '  ${MISSING:-fallback} = %s   (unset triggers the default)\n' "${MISSING:-fallback}"
printf '  ${MISSING-fallback}  = %s   (unset only, empty stays empty)\n' "${MISSING-fallback}"

title "6. what a child actually receives"
printf '$ env -i bash -c "env | sort"\n'
env -i bash -c 'env | sort' | sed 's/^/  /'

title "7. where this shows up in Kubernetes"
cat <<'EOF'
  image ENV       -> baked into the image, overridden by the pod spec
  pod spec env    -> wins over the image and over envFrom
  envFrom         -> bulk import of ConfigMap/Secret keys
  valueFrom       -> one key, or metadata.name / status.podIP
  change a ConfigMap -> env vars do NOT update; the pod must be recreated
  volume mount       -> DOES update (about a minute), unless subPath is used
EOF

# Leave no trace behind.
rm -rf "$work"
printf '\ncleaned up %s\n' "$work"
