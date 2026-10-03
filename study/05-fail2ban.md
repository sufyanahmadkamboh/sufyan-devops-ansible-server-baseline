# 5. fail2ban

## What is it?

**fail2ban** reads log messages, counts failures per IP address, and **bans** addresses that fail too often by adding a firewall rule. After the ban time, it removes the rule again.

## Why this project uses it

Port 22 must stay open for administrators, so bots will knock on it all day. Key-only SSH means they cannot get in, but they still fill logs and use CPU. fail2ban cuts them off after a few attempts, and its counters make attacks **visible** on the dashboard.

**Alternatives:** **CrowdSec** (shares attacker lists between users), **sshguard** (smaller, similar idea), SSH on a non-standard port (reduces noise, but is not security), or keeping SSH off the internet entirely (VPN, bastion). fail2ban is the most widely known and is packaged on every distribution.

## How it works

A **jail** = a log source + a filter (which messages count as a failure) + an action (how to ban).

| Setting | Baseline value | Meaning |
|---|---|---|
| `maxretry` | 5 | failures before a ban |
| `findtime` | 10m | ...within this window |
| `bantime` | 1h | first ban length |
| `bantime.increment` | true | repeat offenders: 1h, 2h, 4h ... up to `bantime.maxtime` (1w) |
| `ignoreip` | 127.0.0.1/8, ::1, the controller | never banned |
| `backend` | systemd | read sshd's messages from the journal (no `/var/log/auth.log` needed) |
| `mode` | aggressive | also count scanners that disconnect before even trying a key |
| `banaction` | `nftables[type=multiport]` | ban by adding the address to fail2ban's own nftables table |

```
sshd: "Invalid user guess3 from 172.30.0.66 port 51234"   → systemd journal
fail2ban sshd jail reads the journal, filter matches, counts 172.30.0.66: 1, 2, 3, 4, 5
→ ban: adds 172.30.0.66 to a set in table inet f2b-table   (nftables)
→ further packets from 172.30.0.66 to port 22 are rejected
```

**Two things the lab showed that surprise people:**

- **One connection can count twice.** In `aggressive` mode a single failed connection usually matches two log lines ("Invalid user ..." and "Connection closed by invalid user ..."), so 5 failures can be reached after only 3 connections.
- **Longer bans are for bans that run out on their own.** `bantime.increment` makes each new ban of a known offender longer (1 h, 2 h, 4 h …). In the lab, an address that was unbanned *by hand* and then banned again got the normal 1 h ban (`fail2ban-client get sshd banip --with-time` shows the length), so a manual unban effectively gives the address a fresh start. Fix a colleague's key *before* unbanning them, or they will simply be banned again.

### Why the controller is on the ignore list
If a test (or a typo) made the Ansible controller fail five times, fail2ban would ban it and **Ansible would be locked out of every server**. `fail2ban_ignoreip_extra` puts the controller's address on the never-ban list.

## Where it is integrated

[`roles/fail2ban/templates/jail.local.j2`](../roles/fail2ban/templates/jail.local.j2):

```ini
[DEFAULT]
ignoreip = {{ (fail2ban_ignoreip + fail2ban_ignoreip_extra) | join(' ') }}
bantime = {{ fail2ban_bantime }}
findtime = {{ fail2ban_findtime }}
maxretry = {{ fail2ban_maxretry }}
banaction = nftables[type=multiport]

[sshd]
enabled = true
backend = systemd
mode = aggressive
```

It is installed as `/etc/fail2ban/jail.d/server-baseline.local` (`.local` files override the package's `.conf` files and survive package upgrades). The package `python3-systemd` lets fail2ban read the journal.

**Metrics:** a small script, [`fail2ban-textfile.sh.j2`](../roles/fail2ban/templates/fail2ban-textfile.sh.j2), runs every minute from a systemd timer and writes `fail2ban_up`, `fail2ban_banned_current`, `fail2ban_banned_total` and `fail2ban_failed_current` to `/var/lib/node_exporter/textfile/fail2ban.prom`. node_exporter publishes them (chapter 10), and the `SSHAttackerBanned` alert fires when someone is banned.

## Try it

```bash
# Attack db-01 from the attacker container: 8 logins with unknown user names
for i in 1 2 3 4 5 6 7 8; do
  docker compose -f lab/compose.yaml exec -T attacker ssh -o BatchMode=yes -o StrictHostKeyChecking=no -o ConnectTimeout=5 guess$i@db-01 true
done
docker compose -f lab/compose.yaml exec db-01 fail2ban-client status sshd      # Banned IP list: 172.30.0.66
docker compose -f lab/compose.yaml exec db-01 nft list table inet f2b-table   # the ban, as a firewall rule
docker compose -f lab/compose.yaml exec db-01 cat /var/lib/node_exporter/textfile/fail2ban.prom
# Unban
docker compose -f lab/compose.yaml exec db-01 fail2ban-client set sshd unbanip 172.30.0.66
```

## Common mistakes

- **Banning yourself**, for example from the office or the automation server. Use `ignoreip`.
- **Wrong log source:** on modern Debian there is no `/var/log/auth.log` by default, so a file-based jail never sees anything. Use `backend = systemd`.
- **Editing `jail.conf`:** a package upgrade overwrites it. Put changes in `jail.d/*.local`.
- **Treating fail2ban as the defence.** It reduces noise; key-only SSH is the defence.

## Check yourself

1. With the baseline values, what happens on the 6th failed login within 10 minutes?
2. Why is the Ansible controller in `ignoreip`?
3. How does a ban reach the Grafana dashboard?

<details><summary>Answers</summary>

1. The address was already banned after the 5th failure, so the 6th connection is rejected by the nftables rule fail2ban added.
2. If it were banned, Ansible could no longer reach the servers, and nobody could repair them with automation.
3. sshd logs the failures to the journal → fail2ban bans → the textfile script writes `fail2ban_banned_current` → node_exporter publishes it → Prometheus scrapes it (and fires `SSHAttackerBanned`) → Grafana shows it in "Addresses banned now".
</details>

Next: [6. Automatic security updates](06-automatic-updates.md)
