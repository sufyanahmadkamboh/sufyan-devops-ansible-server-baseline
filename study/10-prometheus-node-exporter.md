# 10. Prometheus and node_exporter

## What is it?

- **Prometheus** collects numbers over time (**time series**) by visiting a `/metrics` web page on each target every few seconds (**scraping**). It stores them, lets you **query** them with PromQL, and evaluates **alert rules**.
- **node_exporter** is the official program that publishes a Linux server's numbers (CPU, memory, disk, network, ...) on port 9100.

```
web-01: node_exporter :9100/metrics ◄── every 15 s ── Prometheus ──► alert rules ──► Grafana
node_cpu_seconds_total{cpu="0",mode="idle"} 1234.5
node_systemd_unit_state{name="ssh.service",state="active",type="notify"} 1
```

## Why this project uses them

Hardening once is not enough; you need to **know** it is still in place. Prometheus answers, every 15 seconds:
- Is every server reachable? (`up`)
- Is every protection running? (SSH, fail2ban, firewall, update timer, audit timer, auditd on real machines)
- What is each server's Lynis score, and how old is it?
- Is someone being banned for guessing SSH logins?

**Alternatives:** Zabbix, Nagios/Icinga (classic server monitoring), Datadog or New Relic (hosted, paid), the ELK stack for logs. Prometheus is the open-source standard and pairs naturally with Grafana.

## How it works: three ways node_exporter gets numbers

1. **Built-in collectors:** CPU, memory, filesystems, network, ...
2. **The systemd collector** (`--collector.systemd`) reads the state of chosen services over D-Bus: `node_systemd_unit_state{name="ssh.service",state="active"} 1`. That's why the `common` role installs and starts `dbus`.
3. **The textfile collector** (`--collector.textfile.directory`) publishes any `*.prom` file in a folder. This is how **non-exporter tools report metrics**:
   - `fail2ban.prom` from the fail2ban timer (chapter 5)
   - `lynis.prom` from the weekly audit (chapter 9)
   - `baseline.prom`: `server_baseline_info{kind="machine|container",os="...",version="1.0.0"} 1`

## Where it is integrated

### node_exporter, installed safely
[`roles/node_exporter/tasks/main.yml`](../roles/node_exporter/tasks/main.yml):
- downloads version **1.12.1** with `get_url` and `checksum: sha256:...` (from the official `sha256sums.txt`), **before** unpacking
- unpacks it into a versioned folder and points `/usr/local/bin/node_exporter` at it (easy upgrade and rollback)
- runs it as the unprivileged `node_exporter` user, with systemd sandboxing ([`node_exporter.service.j2`](../roles/node_exporter/templates/node_exporter.service.j2)):

```ini
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
CapabilityBoundingSet=
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX AF_NETLINK
```
Port 9100 is open only to Prometheus (chapter 4).

### Prometheus configuration
[`lab/prometheus/prometheus.yml`](../lab/prometheus/prometheus.yml) scrapes both servers and turns `web-01:9100` into a clean `instance="web-01"` label with a **relabel rule**:

```yaml
    relabel_configs:
      - source_labels: [__address__]
        regex: "([^:]+):\\d+"
        target_label: instance
        replacement: "$1"
```

### Alert rules
[`lab/prometheus/rules/server-baseline.yml`](../lab/prometheus/rules/server-baseline.yml):

| Alert | Fires when | Severity |
|---|---|---|
| `ServerDown` | `up{job="node"} == 0` for 2m | critical |
| `SecurityServiceNotRunning` | SSH, fail2ban, firewall, update timer or audit timer not active for 2m | critical |
| `AuditdNotRunning` | auditd not active **on a real machine** (`and on(instance) server_baseline_info{kind="machine"}`) | critical |
| `LynisScoreLow` | `lynis_hardening_index < 75` for 15m | warning |
| `LynisReportStale` | no audit for 8 days | warning |
| `SSHAttackerBanned` | `fail2ban_banned_current > 0` | info |
| `Fail2banNotAnswering` | `fail2ban_up == 0` for 5m | warning |
| `MetricsFileBroken` | `node_textfile_scrape_error == 1` for 10m | warning |
| `DiskAlmostFull` | less than 10% free for 10m | warning |

`for:` means "the condition must stay true this long before the alert fires", which filters out short blips. The `and on(instance)` trick joins two metrics by server: auditd is only expected where the server says it is a machine, not a container.

### Alert rules have unit tests
[`tests/prometheus/server-baseline.test.yml`](../tests/prometheus/server-baseline.test.yml) feeds **synthetic series** to `promtool test rules` and asserts which alerts fire, when, and with which text. Example: the firewall service goes down at minute 2; at minute 3 no alert (still inside `for: 2m`), at minute 5 the alert fires.

A lesson from writing these tests: series given every **1 hour** go "stale" between samples (Prometheus looks back only 5 minutes), which kept resetting the `for:` timer. The stale-report test uses 5-minute samples.

## Try it

```bash
# Open http://localhost:9090 → Status → Targets (both servers UP), then Alerts.
# Queries to paste into the Graph tab:
#   up{job="node"}
#   node_systemd_unit_state{state="active"}
#   lynis_hardening_index
#   fail2ban_banned_current
#   server_baseline_info
docker compose -f lab/compose.yaml exec web-01 curl -s localhost:9100/metrics | grep -E '^(lynis|fail2ban|server_baseline)'
make promtool        # check the rules and run their unit tests
```

## Common mistakes

- **Exposing port 9100 to the world.** Metrics reveal software versions and usage. Restrict it with the firewall.
- **Writing textfile metrics directly** to the final file: a half-written file causes scrape errors. Write and rename.
- **Alerts without `for:`** page on every blip.
- **Untested alert rules:** you find out they are wrong during an incident. Use `promtool test rules`.

## Check yourself

1. How does a shell script get its numbers into Prometheus without being an exporter?
2. Why is the auditd alert joined with `server_baseline_info{kind="machine"}`?
3. What does the relabel rule change, and why?

<details><summary>Answers</summary>

1. It writes a `*.prom` file to node_exporter's textfile directory; node_exporter publishes it with its own metrics.
2. auditd cannot run in containers. Without the join, the alert would fire forever on every lab server; with it, it fires only where auditd is expected.
3. It removes `:9100` from the `instance` label, so dashboards and alerts say `web-01` instead of `web-01:9100`.
</details>

Next: [11. Grafana](11-grafana.md)
