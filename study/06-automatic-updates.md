# 6. Automatic security updates

## What is it?

**unattended-upgrades** is the Debian/Ubuntu tool that installs updates automatically. Two **systemd timers** trigger it every day:
- `apt-daily.timer` → refreshes the package lists (like `apt update`)
- `apt-daily-upgrade.timer` → installs the allowed updates

## Why this project uses it

Most break-ins use **known** vulnerabilities for which a fix already exists. A server that is not updated stays vulnerable for weeks. Automatic **security** updates close that window within a day, without a person remembering to log in.

**Alternatives:** patching with Ansible on a schedule (more control, needs someone to run it), a patch-management service (AWS Systems Manager Patch Manager, Landscape), or immutable servers that are replaced with a new image instead of patched. Automatic security updates are the baseline that works everywhere.

## How it works

The settings live in small files in `/etc/apt/apt.conf.d/`, read in alphabetical order. **Later files override earlier ones.**

| File | Owner | Content |
|---|---|---|
| `20auto-upgrades` | this baseline | turns the daily refresh and install on |
| `50unattended-upgrades` | the distribution | **which** updates: on Debian and Ubuntu, security updates only |
| `52server-baseline` | this baseline | **how**: reboot or not, cleanup, logging |

The baseline deliberately **keeps the distribution's origin list** (`50unattended-upgrades`) instead of writing its own. The distribution maintains it, so it stays correct across releases.

**Reboots:** some updates (kernel, C library) only take effect after a reboot. `auto_updates_reboot` is **false** by default: a reboot should be a decision. `needrestart` (installed by the `common` role) restarts services that use updated libraries.

## Where it is integrated

[`roles/auto_updates/templates/20auto-upgrades.j2`](../roles/auto_updates/templates/20auto-upgrades.j2):

```
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::AutocleanInterval "{{ auto_updates_autoclean_interval }}";
```

[`roles/auto_updates/templates/52server-baseline.j2`](../roles/auto_updates/templates/52server-baseline.j2):

```
Unattended-Upgrade::Automatic-Reboot "{{ 'true' if auto_updates_reboot | bool else 'false' }}";
Unattended-Upgrade::Remove-Unused-Dependencies "..."
Unattended-Upgrade::SyslogEnable "true";
```

The verification ([`roles/auto_updates/tasks/verify.yml`](../roles/auto_updates/tasks/verify.yml)) does not trust the files; it reads the **final merged configuration** with `apt-config dump` and checks that both timers are enabled. The `SecurityServiceNotRunning` alert also fires if `apt-daily-upgrade.timer` stops.

## Try it

```bash
docker compose -f lab/compose.yaml exec web-01 sh -c "apt-config dump | grep -E 'Periodic|Automatic-Reboot'"
docker compose -f lab/compose.yaml exec web-01 systemctl list-timers 'apt-daily*'
# What would be installed right now (changes nothing):
docker compose -f lab/compose.yaml exec web-01 unattended-upgrade --dry-run --debug 2>&1 | tail -20
```

## Common mistakes

- **Enabling all updates, not only security ones,** on production servers: a feature update can change behaviour overnight.
- **Turning on automatic reboots** without knowing what the server does. Plan a maintenance window first.
- **Disabling the timers** "because apt was locked once". Then nothing updates any more; the alert exists for this.

## Check yourself

1. Which file decides *which* updates are installed, and why doesn't the baseline replace it?
2. Why is `Automatic-Reboot` false by default?
3. How would you notice that automatic updates stopped working?

<details><summary>Answers</summary>

1. The distribution's `50unattended-upgrades`. The distribution keeps it correct for each release; the baseline only adds behaviour settings in a later file.
2. A reboot interrupts the service; it should be planned. `needrestart` covers most cases without a reboot.
3. The `SecurityServiceNotRunning` alert fires if `apt-daily-upgrade.timer` is not active, and the "Security services" table in Grafana shows it red. Lynis also warns about missing updates.
</details>

Next: [7. Kernel hardening](07-kernel-hardening.md)
