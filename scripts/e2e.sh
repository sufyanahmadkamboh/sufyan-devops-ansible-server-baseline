#!/usr/bin/env bash
# End-to-end test on the lab, over real SSH: fresh servers -> audit -> harden -> prove every
# control works (including attacks and failures) -> audit again. Results: reports/e2e-results.md
# Every number in the results is measured by this script.
# shellcheck source=lib.sh
source "$(dirname "$0")/lib.sh"
cd "$ROOT"

RESULTS="$ROOT/reports/e2e-results.md"
mkdir -p "$ROOT/reports"
if (( ${E2E_FROM:-1} <= 1 )); then
  printf '# End-to-end results (%s)\n' "$(date -u '+%Y-%m-%d %H:%M UTC')" > "$RESULTS"
fi

record()  { echo "$*" >> "$RESULTS"; }
pass()    { ok "$*"; record "- PASS: $*"; }
fail()    { record "- FAIL: $*"; die "$*"; }
section() { log "$*"; record ""; record "## $*"; }
expect() {
  local what="$1" got="$2" want="$3"
  if [[ "$got" == "$want" ]]; then pass "$what: $got"; else fail "$what: got '$got', expected '$want'"; fi
}

HOSTS=(web-01 db-01)
ATTACKER_IP=172.30.0.66
# Used inside `sh -c` strings that run in the attacker/controller containers.
SSH_OPTS="-o BatchMode=yes -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=5 -o LogLevel=ERROR"

# Login methods the server offers to a stranger, e.g. "publickey,password".
auth_methods() {
  attacker sh -c "ssh $SSH_OPTS -o PreferredAuthentications=none probe@$1 true 2>&1" \
    | sed -nE 's/.*Permission denied \(([^)]*)\).*/\1/p' | head -n1
}

# Tries a password login from the controller: prints accepted / rejected.
password_login() {
  local host="$1" user="$2" password="$3"
  if ctl sh -c "printf '#!/bin/sh\necho %s\n' '$password' > /tmp/askpass && chmod 700 /tmp/askpass \
      && SSH_ASKPASS=/tmp/askpass SSH_ASKPASS_REQUIRE=force DISPLAY=none setsid -w \
         ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=5 -o LogLevel=ERROR \
             -o PreferredAuthentications=password -o PubkeyAuthentication=no -o NumberOfPasswordPrompts=1 \
             $user@$host true" >/dev/null 2>&1; then echo accepted; else echo rejected; fi
}

key_login() {  # user host -> accepted / rejected
  if ctl sh -c "ssh $SSH_OPTS -i /keys/id_ed25519 $1@$2 true" >/dev/null 2>&1; then echo accepted; else echo rejected; fi
}

# Tries to log in as root with a valid key (copied into root's authorized_keys for the test).
root_key_login() {
  local host="$1" result
  on "$host" sh -c 'install -d -m 700 /root/.ssh && cp /home/ops/.ssh/authorized_keys /root/.ssh/authorized_keys'
  result="$(key_login root "$host")"
  on "$host" rm -f /root/.ssh/authorized_keys
  echo "$result"
}

metrics_from_attacker() {
  if attacker curl -fsS -m 4 -o /dev/null "http://$1:9100/metrics" >/dev/null 2>&1; then echo reachable; else echo blocked; fi
}

# Opens a plain TCP connection to port 22 and reads the SSH banner: no login attempt is made.
ssh_from_attacker() {
  if attacker timeout 6 bash -c "exec 3<>/dev/tcp/$1/22 && head -c 7 <&3" 2>/dev/null | grep -q '^SSH-2.0'; then
    echo open
  else
    echo blocked
  fi
}
# Is the attacker in fail2ban's nftables ban set? (looks at the firewall, sends no traffic)
banned_in_nft() {
  if on "$1" nft list set inet f2b-table addr-set-sshd 2>/dev/null | grep -q "$ATTACKER_IP"; then echo yes; else echo no; fi
}

prom_count()       { prom_query "$1" | wc -l | tr -d ' '; }
targets_up()       { [[ "$(prom_count 'up{job="node"} == 1')" == 2 ]]; }
attacker_banned()  { on "$1" fail2ban-client status sshd | grep -q "$ATTACKER_IP"; }
ban_alert_firing() { [[ "$(prom_count 'ALERTS{alertname="SSHAttackerBanned",alertstate="firing"}')" == 1 ]]; }

# Failed logins (one per connection) until fail2ban bans the attacker; prints the count, 0 if never.
attempts_until_banned() {
  local host="$1" max="$2" i
  for (( i = 1; i <= max; i++ )); do
    attacker sh -c "ssh $SSH_OPTS guess$i@$host true" >/dev/null 2>&1 || true
    if wait_for 4 attacker_banned "$host" >/dev/null; then echo "$i"; return; fi
  done
  echo 0
}

run_playbook_timed() {  # name args... -> prints "<seconds> <changed>"; output in reports/<name>.log
  local name="$1" start; shift
  start=$(date +%s)
  if ! playbook "$@" > "$ROOT/reports/$name.log" 2>&1; then
    tail -40 "$ROOT/reports/$name.log" >&2
    fail "$name failed"
  fi
  echo "$(( $(date +%s) - start )) $(recap_changed < "$ROOT/reports/$name.log")"
}

must_fail() {  # name pattern args... -> passes when the playbook fails AND its output contains pattern
  local name="$1" pattern="$2" rc; shift 2
  set +e; playbook "$@" > "$ROOT/reports/$name.log" 2>&1; rc=$?; set -e
  [[ $rc -ne 0 ]] && grep -q "$pattern" "$ROOT/reports/$name.log"
}

drift_check() {  # name args... -> exit code of drift-check.sh; output in reports/<name>.log
  local name="$1" rc; shift
  set +e; scripts/drift-check.sh "$@" > "$ROOT/reports/$name.log" 2>&1; rc=$?; set -e
  echo "$rc"
}

# ---------------------------------------------------------------------------------------------
s1() {
  section "1. Fresh lab"
  scripts/lab-down.sh >/dev/null 2>&1 || true
  start=$(date +%s)
  scripts/lab-up.sh
  record "- Lab created and bootstrapped in $(( $(date +%s) - start )) s"

  # Give ops a random password for this run, to test whether password logins work.
  LAB_PASSWORD="lab-$(head -c 8 /dev/urandom | od -An -tx1 | tr -d ' \n')"
  for host in "${HOSTS[@]}"; do on "$host" sh -c "echo 'ops:$LAB_PASSWORD' | chpasswd"; done
}

s2() {
  section "2. Before hardening (distribution defaults)"
  for host in "${HOSTS[@]}"; do
    record "- $host offers login methods: $(auth_methods "$host")"
    record "- $host password login for ops: $(password_login "$host" ops "$LAB_PASSWORD")"
    record "- $host root login with a valid key: $(root_key_login "$host")"
  done
  start=$(date +%s)
  if ! scripts/audit.sh before > "$ROOT/reports/audit-before.log" 2>&1; then
    tail -30 "$ROOT/reports/audit-before.log"; fail "Lynis audit (before)"
  fi
  record "- Lynis audit of both servers took $(( $(date +%s) - start )) s"
}

s3() {
  section "3. Apply the baseline (first run)"
  read -r secs changed <<< "$(run_playbook_timed harden-1 playbooks/site.yml)"
  pass "first run: $changed changes in $secs s (one server at a time)"
}

s4() {
  section "4. Idempotence (second run must change nothing)"
  read -r secs changed <<< "$(run_playbook_timed harden-2 playbooks/site.yml)"
  expect "changes on the second run" "$changed" "0"
  record "- second run took $secs s"
}

s5() {
  section "5. Verify every control"
  read -r secs changed <<< "$(run_playbook_timed verify playbooks/verify.yml)"
  pass "verify playbook passed on both servers in $secs s"
}

s6() {
  section "6. Access after hardening"
  for host in "${HOSTS[@]}"; do
    expect "$host offers login methods" "$(auth_methods "$host")" "publickey"
    expect "$host password login (correct password)" "$(password_login "$host" ops "$LAB_PASSWORD")" "rejected"
    expect "$host root login with a valid key" "$(root_key_login "$host")" "rejected"
    expect "$host admin login with key" "$(key_login ops "$host")" "accepted"
    expect "$host metrics port from the attacker" "$(metrics_from_attacker "$host")" "blocked"
  done
  wait_for 90 targets_up >/dev/null || fail "Prometheus cannot scrape both servers"
  pass "Prometheus scrapes both servers through the firewall"
}

s7() {
  section "7. Lynis after hardening"
  if ! scripts/audit.sh after > "$ROOT/reports/audit-after.log" 2>&1; then
    tail -30 "$ROOT/reports/audit-after.log"; fail "Lynis audit (after)"
  fi
  scripts/audit.sh compare | tee -a "$RESULTS"
}

s8() {
  section "8. Attack: SSH brute force from the attacker (fail2ban)"
  host=db-01
  on "$host" fail2ban-client unban --all >/dev/null
  start=$(date +%s)
  first="$(attempts_until_banned "$host" 10)"
  [[ "$first" -gt 0 ]] || fail "attacker was not banned after 10 failed logins"
  pass "attacker banned after $first failed logins, $(( $(date +%s) - start )) s after the first one"
  expect "SSH from the banned attacker" "$(ssh_from_attacker "$host")" "blocked"
  expect "Ansible controller still connects (ignore list)" "$(key_login ops "$host")" "accepted"
  wait_for 180 ban_alert_firing >/dev/null || fail "SSHAttackerBanned alert did not fire"
  pass "SSHAttackerBanned alert firing in Prometheus $(( $(date +%s) - start )) s after the attack started"

  record "- ban length: $(on "$host" fail2ban-client get sshd banip --with-time | sed -nE 's/.*\+ ([0-9]+) =.*/\1/p') s"
  on "$host" fail2ban-client set sshd unbanip "$ATTACKER_IP" >/dev/null
  expect "attacker in the firewall ban set after a manual unban" "$(banned_in_nft "$host")" "no"
}

s9() {
  section "9. Drift: someone changes a server by hand"
  on web-01 sed -i 's/^PasswordAuthentication no/PasswordAuthentication yes/' /etc/ssh/sshd_config.d/00-server-baseline.conf
  on web-01 nft delete table inet server_baseline
  on web-01 sysctl -qw net.ipv4.conf.all.accept_redirects=1
  record "- web-01: password login re-enabled, firewall rules deleted, ICMP redirects accepted"
  expect "drift check exit code" "$(drift_check drift-1)" "2"
  pass "drift check found $(sed -n 's/^DRIFT_COUNT=//p' "$ROOT/reports/drift-1.log") drifted setting(s): $(grep -E '^  web-01 \| ' "$ROOT/reports/drift-1.log" | sed 's/^  web-01 | //' | paste -sd ';' - | sed 's/;/; /g')"
  expect "web-01 firewall after the check (check mode is read-only)" \
    "$(on web-01 sh -c 'nft list table inet server_baseline >/dev/null 2>&1 && echo present || echo absent')" "absent"
  read -r secs changed <<< "$(run_playbook_timed harden-3 playbooks/site.yml --limit web-01)"
  pass "re-apply restored web-01: $changed changes in $secs s"
  expect "drift check after re-apply" "$(drift_check drift-2)" "0"
  expect "web-01 offers login methods" "$(auth_methods web-01)" "publickey"
}

s10() {
  section "10. Safety nets (each must stop before changing anything)"
  if must_fail fail-no-admin "lock everyone out" playbooks/site.yml --limit web-01 -e '{"common_admin_users": []}'; then
    pass "no administrator defined: run stopped by the lockout guard"
  else
    fail "lockout guard did not stop the run"
  fi
  if must_fail fail-bad-firewall "failed to validate" playbooks/site.yml --limit web-01 --tags firewall \
      -e '{"firewall_rules": [{"name": "ssh", "port": 22, "sources_v4": ["0.0.0.0/0"], "sources_v6": []}, {"name": "typo", "port": 9100, "sources_v4": ["300.1.1.1/32"], "sources_v6": []}]}'; then
    pass "invalid firewall address rejected by 'nft -c' before it was applied"
  else
    fail "invalid firewall rule was not rejected"
  fi
  if must_fail fail-bad-sshd "failed to validate" playbooks/site.yml --limit web-01 --tags ssh \
      -e '{"ssh_hardening_ciphers": ["no-such-cipher"]}'; then
    pass "invalid SSH setting rejected by 'sshd -t' before it was applied"
  else
    fail "invalid SSH setting was not rejected"
  fi
  expect "web-01 admin login after the failed runs" "$(key_login ops web-01)" "accepted"
  expect "web-01 unchanged by the failed runs (drift check)" "$(drift_check drift-3 --limit web-01)" "0"
}

s11() {
  section "11. Monitoring"
  for q in 'lynis_hardening_index' 'fail2ban_up' 'server_baseline_info' 'node_systemd_unit_state{name="ssh.service",state="active"}'; do
    expect "Prometheus series for $q" "$(prom_count "$q")" "2"
  done
  record ""
  record "Lynis hardening index in Prometheus:"
  prom_query 'lynis_hardening_index' | sed 's/^/- /' >> "$RESULTS"

}

# Run every section, or resume from one on an existing lab: E2E_FROM=8 scripts/e2e.sh
for n in 1 2 3 4 5 6 7 8 9 10 11; do
  if (( n >= ${E2E_FROM:-1} )); then "s$n"; fi   # not `cond && sN`: bash ignores set -e inside && lists
done
ok "All end-to-end checks passed. Results: reports/e2e-results.md"
