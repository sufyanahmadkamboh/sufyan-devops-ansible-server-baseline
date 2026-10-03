#!/usr/bin/env bash
# Shared helpers for the lab scripts. Everything Ansible-related runs inside the
# controller container, so the host only needs Docker (and Git Bash on Windows).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export MSYS_NO_PATHCONV=1  # Git Bash on Windows: do not rewrite /paths in docker arguments
# Docker on Windows needs C:/... paths; `pwd -W` only exists in Git Bash.
ROOT_NATIVE="$(cd "$ROOT" && { pwd -W 2>/dev/null || pwd; })"

compose() { docker compose -f "$ROOT_NATIVE/lab/compose.yaml" "$@"; }

log()  { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
ok()   { printf '\033[1;32m ok\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31mERR\033[0m %s\n' "$*" >&2; exit 1; }

# Run a command on the Ansible controller / the attacker / a lab server.
ctl()      { compose exec -T controller "$@"; }
attacker() { compose exec -T attacker "$@"; }
on()       { local host="$1"; shift; compose exec -T "$host" "$@"; }

playbook() { ctl ansible-playbook "$@"; }

# Sum of "changed=N" over every host in an ansible-playbook PLAY RECAP.
recap_changed() { grep -E '^[a-z0-9-]+ +: ok=' | sed -E 's/.*changed=([0-9]+).*/\1/' | awk '{s+=$1} END {print s+0}'; }

# Instant Prometheus query: one "<instance> <value>" line per series.
prom_query() { ctl python3 scripts/promq.py "$1"; }

# Wait until a command succeeds; prints the seconds it took.
wait_for() {
  local timeout="$1"; shift
  local start; start=$(date +%s)
  until "$@" >/dev/null 2>&1; do
    (( $(date +%s) - start > timeout )) && return 1
    sleep 2
  done
  echo $(( $(date +%s) - start ))
}
