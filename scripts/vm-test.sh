#!/usr/bin/env bash
# Applies the baseline to THE MACHINE THIS RUNS ON and tests it. Meant for a throwaway CI VM:
# it covers what containers cannot (auditd and every kernel setting on a real kernel).
# Needs ansible-playbook on the PATH and passwordless sudo. Results: reports/vm-results.md
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ "${CI:-}" != "true" && "${1:-}" != "--yes-harden-this-machine" ]]; then
  echo "This hardens the current machine (SSH, firewall, kernel). Run it on a disposable VM with:" >&2
  echo "  scripts/vm-test.sh --yes-harden-this-machine" >&2
  exit 1
fi

export ANSIBLE_CONFIG="$ROOT/ansible.cfg"
INVENTORY=(-i inventories/local/hosts.yml)
RESULTS="$ROOT/reports/vm-results.md"
mkdir -p reports
printf '# VM results (%s, kernel %s)\n\n' "$(grep -m1 '^PRETTY_NAME=' /etc/os-release | cut -d'"' -f2)" "$(uname -r)" > "$RESULTS"
record() { echo "$*" | tee -a "$RESULTS"; }
recap_changed() { grep -E '^[a-z0-9-]+ +: ok=' | sed -E 's/.*changed=([0-9]+).*/\1/' | awk '{s+=$1} END {print s+0}'; }

# The admin key only has to exist (nobody logs in over SSH here); it is thrown away afterwards.
keydir="$(mktemp -d)"
trap 'rm -rf "$keydir"' EXIT
ssh-keygen -q -t ed25519 -N '' -C vm-test-throwaway -f "$keydir/id"
export BASELINE_ADMIN_PUBKEY_FILE="$keydir/id.pub"

run() {  # name args... -> "<seconds> <changed>", output in reports/vm-<name>.log
  local name="$1" start; shift
  start=$(date +%s)
  if ! ansible-playbook "${INVENTORY[@]}" "$@" > "reports/vm-$name.log" 2>&1; then
    tail -50 "reports/vm-$name.log" >&2
    record "- FAIL: $name"
    exit 1
  fi
  echo "$(( $(date +%s) - start )) $(recap_changed < "reports/vm-$name.log")"
}

run audit-before playbooks/audit.yml -e lynis_label=vm-before >/dev/null
read -r secs changed <<< "$(run harden-1 playbooks/site.yml)"
record "- PASS: first run, $changed changes in $secs s"
read -r secs changed <<< "$(run harden-2 playbooks/site.yml)"
if [[ "$changed" != 0 ]]; then record "- FAIL: second run changed $changed settings"; exit 1; fi
record "- PASS: second run, 0 changes in $secs s (idempotent)"
read -r secs _ <<< "$(run verify playbooks/verify.yml)"
record "- PASS: verify playbook (all kernel settings and auditd checked live) in $secs s"
grep -E 'kernel settings checked live' "reports/vm-verify.log" | head -n1 | sed 's/^ *msg: */- /' | tee -a "$RESULTS"

# auditd must record a change to a watched file.
echo "# audit test $(date +%s)" | sudo tee -a /etc/hosts >/dev/null
sleep 2
if sudo ausearch -k network -f /etc/hosts -ts recent >/dev/null 2>&1; then
  record "- PASS: auditd recorded the change to /etc/hosts (key: network)"
else
  record "- FAIL: auditd did not record the change to /etc/hosts"; exit 1
fi
record "- auditd rules loaded: $(sudo auditctl -l | wc -l)"

run audit-after playbooks/audit.yml -e lynis_label=vm-after >/dev/null
host=localhost
record ""
python3 roles/lynis/files/lynis_report.py compare \
  "reports/lynis/$host-vm-before.dat" "reports/lynis/$host-vm-after.dat" | tee -a "$RESULTS"

if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then cat "$RESULTS" >> "$GITHUB_STEP_SUMMARY"; fi
