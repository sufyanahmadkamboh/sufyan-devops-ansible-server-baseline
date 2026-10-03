# Glossary

| Term | Meaning |
|---|---|
| **Agentless** | Ansible needs nothing installed on the servers except SSH and Python |
| **Alert rule** | A Prometheus expression that "fires" when true for a set time (`for:`) |
| **auditd / ausearch** | The service that writes kernel audit records / the tool that searches them by key |
| **auid** | Audit user id: the id of the person who logged in, kept even after `sudo` |
| **Bantime / findtime / maxretry** | fail2ban: ban length / counting window / failures allowed in that window |
| **Baseline** | The minimum security configuration every server must have |
| **Become** | Ansible's word for running a task with sudo |
| **Check mode (`--check`)** | Ansible reports what it would change without changing anything |
| **Collector (node_exporter)** | A part of node_exporter that produces one group of metrics (cpu, systemd, textfile, ...) |
| **Connection tracking (`ct state`)** | The kernel remembers connections so replies can be allowed automatically |
| **Container** | An isolated process with its own filesystem and network, sharing the host kernel |
| **Control node / controller** | The machine that runs Ansible; here the `controller` container |
| **Default-deny** | Firewall policy: drop everything that no rule explicitly allows |
| **Diff mode (`--diff`)** | Ansible shows the before/after of changed files |
| **Drift** | A server's configuration differing from the baseline, usually through manual changes |
| **Drop-in** | A small config file in a `.d/` folder that adds to or overrides the main file |
| **Facts** | Information Ansible gathers about a server before running tasks |
| **fail2ban jail** | A log source + filter + ban action, here for sshd |
| **Handler** | An Ansible task that runs only when notified by a changed task, once, at the end |
| **Hardening** | Reducing a system's attack surface: fewer ways in, stronger locks, better records |
| **Hardening index** | Lynis' summary score from 0 to 100 |
| **Hook (nftables)** | The point in the kernel's packet path where a chain is attached (input, forward, output) |
| **Idempotent** | Running it again gives the same result and changes nothing if nothing drifted |
| **Inventory** | Ansible's list of servers, groups and their variables |
| **Jinja2** | The template language Ansible uses: `{{ variable }}`, `{% for %}` |
| **Journal (journald)** | systemd's log store; read with `journalctl` |
| **Key pair** | A private key (kept secret) and a public key (put on servers) for SSH login |
| **Least privilege** | Give every user and program only the rights it needs |
| **Lockout guard** | An assert that stops the run before a change could lock administrators out |
| **Lynis** | Open-source security auditing tool that scores a Linux system |
| **Molecule** | Test framework for Ansible roles: create, converge, idempotence, verify, destroy |
| **nftables / nft** | The Linux kernel firewall / its command-line tool |
| **node_exporter** | Prometheus' official exporter of Linux server metrics, port 9100 |
| **Pipelining** | Ansible setting that sends modules over the existing SSH session (faster) |
| **Play / playbook** | One "on these hosts, do these things" block / a file of plays |
| **Privileged container** | A container with almost all host capabilities; needed here for systemd in tests |
| **PromQL** | Prometheus' query language |
| **promtool** | Prometheus' tool to check configs and unit-test rules |
| **Provisioning (Grafana)** | Loading data sources and dashboards from files at start-up |
| **Relabelling** | Rewriting a target's labels in Prometheus before storing samples |
| **Role** | A reusable Ansible folder of tasks, defaults, templates and handlers for one job |
| **Scrape** | Prometheus fetching a target's `/metrics` page |
| **Serial** | Ansible rolling update: how many hosts to change at a time |
| **sshd -t / sshd -T** | Test the SSH server config / print the effective settings |
| **Socket activation** | systemd listens on a port and starts the service on the first connection (Ubuntu's ssh.socket) |
| **sudo / sudoers** | Run a command as root / the file that says who may |
| **sysctl** | Kernel settings under `/proc/sys`, persisted in `/etc/sysctl.d/` |
| **systemd unit / service / timer** | Something systemd manages / a long-running program / a schedule |
| **Tags** | Labels to run part of a playbook (`--tags ssh`) |
| **Textfile collector** | node_exporter feature that publishes `*.prom` files written by other tools |
| **unattended-upgrades** | Debian/Ubuntu tool that installs (security) updates automatically |
| **validate:** | Ansible option: test a new file with a command before installing it |
