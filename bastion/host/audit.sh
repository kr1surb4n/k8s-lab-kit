#!/usr/bin/env bash
# Log interactive bastion commands to journald, tagged "bastion".
#
# This is a trail, not a tamper-proof audit system: a user with root can edit
# it. Ship journald off the host if the trail matters.
set -Eeuo pipefail

# Nothing to do for non-interactive shells.
[[ $- == *i* ]] || exit 0

# Keep history across sessions and timestamp it.
shopt -s histappend
export HISTTIMEFORMAT='%F %T '
export HISTSIZE=10000
export HISTFILESIZE=20000

# Log the previous command at every prompt.
# shellcheck disable=SC2016
PROMPT_COMMAND='history -a; logger -t bastion -p auth.info "user=$(id -un) tty=$(tty 2>/dev/null) pwd=$PWD cmd=$(history 1 | sed "s/^ *[0-9]* *//")"'
