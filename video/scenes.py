"""The video: scenes, visuals and narration.

Each scene has a title, a body (HTML from components.py) and steps. A step is one narration segment; elements with
data-s=<n> appear at step n. `hl` highlights code lines (1-based, inclusive) in the scene's code panel. `tts` overrides
the spoken text when the caption spelling would be read badly (the caption always shows `say`).
Every number is from docs/test-results.md and reports/ (lab end-to-end run 2026-10-03, CI VM job) unless stated.
"""

from __future__ import annotations

from components import arrow, box, card, checklist, code, grid, label, notes, svg, terminal, tile


def S(say: str, hl: tuple[int, int] | None = None, tts: str | None = None) -> dict:
    return {"say": say, "hl": hl, "tts": tts}


REPO = "github.com/sufyanahmadkamboh/sufyan-devops-ansible-server-baseline"

SCENES: list[dict] = []


def scene(chapter: str | None, kicker: str, title: str, body: str, steps: list[dict], layout: str = "full") -> None:
    SCENES.append({"chapter": chapter, "kicker": kicker, "title": title, "body": body, "steps": steps, "layout": layout})


# ---------------------------------------------------------------- 0. Hook
scene("The question", "Linux server hardening with Ansible", "Is your new server safe the minute it boots?", svg(
    box(0, 40, 60, 470, 250, "🖥️", "Fresh Ubuntu server", ["password login: on", "root login with a key: on"], "bad", "#2a1520")
    + arrow(0, 515, 185, 640, 185, "bad")
    + box(1, 650, 60, 420, 250, "🤖", "Bots on the internet", ["guess SSH passwords", "within minutes"], "amber")
    + arrow(1, 1075, 185, 1200, 185, "bad")
    + box(2, 1210, 60, 470, 250, "🧩", "Hardened by hand", ["every server a little", "different, drift unseen"], "bad", "#2a1520")
    + box(3, 300, 430, 1120, 150, "🛡️", "This project: one command, the same baseline everywhere", ["hardened, monitored, audited, and proven by tests"], "ok", "#0f2a22")
    + label(4, 860, 660, "Lynis 61 → 77 · password login rejected · brute force banned in 7 s", 34, "ok", "middle", 900)
), [
    S("You install a fresh Ubuntu or Debian server. Out of the box, it accepts password logins, and it lets root log in with a key."),
    S("Bots start guessing SSH passwords on internet facing servers within minutes of them coming online."),
    S("And when teams harden servers by hand from a checklist, every server ends up a little different, and nobody notices when someone quietly switches password login back on."),
    S("In this video I will show you a project that fixes all of that with one Ansible command: the same security baseline on every server, with monitoring and an audit score."),
    S("And everything is measured. The Lynis hardening score goes from 61 to 77, password logins are rejected, and a brute force attacker is banned in seven seconds. The code and a free study guide are linked in the description."),
])

# ---------------------------------------------------------------- 1. Map
scene(None, "What you will learn", "One playbook, nine roles, one goal", grid([
    card(0, "⚠️", "The problem", "why fresh servers are not safe", "bad"),
    card(0, "💡", "The idea", "a baseline as code, safe and repeatable", "amber"),
    card(1, "🗺️", "Architecture + lab", "controller, two servers, an attacker"),
    card(2, "🔑", "SSH hardening", "keys only, no root, modern crypto"),
    card(2, "🧱", "nftables firewall", "default deny, own table"),
    card(2, "🚫", "fail2ban", "ban password guessers"),
    card(2, "⚙️", "Kernel + updates + auditd", "sysctl, modules, audit trail"),
    card(3, "🛟", "Safety nets", "never lock yourself out"),
    card(3, "📊", "Prometheus + Grafana + Lynis", "watch every protection"),
    card(4, "🧪", "Molecule + e2e + real VM", "proof on every push"),
    card(4, "💻", "Run it yourself", "the whole lab on your laptop"),
    card(4, "🏭", "Production rollout", "check, canary, then everyone", "ok"),
], 3, 22), [
    S("Here is the plan. First, why a fresh server is not safe, and the idea behind the fix."),
    S("Then the architecture, and the lab: a controller, two servers and an attacker, all in Docker."),
    S("Then the roles, one by one: SSH, the firewall, fail2ban, the kernel, automatic updates and the audit trail."),
    S("Next, the safety nets that make sure the automation can never lock you out, and the monitoring with Prometheus, Grafana and Lynis."),
    S("And finally the tests that prove it on every push, how to run the whole lab on your own laptop, and how to roll it out to real servers."),
])

# ---------------------------------------------------------------- 2. Problem
scene("The problem", "Why this matters", "A new server is not secure by default", notes([
    (0, "🔓 Password logins are on", "Debian and Ubuntu install OpenSSH with password login switched on, and root may log in with a key."),
    (1, "🌐 The firewall is open", "Every port a service opens is reachable, and nothing records who changed what."),
    (2, "📋 Hardening by hand does not repeat", "Ten servers hardened from a checklist become ten different servers."),
    (3, "👻 Drift is invisible", "A quick fix stays forever, and nobody knows the baseline is broken."),
    (4, "🔒 One typo can lock you out", "A bad sshd_config or firewall rule cuts off the only way in."),
    (5, "❓ \"Is it secure?\" has no number", "Without an audit score you cannot show progress or catch a regression."),
]), [
    S("Let us start with the problem. Debian and Ubuntu install OpenSSH with password logins switched on, and they allow root to log in with a key."),
    S("The firewall is open, so every port a service opens is reachable. And nothing records who changed what."),
    S("Hardening is usually done by hand, from a checklist. So ten servers hardened by hand become ten slightly different servers."),
    S("Then drift sets in. Someone temporarily switches password login back on to debug something, and it stays that way forever."),
    S("And hardening itself is risky. One typo in the SSH config or one wrong firewall rule, and you have cut off the only way into the server."),
    S("Finally, if someone asks: is this server secure? Without an audit score, there is no number to show, and no way to catch a regression."),
])

# ---------------------------------------------------------------- 3. Idea
scene("The idea", "The idea", "A security baseline as code", checklist([
    (0, "1", "One command, any number of servers", "the same baseline on Debian and Ubuntu"),
    (1, "2", "Safe", "validated before it is written, guarded against lockout"),
    (2, "3", "Idempotent", "a second run changes nothing, so a re-run is a drift report or a repair"),
    (3, "4", "Measured", "Lynis before and after, and every week"),
    (4, "5", "Monitored and proven", "alerts on every protection; tests with real attacks on every push"),
]), [
    S("Here is the idea: write the security baseline as code, with Ansible, and apply it to any number of servers with one command."),
    S("Every change must be safe. Risky files are validated by the program that will read them before they are written, and guards stop the run before anything could lock you out."),
    S("The playbook is idempotent: running it again changes nothing. That gives you two things for free. In check mode, a re-run is a drift report. In normal mode, it is the repair."),
    S("The result is measured with Lynis, an open source audit tool, before and after, and then every week."),
    S("And the protections themselves are monitored, with alerts, and proven by tests that attack the servers on every push."),
])

# ---------------------------------------------------------------- 4. Architecture
scene("Architecture", "Architecture", "From one command to a hardened, watched server", svg(
    box(0, 30, 40, 420, 210, "🧑‍💻", "You", ["make harden", "(or ansible-playbook)"], "blue")
    + arrow(0, 455, 145, 560, 145)
    + box(0, 570, 40, 470, 210, "🎛️", "Controller", ["pinned toolbox image:", "Ansible, Molecule, linters"], "sky")
    + arrow(1, 1045, 110, 1180, 80, "ok", label="SSH, key only")
    + arrow(1, 1045, 180, 1180, 230, "ok")
    + box(1, 1190, 20, 500, 150, "🐧", "web-01 · Ubuntu 24.04", ["hardened by 9 roles"], "ok", "#0f2a22")
    + box(1, 1190, 190, 500, 150, "🐧", "db-01 · Debian 12", ["hardened by 9 roles"], "ok", "#0f2a22")
    + box(2, 1190, 420, 500, 170, "🦹", "Attacker", ["brute force and port probes", "(tests only)"], "bad", "#2a1520")
    + arrow(2, 1440, 415, 1440, 345, "bad")
    + box(3, 570, 420, 470, 170, "📈", "Prometheus", ["scrapes :9100 every 15 s", "9 alert rules"], "amber")
    + arrow(3, 1045, 505, 1185, 300, "sky", True)
    + box(3, 30, 420, 420, 170, "📊", "Grafana", ["dashboard as code"], "violet")
    + arrow(3, 565, 505, 455, 505)
    + label(4, 860, 680, "every server: sshd · nftables · fail2ban · auto updates · sysctl · auditd · node_exporter · weekly Lynis", 25, "sky", "middle", 800)
), [
    S("Here is the architecture. You run one command, make harden, or the Ansible playbook directly."),
    S("A controller container runs Ansible, and connects to the servers over SSH, with a key. In the lab there are two servers: web-01 on Ubuntu 24.04 and db-01 on Debian 12."),
    S("An attacker container sits on the same network. The tests use it for SSH brute force and port probes."),
    S("Prometheus scrapes every server's node exporter on port 9100 every fifteen seconds, and evaluates nine alert rules. Grafana shows it all on one dashboard."),
    S("After the run, every server has the same set of protections: hardened SSH, an nftables firewall, fail2ban, automatic updates, kernel settings, an audit trail, metrics, and a weekly Lynis audit."),
])

# ---------------------------------------------------------------- 5. Playbook
SITE = """- name: Apply the server baseline
  hosts: baseline
  become: true
  serial: "{{ baseline_serial | default(1) }}"
  max_fail_percentage: 0

  roles:
    - common
    - kernel_hardening
    - ssh_hardening
    - firewall
    - fail2ban
    - auto_updates
    - auditd
    - node_exporter
    - lynis

  post_tasks:
    - ansible.builtin.meta: flush_handlers
    - ansible.builtin.meta: reset_connection
    - ansible.builtin.wait_for_connection:
        timeout: 60"""
scene("The playbook", "Ansible", "One playbook, nine roles, in a fixed order", code("playbooks/site.yml (shortened)", SITE, "yaml", 21) + notes([
    (1, "serial: 1", "one server at a time; the first failure stops the rollout"),
    (2, "Nine roles", "each control is its own role, in a safe order"),
    (3, "Prove access", "a brand-new SSH connection at the end"),
]), [
    S("Ansible is an agentless configuration tool. It connects over SSH, and its modules only change what differs from the desired state. This is the main playbook."),
    S("Serial one means one server at a time, and max fail percentage zero means the first failure stops the rollout. A mistake hits one server, not the whole fleet.", (4, 5)),
    S("Then nine roles, in a fixed order. Each security control is its own role, with its own defaults, templates, and its own verify tasks.", (7, 16)),
    S("At the end, it applies pending service changes, throws away the existing SSH connection, and opens a brand new one. If the new SSH or firewall settings had locked us out, the run fails right here.", (18, 22)),
], "code")

# ---------------------------------------------------------------- 6. common + kernel
scene("The roles", "Roles 1 and 2", "Admins, then the kernel", grid([
    card(0, "👤", "common", "admins with SSH keys only; other keys removed; sudo; banners; umask 027; no core dumps; persistent journal; no telnet or rsh"),
    card(1, "🛑", "Lockout guard", "the run stops if no admin with a key is defined", "bad"),
    card(2, "🧠", "kernel_hardening", "34 sysctl settings persisted and applied; 9 rarely used kernel modules blocked"),
    card(3, "🔍", "Read, compare, write", "only values that differ are written, so changed means drifted", "amber"),
], 2, 26), [
    S("Role one, common, creates the administrators. They log in with SSH keys only, and any other keys are removed. It also sets up sudo, login banners, a strict umask, no core dumps, and a persistent journal."),
    S("This role has the first safety net. If no administrator with an SSH key is defined, the run stops right there, before SSH is touched."),
    S("Role two hardens the kernel: 34 sysctl settings, for example ignoring ICMP redirects, persisted to a file and applied live. And nine rarely used kernel modules are blocked."),
    S("One design detail: the role reads the running values first, and writes only the ones that differ. So when this role reports changed, it really means something drifted."),
])

# ---------------------------------------------------------------- 7. SSH
SSHD = """# Who and how: named groups only, SSH keys only, never root.
AllowGroups {{ ssh_hardening_allow_groups | join(' ') }}
PermitRootLogin no
AuthenticationMethods publickey
PasswordAuthentication no
KbdInteractiveAuthentication no

# No tunnels or forwarding.
AllowTcpForwarding no
AllowAgentForwarding no
X11Forwarding no

# Modern cryptography only.
KexAlgorithms {{ ssh_hardening_kex_algorithms | join(',') }}
Ciphers {{ ssh_hardening_ciphers | join(',') }}
MACs {{ ssh_hardening_macs | join(',') }}
LogLevel VERBOSE"""
SSHTASK = """- template:
    src: sshd-baseline.conf.j2
    dest: /etc/ssh/sshd_config.d/
          00-server-baseline.conf
    validate: sshd -t -f %s
  notify: Reload sshd"""
scene(None, "Role 3 · ssh_hardening", "SSH: keys only, never root", code("roles/ssh_hardening/templates/sshd-baseline.conf.j2 (excerpt)", SSHD, "text", 21)
      + f'<div class="st" data-s="3">{code("ssh_hardening/tasks/main.yml", SSHTASK, "yaml", 20)}</div>', [
    S("Role three is SSH. Only members of the ssh users group may log in, root may never log in, and the only accepted method is a public key. Password and keyboard interactive logins are off.", (1, 6)),
    S("Tunnels and forwarding are switched off, so a login is a shell, not a network path into the server.", (8, 11)),
    S("Only modern key exchange, ciphers and MACs are allowed, weak Diffie Hellman groups are removed, and verbose logging records the key fingerprint of every login.", (13, 17)),
    S("Two details matter. The file is a drop in named zero zero, because sshd uses the first value it reads, so cloud init cannot override it. And validate runs sshd dash t on the new file first. If the check fails, the old config stays in place.", (1, 17)),
], "code")

# ---------------------------------------------------------------- 8. Firewall
NFT = """table inet {{ firewall_table }} {
  chain input {
    type filter hook input priority filter; policy drop;

    ct state invalid drop
    ct state established,related accept
    iif "lo" accept

{% for rule in firewall_rules %}
    ip saddr { {{ rule.sources_v4 | join(', ') }} } tcp dport {{ rule.port }} accept
{% endfor %}
  }
}"""
scene(None, "Role 4 · firewall", "nftables: drop everything, allow by name", code("roles/firewall/templates/server-baseline.nft.j2 (shortened)", NFT, "text", 22) + notes([
    (0, "policy drop", "anything not allowed is dropped"),
    (1, "One rule per port and source", "e.g. 9100 only from Prometheus"),
    (2, "Its own table", "Docker and fail2ban tables stay untouched"),
    (3, "nft -c first", "and a guard: no SSH rule, no run"),
]), [
    S("Role four is the firewall, with nftables, the modern Linux firewall. The input chain has a default policy of drop: anything that is not explicitly allowed is dropped.", (1, 3)),
    S("Then one rule per allowed port and source. For example, port 9100, the metrics port, is only open to the Prometheus server.", (9, 11)),
    S("The project uses its own table, and never flushes the whole rule set. That way the tables of Docker, fail2ban or Kubernetes stay untouched.", (1, 1)),
    S("And again, two safety nets. The new rules are checked with nft dash c before they are loaded. And if the rule list has no rule for SSH, the run stops before the firewall is touched."),
], "code")

# ---------------------------------------------------------------- 9. fail2ban
JAIL = """[DEFAULT]
ignoreip = {{ (fail2ban_ignoreip + fail2ban_ignoreip_extra) | join(' ') }}
bantime = {{ fail2ban_bantime }}
findtime = {{ fail2ban_findtime }}
maxretry = {{ fail2ban_maxretry }}
bantime.increment = true
banaction = nftables[type=multiport]

[sshd]
enabled = true
backend = systemd
mode = aggressive"""
scene(None, "Role 5 · fail2ban", "fail2ban: ban the password guessers", code("roles/fail2ban/templates/jail.local.j2 (excerpt)", JAIL, "ini", 22) + notes([
    (0, "Reads the journal", "failed SSH logins, from systemd"),
    (1, "Bans in nftables", "its own table, next to the baseline"),
    (2, "Repeat offenders", "longer bans, up to one week"),
    (3, "Never ban the controller", "ignoreip keeps Ansible connected"),
]), [
    S("Role five is fail2ban. It reads failed SSH logins from the systemd journal. In aggressive mode it also counts scanners that never even try a key or a password.", (9, 12)),
    S("After too many failures, the address is banned, in fail2ban's own nftables table, next to the baseline table.", (7, 7)),
    S("Repeat offenders get longer and longer bans, up to one week.", (3, 6)),
    S("And the Ansible controller is on the ignore list, so a ban can never cut off your automation. A small timer also exports the ban counters for Prometheus.", (2, 2)),
], "code")

# ---------------------------------------------------------------- 10. updates, auditd, metrics, lynis
scene(None, "Roles 6 to 9", "Updates, audit trail, metrics and a score", grid([
    card(0, "📦", "auto_updates", "daily security updates with unattended-upgrades; no surprise reboots"),
    card(1, "📝", "auditd", "records changes to accounts, sudo, SSH, the firewall, services, the clock, kernel modules and root commands"),
    card(2, "📡", "node_exporter 1.12.1", "pinned and checksum verified, sandboxed; systemd and textfile collectors"),
    card(3, "🏅", "Lynis 3.1.7", "pinned, weekly audit timer; score exported as lynis_hardening_index", "ok"),
], 2, 26), [
    S("Role six turns on daily security updates with unattended upgrades. Reboots are not automatic by default: a reboot should be a decision."),
    S("Role seven is auditd, the kernel audit trail. It records changes to accounts, sudo, the SSH settings, the firewall, services, the clock and kernel modules, and every command run as root by a logged in user."),
    S("Role eight installs node exporter, pinned and checksum verified, in a sandboxed systemd unit. It exports the state of every security service, and custom metrics from small text files."),
    S("And role nine installs Lynis 3.1.7, also pinned and checksum verified. A weekly timer runs the audit, and a small Python script turns the report into a Prometheus metric: the hardening index."),
])

# ---------------------------------------------------------------- 11. Safety nets
scene("Safety nets", "Never lock yourself out", "Four safety nets, in the order they act", checklist([
    (0, "1", "Guards", "stop if no admin key exists, the SSH groups are empty, or the firewall has no SSH rule"),
    (1, "2", "Validate before write", "sshd -t, nft -c and visudo -cf check every risky file; a failure keeps the old one"),
    (2, "3", "One server at a time", "serial: 1 with max_fail_percentage: 0"),
    (3, "4", "Prove access", "a brand-new SSH connection at the end of the run"),
]), [
    S("Automation that changes SSH and the firewall can lock you out of every server at once. So this project has four safety nets. First, the guards: the run stops if no admin key exists, if the allowed SSH groups are empty, or if the firewall has no SSH rule."),
    S("Second, validate before write. Every risky file is checked by the program that will read it: sshd dash t, nft dash c, and visudo. If the check fails, the old file stays in place."),
    S("Third, one server at a time. If something goes wrong, it stops after the first server."),
    S("And fourth, the access proof: a brand new SSH connection at the end shows that the admin can still get in."),
])

scene(None, "Safety nets, tested", "Each mistake must stop before changing anything", terminal([
    (0, "$ make harden   # with an unknown SSH cipher in the config", "cmd"),
    (0, "TASK [ssh_hardening : Install the hardened SSH settings]", ""),
    (0, "fatal: [web-01]: FAILED! =>", "bad"),
    (0, "    msg: failed to validate", "bad"),
    (0, "    stderr: ... line 40: Bad SSH2 cipher spec 'no-such-cipher'.", "bad"),
    (0, "web-01  : ok=6  changed=0  unreachable=0  failed=1", "warn"),
    (1, "# invalid firewall address 300.1.1.1/32  ->  rejected by nft -c, old rules stay active", "dim"),
    (2, "# no admin user defined  ->  stopped by the lockout guard before SSH is touched", "dim"),
    (3, "# after all three: admin login works, and the drift check is clean (nothing changed)", "ok"),
], "reports/fail-bad-sshd.log (excerpt)"), [
    S("And the end to end test makes these mistakes on purpose. Here is a run with an unknown SSH cipher. sshd dash t rejects the file, the task fails, and changed is zero."),
    S("An invalid firewall address, three hundred dot one dot one dot one, is rejected by nft dash c, and the old rules stay active."),
    S("And with no administrator defined, the lockout guard stops the run before SSH is touched."),
    S("After all three failed runs, the admin can still log in, and a drift check confirms that nothing was changed."),
])

# ---------------------------------------------------------------- 12. Results: logins
scene("Measured results", "Before and after", "What the servers allow", svg(
    box(0, 40, 40, 780, 300, "🔓", "Before (distribution defaults)", ["login methods: publickey, password", "password login for ops: accepted", "root login with a valid key: accepted", "metrics port: not installed"], "bad", "#2a1520")
    + arrow(1, 830, 190, 900, 190, "ok")
    + box(1, 910, 40, 780, 300, "🔒", "After the baseline", ["login methods: publickey", "password login: rejected", "root login with a valid key: rejected", "port 9100 from the attacker: blocked"], "ok", "#0f2a22")
    + box(2, 40, 420, 1650, 150, "🧑‍🔧", "And the admin?", ["admin login with key: accepted · Prometheus still scrapes both servers through the firewall"], "sky")
), [
    S("So what does the baseline change? Here are the measured results from the lab, on both servers. Before, with distribution defaults, the servers offered password login, accepted the correct password, and let root log in with a valid key."),
    S("After the baseline, the only login method offered is public key. The correct password is rejected, root is rejected even with a valid key, and the metrics port is blocked for the attacker."),
    S("And the admin still logs in with a key, and Prometheus still scrapes both servers through the firewall."),
])

scene(None, "Lynis 3.1.7", "The audit score: 61 → 77", grid([
    tile(0, "🐧", "web-01 hardening index", "61 → 77", "ok", "Ubuntu 24.04"),
    tile(0, "🐧", "db-01 hardening index", "61 → 77", "ok", "Debian 12"),
    tile(1, "💡", "Suggestions (web-01)", "44 → 26", "amber", "18 fewer"),
    tile(2, "🖥️", "Real VM (CI)", "61 → 73", "sky", "GitHub-hosted Ubuntu 24.04"),
], 4, 22), [
    S("Lynis gives every server a hardening index. Both lab servers went from 61 to 77, and the same result came from three separate clean runs."),
    S("On web-01, the number of Lynis suggestions dropped from 44 to 26. Many of the remaining ones come from the container environment, or from choices left to you, like separate partitions or a mail relay."),
    S("On a real virtual machine in CI, the score went from 61 to 73. A score is a direction, not a certificate, but it shows progress, and an alert fires if it ever drops below 75 in the lab."),
])

scene(None, "Idempotence", "The second run changes nothing", terminal([
    (0, "$ make harden          # first run, one server at a time", "cmd"),
    (0, "94 changes in 169 s", "ok"),
    (1, "$ make harden          # second run", "cmd"),
    (1, "PLAY RECAP", ""),
    (1, "db-01   : ok=69   changed=0   unreachable=0   failed=0   skipped=8", "ok"),
    (1, "web-01  : ok=69   changed=0   unreachable=0   failed=0   skipped=8", "ok"),
    (2, "$ make verify          # every control, on both servers: passed in 26 s", "ok"),
], "reports/harden-2.log (recap)"), [
    S("The first run made 94 changes in 169 seconds, one server at a time."),
    S("The second run made zero changes on both servers. That is idempotence, and it is what makes drift detection possible."),
    S("Then the verify playbook checks every single control on both servers. It passed in 26 seconds."),
])

# ---------------------------------------------------------------- 13. Attack
scene(None, "Attack", "SSH brute force from the attacker", grid([
    tile(0, "🔢", "Failed logins until ban", "2", "ok", "aggressive mode counts twice"),
    tile(1, "⏱️", "First attempt → ban", "7 s", "ok", "3 to 7 s across runs"),
    tile(2, "🚧", "SSH from the banned address", "blocked", "ok", "fail2ban's nftables table"),
    tile(2, "🎛️", "Ansible controller", "connects", "sky", "on the ignore list"),
    tile(3, "🚨", "SSHAttackerBanned alert", "100 s", "amber", "32 to 100 s across runs"),
    tile(3, "⌛", "Ban length", "3600 s", "sky", "longer for repeat offenders"),
], 3, 22), [
    S("Now the attack. The attacker container tries to log in to db-01 with wrong passwords. It was banned after two failed logins, because in aggressive mode one connection counts twice."),
    S("The ban came seven seconds after the first attempt. Across the runs, it was between three and seven seconds."),
    S("From then on, SSH from that address is blocked. But the Ansible controller still connects, because it is on the ignore list."),
    S("And the SSH attacker banned alert fired in Prometheus 100 seconds after the attack started. That delay depends on the one minute timer that exports the ban counter. The ban lasts one hour."),
])

# ---------------------------------------------------------------- 14. Drift
scene(None, "Drift", "Someone changes a server by hand", terminal([
    (0, "# on web-01: password login re-enabled, firewall table deleted, ICMP redirects accepted", "dim"),
    (1, "$ make drift          # ansible-playbook site.yml --check --diff", "cmd"),
    (1, "--- before: /etc/ssh/sshd_config.d/00-server-baseline.conf", ""),
    (1, "-PasswordAuthentication yes", "bad"),
    (1, "+PasswordAuthentication no", "ok"),
    (2, "Drifted settings (server | task):", ""),
    (2, "  web-01 | kernel_hardening : Report kernel values that differ (check mode)", "warn"),
    (2, "  web-01 | ssh_hardening : Install the hardened SSH settings", "warn"),
    (2, "  web-01 | firewall : Check that the rules are really loaded", "warn"),
    (2, "DRIFT 3 setting(s) differ from the baseline.          (exit code 2)", "warn"),
    (3, "$ make harden --limit web-01   ->  5 changes in 51 s;  drift check again: clean", "ok"),
], "reports/drift-1.log"), [
    S("What about drift? The test makes three changes by hand on web-01: password login back on, the firewall table deleted, and ICMP redirects accepted."),
    S("Then it runs the drift check. That is the same playbook, in check and diff mode, so it changes nothing. It shows the exact line: password authentication yes, instead of no."),
    S("It lists exactly the three settings that drifted, and exits with code two, so a scheduler or CI job can alert on it. And because check mode is read only, the firewall is still deleted afterwards."),
    S("Running the playbook again on web-01 restored everything: five changes in 51 seconds. And the next drift check was clean."),
])

# ---------------------------------------------------------------- 15. Monitoring
scene("Monitoring", "Prometheus + Grafana", "Watch the protections themselves",
      '<img class="shot st" data-s="0" src="../../docs/images/grafana-dashboard.png" alt="Grafana dashboard">', [
    S("Hardening is not a one time event, so the protections are monitored. This is the Grafana dashboard, provisioned from a JSON file in git, at the end of a real lab run."),
    S("It shows the Lynis score per server, banned addresses, firing alerts, days since the last audit, every security service per server, the baseline version, and fail2ban activity, CPU, memory and network."),
])

RULES = """- alert: LynisScoreLow
  expr: lynis_hardening_index < 75
  for: 15m

- alert: SSHAttackerBanned
  expr: fail2ban_banned_current > 0

- alert: Fail2banNotAnswering
  expr: fail2ban_up == 0
  for: 5m"""
scene(None, "Alert rules", "Nine alert rules, each with a unit test", code("lab/prometheus/rules/server-baseline.yml (excerpt)", RULES, "yaml", 24) + notes([
    (0, "Availability", "ServerDown"),
    (1, "Protections", "SecurityServiceNotRunning · AuditdNotRunning · Fail2banNotAnswering"),
    (2, "Audit", "LynisScoreLow (below 75) · LynisReportStale (over 8 days)"),
    (3, "Attacks + housekeeping", "SSHAttackerBanned · MetricsFileBroken · DiskAlmostFull"),
]), [
    S("Prometheus evaluates nine alert rules. Server down covers availability."),
    S("Three rules watch the protections themselves: a security service that stopped, auditd not running, and fail2ban not answering.", (8, 10)),
    S("Two rules watch the audit: the score dropping below 75, and a report older than eight days, which means the weekly timer did not run.", (1, 3)),
    S("And the rest cover attacks and housekeeping. Every rule has a unit test that runs with prom tool in CI.", (5, 6)),
], "code")

# ---------------------------------------------------------------- 16. Testing
scene("Testing", "Proof on every push", "Four test layers in GitHub Actions", checklist([
    (0, "1", "Static", "yamllint, ansible-lint (production profile, 0 failures), ShellCheck, 7 pytest tests, promtool rule tests"),
    (1, "2", "Molecule", "every role on Ubuntu 24.04, Debian 12, Debian 13: converge → idempotence (0 changes) → verify (44 checks)"),
    (2, "3", "Lab end-to-end", "real SSH: logins, Lynis, brute force, drift, safety nets, monitoring (823 s, all checks passed)"),
    (3, "4", "Real VM", "what containers cannot test: all 34 kernel settings live, audit rules loaded, 0 changes on the 2nd run"),
]), [
    S("All of this runs in GitHub Actions on every push, in four layers. First, static checks: yamllint, ansible lint with the production profile, ShellCheck, seven pytest tests, and the alert rule tests."),
    S("Second, Molecule. It runs every role on three distributions, Ubuntu 24.04, Debian 12 and Debian 13, in systemd containers. The second run must change nothing, and 44 verify checks must pass. Locally the whole Molecule test took 430 seconds."),
    S("Third, the lab end to end test, with real SSH and real attacks: everything you saw in the results. The final clean run took 823 seconds, and every check passed."),
    S("And fourth, a real virtual machine. Containers cannot load audit rules or most kernel settings, so a CI job applies the baseline to the runner itself: 50 changes in 121 seconds, then zero changes, with all 34 kernel settings live and every audit rule loaded."),
])

scene(None, "Honest findings", "What the tests found", notes([
    (0, "pytest", "the metric writer printed the Lynis timestamp as 1.79102e+09, losing precision"),
    (1, "Molecule", "downloads.cisofy.com answers 403 to Ansible: pinned GitHub release + SHA-256 instead"),
    (2, "End-to-end", "the unban check itself was counted as a failed login: check the nftables ban set instead"),
    (3, "Real VM", "auditd running and every rule loaded, but the runner's kernel emitted no audit records at all"),
]), [
    S("And the tests found real bugs. The unit tests caught that the metric writer printed the Lynis timestamp in scientific notation, losing precision. Whole numbers are now written as integers."),
    S("Molecule found that the Lynis download site answers 403 to Ansible. The project now downloads a pinned GitHub release, verified by its SHA 256 checksum."),
    S("The end to end test found that its own unban check, which sent an SSH probe, was counted as another failed login. It now checks the nftables ban set instead."),
    S("And one honest limit. On GitHub hosted runners, auditd was running and every rule was loaded, but the kernel produced no audit records at all, for any rule. The test reports this as not verifiable here, instead of hiding it, and you should confirm it once on a real server."),
])

# ---------------------------------------------------------------- 17. Run it yourself
scene("Run it yourself", "Hands-on lab", "The whole lab on your laptop", terminal([
    (0, f"$ git clone https://{REPO}.git", "cmd"),
    (0, "$ cd sufyan-devops-ansible-server-baseline", "cmd"),
    (1, "$ make lab-up              # two fresh servers, attacker, Prometheus, Grafana", "cmd"),
    (2, "$ make audit LABEL=before  # Lynis score of the untouched servers", "cmd"),
    (2, "$ make harden              # apply the baseline, one server at a time", "cmd"),
    (2, "$ make audit LABEL=after", "cmd"),
    (3, "$ make compare             # before/after table", "cmd"),
    (3, "$ make verify              # check every control", "cmd"),
    (3, "$ make drift               # what differs from the baseline? (changes nothing)", "cmd"),
    (4, "Grafana: http://localhost:3000     Prometheus: http://localhost:9090", "ok"),
], "your terminal"), [
    S("Now let us make it practical. You need Docker with Compose, and a Bash terminal. Git Bash on Windows works, and about three gigabytes of disk space. Clone the repository and go into the folder."),
    S("Make lab up creates two fresh servers, web-01 on Ubuntu and db-01 on Debian, plus the attacker, Prometheus and Grafana. Ansible, Molecule and the linters are all inside a pinned controller image, so you do not install anything else."),
    S("Then measure the untouched servers with make audit, apply the baseline with make harden, and measure again."),
    S("Make compare shows the before and after table, make verify checks every control, and make drift shows anything that differs from the baseline."),
    S("Grafana runs on localhost port 3000, and Prometheus on port 9090. To run the whole proof from scratch, with the attacks, run make e2e. It takes about ten minutes, and make lab down removes everything again."),
])

scene(None, "Practice", "Break it, then let the baseline fix it", checklist([
    (0, "1", "Try to log in with a password", "ssh with the password from the lab: rejected"),
    (1, "2", "Brute force from the attacker", "watch the ban, then the SSHAttackerBanned alert"),
    (2, "3", "Change a setting by hand", "make drift finds it; make harden repairs it"),
    (3, "4", "Make a mistake on purpose", "an invalid cipher or firewall address: the run stops safely"),
]), [
    S("Once the lab is up, practice like an attacker and like an operator. Try to log in with a password, and see it rejected."),
    S("Run a brute force from the attacker container, and watch fail2ban ban it, and the alert appear in Prometheus."),
    S("Change a setting by hand on one of the servers, then let make drift find it, and make harden repair it."),
    S("And make a mistake on purpose, like an invalid cipher or firewall address, and see the safety nets stop the run. The study guide has nine hands-on labs, step by step."),
])

# ---------------------------------------------------------------- 18. Production
scene("Production rollout", "Real servers", "From the lab to your own servers", checklist([
    (0, "1", "Copy the inventory", "inventories/lab → inventories/<env>; set ansible_user, admins, firewall rules"),
    (1, "2", "Preview", "ansible-playbook … site.yml --check --diff: nothing changes"),
    (2, "3", "Canary", "--limit <one-host>, then check that you can still log in"),
    (3, "4", "Everyone", "the rest of the fleet, one server at a time (serial: 1)"),
    (4, "5", "Keep it true", "a scheduled drift check, the weekly Lynis score, and the alerts"),
]), [
    S("How do you use this on real servers? Copy the lab inventory to a new folder for your environment, and set three things: the SSH user, your administrators with their public keys, and the firewall rules."),
    S("Then preview. Run the playbook in check and diff mode. It changes nothing, and shows you exactly what it would change."),
    S("Then a canary: apply it to one host with limit, and check that you can still log in."),
    S("Then the rest of the fleet, one server at a time."),
    S("And keep it true: run the drift check on a schedule, watch the weekly Lynis score, and route the alerts to your team."),
])

scene("Limits", "Honest limits", "What this does not do", notes([
    (0, "Debian and Ubuntu only", "apt and Debian service names; RHEL/Rocky is a future step"),
    (1, "Lab, not cloud", "containers and a CI VM stand in for real servers"),
    (2, "Lynis is a heuristic", "the score shows direction, not compliance"),
    (3, "Next steps", "CIS mapping, Alertmanager routing, TLS for node_exporter, SSH certificates"),
]), [
    S("Let us be honest about the limits. It supports Debian and Ubuntu only."),
    S("Containers and a CI virtual machine stand in for real cloud servers, and containers cannot load audit rules or most kernel settings. That is why the VM job exists."),
    S("Lynis is a heuristic, not a compliance certificate. The score shows direction, not that a server is secure."),
    S("And next on the list: mapping every task to the CIS benchmark, alert routing with Alertmanager, TLS for node exporter, and SSH certificates instead of individual keys."),
])

scene(None, "Thanks for watching", "One command, a hardened and watched server", svg(
    box(0, 160, 60, 1400, 170, "🛡️", "The baseline", ["keys only · no root · default-deny firewall · bans · updates · kernel · audit trail"], "ok", "#0f2a22")
    + box(1, 160, 270 + 20, 1400, 170, "📚", "Code + free study guide + PDF", [f"{REPO}"], "sky")
    + box(2, 160, 500, 1400, 170, "💬", "Your turn", ["how do you keep your servers on the baseline? tell me in the comments"], "amber")
), [
    S("That is the project. One command turns a fresh server into a hardened, monitored and audited server, and the same command finds and repairs drift."),
    S("The code, the documentation and a free study guide, with nine labs and 25 interview questions, are linked in the description. Clone it, run make lab up, and attack your own servers."),
    S("Now I would like to hear from you: how do you keep your servers on a baseline today? Tell me in the comments. And if this helped, subscribe for more real DevOps projects. Thanks for watching."),
])
