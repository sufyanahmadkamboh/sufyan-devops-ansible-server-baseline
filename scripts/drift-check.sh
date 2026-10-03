#!/usr/bin/env bash
# Drift check: runs the baseline in --check --diff mode, which changes nothing and lists
# every setting that differs from the baseline.
#   exit 0 = every server matches the baseline
#   exit 2 = drift found (listed, with diffs); `make harden` puts it back
# shellcheck source=lib.sh
source "$(dirname "$0")/lib.sh"

log "Comparing the servers with the baseline (no changes are made)"
out="$(playbook playbooks/site.yml --check --diff "$@" 2>&1)" || { echo "$out"; die "drift check could not run"; }

if [[ "$(echo "$out" | recap_changed)" -eq 0 ]]; then
  ok "No drift: every server matches the baseline"
  exit 0
fi

# Tasks (not handlers) that would change something = the settings that drifted.
drifted="$(echo "$out" | awk '
  /^TASK \[/            { task = $0; sub(/^TASK \[/, "", task); sub(/\] \**$/, "", task); next }
  /^RUNNING HANDLER \[/ { task = ""; next }
  /^changed: \[/ && task != "" {
    host = $2; gsub(/[\[\]:]/, "", host)
    key = host " | " task
    if (!(key in seen)) { seen[key] = 1; print "  " key }
  }')"

echo "$out" | sed -n '/^--- before/,/^changed:/p' | grep -vE '^changed:' || true
echo
echo "Drifted settings (server | task):"
echo "$drifted"
count="$(echo "$drifted" | grep -c .)"
printf '\033[1;33mDRIFT\033[0m %s setting(s) differ from the baseline. Run make harden to restore them.\n' "$count"
echo "DRIFT_COUNT=$count"
exit 2
