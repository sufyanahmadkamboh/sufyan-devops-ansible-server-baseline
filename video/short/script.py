"""The 1-minute vertical short: one entry per voiceover line (see build_short.py).

`say` is the caption; the spoken text is in voiceover/lines.json. Numbers and log lines are from
docs/test-results.md and reports/ (lab end-to-end run); the dashboard is docs/images/grafana-dashboard.png.
"""

from parts import crop, end_card, logo, term

NAME = "server-hardening-short"
HEADER = {"logo": "server-icon.svg", "topic": "Linux server hardening", "sub": "one Ansible command · measured"}
DASH = "../../docs/images/grafana-dashboard.png"

LINES = [
    {"id": "a01", "say": "A bot started guessing passwords on this server. It was banned in 7 seconds.", "sfx": "error", "body": """
<div class="stamp bad" data-at="-1">SSH BRUTE FORCE</div>
<div class="label dim" data-at="-1">🤖 BOT ATTACK ON <img class="inl" src="logos/server-icon.svg">YOUR SERVER</div>
<div class="big ok" data-at="2.6"><span data-count="7">7</span><small>s</small></div>
<div class="label ok" data-at="2.8">BANNED AUTOMATICALLY</div>"""},
    {"id": "a02", "say": "I didn't lift a finger.", "sfx": "pop", "body": """
<div class="emoji" data-at="0">🙅‍♂️</div><div class="label" data-at="0.2">0 HUMANS · 0 BUTTONS</div>"""},
    {"id": "a03", "say": "Here's the problem. A fresh Ubuntu server accepts password logins, and lets root log in with a key.",
     "sfx": "scene", "body": logo(None, "🐧 Fresh Ubuntu, defaults") + term([
         (1.2, "login methods: publickey, password", "r"),
         (2.6, "password login for ops: accepted", "r"),
         (4.0, "root login with a valid key: accepted", "r")], "reports/e2e-results.md · before")},
    {"id": "a04", "say": "Bots start guessing within minutes.", "sfx": "error", "body": """
<div class="emoji" data-at="0">🤖🤖🤖</div><div class="label bad" data-at="0.5">WITHIN MINUTES</div>"""},
    {"id": "a05", "say": "So I wrote one Ansible command that hardens any Ubuntu or Debian server.", "sfx": "chapter",
     "body": logo(None, "⚙️ Ansible") + term([(0.8, "$ make harden", "c")]) + """
<div class="title" data-at="1.8">One command.<br><span class="ok">Any server.</span></div>"""},
    {"id": "a06", "say": "SSH keys only. Never root. A firewall that blocks everything else. Automatic security updates. And an audit trail.",
     "sfx": "scene", "body": """
<div class="checks"><div class="check" data-at="0">🔑 SSH keys only</div><div class="check" data-at="1.0">🚫 never root</div>
<div class="check" data-at="1.8">🧱 default-deny firewall</div><div class="check" data-at="3.6">📦 security updates</div>
<div class="check" data-at="5.0">📝 audit trail</div></div>"""},
    {"id": "a07", "say": "Every risky file is checked before it's written, so one typo can never lock you out.", "sfx": "scene",
     "body": term([(0.3, "$ make harden   # with a typo in the SSH config", "c"),
                   (1.4, "fatal: [web-01]: FAILED! msg: failed to validate", "r"),
                   (2.4, "web-01 : ok=6  changed=0  failed=1", "y"),
                   (3.4, "→ old config kept, admin still logs in", "g")], "reports/fail-bad-sshd.log")},
    {"id": "a08", "say": "The security score jumped from 61 to 77.", "sfx": "success",
     "body": logo("grafana-icon.svg", "Grafana · real run", 0, 72) + crop(DASH, 295, 100, 500, 185, 1000, 1600) + """
<div class="tag ok" data-at="1.0">LYNIS 61 → 77</div>"""},
    {"id": "a09", "say": "Password login? Rejected. Root? Rejected.", "sfx": "pop", "body": """
<div class="label" data-at="0">🔐 PASSWORD LOGIN</div><div class="stamp bad" data-at="0.8">REJECTED</div>
<div class="label" data-at="1.6">👑 ROOT LOGIN</div><div class="stamp bad" data-at="2.1">REJECTED</div>"""},
    {"id": "a10", "say": "Brute force? Banned after two attempts, and Prometheus fires an alert.", "sfx": "error",
     "body": crop(DASH, 1000, 595, 545, 220, 1000, 1600) + """
<div class="tag bad" data-at="1.0">BANNED AFTER 2 TRIES</div>""" + logo("prometheus-icon-color.svg", "Alert fired", 3.0, 72)},
    {"id": "a11", "say": "Someone turns password login back on by hand? The same command finds it, and puts it back.",
     "sfx": "scene", "body": term([(0.6, "-PasswordAuthentication yes", "r"), (1.0, "+PasswordAuthentication no", "g"),
                                   (2.4, "DRIFT 3 setting(s) differ from the baseline.", "y"),
                                   (4.0, "$ make harden → drift check again: clean", "g")], "reports/drift-1.log")},
    {"id": "a12", "say": "Run it twice, it changes nothing. That's how you know it's safe.", "sfx": "success",
     "body": term([(0.2, "PLAY RECAP", ""), (0.6, "db-01  : ok=69  changed=0  failed=0", "g"),
                   (0.9, "web-01 : ok=69  changed=0  failed=0", "g")], "reports/harden-2.log · second run") + """
<div class="label ok" data-at="1.6">2ND RUN: 0 CHANGES</div>"""},
    {"id": "a13", "say": "The full project is free. Follow, and I'll show you how to build it.", "sfx": "outro",
     "body": end_card(["server-icon.svg", "prometheus-icon-color.svg", "grafana-icon.svg"], "Full DevSecOps project")},
]
