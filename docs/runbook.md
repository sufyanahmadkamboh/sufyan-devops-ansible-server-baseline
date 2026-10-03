# Runbook

Day-to-day operation of the baseline. Commands are for the lab; for real servers use your own
inventory (`-i inventories/<env>/hosts.yml`) with the same playbooks.

## Add a new server

1. Make sure you can log in with an SSH key as a user with sudo (the cloud provider usually does this).
2. Add the host to the inventory under `baseline:`.
3. Audit it before anything changes: `scripts/audit.sh before`
4. Apply: `scripts/harden.sh --limit <host>`
5. Check: `scripts/verify.sh --limit <host>` and the dashboard (Lynis score appears after the next audit:
   `scripts/audit.sh after`).

## Add or remove an administrator

Edit `common_admin_users` in the inventory (`name` + `pubkeys`) and run `scripts/harden.sh --tags common`.
Keys not listed are removed from that user (`exclusive: true`), so a lost laptop key is revoked by deleting
one line. Removing a user from the list does not delete the account; lock it with `usermod -L` or delete it.

## Open a port

Add a rule to `firewall_rules`:

```yaml
firewall_rules:
  - name: https
    port: 443
    sources_v4: ["0.0.0.0/0"]
    sources_v6: ["::/0"]
```

Then `scripts/harden.sh --tags firewall`. The rule file is validated with `nft -c` before it is loaded.

## Check for drift (someone changed a server by hand)

```bash
scripts/drift-check.sh          # exit 0 = matches, exit 2 = drift (diff printed)
scripts/harden.sh --limit <host> # put it back
```

Run it on a schedule (for example a nightly CI job) to catch changes early.

## Unban an address

```bash
docker compose -f lab/compose.yaml exec db-01 fail2ban-client status sshd
docker compose -f lab/compose.yaml exec db-01 fail2ban-client set sshd unbanip 203.0.113.7
```

To never ban a bastion or office address, add it to `fail2ban_ignoreip_extra`.

## Respond to alerts

| Alert | First steps |
|---|---|
| ServerDown | Is the server up? Is node_exporter running (`systemctl status node_exporter`)? Does the firewall rule for 9100 include Prometheus's address? |
| SecurityServiceNotRunning | `systemctl status <unit>`; `journalctl -u <unit> -n 50`; re-apply with `scripts/harden.sh --limit <host>` |
| AuditdNotRunning | `systemctl status auditd`; full disk? (`df -h /var/log`); restart with `service auditd restart` |
| LynisScoreLow | `scripts/audit.sh now` and read the new suggestions in `/var/log/lynis-report.dat`; run `scripts/drift-check.sh` |
| LynisReportStale | `systemctl list-timers server-baseline-audit.timer`; run `systemctl start server-baseline-audit` |
| SSHAttackerBanned | Usually internet scanners. If it is a colleague, unban and fix their key. |
| Fail2banNotAnswering | `fail2ban-client ping`; `journalctl -u fail2ban -n 50` |
| MetricsFileBroken | `cat /var/lib/node_exporter/textfile/*.prom`; re-run the timer that writes the broken file |
| DiskAlmostFull | `du -xh / --max-depth=2 \| sort -h \| tail`; journald is capped at 500 MB, audit logs at 10 × 50 MB |

## Upgrade node_exporter or Lynis

1. Change `node_exporter_version` / `lynis_version` and the matching checksum in the role defaults.
   node_exporter checksums are in the release's `sha256sums.txt`; for Lynis compute the SHA-256 of
   the GitHub tag archive.
2. `make molecule` (all three distributions), then `scripts/harden.sh --limit <one host>`, then the rest.
3. Old versions stay in `/opt/node_exporter/<version>`; rolling back is setting the old version again.

## Apply on real servers

- Keep `serial: 1` (default) and run against one canary server first: `--limit <host>`.
- Run `--check --diff` first on servers that were set up by hand.
- Keep an open SSH session while applying for the first time; the play also proves access at the end
  with a fresh connection.
- Decide on reboots: `auto_updates_reboot: true` + `auto_updates_reboot_time` if unattended reboots are acceptable.

## Lab commands

| Command | What it does |
|---|---|
| `make lab-up` | two fresh servers, attacker, controller, Prometheus (localhost:9090), Grafana (localhost:3000) |
| `make audit LABEL=before` / `make harden` / `make audit LABEL=after` / `make compare` | the main flow |
| `make verify` | every check, changes nothing |
| `make drift` | drift check |
| `make e2e` | whole test from scratch, writes `reports/e2e-results.md` |
| `make lab-down` | remove everything (reports are kept) |
