# 4. Firewall with nftables

## What is it?

A **firewall** decides which network packets may reach the server. **nftables** is the modern Linux firewall built into the kernel; its command is `nft`. It replaces the older `iptables`.

## Why this project uses it

Without a firewall, **every port any program opens is reachable from the internet**. The baseline turns this around: **drop everything, then allow a short list**. In the lab:
- port **22 (SSH)** from anywhere (fail2ban guards it, chapter 5)
- port **9100 (node_exporter metrics)** only from Prometheus at `172.30.0.10`

The lab test proves it: Prometheus can scrape port 9100, the attacker container cannot.

**Alternatives:** `ufw` (Ubuntu's simple front end), `firewalld` (Red Hat), cloud security groups. Cloud security groups are a good extra layer, but they don't exist on bare metal and don't protect against traffic from inside the same network. Raw nftables works the same on Debian and Ubuntu and teaches what the front ends hide.

## How it works

```
table inet server_baseline           ← a named container of rules; "inet" = IPv4 + IPv6
  chain input                         ← attached to the "input" hook: packets for this machine
    policy drop                       ← anything no rule accepts is dropped
    rule: ct state established,related accept   ← replies to connections we started
    rule: iif "lo" accept                         ← the machine talking to itself
    rule: ip saddr { 0.0.0.0/0 } tcp dport 22 accept
    rule: ip saddr { 172.30.0.10/32 } tcp dport 9100 accept
    (everything else → policy drop, logged at most 10 times a minute)
```

- **Table:** a namespace for chains. Several tables can exist side by side (fail2ban creates its own, Docker creates its own).
- **Chain with a hook:** the kernel sends packets to it at that point (input, forward, output).
- **Policy:** what happens at the end of the chain.
- **Connection tracking (`ct state`):** the kernel remembers connections, so answers to outgoing requests (updates, DNS) come back without extra rules.

### Why the baseline uses its own table and no `flush ruleset`

Many examples start with `flush ruleset`, which **deletes every rule on the machine**, including Docker's and fail2ban's. The baseline only replaces **its own table**:

```
table inet server_baseline
delete table inet server_baseline
table inet server_baseline { ... }
```
The first line creates the table if it is missing, so the delete never fails; the last line rebuilds it. All three happen in one atomic transaction.

### `nft -c`: check before applying
`nft -c -f file` parses the file **and checks it against the running kernel** without changing anything. A typo (or an impossible address like `300.1.1.1`) is rejected before it can cut off SSH.

## Where it is integrated

[`roles/firewall/templates/server-baseline.nft.j2`](../roles/firewall/templates/server-baseline.nft.j2) builds the rules from the `firewall_rules` variable:

```
{% for rule in firewall_rules %}
    # {{ rule.name }}
{% if rule.sources_v4 | default([]) | length > 0 %}
    ip saddr { {{ rule.sources_v4 | join(', ') }} } tcp dport {{ rule.port }} accept comment "{{ rule.name }}"
{% endif %}
```

The lab rules live in [`inventories/lab/group_vars/baseline.yml`](../inventories/lab/group_vars/baseline.yml):

```yaml
firewall_rules:
  - name: ssh
    port: 22
    sources_v4: ["0.0.0.0/0"]
    sources_v6: ["::/0"]
  - name: node-exporter
    port: 9100
    sources_v4: ["{{ lab_prometheus_ip }}/32"]
    sources_v6: []
```

[`roles/firewall/tasks/main.yml`](../roles/firewall/tasks/main.yml) has three safety features:
1. **Lockout guard:** fails if no rule opens the SSH port (`firewall_ssh_port`).
2. **`validate: /usr/sbin/nft -c -f %s`** on the template.
3. **A runtime check:** a systemd oneshot service stays "active" even if someone deletes the rules by hand, so the role asks the kernel directly (`nft list table inet server_baseline`) and reloads if the table is missing. This is how the drift test catches a deleted firewall.

The rules are loaded at boot by its own unit, [`server-baseline-firewall.service.j2`](../roles/firewall/templates/server-baseline-firewall.service.j2): `ExecStart`/`ExecReload` load the file, `ExecStop` deletes only this table.

`firewall_manage_forward` adds a `forward` chain with policy drop (a server is not a router). It is set to `false` on the CI VM, which also runs Docker containers that need forwarding.

## Try it

```bash
docker compose -f lab/compose.yaml exec web-01 nft list table inet server_baseline
docker compose -f lab/compose.yaml exec web-01 nft list tables           # yours, fail2ban's, others
# From the attacker: metrics port blocked (times out)
docker compose -f lab/compose.yaml exec attacker curl -m 4 http://web-01:9100/metrics
# From Prometheus' point of view: Status → Targets at http://localhost:9090 shows both servers UP
# Dropped packets are logged by the kernel:
docker compose -f lab/compose.yaml exec web-01 sh -c "journalctl -k | grep nft-baseline-drop | tail -3"
```

## Common mistakes

- **`flush ruleset`** in a firewall file on a Docker host: containers lose networking and DNS.
- **Forgetting `ct state established,related accept`:** outgoing connections never get their answers.
- **Applying a firewall over SSH without a rule for SSH.** The lockout guard blocks this.
- **Trusting `systemctl status`:** a oneshot unit says "active" even if the rules were deleted by hand. Check the kernel.

## Check yourself

1. Why does the template start with `table inet server_baseline` followed by `delete table inet server_baseline`?
2. Port 9100 is open only to `172.30.0.10/32`. What is `/32`?
3. What happens to a packet for port 8080?
4. Why is the forward chain switched off on the CI VM?

<details><summary>Answers</summary>

1. The first line creates the table if it doesn't exist, so the delete always succeeds; then the table is rebuilt. Only this table is replaced; other tables (fail2ban, Docker) are untouched.
2. A network of exactly one address: only Prometheus.
3. No rule accepts it, so the chain's `policy drop` drops it (and it may be logged as `nft-baseline-drop:`).
4. The runner also runs Docker containers whose traffic is forwarded through the host. A forward chain with policy drop would cut them off.
</details>

Next: [5. fail2ban](05-fail2ban.md)
