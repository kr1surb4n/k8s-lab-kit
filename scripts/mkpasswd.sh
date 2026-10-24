#!/usr/bin/env bash
# Print one htpasswd line in a format nginx accepts.
#
# Uses htpasswd when it is installed, and openssl otherwise. Both produce the
# apr1 ($apr1$...) format that nginx's auth_basic_user_file understands.
#
# Examples:
#   scripts/mkpasswd.sh lab labpass
#   scripts/mkpasswd.sh lab              # asks for the password
#   scripts/mkpasswd.sh lab labpass > .htpasswd
set -Eeuo pipefail

usage() {
  cat <<EOF
Usage: $(basename "${BASH_SOURCE[0]}") USER [PASSWORD]

Print "USER:HASH" for an nginx basic-auth file.
With no PASSWORD, read it from the terminal without echo.

Example:
  scripts/mkpasswd.sh lab 'labpass' > .htpasswd
EOF
}

case "${1:-}" in
  -h | --help) usage; exit 0 ;;
  "") usage >&2; exit 2 ;;
esac

user=$1
password=${2:-}

# Ask for the password when it was not given on the command line.
if [[ -z $password ]]; then
  if [[ ! -t 0 ]]; then
    printf 'error: no password and no terminal to ask on\n' >&2
    exit 2
  fi
  read -r -s -p "password for $user: " password
  printf '\n' >&2
  [[ -n $password ]] || { printf 'error: empty password\n' >&2; exit 2; }
fi

# Prefer htpasswd; fall back to openssl, which every Debian has.
if command -v htpasswd >/dev/null 2>&1; then
  htpasswd -nb "$user" "$password"
else
  printf '%s:%s\n' "$user" "$(openssl passwd -apr1 "$password")"
fi
