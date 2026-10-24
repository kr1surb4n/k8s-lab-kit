#!/bin/sh
# Generate host keys, install the authorized key, then run sshd in the foreground.
set -eu

key=/etc/ssh/keys/ssh_host_ed25519_key
if [ ! -f "$key" ]; then
  ssh-keygen -q -t ed25519 -N '' -f "$key"
fi

mkdir -p /home/labjump/.ssh
if [ -f /etc/ssh/authorized_keys/authorized_keys ]; then
  cp /etc/ssh/authorized_keys/authorized_keys /home/labjump/.ssh/authorized_keys
  chown labjump:labjump /home/labjump/.ssh/authorized_keys
  chmod 0600 /home/labjump/.ssh/authorized_keys
fi
chown -R labjump:labjump /home/labjump/.ssh
chmod 0700 /home/labjump/.ssh

mkdir -p /run/sshd
exec /usr/sbin/sshd -D -e -f /etc/ssh/sshd_config.d/10-bastion.conf
