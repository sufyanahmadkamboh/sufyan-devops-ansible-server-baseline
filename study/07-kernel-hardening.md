# 7. Kernel hardening

## What is it?

The **kernel** is the core of Linux. It has hundreds of settings, called **sysctl** parameters, visible as files under `/proc/sys/`. For example `net.ipv4.conf.all.accept_redirects` is `/proc/sys/net/ipv4/conf/all/accept_redirects`.

`sysctl -n KEY` reads a value, `sysctl -w KEY=VALUE` changes it **until the next reboot**, and files in `/etc/sysctl.d/` apply values **at every boot**.

The kernel can also load **modules** (drivers for filesystems, network protocols). Files in `/etc/modprobe.d/` can block modules from loading.

## Why this project uses it

Several defaults are convenient but help attackers:

| Setting | Baseline | Protects against |
|---|---|---|
| `net.ipv4.conf.*.accept_redirects` | 0 | Fake "use this router instead" messages that redirect traffic |
| `net.ipv4.conf.*.rp_filter` | 1 | Packets with spoofed source addresses |
| `net.ipv4.tcp_syncookies` | 1 | SYN-flood attacks |
| `net.ipv4.conf.*.log_martians` | 1 | Logs impossible source addresses |
| `kernel.kptr_restrict` | 2 | Hides kernel memory addresses that make exploits easier |
| `kernel.dmesg_restrict` | 1 | Only root can read the kernel log |
| `kernel.yama.ptrace_scope` | 1 | A program cannot inspect another program's memory (password theft) |
| `kernel.unprivileged_bpf_disabled` | 1 | Removes a common local-exploit path |
| `fs.suid_dumpable` | 0 | Privileged programs never write memory dumps |
| `fs.protected_symlinks` / `_hardlinks` | 1 | Link tricks in shared folders like `/tmp` |

Blocked modules: rare filesystems (`cramfs`, `hfs`, `jffs2`, ...) and rare network protocols (`dccp`, `sctp`, `rds`, `tipc`) that a normal server never uses but that have had kernel bugs.

**Not set on purpose:** `net.ipv4.ip_forward`. Docker and Kubernetes hosts need forwarding, so it is left to the machine's role.

**Alternatives:** CIS benchmark roles set many more values; a hardened image bakes them in. This list follows the common recommendations Lynis checks for (test `KRNL-6000`).

## How it works: and why containers are different

A container **shares the host's kernel**. Most kernel settings (`kernel.*`, `fs.*`) are **global**: changing them inside a privileged container would change them for the **host and every other container**. Only some network settings (`net.ipv4.*`, `net.ipv6.*`) exist **per container** (each container has its own network namespace).

So the role decides at run time:

```yaml
# roles/kernel_hardening/defaults/main.yml
kernel_hardening_in_container: >-
  {{ ansible_facts['virtualization_role'] == 'guest'
     and ansible_facts['virtualization_type'] in ['docker', 'podman', 'container', 'containerd', 'lxc'] }}
kernel_hardening_container_safe_prefixes:
  - net.ipv4.
  - net.ipv6.
```

- **In a container** (Molecule, the lab): the persistent file is written with **all** settings, but only `net.*` settings are applied live.
- **On a real machine or VM** (the CI `vm` job): **every** setting is applied and verified live.

The verify step says which case it checked, for example "... kernel settings checked live (container: per-container network settings only)".

## Where it is integrated

- [`roles/kernel_hardening/defaults/main.yml`](../roles/kernel_hardening/defaults/main.yml): the list of settings. `optional: true` marks settings some kernels don't have.
- [`roles/kernel_hardening/templates/sysctl.conf.j2`](../roles/kernel_hardening/templates/sysctl.conf.j2) writes `/etc/sysctl.d/90-server-baseline.conf`. Optional keys get a leading `-`, which tells sysctl "skip this if the kernel doesn't have it":

```
{{ '-' if s.optional | default(false) else '' }}{{ s.key }} = {{ s.value }}
```

- [`roles/kernel_hardening/templates/modprobe.conf.j2`](../roles/kernel_hardening/templates/modprobe.conf.j2): `install dccp /bin/false` plus `blacklist dccp`. `blacklist` alone only stops automatic loading; `install ... /bin/false` also stops explicit loading.
- [`roles/kernel_hardening/tasks/main.yml`](../roles/kernel_hardening/tasks/main.yml): reads each live value and writes only the ones that differ (idempotent), plus a check-mode task that **reports** differences for the drift check.

## Try it

```bash
docker compose -f lab/compose.yaml exec web-01 cat /etc/sysctl.d/90-server-baseline.conf
docker compose -f lab/compose.yaml exec web-01 sysctl net.ipv4.conf.all.accept_redirects
# Make the server drift, then let the drift check find it:
docker compose -f lab/compose.yaml exec web-01 sysctl -w net.ipv4.conf.all.accept_redirects=1
make drift          # reports the difference, changes nothing
make harden         # puts it back
```

## Common mistakes

- **Changing global kernel settings inside a privileged container:** you silently change the host.
- **Using only `sysctl -w`:** gone after a reboot. Use `/etc/sysctl.d/`.
- **Disabling forwarding on a container host:** Docker networking stops.
- **Blocking `udf`:** some clouds (for example Azure) deliver provisioning data on a UDF disk, so it is not in the list.

## Check yourself

1. Why does the role apply only `net.*` settings inside containers?
2. What is the difference between `blacklist sctp` and `install sctp /bin/false`?
3. What does the leading `-` mean in `-kernel.yama.ptrace_scope = 1`?

<details><summary>Answers</summary>

1. Containers share the host kernel. Only network settings are per container; changing the others would change the host and all its containers.
2. `blacklist` stops automatic loading only; `install ... /bin/false` makes every attempt to load it run `/bin/false` instead, so it never loads.
3. "Ignore errors for this key": if the kernel doesn't have the setting, boot continues without an error.
</details>

Next: [8. auditd](08-auditd.md)
