# 9. Lynis

## What is it?

**Lynis** is an open-source security auditing tool from CISOfy. It runs a few hundred checks on a Linux system (SSH settings, firewall, updates, kernel settings, file permissions, logging, ...) and produces:
- a **hardening index** from 0 to 100
- **warnings** (serious findings) and **suggestions** (improvements), each with a test id like `SSH-7408`
- a machine-readable report, `/var/log/lynis-report.dat`

It only **reads**; it never changes the system.

## Why this project uses it

"We hardened the servers" is an opinion. **"The Lynis hardening index went from X to Y, and these suggestions were resolved"** is a measurement made by an independent tool. Lynis gives:
1. **Before/after proof** of what the baseline achieves (see [`docs/test-results.md`](../docs/test-results.md) for the measured values).
2. **Continuous checking:** a weekly audit on every server, with the score sent to Prometheus, so a drop raises an alert.

**Alternatives:** **OpenSCAP** with CIS or DISA STIG profiles (formal compliance reports, heavier), **CIS-CAT** (commercial), cloud tools such as AWS Inspector. Lynis is light, needs no agent or server, and its score is easy to explain.

**Honest limits:** the index is a summary, not a guarantee. Some tests are skipped inside containers, and a few suggestions are deliberately not followed (for example moving SSH to another port). Compare scores from the **same Lynis version on the same kind of machine**, which is why the version is pinned.

## How it works in this project

```
roles/lynis
  ├─ downloads Lynis 3.1.7 from the official CISOfy GitHub tag, SHA-256 verified
  ├─ unpacks it to /opt/lynis-3.1.7 (owned by root: Lynis refuses files owned by others)
  ├─ installs /usr/local/sbin/server-baseline-audit:
  │     lynis audit system --quick --cronjob  →  /var/log/lynis-report.dat
  │     lynis_report.py prom                  →  /var/lib/node_exporter/textfile/lynis.prom
  └─ server-baseline-audit.timer: weekly, random delay up to 1h, catches up after downtime
```

### The report converter: `lynis_report.py`
[`roles/lynis/files/lynis_report.py`](../roles/lynis/files/lynis_report.py) is a small Python program (standard library only, so it runs on any server that runs Ansible). It has two commands:

- `prom REPORT --output FILE` writes metrics for Prometheus:
  ```
  lynis_hardening_index 0..100
  lynis_warnings / lynis_suggestions / lynis_tests_done
  lynis_last_run_timestamp_seconds
  lynis_info{version="3.1.7"} 1
  ```
  It writes to a temporary file and **renames** it, so node_exporter never reads a half-written file.
- `compare BEFORE AFTER` prints the before/after Markdown table and lists the suggestion ids that were resolved.

It has its own unit tests: [`tests/test_lynis_report.py`](../tests/test_lynis_report.py). One of them caught a real bug during development: Python's `:g` number format printed the timestamp as `1.79102e+09`, losing precision.

### Before and after
[`playbooks/audit.yml`](../playbooks/audit.yml) installs Lynis (if missing), runs the audit now, and copies each report to the controller as `reports/lynis/<host>-<label>.dat`:

```bash
scripts/audit.sh before     # on the fresh servers
make harden
scripts/audit.sh after
scripts/audit.sh compare    # the table
```

### Why GitHub and not downloads.cisofy.com?
The CISOfy download server answers **HTTP 403** to Ansible's HTTP client (it filters by user agent). Instead of pretending to be a browser, the role downloads the same release from CISOfy's official GitHub tag and pins its checksum:

```yaml
lynis_version: 3.1.7
lynis_checksum: sha256:48d829d0dc2c583a3e838cc09a7190b69a3af844bcb913c7cf9c0226b04b95c5
lynis_url: https://github.com/CISOfy/lynis/archive/refs/tags/{{ lynis_version }}.tar.gz
```

## Where it is integrated

- [`roles/lynis/`](../roles/lynis/): install, timer, wrapper, converter
- [`roles/lynis/tasks/audit.yml`](../roles/lynis/tasks/audit.yml): "run now and fetch"
- [`lab/prometheus/rules/server-baseline.yml`](../lab/prometheus/rules/server-baseline.yml): `LynisScoreLow` (below 75 for 15 min) and `LynisReportStale` (no audit for 8 days)
- Grafana: "Lynis hardening index" bar gauge and "Days since last audit"

## Try it

```bash
docker compose -f lab/compose.yaml exec web-01 /usr/local/sbin/server-baseline-audit   # about a minute
docker compose -f lab/compose.yaml exec web-01 grep -E '^(hardening_index|lynis_tests_done)=' /var/log/lynis-report.dat
docker compose -f lab/compose.yaml exec web-01 sh -c "grep '^suggestion' /var/log/lynis-report.dat | head"
docker compose -f lab/compose.yaml exec web-01 cat /var/lib/node_exporter/textfile/lynis.prom
docker compose -f lab/compose.yaml exec web-01 systemctl list-timers server-baseline-audit.timer
```

## Common mistakes

- **Chasing 100.** Some suggestions don't fit every server. Decide, document, and set a realistic target (here: 75 and above).
- **Comparing scores across Lynis versions or machine types.** Pin the version.
- **Running it once.** Security decays; the weekly timer and the stale-report alert keep it honest.
- **Using the distribution's old package** without noticing it is several versions behind.

## Check yourself

1. Does Lynis change anything on the server?
2. Why is the metrics file written to a temporary file first and then renamed?
3. Which alert tells you the weekly audit stopped running?

<details><summary>Answers</summary>

1. No. It only reads and reports; the Ansible roles make the changes.
2. A rename is atomic: node_exporter sees either the old complete file or the new complete file, never a half-written one (which would be a scrape error).
3. `LynisReportStale`: `time() - lynis_last_run_timestamp_seconds` is above 8 days.
</details>

Next: [10. Prometheus and node_exporter](10-prometheus-node-exporter.md)
