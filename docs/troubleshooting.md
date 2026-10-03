# Troubleshooting

Problems met while building and testing this project, with the cause and the fix.

## Ansible and SSH

**"Refuse to continue without an administrator who can log in" / "lock everyone out"**
The lockout guard: `common_admin_users` is empty or a user has no key. Add an admin with a public key.
This is intended: SSH is about to become key-only.

**"None of ['ssh-users'] has members"**
Same idea for SSH: nobody is in the allowed groups. Run the `common` role first (it adds the admins).

**`failed to validate` on `00-server-baseline.conf`**
`sshd -t` rejected the new settings (for example an algorithm this OpenSSH does not know). The old file is
still in place and SSH still works. Check with `sudo sshd -t -f /etc/ssh/sshd_config.d/00-server-baseline.conf`.

**Locked out anyway**
Use the provider console. Then: `sudo rm /etc/ssh/sshd_config.d/00-server-baseline.conf && sudo systemctl reload ssh`
and `sudo systemctl stop server-baseline-firewall` (removes only the baseline table).

**`Host key verification failed` in the lab**
The lab servers got new host keys after `make lab-up`. lab-up clears `/keys/known_hosts`; if you recreated a
container by hand: `docker compose -f lab/compose.yaml exec controller rm -f /keys/known_hosts`.

**Ansible ignores `ansible.cfg` ("world writable directory")**
On Windows bind mounts every file looks world-writable, so Ansible skips `ansible.cfg` in the current
directory. The controller image sets `ANSIBLE_CONFIG=/work/ansible.cfg`, which Ansible always honours.

**`serial` from the inventory has no effect**
`serial` is a play keyword evaluated before hosts are known; inventory variables are not available there.
Pass it as an extra var: `-e baseline_serial=0` (Molecule does this).

**Lab: `Connection refused` on port 22 of web-01 right after `make lab-up` (intermittent)**
The first lab image generated host keys in a separate unit ordered `Before=ssh.socket`. On Ubuntu, where
`ssh.socket` starts very early, that ordering conflicts with the unit's default dependencies, so systemd
sometimes dropped the key job. sshd then exited with "no hostkeys available" until it hit its restart limit.
Fix: generate the keys inside `ssh.service` itself (`lab/target/ssh-hostkeys.conf`, `ExecStartPre=ssh-keygen -A`
before `sshd -t`), so whatever starts sshd also creates the keys first. Debian was never affected (no socket).

## Firewall

**`failed to validate` on `server-baseline.nft`**
`nft -c` found an error (for example an invalid address like `300.1.1.1`). Nothing was loaded; the old
rules are still active.

**Docker containers on the host lost network access**
`firewall_manage_forward: true` drops forwarded traffic. Set it to `false` on Docker/Kubernetes hosts.

**Rules disappeared but the service says "active"**
Someone ran `nft delete table` or `nft flush ruleset`. The next run notices (`nft list table` fails) and
reloads; `scripts/drift-check.sh` reports it.

## fail2ban

**Nothing gets banned**
fail2ban reads the journal (`backend = systemd`), which needs `python3-systemd`. Check
`fail2ban-client get sshd journalmatch` and `journalctl -u ssh -n 20` for "Invalid user"/"Connection closed" lines.

**Banned yourself**
From another address or the console: `fail2ban-client set sshd unbanip <ip>`; add your address to
`fail2ban_ignoreip_extra`.

## Containers vs. real machines

**auditd fails to start in a container (`Operation not permitted`)**
The kernel audit system belongs to the host and is not available inside containers. The role installs the
rules there but only manages the service on real machines; CI tests it on a VM.

**Only 19 of 34 kernel settings checked in Molecule**
In containers only per-container network settings (`net.ipv4.*`, `net.ipv6.*`) are applied; the rest would
change the Docker host. All 34 are checked on the CI VM.

**`Destination directory /etc/modprobe.d does not exist`**
Minimal container images have no kmod configuration directory. The role creates it.

**No audit records on GitHub-hosted runners**
On the Azure-based Ubuntu runners, auditd ran and all rules were loaded, but the kernel produced no syscall
records at all (for any rule). The VM test reports this as "not verifiable here", with the evidence: the kernel
config, the command line and the runner's audit.rules. On your own servers, check recording with
`sudo useradd t1 && sudo ausearch -k identity -i | tail`.

## Downloads

**Lynis download returns HTTP 403**
downloads.cisofy.com rejects Ansible's HTTP client. The role downloads the same release from the official
CISOfy GitHub repository (tag archive) and verifies its SHA-256.

**Checksum mismatch**
The pinned checksum does not match the file: either the version changed without the checksum, or the
download is not what it should be. Do not disable the check; update both values together.

## Monitoring

**Target down in Prometheus but the server is fine**
The firewall only allows port 9100 from `lab_prometheus_ip`. Check the rule and `curl` from the Prometheus host.

**`node_textfile_scrape_error 1`**
A `.prom` file has invalid content. The writers use temp file + rename so this should not happen mid-write;
look at the files in `/var/lib/node_exporter/textfile/`.

**Number formatting bug found by the unit tests**
`f"{value:g}"` printed the Lynis timestamp as `1.79102e+09` (lost precision). Whole numbers are now written
as integers; `tests/test_lynis_report.py` covers it.

## Windows / Git Bash

**`open C:\c\Users\...\compose.yaml: The system cannot find the path specified`**
With `MSYS_NO_PATHCONV=1` Docker for Windows receives `/c/Users/...`. `scripts/lib.sh` passes the native
path from `pwd -W`.

**promtool test for "stale report" never fired**
Hourly test samples go stale after Prometheus' 5-minute lookback, which resets the alert's `for:` timer.
The test uses 5-minute samples.
