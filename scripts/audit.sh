#!/usr/bin/env bash
# Runs a Lynis audit on every lab server and saves reports/lynis/<host>-<label>.dat.
#   scripts/audit.sh before      # on fresh servers
#   scripts/audit.sh after       # after make harden
#   scripts/audit.sh compare     # before/after table from the saved reports
# shellcheck source=lib.sh
source "$(dirname "$0")/lib.sh"

label="${1:-manual}"

if [[ "$label" == "compare" ]]; then
  for host in web-01 db-01; do
    echo "### $host"
    ctl python3 roles/lynis/files/lynis_report.py compare \
      "reports/lynis/$host-before.dat" "reports/lynis/$host-after.dat"
    echo
  done
  exit 0
fi

log "Lynis audit ($label)"
playbook playbooks/audit.yml -e "lynis_label=$label"
