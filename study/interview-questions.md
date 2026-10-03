# Interview questions this project prepares you for

Try to answer each question out loud first, then open the answer.

## Ansible

1. **What does "idempotent" mean, and how do you prove a playbook is?**
   <details><summary>Answer</summary>Running it again gives the same result and changes nothing if nothing drifted. Proof: run it twice and require `changed=0` on the second run. Molecule's idempotence step, the lab end-to-end test and the CI VM test all do this here.</details>

2. **How do you make a `command` task idempotent?**
   <details><summary>Answer</summary>Read first (`changed_when: false`, `check_mode: false`), then run the write command only `when` the value differs, and set `changed_when` honestly. The kernel_hardening role does exactly this for sysctl values.</details>

3. **What is the difference between a task and a handler? When do handlers run?**
   <details><summary>Answer</summary>Handlers run only when notified by a task that reported "changed", once per play, after the tasks, or earlier at `meta: flush_handlers`. Used for reloads and restarts so services aren't restarted on every run.</details>

4. **How do you change hundreds of servers without breaking all of them at once?**
   <details><summary>Answer</summary>A rolling update: `serial` (here 1 server at a time) with `max_fail_percentage: 0`, so the first failure stops the run. Plus a reconnect test at the end of each server (`reset_connection` + `wait_for_connection`) so access problems are found on the first server.</details>

5. **How do you detect configuration drift with Ansible?**
   <details><summary>Answer</summary>Run the same playbook with `--check --diff`: it reports what would change without changing anything. `scripts/drift-check.sh` turns the recap into an exit code (0 = clean, 2 = drift). Read tasks need `check_mode: false` so the comparison still has data.</details>

6. **What does `validate:` do on the template module? Give examples.**
   <details><summary>Answer</summary>It runs a command against the new file (in a temporary path) and installs it only if the command succeeds: `visudo -cf %s` for sudoers, `sshd -t -f %s` for SSH, `nft -c -f %s` for the firewall. A broken file never reaches the server.</details>

7. **Where would you put variables, and why use role defaults?**
   <details><summary>Answer</summary>Role `defaults/main.yml` hold safe, documented defaults with the lowest priority; inventories (`group_vars`) override them per environment. Prefixing variables with the role name (`ssh_hardening_*`) avoids collisions and is checked by ansible-lint.</details>

## Linux security

8. **Walk me through how you would harden a fresh Linux server.**
   <details><summary>Answer</summary>Admin users with keys and sudo; key-only SSH, no root login, allowed group, modern crypto; default-deny firewall with a short allow-list; fail2ban; automatic security updates; kernel sysctl hardening and blocked rare modules; auditd for accountability; remove legacy packages; persistent logs; then measure with Lynis and monitor that every protection keeps running.</details>

9. **Why disable password authentication and root login over SSH?**
   <details><summary>Answer</summary>Passwords can be guessed or reused; keys cannot be brute-forced. Root is the one account name every attacker knows, and direct root logins lose the information of which person acted. Admins log in as themselves and use sudo, which is logged.</details>

10. **How do you make sure an SSH hardening change doesn't lock you out?**
    <details><summary>Answer</summary>Guards before the change (an admin with a key exists; the allowed group has members; the firewall allows the SSH port), `sshd -t` validation, a reload instead of a stop, a fresh test connection afterwards, one server at a time, and the controller on fail2ban's ignore list.</details>

11. **How do you check the SSH settings that are really in effect?**
    <details><summary>Answer</summary>`sshd -T`. With drop-in files, the first value read wins, so reading `sshd_config` alone can mislead. The verify tasks assert on the `sshd -T` output.</details>

12. **Why does the firewall use its own nftables table instead of `flush ruleset`?**
    <details><summary>Answer</summary>`flush ruleset` deletes every rule on the machine, including fail2ban's bans and Docker's networking rules. Replacing only its own table in one atomic transaction leaves the others untouched.</details>

13. **How does fail2ban work, and what are its limits?**
    <details><summary>Answer</summary>It reads logs (here the systemd journal), counts failures per address within `findtime`, and bans after `maxretry` by adding an nftables rule for `bantime`. Limits: distributed attacks from many addresses, and it is noise reduction, not the defence; key-only SSH is the defence.</details>

14. **Which kernel settings would you harden, and which would you leave alone?**
    <details><summary>Answer</summary>Harden: no ICMP redirects or source routing, reverse-path filtering, SYN cookies, `kptr_restrict`, `dmesg_restrict`, `ptrace_scope`, unprivileged BPF off, `suid_dumpable=0`, protected links. Leave alone: `ip_forward` on container hosts, which need it.</details>

15. **What is auditd for, and why can't you test it in a container?**
    <details><summary>Answer</summary>It records changes to important files and root commands at the kernel level, with the login user id (`auid`), for investigations and compliance. The kernel audit system is not namespaced; it belongs to the host, so containers get "Operation not permitted". This project tests it on a throwaway CI VM.</details>

16. **Should servers install updates automatically?**
    <details><summary>Answer</summary>Security updates: yes, daily, because most attacks use known, already-fixed vulnerabilities. Feature updates and reboots: planned. The baseline keeps the distribution's security-only origin list, disables automatic reboots by default, and uses needrestart for services.</details>

## Measuring and monitoring

17. **How do you prove that hardening improved security?**
    <details><summary>Answer</summary>Measure with an independent tool before and after, with the same version: Lynis' hardening index, warnings and suggestions, plus functional tests from outside (password login rejected, root key login rejected, metrics port blocked, attacker banned).</details>

18. **What are the limits of a Lynis score?**
    <details><summary>Answer</summary>It is a weighted summary of checks, not a guarantee; some tests are skipped in containers; some suggestions deliberately don't apply. Compare like with like (same version, same kind of machine) and keep it as a trend with a realistic target.</details>

19. **How would you monitor that security controls keep running?**
    <details><summary>Answer</summary>node_exporter's systemd collector exports each service's state; an alert fires if SSH, fail2ban, the firewall, the update timer or the audit timer is not active. Lynis scores and fail2ban counters come in through the textfile collector, with alerts for a low score, a stale audit and bans.</details>

20. **How do you get metrics from a tool that is not a Prometheus exporter?**
    <details><summary>Answer</summary>Write a `*.prom` file in node_exporter's textfile directory from a script or timer, atomically (temp file + rename). Here: `lynis_report.py` and the fail2ban metrics script.</details>

21. **How do you test Prometheus alert rules?**
    <details><summary>Answer</summary>`promtool test rules` with synthetic input series and expected alerts at given times, including "no alert yet" inside the `for:` window. Watch out for sample spacing: samples further apart than the 5-minute lookback go stale and reset `for:`.</details>

## Testing and CI

22. **How do you test Ansible roles?**
    <details><summary>Answer</summary>Static: yamllint, ansible-lint, syntax check. Then Molecule: create containers for several distributions, converge, idempotence, verify, destroy. Here, three distributions, and the converge/verify playbooks import the real ones.</details>

23. **What can't you test with containers, and what do you do about it?**
    <details><summary>Answer</summary>Anything host-wide: kernel audit, global sysctl settings, real boot behaviour. This project runs the baseline on the GitHub Actions runner VM, which is thrown away after the job.</details>

24. **Why run Ansible from a container instead of installing it locally?**
    <details><summary>Answer</summary>Pinned, identical versions of ansible-core, ansible-lint, Molecule, collections and the Docker CLI for everyone and for CI; no "works on my machine". Also, the Ansible control node does not run natively on Windows.</details>

25. **How do you keep secrets out of a repository like this?**
    <details><summary>Answer</summary>Generate them at runtime and keep them outside Git: the SSH key in a Docker volume, the Grafana password in a git-ignored file passed as a Docker secret, the CI admin key created per run and deleted. `.gitignore` covers `.lab/`, keys and reports. Public keys in test data are fine because they are not secret.</details>
