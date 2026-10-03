# 0. The big picture (no jargon)

## The problem, as a story

A company rents a new Linux server. The provider hands it over with **default settings**: anyone on the internet can try to log in with a password, the administrator account `root` can log in directly, every network port that a program opens is reachable, and nobody checks whether security updates get installed.

Within minutes, automated scanners find it and start guessing passwords. This happens to every server with a public address.

**The usual fix:** an engineer logs in and changes settings by hand, following a checklist from a blog post. On the next server they forget a step. Six months later someone "temporarily" re-enables password login and never switches it off. Nobody notices, because nobody re-checks.

## What this project does instead

Think of a company that owns many buildings. Instead of letting each caretaker secure their building their own way, it writes **one security checklist**:
- only people with a key card get in, and there is no master key at the front door
- every door is locked except the ones on a short list
- anyone who tries the wrong key card five times is turned away for an hour
- the locks are upgraded automatically when the manufacturer announces a weakness
- a logbook records who changed the alarm settings
- a **guard walks through every building each week** with the checklist and writes down a score

This project is that checklist, written as code (**Ansible**), plus the guard (**Lynis** weekly audits and **Prometheus** monitoring):

1. **One command** (`make harden`) applies the same checklist to every server.
2. **Running it again changes nothing** if everything is still correct. If someone changed a setting by hand, the **drift check** shows exactly what, and the next run puts it back.
3. A **security score** is measured before and after, so the improvement is a number, not an opinion.
4. **Dashboards and alerts** show if a protection stops running, if the score drops, or if someone is being banned for guessing passwords.

## The pieces, and their jobs

| Piece | Job in one sentence | Building analogy |
|---|---|---|
| **Ansible** | Applies the checklist to every server over SSH, and only changes what differs | The facilities team with the master checklist |
| **SSH hardening** | Key-only logins, no direct root login, modern encryption | Key cards only, no master key at the front door |
| **nftables firewall** | Drops all network traffic except a short allow-list | Every door locked except the ones on the list |
| **fail2ban** | Bans addresses that keep failing to log in | The doorman who turns away repeat offenders |
| **unattended-upgrades** | Installs security updates every day by itself | Automatic lock upgrades |
| **Kernel hardening** | Safer settings deep in the operating system | Reinforced walls and alarm wiring |
| **auditd** | Records changes to accounts, sudo, SSH and firewall files | The logbook |
| **Lynis** | Audits the server and gives it a score from 0 to 100 | The weekly guard walk with a scorecard |
| **node_exporter + Prometheus** | Collect health and security numbers every 15 seconds and raise alerts | Sensors in every building, wired to a control room |
| **Grafana** | Draws those numbers as a dashboard | The control-room screens |
| **Molecule** | Tests the checklist on three Linux versions before it is used | A test building where every change is rehearsed |
| **GitHub Actions** | Runs all tests automatically on every change | The inspector who signs off every new version of the checklist |

## The flow, in one picture

```
 you: make harden
        │
        ▼
 controller container (Ansible) ──SSH──► web-01 (Ubuntu 24.04)   db-01 (Debian 12)
        │                                  │  roles, in order:
        │                                  │  common → kernel_hardening → ssh_hardening → firewall
        │                                  │  → fail2ban → auto_updates → auditd → node_exporter → lynis
        │                                  ▼
        │                         hardened server, node_exporter on port 9100
        │                                  │  (port 9100 only open to Prometheus)
        ▼                                  ▼
 make drift  (check mode,           Prometheus ──► alert rules ──► Grafana dashboard
 changes nothing, lists               (up, services running, Lynis score, fail2ban bans)
 every difference)
```

## What you will be able to do after this guide

- Explain each tool and **why it was chosen**, and what the alternatives are.
- Harden a fresh server, measure the improvement, attack it, detect drift and repair it.
- Read and change the Ansible roles, the firewall rules, the alert rules and the CI pipeline.
- Answer the questions in [interview-questions.md](interview-questions.md).

Next: [1. Linux server basics](01-linux-server-basics.md)
