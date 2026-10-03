# 1. Linux server basics

## What is it?

A **Linux server** is a computer running Linux with no screen, managed remotely through a terminal. This project targets two of the most common server distributions: **Ubuntu** (24.04 "noble") and **Debian** (12 "bookworm", 13 "trixie"). Ubuntu is built on Debian, so they share the same package manager (`apt`) and the same service manager (`systemd`).

You need five ideas to follow the rest of this guide: **users and groups**, **sudo**, **packages**, **systemd services and timers**, and **logs**.

## Why this project needs them

Every hardening step changes one of these five things:
- **Users and groups:** who can log in (the `ops` administrator, the `ssh-users` group)
- **sudo:** who can become `root` for admin tasks
- **Packages:** install security tools (fail2ban, auditd), remove dangerous ones (telnet)
- **systemd:** start the protections now and at every boot, and run jobs on a schedule
- **Logs:** where SSH failures are written, so fail2ban can read them

**Alternatives:** Red Hat family systems (RHEL, Rocky, Alma) use `dnf` instead of `apt` and `firewalld` by default. The ideas are the same; the roles here only support Debian and Ubuntu, and say so on the first task.

## How it works

### Users, groups and root
- Every person and every program runs as a **user**. `root` (user id 0) can do anything.
- A **group** is a named list of users. Permissions can be given to a group instead of to each user.
- `/etc/passwd` lists users, `/etc/group` lists groups, `/etc/shadow` holds password hashes.
- **System users** (like `node_exporter`) have no password and no login shell (`/usr/sbin/nologin`). They exist only so a program runs with few permissions.

### sudo
`sudo command` runs one command as root, if `/etc/sudoers` (or a file in `/etc/sudoers.d/`) allows it. A broken sudoers file can lock every admin out of root, so it must always be checked with `visudo -c` before it is installed.

### Packages
`apt install X` downloads and installs package X and what it needs. `apt purge X` removes it with its config files. `apt update` refreshes the list of available versions.

### systemd: services and timers
**systemd** is the first program started at boot (process 1). It starts everything else.
- A **unit** is one thing systemd manages, described in a file such as `/etc/systemd/system/node_exporter.service`.
- A **service** is a program systemd starts and restarts if it crashes. `systemctl start/stop/restart/reload/status NAME`.
- **enabled** means "start at boot"; **active** means "running now". They are independent: a service can be running but not start at the next boot.
- A **timer** is systemd's scheduler (like cron): `OnCalendar=weekly` starts a matching `.service` on a schedule.
- After you change a unit file, systemd needs `daemon-reload` to read it again.

### Logs: journald
systemd collects the output of every service in the **journal**. `journalctl -u ssh` shows the SSH server's messages. By default some systems keep the journal only in memory, so it disappears at reboot; this project makes it **persistent**.

## Where it is integrated

The [`common`](../roles/common/tasks/main.yml) role does the basic Linux work. From [`roles/common/tasks/main.yml`](../roles/common/tasks/main.yml):

```yaml
- name: Create administrator accounts
  ansible.builtin.user:
    name: "{{ item.name }}"
    shell: /bin/bash
    groups: "{{ common_ssh_group }}"
    append: true
    create_home: true
  loop: "{{ common_admin_users }}"
```

The sudoers file is validated before it replaces anything ([`roles/common/templates/sudoers.j2`](../roles/common/templates/sudoers.j2)):

```yaml
- name: Allow administrators to use sudo
  ansible.builtin.template:
    src: sudoers.j2
    dest: /etc/sudoers.d/90-server-baseline
    mode: "0440"
    validate: /usr/sbin/visudo -cf %s
```

Other basics in the same role: removing `telnet`, `rsh-client` and other clear-text tools; the login banner in `/etc/issue.net`; `UMASK 027` in `/etc/login.defs` (new files are not readable by "others"); no core dumps (`/etc/security/limits.d/90-server-baseline.conf`); and persistent logs ([`roles/common/templates/journald.conf.j2`](../roles/common/templates/journald.conf.j2)):

```ini
[Journal]
Storage=persistent
Compress=yes
SystemMaxUse=500M
```

Custom systemd units in this project: `server-baseline-firewall.service` (firewall role), `node_exporter.service`, `fail2ban-textfile.timer` and `server-baseline-audit.timer` (Lynis).

## Try it

```bash
make lab-up
docker compose -f lab/compose.yaml exec web-01 bash      # a shell on the lab server web-01
id ops                                                     # the admin user and its groups
systemctl list-units --type=service --state=running       # what is running
systemctl list-timers                                      # what runs on a schedule
journalctl -u ssh --since "10 min ago"                    # SSH server messages
exit
```

After `make harden`, run them again and compare: `ops` is now in `ssh-users`, and there are new services and timers.

## Common mistakes

- **Editing `/etc/sudoers` without `visudo`:** one typo and nobody can use sudo.
- **"enabled" vs "active":** starting a service by hand but forgetting to enable it, so it is gone after a reboot. The roles always set both (`state: started`, `enabled: true`).
- **Forgetting `daemon-reload`** after changing a unit file: systemd keeps using the old version.
- **Logs only in memory:** after a reboot the evidence of an attack is gone.

## Check yourself

1. What is the difference between an *enabled* and an *active* service?
2. Why does `node_exporter` run as its own user instead of root?
3. What does `validate: /usr/sbin/visudo -cf %s` protect against?

<details><summary>Answers</summary>

1. **Enabled** means systemd starts it at boot; **active** means it is running right now. You usually want both.
2. **Least privilege:** if the program had a bug that let an attacker control it, the attacker would only get the rights of a user with no shell and no password, not root.
3. Ansible writes the new sudoers file to a temporary path, runs `visudo -c` on it, and only replaces the real file if the check passes. A broken file never reaches the server, so sudo keeps working.
</details>

Next: [2. SSH and keys](02-ssh-and-keys.md)
