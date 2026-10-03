# 15. Hands-on labs

Do these in order. Each lab says what to do, what you should see, and what you learned. Commands run from the repository root in bash (Git Bash on Windows). A shortcut used below:

```bash
lab() { docker compose -f lab/compose.yaml exec "$@"; }     # lab web-01 <command>
```

Open three windows: a terminal, Prometheus (<http://localhost:9090>) and Grafana (<http://localhost:3000>).

## Lab 1: Explore a fresh server (15 min)

```bash
make lab-up
lab web-01 bash -c '. /etc/os-release; echo $PRETTY_NAME'
lab web-01 sh -c "sshd -T | grep -E 'passwordauthentication|permitrootlogin'"
lab web-01 nft list ruleset                       # empty: no firewall
lab web-01 systemctl is-active fail2ban           # not installed
lab attacker ssh -o BatchMode=yes -o StrictHostKeyChecking=no -o PreferredAuthentications=none probe@web-01
```
**You should see:** password login on, root login with a key allowed (`prohibit-password`), no firewall, `Permission denied (publickey,password)`.

✅ **You learned:** what "distribution defaults" really look like.

## Lab 2: Measure, harden, measure again (20 min)

```bash
scripts/audit.sh before
make harden                 # watch the roles run, web-01 first, then db-01
make harden                 # again: every host shows changed=0
make verify
scripts/audit.sh after
scripts/audit.sh compare    # the before/after table and the resolved Lynis suggestions
```
Repeat the Lab 1 commands and compare. In Grafana, the Lynis bars and the "Security services" grid fill in.

✅ **You learned:** idempotence in practice, and how to prove an improvement with an independent score.

## Lab 3: Break it: drift (15 min)

```bash
lab web-01 sed -i 's/^PasswordAuthentication no/PasswordAuthentication yes/' /etc/ssh/sshd_config.d/00-server-baseline.conf
lab web-01 nft delete table inet server_baseline
lab web-01 sysctl -w net.ipv4.conf.all.accept_redirects=1
make drift; echo "exit code: $?"
```
**You should see:** exit code 2, a diff of the SSH file, and "changed" for the firewall and the kernel setting. Check that nothing was repaired yet: `lab web-01 nft list tables`. Then:
```bash
make harden
make drift                   # "No drift", exit code 0
```

✅ **You learned:** check mode reports without changing, and why the firewall role asks the kernel instead of trusting the service state.

## Lab 4: Break it: the safety nets (15 min)

Each of these must **fail before changing anything**:
```bash
# 1. No administrator → lockout guard
scripts/harden.sh --limit web-01 -e '{"common_admin_users": []}'
# 2. Impossible firewall address → nft -c rejects it
scripts/harden.sh --limit web-01 --tags firewall \
  -e '{"firewall_rules": [{"name": "ssh", "port": 22, "sources_v4": ["0.0.0.0/0"], "sources_v6": []}, {"name": "typo", "port": 9100, "sources_v4": ["300.1.1.1/32"], "sources_v6": []}]}'
# 3. Unknown cipher → sshd -t rejects it
scripts/harden.sh --limit web-01 --tags ssh -e '{"ssh_hardening_ciphers": ["no-such-cipher"]}'
# Afterwards: nothing changed and you can still log in
make drift
```
Read the error messages: "lock everyone out", "failed to validate".

✅ **You learned:** guards and `validate:` turn dangerous mistakes into harmless failed runs.

## Lab 5: Attack: SSH brute force (15 min)

```bash
for i in 1 2 3 4 5 6 7 8; do
  docker compose -f lab/compose.yaml exec -T attacker ssh -o BatchMode=yes -o StrictHostKeyChecking=no -o ConnectTimeout=5 guess$i@db-01 true
done
lab db-01 fail2ban-client status sshd             # 172.30.0.66 in the banned list
lab db-01 nft list table inet f2b-table
lab attacker ssh -o ConnectTimeout=5 probe@db-01  # refused now
lab db-01 journalctl -u ssh --since "5 min ago" | grep -i invalid | tail -3
```
Within about two minutes: Prometheus → Alerts shows `SSHAttackerBanned` firing; Grafana shows "Addresses banned now = 1". Unban:
```bash
lab db-01 fail2ban-client set sshd unbanip 172.30.0.66
```

✅ **You learned:** the full path from a log line to a firewall rule to an alert (chapter 14, part B).

## Lab 6: Change a parameter (20 min)

**a) Stricter fail2ban.** In [`inventories/lab/group_vars/baseline.yml`](../inventories/lab/group_vars/baseline.yml) add `fail2ban_maxretry: 3`, run `make harden`, and check only the fail2ban task and its handler changed. Repeat Lab 5: the ban now comes after 3 attempts.

**b) Open a new port.** Add a rule to `firewall_rules`:
```yaml
  - name: web
    port: 80
    sources_v4: ["0.0.0.0/0"]
    sources_v6: ["::/0"]
```
`make harden`, then `lab web-01 nft list table inet server_baseline` shows `comment "web"`. The verify playbook now also checks this rule exists. Remove it again afterwards.

✅ **You learned:** the baseline is data-driven: inventory variables change behaviour, the roles stay the same.

## Lab 7: Stop a protection and watch the alert (10 min)

```bash
lab web-01 systemctl stop fail2ban
```
Grafana's "Security services" grid turns red for web-01; after 2 minutes `SecurityServiceNotRunning` fires in Prometheus. `make harden` starts it again (the role's `state: started`), and the alert resolves.

✅ **You learned:** monitoring the protections themselves, not just CPU and memory.

## Lab 8: Test the tests (30 min)

A test you have never seen fail proves nothing. Make each test layer fail on purpose, then undo the change (`git checkout -- <file>`).

1. **Idempotence:** add this task at the end of [`roles/common/tasks/main.yml`](../roles/common/tasks/main.yml):
   ```yaml
   - name: A task that always changes
     ansible.builtin.command: date
   ```
   `make molecule` fails at the **idempotence** step (and ansible-lint complains with `no-changed-when` in `make lint`).
2. **Verify:** in [`roles/ssh_hardening/templates/sshd-baseline.conf.j2`](../roles/ssh_hardening/templates/sshd-baseline.conf.j2) change `MaxAuthTries {{ ssh_hardening_max_auth_tries }}` to `MaxAuthTries 6`. Molecule's **verify** step fails on `maxauthtries`.
3. **Alert tests:** in [`lab/prometheus/rules/server-baseline.yml`](../lab/prometheus/rules/server-baseline.yml) change `for: 2m` of `SecurityServiceNotRunning` to `for: 10m`. `make promtool` fails: the test expects the alert at minute 5.
4. **Unit tests:** in [`roles/lynis/files/lynis_report.py`](../roles/lynis/files/lynis_report.py) in `to_prometheus`, change the `lynis_warnings` line to count `report.suggestions` instead of `report.warnings`. `pytest tests` (or `make lint`) fails on `lynis_warnings 1`.

✅ **You learned:** what each test layer protects, and that each one really catches the mistake it is meant for.

## Lab 9 (optional): The full end-to-end test

```bash
make e2e
cat reports/e2e-results.md
```
This rebuilds the lab from zero and runs Labs 1–7 automatically, with real measurements. Compare your numbers with [`docs/test-results.md`](../docs/test-results.md).

When you are done: `make lab-down`.
