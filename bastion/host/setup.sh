#!/usr/bin/env bash
# Prepare this host as an SSH bastion.
#
# Creates one key-only user, installs the hardened sshd drop-in, applies a
# default-deny firewall for SSH, and validates the config before reloading.
# It never disables your current session; keep a second one open anyway.
#
# Examples:
#   bastion/host/setup.sh --dry-run
#   sudo bastion/host/setup.sh --user labjump --key ~/.ssh/id_ed25519.pub
#   sudo bastion/host/setup.sh --user labjump --key - < key.pub
set -Eeuo pipefail
trap 'printf "error: unexpected failure at line %s: %s\n" "$LINENO" "$BASH_COMMAND" >&2' ERR

user=labjump
key=""
lan=""
dry_run=0
assume_yes=0
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)

usage() {
  cat <<EOF
Usage: sudo $(basename "${BASH_SOURCE[0]}") [options]

Options:
      --user NAME     account to create (default: labjump)
      --key PATH      public key file, or '-' for stdin
      --lan CIDR      allow SSH only from this network (default: any)
      --yes           do not ask
  -d, --dry-run       print what would happen
  -h, --help          print this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h | --help) usage; exit 0 ;;
    --user) user=${2:?missing user}; shift ;;
    --key) key=${2:?missing key path}; shift ;;
    --lan) lan=${2:?missing CIDR}; shift ;;
    --yes) assume_yes=1 ;;
    -d | --dry-run) dry_run=1 ;;
    *) printf 'unknown argument: %s\n' "$1" >&2; exit 2 ;;
  esac
  shift
done

# Run a command, or print it.
doit() {
  if [[ $dry_run == 1 ]]; then printf '+ %s\n' "$*"; else "$@"; fi
}

# Ask once.
confirm() {
  [[ $assume_yes == 1 || $dry_run == 1 ]] && return 0
  local answer
  read -r -p "$1 [y/N] " answer
  [[ $answer == [yY]* ]]
}

if [[ $dry_run == 0 && $EUID -ne 0 ]]; then
  printf 'error: run with sudo (or --dry-run)\n' >&2
  exit 1
fi

# Read the public key before changing anything.
pubkey=""
if [[ $key == - ]]; then
  pubkey=$(cat)
elif [[ -n $key ]]; then
  [[ -r $key ]] || { printf 'error: cannot read %s\n' "$key" >&2; exit 1; }
  pubkey=$(cat "$key")
fi

cat <<EOF
user:       $user
ssh config: /etc/ssh/sshd_config.d/10-bastion.conf
firewall:   ${lan:-any} -> tcp/22
dry run:    $dry_run
EOF

# 1. The account. No password, no sudo.
if id -u "$user" >/dev/null 2>&1; then
  echo "user $user already exists"
else
  doit useradd --create-home --shell /bin/bash --comment "lab bastion" "$user"
  doit passwd -l "$user"
fi

# 2. The authorized key.
if [[ -n $pubkey ]]; then
  doit install -d -m 0700 -o "$user" -g "$user" "/home/$user/.ssh"
  if [[ $dry_run == 1 ]]; then
    printf '+ install -m 0600 /dev/stdin /home/%s/.ssh/authorized_keys\n' "$user"
  else
    printf '%s\n' "$pubkey" >"/home/$user/.ssh/authorized_keys"
    chown "$user:$user" "/home/$user/.ssh/authorized_keys"
    chmod 0600 "/home/$user/.ssh/authorized_keys"
  fi
else
  echo "no key given; authorized_keys left alone"
fi

# 3. The sshd drop-in. Validate before reloading.
doit install -d -m 0755 /etc/ssh/sshd_config.d
doit install -m 0644 "$here/sshd_config.d/10-bastion.conf" \
  /etc/ssh/sshd_config.d/10-bastion.conf
if [[ $dry_run == 0 ]]; then
  sshd -t || { echo "sshd config is invalid, not reloading" >&2; exit 1; }
fi
doit systemctl reload ssh 2>/dev/null || doit systemctl reload sshd

# 4. Firewall: deny incoming, allow SSH from the LAN only.
if command -v ufw >/dev/null 2>&1; then
  doit ufw default deny incoming
  doit ufw default allow outgoing
  if [[ -n $lan ]]; then
    doit ufw allow from "$lan" to any port 22 proto tcp
  else
    doit ufw allow 22/tcp
  fi
  doit ufw --force enable
else
  echo "ufw not installed; add the equivalent nftables/iptables rule yourself"
fi

# 5. Patch policy: a bastion is a server, not a pet.
if ! dpkg -l unattended-upgrades 2>/dev/null | grep -q '^ii'; then
  echo "warning: unattended-upgrades is not installed"
fi

# 6. Audit logging for interactive sessions.
doit install -m 0755 "$here/audit.sh" /usr/local/bin/bastion-audit
doit install -m 0644 "$here/profile.d/00-bastion-audit.sh" /etc/profile.d/00-bastion-audit.sh

cat <<EOF

done. before you close this session:
  1. open a second terminal and test: ssh -i <key> $user@<this-host>
  2. only then close the old one
  3. from the laptop: ssh -J $user@<this-host> <lab-user>@<lab-host>
EOF
