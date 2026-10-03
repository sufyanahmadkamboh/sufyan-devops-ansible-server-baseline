# Study guide: learn every tool used in this project

This guide is for engineers who are **new to DevOps and Linux security**. You don't need to know any of these tools before you start. Each chapter explains:

1. **What** the tool is, in plain language
2. **Why** this project uses it, and the alternatives
3. **How** it works: the few concepts you really need
4. **Where** it is wired into this repository, with real file paths and snippets
5. **Try it:** commands to run in the lab
6. **Common mistakes** people make with it
7. **Check yourself:** short questions (answers at the end of each chapter)

> 📄 **Prefer one file?** Download the whole guide as a single PDF: **[study-guide.pdf](study-guide.pdf)** (55 pages; answers expanded, ready to print).
> Rebuild it after editing with `python study/tools/build_pdf.py`.

## How to use this guide

Read the chapters in order. Each one builds on the previous ones. Do the "Try it" sections with the lab running (`make lab-up`). Reading alone won't make the ideas stick; running the commands will.

| Step | Chapter | You will understand |
|---|---|---|
| 0 | [The big picture](00-big-picture.md) | What the whole project does, in 5 minutes, with no jargon |
| 1 | [Linux server basics](01-linux-server-basics.md) | Users, sudo, packages, systemd services and timers, logs |
| 2 | [SSH and keys](02-ssh-and-keys.md) | How remote login works and why passwords and root are switched off |
| 3 | [Ansible](03-ansible.md) | How one command configures many servers the same way, safely and repeatably |
| 4 | [Firewall with nftables](04-firewall-nftables.md) | "Deny everything, allow a short list" |
| 5 | [fail2ban](05-fail2ban.md) | How password guessers get banned automatically |
| 6 | [Automatic security updates](06-automatic-updates.md) | unattended-upgrades and the apt timers |
| 7 | [Kernel hardening](07-kernel-hardening.md) | sysctl settings and blocked kernel modules |
| 8 | [auditd](08-auditd.md) | Recording who changed important files |
| 9 | [Lynis](09-lynis.md) | Measuring security with a score, before and after |
| 10 | [Prometheus and node_exporter](10-prometheus-node-exporter.md) | Collecting server and security metrics, alert rules and their tests |
| 11 | [Grafana](11-grafana.md) | The dashboard, provisioned as code |
| 12 | [Molecule and Docker](12-molecule-and-docker.md) | Testing Ansible roles on three Linux distributions |
| 13 | [GitHub Actions](13-github-actions.md) | The four CI jobs that test every change |
| 14 | [How everything fits together](14-how-it-fits-together.md) | One `make harden` and one SSH attack, traced through every tool |
| 15 | [Hands-on labs](15-hands-on-labs.md) | Guided exercises, from "look around" to "attack it" and "break the tests" |
| | [Glossary](glossary.md) | Every term in one place |
| | [Interview questions](interview-questions.md) | 25 questions this project prepares you for, with answers |

## Before you start

**You need:**
- **Docker Desktop** (or Docker Engine on Linux), running
- **bash** and **make**. On Windows, use Git Bash or WSL.
- About **3 GB** of free memory

You do **not** need to install Ansible: it runs inside the `controller` container, with every tool version pinned.

```bash
make lab-up    # two fresh "servers", an attacker, the Ansible controller, Prometheus and Grafana
```

**Time needed:**
- about 1.5 hours to read chapters 0–5
- about 2 hours for chapters 6–14
- 2–3 hours for the labs

The measured results of this project (Lynis scores before and after, run times, attack timings) are in [`docs/test-results.md`](../docs/test-results.md). This guide explains *how* things work; that file shows *what was measured*.

## A tip for learning

Every time you read "this project uses X", open the file mentioned next to it and find the line. The best way to learn a tool is to see it doing a real job, and this repository is that job.
