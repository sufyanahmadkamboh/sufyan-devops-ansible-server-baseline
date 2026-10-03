# Architecture

## What the system does

One Ansible playbook (`playbooks/site.yml`) turns a freshly installed Debian or Ubuntu server into a
hardened, monitored server. Each security control is its own role; every role is idempotent, so the
same playbook also works as a drift detector (`--check --diff`) and as the repair tool.

```
                         ┌──────────────────────── lab network 172.30.0.0/24 ───────────────────────┐
  you ── make harden ──► │ controller 172.30.0.5                                                     │
                         │  ansible-playbook site.yml ──SSH (key only)──►  web-01  Ubuntu 24.04 .21   │
                         │  (pinned toolbox image)                    └──►  db-01   Debian 12    .22   │
                         │                                                    │                        │
                         │                       each server after hardening: │                        │
                         │   sshd (keys, no root) · nftables (default drop) · fail2ban · auto updates  │
                         │   kernel sysctl · auditd rules · node_exporter :9100 · weekly Lynis audit   │
                         │                                                    │ :9100 (only from .10)  │
                         │  prometheus 172.30.0.10 ◄──── scrape every 15 s ───┘                        │
                         │     alert rules ──► grafana 172.30.0.11 dashboard "Server baseline"         │
                         │                                                                             │
                         │  attacker 172.30.0.66 ── SSH brute force / port probes (tests only)        │
                         └─────────────────────────────────────────────────────────────────────────────┘
```

## Roles and order

| Order | Role | What it guarantees | Safety net |
|---|---|---|---|
| 1 | `common` | admins exist with SSH keys only (other keys removed), sudo, banners, umask 027, no core dumps, persistent journal, no telnet/rsh | stops if no admin with a key is defined |
| 2 | `kernel_hardening` | 34 sysctl settings persisted in `/etc/sysctl.d/90-server-baseline.conf` and applied live; 9 unused kernel modules blocked | in containers only per-container `net.*` settings are applied |
| 3 | `ssh_hardening` | key-only login for `ssh-users`, no root, no forwarding, modern ciphers/KEX/MACs, weak DH groups removed | `sshd -t` validates before the file is replaced; stops if the allowed groups are empty |
| 4 | `firewall` | nftables table `inet server_baseline`, input policy drop, one rule per allowed port and source | `nft -c` validates first; stops if SSH is not allowed |
| 5 | `fail2ban` | SSH jail from the systemd journal, nftables bans, longer bans for repeat offenders, ban counters for Prometheus | controller in `ignoreip` |
| 6 | `auto_updates` | daily security updates with unattended-upgrades, no surprise reboots | distribution's own origin list (security only) |
| 7 | `auditd` | records changes to accounts, sudo, SSH, firewall, hosts, services, clock, modules and every root command run by a logged-in user | service only managed where the kernel allows it |
| 8 | `node_exporter` | pinned 1.12.1, SHA-256 verified, sandboxed systemd unit, systemd + textfile collectors, `server_baseline_info` metric | checksum must match before unpacking |
| 9 | `lynis` | pinned Lynis 3.1.7, weekly audit timer, score exported as `lynis_hardening_index` | checksum must match before unpacking |

`playbooks/verify.yml` runs `tasks/verify.yml` of every role: the same checks are used by Molecule,
the lab end-to-end test and the CI VM job.

## How a change reaches a server safely

1. **Validate before write.** Every config whose mistake could cut access is checked by the program that
   will read it: `sshd -t -f`, `nft -c -f`, `visudo -cf`. A failed check leaves the old file in place.
2. **Guards before risk.** The run stops before touching SSH if no administrator key exists, if the
   allowed SSH groups are empty, or if the firewall rules have no SSH rule.
3. **One server at a time.** `serial: 1` with `max_fail_percentage: 0`: a mistake stops after the first server.
4. **Prove access at the end.** `meta: reset_connection` + `wait_for_connection` opens a brand-new SSH
   connection with the new SSH and firewall settings. If that fails, the run fails while the old
   multiplexed connection is still open to repair it.

## Monitoring data flow

```
sshd ──logs──► journald ──► fail2ban ──bans──► nftables (table f2b-table)
                               │
              fail2ban-textfile.timer (1 min) ──► /var/lib/node_exporter/textfile/fail2ban.prom
server-baseline-audit.timer (weekly) ─► Lynis ─► lynis_report.py ─► lynis.prom
Ansible (node_exporter role) ─────────────────────────────────────► baseline.prom
systemd (D-Bus) ──► node_exporter systemd collector (state of ssh, fail2ban, firewall, auditd, timers)
                               │
node_exporter :9100 ◄── Prometheus (only 172.30.0.10 allowed by the firewall) ──► alert rules ──► Grafana
```

Alerts (`lab/prometheus/rules/server-baseline.yml`, unit-tested with promtool):
ServerDown, SecurityServiceNotRunning, AuditdNotRunning (machines only), LynisScoreLow, LynisReportStale,
SSHAttackerBanned, Fail2banNotAnswering, MetricsFileBroken, DiskAlmostFull.

## Test layers

| Layer | Where | What it proves |
|---|---|---|
| Static | CI `static` | yamllint, ansible-lint (production profile), syntax check, ShellCheck, 7 pytest tests, promtool rule tests, compose and dashboard validity |
| Molecule | CI `molecule` | every role converges on Ubuntu 24.04, Debian 12 and Debian 13; second run changes nothing; all verify checks pass |
| Lab end-to-end | CI `lab-e2e`, `make e2e` | over real SSH: before/after Lynis, logins, root, firewall, brute-force ban + alert, drift detect and repair, three safety nets |
| Real VM | CI `vm` | the parts containers cannot test: auditd rules loaded, every kernel setting live, idempotence and Lynis (61 → 73) on a real kernel |

## Decision log

| # | Decision | Why | Trade-off |
|---|---|---|---|
| 1 | Own nftables table, no `flush ruleset` | Docker, fail2ban and Kubernetes keep their own tables; flushing everything breaks them | Rules from other tools are not reviewed by this baseline |
| 2 | Own `server-baseline-firewall.service` instead of `nftables.service` | the distribution unit flushes the whole ruleset on stop | One more unit to know about |
| 3 | Firewall runtime check (`nft list table`) every run | the service stays "active" after someone deletes the rules by hand; checking the kernel catches that drift | One extra command per run |
| 4 | SSH settings in a `00-` drop-in, not `sshd_config` | sshd uses the first value it reads, so `00-` wins over cloud-init's `50-cloud-init.conf`; the distribution file stays untouched for upgrades | Settings live in two files (`sshd -T` shows the result) |
| 5 | Socket activation switched off on Ubuntu 24.04 | one always-running `ssh.service` behaves the same on Debian and Ubuntu and keeps the port in one place | Slightly more memory than on-demand sshd |
| 6 | Kernel settings: read, compare, write only differences | `changed` then means "something drifted"; `--check` reports differences | Custom tasks instead of `ansible.posix.sysctl` |
| 7 | In containers only `net.*` sysctls | most kernel settings belong to the host; changing them from a container changes the host | Container tests cover fewer settings, so CI adds a real VM job |
| 8 | auditd rules installed everywhere, service only on machines | the kernel audit system is not namespaced; auditd cannot start in a container | Covered by the VM job instead |
| 9 | Lynis pinned from GitHub, not apt | apt has 3.0.x; one version keeps before/after scores comparable; downloads.cisofy.com rejects Ansible's HTTP client (403) | Checksum must be updated with the version |
| 10 | Lynis score exported to Prometheus | a weekly score on a dashboard shows when a server gets weaker, not only on audit day | Score is weekly, not real time |
| 11 | No automatic reboots by default | a reboot should be a decision; needrestart restarts affected services | Kernel updates wait for a planned reboot |
| 12 | Port 22 kept | changing the port is obscurity; keys + fail2ban + firewall do the work | Noisy logs from scanners (fail2ban handles them) |
| 13 | Controller in a container | the same pinned tools on Windows, macOS, Linux and CI | Docker is required locally |
| 14 | `serial: 1` by default | limits the impact of a bad change to one server | Slower on large fleets (override `baseline_serial`) |
| 15 | No IP forwarding setting | Docker and Kubernetes hosts need forwarding; forcing it off would break them | Routers must set it explicitly |
