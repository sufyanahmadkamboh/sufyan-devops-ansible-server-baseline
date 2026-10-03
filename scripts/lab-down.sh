#!/usr/bin/env bash
# Removes every lab container, the lab network and the SSH key volume. Reports are kept.
# shellcheck source=lib.sh
source "$(dirname "$0")/lib.sh"

log "Removing the lab"
compose down --volumes --remove-orphans --timeout 5
ok "Lab removed (reports/ kept)"
