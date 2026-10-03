#!/usr/bin/env bash
# Applies the baseline to every lab server. Extra arguments go to ansible-playbook,
# for example: scripts/harden.sh --limit web-01 --tags ssh
# shellcheck source=lib.sh
source "$(dirname "$0")/lib.sh"

log "Applying the server baseline"
playbook playbooks/site.yml "$@"
