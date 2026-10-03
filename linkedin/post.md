What happens to a brand-new Linux server in its first hour online? 🤔

Bots find it. Within minutes they start guessing passwords on SSH. And by default, Debian and Ubuntu let them try:
👉 password login is ON
👉 root can log in with a key
👉 nothing records who changed what

Most teams fix this by hand, from a checklist. Ten servers later you have ten slightly different servers, and nobody notices when someone switches password login back on "just for today".

So I built a project that treats server security like a building inspection 🏢

1️⃣ Write the security checklist once, as code (Ansible)
2️⃣ Stamp it on every server with one command
3️⃣ Run it again any time: it changes nothing if all is well, and lists anything someone changed by hand
4️⃣ A weekly inspector (Lynis) gives each server a security score, and a dashboard watches every protection 24/7

Every risky change is checked before it lands. A typo in the firewall or SSH settings is rejected, so you can't lock yourself out.

🧪 Tested on 2 fresh servers (Ubuntu 24.04 + Debian 12) in a local lab, over real SSH:
✅ Security score: 61 → 77 on both
🔐 Password login: accepted → rejected
👑 Root login with a valid key: accepted → rejected
🤖 Password-guessing "attacker": banned 7 seconds after its first attempt, alert on the dashboard 100 s later
🔁 Second run of the playbook: 0 changes
🕵️ I changed 3 settings by hand: the drift check found exactly those 3, and one command put them back

📚 New to DevOps or Linux security? I wrote a free study guide for this project. It explains every tool from zero (Linux, SSH, Ansible, firewalls, fail2ban, Prometheus, Grafana, Molecule, GitHub Actions) with 9 hands-on labs and 25 interview questions. It's also a 55-page PDF.

👉 Swipe through the slides: the problem, when to use it, the architecture, how it works, the results, and how to run it yourself with only Docker.

💻 Code + study guide: https://github.com/sufyanahmadkamboh/sufyan-devops-ansible-server-baseline
🌐 Slides + all my projects: https://sufyanahmadkamboh.github.io/#story=ansible-server-baseline&slide=1

What's the first thing YOU harden on a new server? 👇

#DevOps #Ansible #Linux #CyberSecurity #InfrastructureAsCode #ServerHardening #Prometheus #Grafana #SRE #LearningDevOps
