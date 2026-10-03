#!/usr/bin/env bash
# Checks every control of the baseline on the lab servers (changes nothing).
# shellcheck source=lib.sh
source "$(dirname "$0")/lib.sh"

log "Verifying the baseline"
playbook playbooks/verify.yml "$@"
