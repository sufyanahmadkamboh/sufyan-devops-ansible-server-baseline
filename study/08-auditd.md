# 8. auditd

## What is it?

The Linux kernel has an **audit system** that can record events: "file X was written", "program Y was run as root". **auditd** is the service that receives these records and writes them to `/var/log/audit/audit.log`. You search them with **`ausearch`** and summarise them with `aureport`.

## Why this project uses it

After an incident, the first questions are: *who changed this account? who edited the SSH settings? who ran what as root?* Normal logs often don't say. auditd records it **at the kernel level**, so it works even if a program writes no log at all. Security standards (CIS, ISO 27001, PCI DSS) ask for it.

**Alternatives:** **Falco** or **Tetragon** (eBPF-based, popular on Kubernetes), osquery, commercial EDR agents. auditd is built into every Linux distribution and is what Lynis checks for (test `ACCT-9628`).

## How it works

Two kinds of rules, in `/etc/audit/rules.d/*.rules`, combined and loaded by `augenrules --load`:

```
-w /etc/sudoers -p wa -k privilege
   │              │      └─ key: a tag to search by
   │              └─ watch for writes (w) and attribute changes (a)
   └─ watch this file or folder

-a always,exit -F arch=b64 -S execve -F euid=0 -F auid>=1000 -F auid!=unset -k root-commands
   └─ on every program start (execve) running as root (euid=0) by a logged-in person (auid >= 1000)
```

`auid` is the **login user id**: it stays the same after `sudo`, so the record shows *which person* became root.

**Immutable mode** (`-e 2`) locks the rules until the next reboot, so an attacker with root cannot switch auditing off quietly. It also means every rule change needs a reboot, so `auditd_immutable` is `false` by default.

### Why auditd cannot run in the lab containers
The kernel audit system is **not namespaced**: there is one per kernel, owned by the host. Inside a container, `auditctl` fails with `Operation not permitted`. So:
- In containers, the role installs the rules but leaves the service disabled, and says so.
- The CI **`vm` job** runs the baseline on a real GitHub runner VM, where auditd runs, the rules are loaded, and the test writes to `/etc/hosts` and checks that `ausearch -k network` finds the event.
- In Prometheus, the `AuditdNotRunning` alert only fires on servers with `server_baseline_info{kind="machine"}`.

## Where it is integrated

[`roles/auditd/defaults/main.yml`](../roles/auditd/defaults/main.yml) lists the watched files:

```yaml
auditd_manage_service: "{{ not (auditd_in_container | bool) }}"
auditd_watches:
  - {path: /etc/passwd, key: identity}
  - {path: /etc/shadow, key: identity}
  - {path: /etc/sudoers.d/, key: privilege}
  - {path: /etc/ssh/sshd_config.d/, key: sshd}
  - {path: /etc/nftables.d/, key: firewall}
  ...
```

[`roles/auditd/templates/server-baseline.rules.j2`](../roles/auditd/templates/server-baseline.rules.j2) turns them into rules and adds time changes, hostname changes, kernel module loading and root commands.

[`roles/auditd/handlers/main.yml`](../roles/auditd/handlers/main.yml) has a detail worth knowing: auditd refuses `systemctl restart` (its unit has `RefuseManualStop=yes`), so the handler uses `service auditd restart`, with a `# noqa` comment explaining it to ansible-lint.

The VM test: [`scripts/vm-test.sh`](../scripts/vm-test.sh)
```bash
echo "# audit test $(date +%s)" | sudo tee -a /etc/hosts >/dev/null
sudo ausearch -k network -f /etc/hosts -ts recent
```

## Try it

In the lab you can look at the rules, but not load them:
```bash
docker compose -f lab/compose.yaml exec web-01 cat /etc/audit/rules.d/50-server-baseline.rules
```
On a real Linux VM with the baseline applied:
```bash
sudo auditctl -l                     # rules loaded in the kernel
sudo usermod -c "test" ops           # change an account
sudo ausearch -k identity -i | tail  # who did it, when, with which program
sudo aureport --summary
```

## Common mistakes

- **Watching too much** (for example every `execve` of every user): the log grows very fast and the disk fills up. The baseline rotates logs (`max_log_file_action = ROTATE`) and alerts on full disks.
- **Watching paths that don't exist** (for example `/var/log/lastlog` on Debian 13): rule loading fails.
- **Expecting auditd in containers.** Test it on a VM.
- **Immutable mode during development:** every change needs a reboot.

## Check yourself

1. What does `-p wa` mean in a watch rule?
2. Why is `auid` more useful than the normal user id after `sudo`?
3. How does this project prove auditd works, given the lab can't run it?

<details><summary>Answers</summary>

1. Record **w**rites and **a**ttribute changes (permissions, owner) to the watched path.
2. After `sudo`, the user id is 0 (root), but `auid` still holds the id of the person who logged in, so the record says who did it.
3. The CI `vm` job applies the baseline to the GitHub runner VM, checks every watch rule is loaded (`auditctl -l`), changes `/etc/hosts`, and checks `ausearch` finds the event.
</details>

Next: [9. Lynis](09-lynis.md)
