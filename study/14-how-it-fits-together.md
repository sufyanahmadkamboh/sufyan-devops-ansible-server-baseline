# 14. How everything fits together

This chapter follows **one `make harden` run** and then **one SSH attack** through every tool, so you can see how each piece hands work to the next.

## A. The life of one `make harden`

```
 make harden
  └─ scripts/harden.sh → docker compose exec controller ansible-playbook playbooks/site.yml
       (ansible.cfg: inventory inventories/lab/hosts.yml, SSH key /keys/id_ed25519, pipelining)

 Gathering facts on web-01 (over SSH as ops, sudo)                    distribution, virtualization type …
 serial: 1 → web-01 first; db-01 only starts if web-01 succeeded

 common            assert Debian/Ubuntu · LOCKOUT GUARD: an admin with a key exists
                   apt: base packages in, telnet & co. out · dbus started · timezone
                   group ssh-users · user ops · authorized_keys (exclusive)
                   sudoers ── validate: visudo -cf ──► installed
                   banners · UMASK 027 · no core dumps · journald persistent ─► notify Restart journald
 kernel_hardening  /etc/sysctl.d/90-server-baseline.conf · /etc/modprobe.d blocklist
                   read live values → container? only net.* · write only differences
 ssh_hardening     LOCKOUT GUARD: ssh-users has members
                   Include line in sshd_config · /run/sshd
                   00-server-baseline.conf ── validate: sshd -t ──► installed ─► notify Reload sshd
                   weak moduli removed · Ubuntu: ssh.socket off, ssh.service on
 firewall          LOCKOUT GUARD: a rule for port 22 exists
                   /etc/nftables.d/server-baseline.nft ── validate: nft -c ──► installed ─► notify Reload firewall
                   server-baseline-firewall.service started + enabled
                   kernel check: table loaded? (catches hand-deleted rules)
 fail2ban          jail.d/server-baseline.local ─► notify Restart fail2ban · metrics timer
 auto_updates      20auto-upgrades + 52server-baseline · apt timers enabled
 auditd            rules.d/50-server-baseline.rules · container? install only : load + start
 node_exporter     get_url with sha256 → unpack → symlink · baseline.prom · sandboxed unit ─► notify Restart
 lynis             get_url with sha256 → /opt/lynis-3.1.7 · audit wrapper · weekly timer

 post_tasks        flush_handlers: Reload sshd, Reload firewall, Restart fail2ban … run NOW
                   reset_connection + wait_for_connection: a NEW SSH login must still work
 → same for db-01
 PLAY RECAP: web-01 changed=N, db-01 changed=N      (second run: changed=0 → idempotent)
```

Three kinds of safety net appear in that trace:
1. **Guards** (`assert`) stop the run *before* anything that could lock you out.
2. **`validate:`** stops a broken file from ever being installed.
3. **The final reconnect** proves access still works, server by server, before moving to the next one.

## B. The life of one SSH brute-force attack

```
 t=0    attacker (172.30.0.66): ssh guess1@db-01 … guess8@db-01
          └─ TCP 22 allowed by the firewall rule "ssh"                         (nftables, table server_baseline)
 t≈0    sshd: "Invalid user guess1 from 172.30.0.66" … refuses (publickey only) (sshd, AllowGroups, keys only)
          └─ message goes to the systemd journal                                 (journald, persistent)
 t≈s    fail2ban sshd jail (backend = systemd, mode = aggressive) counts 5 failures in 10 min
          └─ ban: 172.30.0.66 added to table inet f2b-table                      (fail2ban → nftables)
          └─ further connections from the attacker: rejected                    (nftables)
          └─ the controller 172.30.0.5 is in ignoreip: Ansible still connects
 ≤1 min fail2ban-textfile.timer → fail2ban_banned_current{jail="sshd"} 1      (textfile collector file)
 +15 s  Prometheus scrapes db-01:9100 (allowed: source 172.30.0.10)           (node_exporter, firewall rule)
 +15 s  rule SSHAttackerBanned: fail2ban_banned_current > 0 → FIRING          (Prometheus alert rules)
        Grafana: "Addresses banned now" = 1, fail2ban chart shows the ban     (Grafana)
 +1h    ban expires; a repeat offender gets 2h, then 4h … (bantime.increment)
```

The measured times for this attack in the lab are in [`docs/test-results.md`](../docs/test-results.md).

## C. Remove one piece: what breaks?

| Remove | What happens |
|---|---|
| The `common` lockout guard | An empty admin list would let SSH become key-only with **nobody** allowed in |
| `validate: sshd -t` | One wrong cipher name, a reload, and sshd may refuse every new login |
| `00-` prefix of the SSH drop-in | A cloud-init drop-in could switch password login back on |
| The firewall's own table (using `flush ruleset`) | fail2ban's bans and Docker's rules are wiped on every reload |
| The firewall's kernel check | Someone deletes the rules by hand; the service still says "active"; the drift check misses it |
| `ignoreip` for the controller | One failed test locks Ansible out of the server |
| `backend = systemd` | fail2ban looks for `/var/log/auth.log`, which Debian doesn't write; nothing is ever banned |
| `check_mode: false` on read tasks | The drift check can't see kernel drift |
| `serial: 1` | A bad change breaks every server at once |
| Textfile metrics | Prometheus can't see bans or Lynis scores; no alerts for them |
| The `kind` label on `server_baseline_info` | `AuditdNotRunning` fires forever on every container |
| Molecule's idempotence step | A task that always "changes" goes unnoticed and drift checks become noise |
| The CI `vm` job | auditd and global kernel settings would never be tested |

## D. Concept → file map

| Concept | File |
|---|---|
| Which servers, which variables | [`inventories/lab/hosts.yml`](../inventories/lab/hosts.yml), [`inventories/lab/group_vars/baseline.yml`](../inventories/lab/group_vars/baseline.yml) |
| Order of the roles, rolling update, reconnect test | [`playbooks/site.yml`](../playbooks/site.yml) |
| All checks in one place | [`playbooks/verify.yml`](../playbooks/verify.yml) + `roles/*/tasks/verify.yml` |
| Before/after audit | [`playbooks/audit.yml`](../playbooks/audit.yml), [`roles/lynis/tasks/audit.yml`](../roles/lynis/tasks/audit.yml) |
| SSH settings | [`roles/ssh_hardening/templates/sshd-baseline.conf.j2`](../roles/ssh_hardening/templates/sshd-baseline.conf.j2) |
| Firewall rules | [`roles/firewall/templates/server-baseline.nft.j2`](../roles/firewall/templates/server-baseline.nft.j2) |
| fail2ban jail | [`roles/fail2ban/templates/jail.local.j2`](../roles/fail2ban/templates/jail.local.j2) |
| Kernel settings | [`roles/kernel_hardening/defaults/main.yml`](../roles/kernel_hardening/defaults/main.yml) |
| Audit rules | [`roles/auditd/templates/server-baseline.rules.j2`](../roles/auditd/templates/server-baseline.rules.j2) |
| Lynis → metrics | [`roles/lynis/files/lynis_report.py`](../roles/lynis/files/lynis_report.py) |
| Alerts and their tests | [`lab/prometheus/rules/server-baseline.yml`](../lab/prometheus/rules/server-baseline.yml), [`tests/prometheus/server-baseline.test.yml`](../tests/prometheus/server-baseline.test.yml) |
| Dashboard | [`lab/grafana/dashboards/server-baseline.json`](../lab/grafana/dashboards/server-baseline.json) |
| Lab layout | [`lab/compose.yaml`](../lab/compose.yaml) |
| Drift check | [`scripts/drift-check.sh`](../scripts/drift-check.sh) |
| End-to-end test | [`scripts/e2e.sh`](../scripts/e2e.sh) |
| Role tests | [`molecule/default/molecule.yml`](../molecule/default/molecule.yml) |
| CI | [`.github/workflows/ci.yaml`](../.github/workflows/ci.yaml) |

Next: [15. Hands-on labs](15-hands-on-labs.md)
