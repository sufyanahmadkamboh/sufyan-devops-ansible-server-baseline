# Project summary

**Automated Linux Server Hardening & Monitoring with Ansible** · Intermediate

**What it does:** One idempotent Ansible playbook (9 roles) turns a fresh Debian/Ubuntu server into a hardened, monitored and audited one. It applies:
- key-only SSH with no root login and modern cryptography
- a default-deny nftables firewall in its own table
- fail2ban with nftables bans
- unattended security updates
- 34 kernel sysctl settings and a kernel module blocklist
- auditd rules
- a pinned, sandboxed node_exporter
- a weekly Lynis audit, with its score exported to Prometheus

Running it again in `--check --diff` mode is a drift report; running it normally repairs the drift.

**Safety:**
- Lockout guards (no admin key, empty SSH groups, no SSH firewall rule).
- Validate-before-write (`sshd -t`, `nft -c`, `visudo -cf`).
- `serial: 1` rollout.
- A fresh SSH connection at the end to prove access.

**Monitoring:**
- Prometheus with 9 alert rules, all unit-tested with promtool:
  - a security service stopped
  - auditd down on real machines
  - Lynis score below 75 or stale
  - attacker banned
  - metrics file broken
  - disk almost full
- A Grafana dashboard provisioned as code.

**Testing:**
- **Static:** ansible-lint (production profile), yamllint, ShellCheck, pytest, promtool.
- **Molecule:** Ubuntu 24.04, Debian 12 and Debian 13 (converge, idempotence, verify).
- **Lab end-to-end over real SSH:**
  - before/after logins and Lynis
  - firewall and brute-force ban with alert
  - drift detect and repair
  - three safety nets
- **CI job on a real Ubuntu VM:** auditd and every kernel setting live.

**Measured (lab):**
- Lynis 61 → 77 on both servers.
- Password and root-key logins accepted → rejected.
- Attacker banned 7 s after its first attempt, with the alert firing 100 s later.
- Second run: 0 changes.
- 3 hand-made changes detected and repaired.

**Stack:** Ansible 2.21, Molecule 26.9, nftables, fail2ban, unattended-upgrades, auditd, Lynis 3.1.7, Prometheus 3.15, node_exporter 1.12.1, Grafana 13.2, GitHub Actions, Python.
