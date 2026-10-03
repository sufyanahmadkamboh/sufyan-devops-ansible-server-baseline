# Test results

Every number below was measured. Where a test ran is stated for each layer:
- **Local:** Windows 11, Docker Desktop 29.4.3, 2026-10-03.
- **CI:** GitHub Actions, `ubuntu-24.04` runners. See the CI badge in the README and the job summaries.

## 1. Static checks (local and CI)

| Check | Result |
|---|---|
| yamllint `--strict` | 0 problems |
| ansible-lint 26.9.0, **production** profile | 0 failures, 0 warnings (89 files) |
| `ansible-playbook --syntax-check` (site, verify, audit) | ok |
| ShellCheck `-S style` (10 scripts) | 0 findings |
| pytest (Lynis report converter) | 7 passed |
| promtool `check rules` / `check config` | 9 rules, config valid |
| promtool `test rules` (6 alert scenarios) | SUCCESS |

The unit tests caught a real bug: the metric writer used `f"{value:g}"`, which printed the Lynis timestamp
as `1.79102e+09`, losing precision. Whole numbers are now written as integers.

## 2. Molecule (local, 3 distributions)

`molecule test`: destroy → syntax → create → converge → idempotence → verify → destroy. Took **430 s** in total.

| Platform | Converge (changed) | Idempotence (changed) | Verify |
|---|---|---|---|
| Ubuntu 24.04 | 60 | **0** | 44 checks ok |
| Debian 12 | 59 | **0** | 44 checks ok |
| Debian 13 | 58 | **0** | 44 checks ok |

In containers, 19 of the 34 kernel settings (the per-container `net.*` ones) are applied and checked. auditd
rules are installed but cannot be loaded there; both are covered by the VM job.

## 3. Lab end-to-end (local, `scripts/e2e.sh`, final clean run: 823 s, all checks passed)

Lab: web-01 = Ubuntu 24.04, db-01 = Debian 12, both systemd containers reached over real SSH from the
controller container. Created and bootstrapped in 14 s.

### Before hardening (distribution defaults)

| | web-01 | db-01 |
|---|---|---|
| Login methods offered | publickey, password | publickey, password |
| Password login for `ops` (correct password) | **accepted** | **accepted** |
| Root login with a valid key | **accepted** | **accepted** |

### Apply and idempotence

| Run | Changes | Time |
|---|---|---|
| First run (both servers, `serial: 1`) | 94 | 169 s |
| Second run | **0** | 107 s |
| verify.yml | all checks passed | 26 s |

### After hardening

| | web-01 | db-01 |
|---|---|---|
| Login methods offered | **publickey** | **publickey** |
| Password login (correct password) | **rejected** | **rejected** |
| Root login with a valid key | **rejected** | **rejected** |
| Admin login with key | accepted | accepted |
| Metrics port 9100 from the attacker | **blocked** | **blocked** |
| Metrics port 9100 from Prometheus | scraped (up = 1) | scraped (up = 1) |

### Lynis 3.1.7 (`--quick`), before → after

| Measure | web-01 before | web-01 after | db-01 before | db-01 after |
|---|---|---|---|---|
| Hardening index | 61 | **77** | 61 | **77** |
| Warnings | 1 | 1 | 1 | 1 |
| Suggestions | 44 | 26 | 45 | 27 |
| Tests performed | 253 | 257 | 252 | 256 |

The same result came from 3 separate clean runs. The remaining warning and many of the remaining suggestions
come from the container environment (for example kernel and boot checks Lynis cannot do in a container)
and from choices left to the operator (separate partitions, a mail relay, malware scanners).

### Attack: SSH brute force from the attacker container (db-01)

| Step | Result |
|---|---|
| Failed logins until ban | **2** (in `aggressive` mode one connection counts twice) |
| Time from first attempt to ban | **7 s** |
| SSH from the banned address | blocked (`reject` by fail2ban's nftables table) |
| Ansible controller during the ban | still connects (`ignoreip`) |
| `SSHAttackerBanned` alert firing in Prometheus | **100 s** after the attack started (textfile timer 1 min + scrape 15 s + evaluation) |
| Ban length | 3600 s |
| Manual unban | address removed from the nftables ban set |

Across the runs the ban came 3–7 s after the first attempt and the alert 32–100 s after it; the alert delay depends on where
the 1-minute textfile timer happened to be.

### Drift: three hand-made changes on web-01

Changes made: password login re-enabled in the SSH drop-in, firewall table deleted, ICMP redirects accepted.

| Step | Result |
|---|---|
| `scripts/drift-check.sh` | exit 2, **3 drifted settings** found: kernel values, SSH settings, firewall rules |
| Server after the check | unchanged (firewall still deleted): check mode is read-only |
| Re-apply (`--limit web-01`) | 5 changes in 51 s (3 settings + sshd and firewall reloads) |
| Drift check again | exit 0, clean |

### Safety nets (each must stop before changing anything)

| Mistake | Result |
|---|---|
| No admin user defined | stopped by the lockout guard |
| Invalid firewall address (`300.1.1.1/32`) | rejected by `nft -c`; old rules stay active |
| Unknown SSH cipher | rejected by `sshd -t`; old settings stay active |
| After all three | admin login works; drift check clean (nothing changed) |

### Monitoring

Prometheus had 2 series each for `lynis_hardening_index` (77, 77), `fail2ban_up`, `server_baseline_info`
and `node_systemd_unit_state{name="ssh.service",state="active"}`. The dashboard screenshot in the README
was taken at the end of the same run.

## 4. Real VM (CI job `vm`)

Runs `scripts/vm-test.sh` on the GitHub-hosted Ubuntu 24.04 runner itself:
- the full baseline is applied, then applied again (it must report 0 changes)
- the verify playbook checks all 34 kernel settings live and the loaded auditd rules
- a change to `/etc/hosts` must appear in `ausearch -k network`
- Lynis runs before and after

Results are in the job summary of each CI run.

## 5. Problems found by these tests

| Found by | Problem | Fix |
|---|---|---|
| pytest | metric timestamp lost precision (`:g` format) | write whole numbers as integers |
| promtool test | hourly test samples went stale and reset the `for:` timer | 5-minute samples |
| Molecule | `/etc/modprobe.d` missing on minimal images | role creates it |
| Molecule | downloads.cisofy.com answers 403 to Ansible | pinned GitHub release archive + SHA-256 |
| e2e | lab image's host-key unit could lose a race against Ubuntu's `ssh.socket` | keys generated inside `ssh.service` |
| e2e | first drift count included handlers (5 instead of 3) | drift check lists tasks only |
| e2e | unban check that sent an SSH probe was itself counted as a failure | check the nftables ban set instead |
| dashboard review | auditd shown as "stopped" on containers, where it cannot run | hidden for `kind="container"` |
