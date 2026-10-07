Is your new Linux server safe the minute it boots? In this full DevOps project I build an Ansible baseline that turns a fresh Ubuntu or Debian server into a hardened, monitored and audited server with one command: SSH keys only and no root, a default-deny nftables firewall, fail2ban, automatic security updates, kernel hardening, an auditd trail, node_exporter metrics and a weekly Lynis audit. The same command detects drift and repairs it, four safety nets make sure it can never lock you out, and every claim is measured with real attacks.

💻 Code: https://github.com/sufyanahmadkamboh/sufyan-devops-ansible-server-baseline
📚 Free study guide (PDF, 9 hands-on labs, 25 interview questions): https://github.com/sufyanahmadkamboh/sufyan-devops-ansible-server-baseline/tree/main/study
📈 Measured test results: https://github.com/sufyanahmadkamboh/sufyan-devops-ansible-server-baseline/blob/main/docs/test-results.md
🌐 All my projects: https://sufyanahmadkamboh.github.io/

🧪 Run it on your laptop (Docker with Compose and Bash; Git Bash on Windows works):
git clone https://github.com/sufyanahmadkamboh/sufyan-devops-ansible-server-baseline.git
cd sufyan-devops-ansible-server-baseline
make lab-up && make audit LABEL=before && make harden && make audit LABEL=after && make compare
make verify · make drift · make e2e (the whole proof with attacks, about 10 minutes) · make lab-down

⏱️ Chapters
0:00 The question
1:30 The problem
2:22 The idea
3:05 Architecture
3:54 The playbook
4:38 The roles
8:15 Safety nets
9:39 Measured results
12:35 Monitoring
13:29 Testing
15:30 Run it yourself
17:03 Production rollout
17:42 Limits

🧰 Tools used, and what each one does here
• Ansible (ansible-core 2.21): nine roles, serial rollout, validate-before-write, check/diff drift detection
• OpenSSH: keys only, AllowGroups, no root, no forwarding, modern ciphers/KEX/MACs
• nftables: default-deny input, one rule per port and source, its own table
• fail2ban: SSH jail from the journal, nftables bans, longer bans for repeat offenders
• unattended-upgrades: daily security updates, no surprise reboots
• sysctl + modprobe: 34 kernel settings, 9 unused kernel modules blocked
• auditd: an audit trail of accounts, sudo, SSH, firewall, services, clock, modules and root commands
• node_exporter + Prometheus: service state and custom metrics, 9 alert rules unit-tested with promtool
• Grafana: a dashboard as code
• Lynis 3.1.7: before/after and weekly hardening index
• Molecule: every role on Ubuntu 24.04, Debian 12 and Debian 13
• GitHub Actions: static checks, Molecule, lab end-to-end with attacks, and a real-VM job

📊 Measured
• Lynis hardening index: 61 → 77 on both lab servers (61 → 73 on a real CI VM)
• Password login: accepted → rejected · root login with a valid key: accepted → rejected
• First run: 94 changes in 169 s · second run: 0 changes
• SSH brute force: banned after 2 failed logins, 7 s after the first one; alert in Prometheus after 100 s
• Drift (3 hand-made changes): all 3 found by the check, repaired with 5 changes in 51 s
• Safety nets: invalid SSH cipher, invalid firewall address and a missing admin all stopped before any change

💬 Tell me in the comments: how do you keep your servers on a baseline today?

#Ansible #LinuxSecurity #DevOps
