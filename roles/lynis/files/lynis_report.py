#!/usr/bin/env python3
"""Read a Lynis report (lynis-report.dat).

  lynis_report.py prom REPORT [--output FILE]   write Prometheus metrics for node_exporter
  lynis_report.py compare BEFORE AFTER [--host NAME]   print a before/after Markdown table

Only the Python standard library is used, so it runs on any server that runs Ansible.
"""

from __future__ import annotations

import argparse
import calendar
import os
import sys
import tempfile
import time
from dataclasses import dataclass, field

DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


@dataclass
class Finding:
    test_id: str
    text: str


@dataclass
class Report:
    lynis_version: str = "unknown"
    hardening_index: int | None = None
    tests_done: int | None = None
    finished_at: float | None = None  # unix time; Lynis writes the server's local time (UTC here)
    warnings: list[Finding] = field(default_factory=list)
    suggestions: list[Finding] = field(default_factory=list)


def _finding(value: str) -> Finding:
    # Format: TEST-ID|text|details|solution|
    parts = value.split("|")
    return Finding(test_id=parts[0].strip(), text=parts[1].strip() if len(parts) > 1 else "")


def parse_report(text: str) -> Report:
    report = Report()
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key == "lynis_version":
            report.lynis_version = value
        elif key == "hardening_index":
            report.hardening_index = int(value)
        elif key == "lynis_tests_done":
            report.tests_done = int(value)
        elif key == "report_datetime_end":
            report.finished_at = float(calendar.timegm(time.strptime(value, DATE_FORMAT)))
        elif key == "warning[]":
            report.warnings.append(_finding(value))
        elif key == "suggestion[]":
            report.suggestions.append(_finding(value))
    if report.hardening_index is None:
        raise ValueError("not a complete Lynis report: hardening_index is missing")
    return report


def to_prometheus(report: Report) -> str:
    def metric(name: str, kind: str, help_text: str, value: float, labels: str = "") -> list[str]:
        # Whole numbers are written without a decimal point or exponent (no precision loss).
        shown = str(int(value)) if float(value).is_integer() else repr(float(value))
        return [f"# HELP {name} {help_text}", f"# TYPE {name} {kind}", f"{name}{labels} {shown}"]

    version = report.lynis_version.replace("\\", "\\\\").replace('"', '\\"')
    lines: list[str] = []
    lines += metric("lynis_info", "gauge", "Lynis version that produced the last report.", 1, f'{{version="{version}"}}')
    lines += metric("lynis_hardening_index", "gauge", "Lynis hardening index (0-100, higher is better).",
                    report.hardening_index or 0)
    lines += metric("lynis_warnings", "gauge", "Warnings in the last Lynis report.", len(report.warnings))
    lines += metric("lynis_suggestions", "gauge", "Suggestions in the last Lynis report.", len(report.suggestions))
    if report.tests_done is not None:
        lines += metric("lynis_tests_done", "gauge", "Tests performed in the last Lynis run.", report.tests_done)
    if report.finished_at is not None:
        lines += metric("lynis_last_run_timestamp_seconds", "gauge", "When the last Lynis run finished (unix time).",
                        report.finished_at)
    return "\n".join(lines) + "\n"


def compare(before: Report, after: Report, host: str = "") -> str:
    def row(label: str, a: object, b: object) -> str:
        return f"| {host + ' ' if host else ''}{label} | {a} | {b} |"

    fixed = sorted({f.test_id for f in before.suggestions} - {f.test_id for f in after.suggestions})
    lines = [
        "| Measure | Before | After |",
        "|---|---|---|",
        row("Hardening index", before.hardening_index, after.hardening_index),
        row("Warnings", len(before.warnings), len(after.warnings)),
        row("Suggestions", len(before.suggestions), len(after.suggestions)),
        row("Tests performed", before.tests_done, after.tests_done),
        "",
        f"Suggestions resolved ({len(fixed)}): {', '.join(fixed) if fixed else 'none'}",
    ]
    return "\n".join(lines) + "\n"


def _write_atomic(path: str, content: str) -> None:
    # node_exporter must never read a half-written file, so write a temp file and rename it.
    directory = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=".lynis-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
        os.chmod(tmp, 0o644)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def _read(path: str) -> Report:
    with open(path, encoding="utf-8", errors="replace") as handle:
        return parse_report(handle.read())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    prom = sub.add_parser("prom", help="write Prometheus metrics")
    prom.add_argument("report")
    prom.add_argument("--output", help="file to write atomically (default: stdout)")
    cmp_ = sub.add_parser("compare", help="compare two reports")
    cmp_.add_argument("before")
    cmp_.add_argument("after")
    cmp_.add_argument("--host", default="")
    args = parser.parse_args(argv)

    try:
        if args.command == "prom":
            text = to_prometheus(_read(args.report))
            if args.output:
                _write_atomic(args.output, text)
            else:
                sys.stdout.write(text)
        else:
            sys.stdout.write(compare(_read(args.before), _read(args.after), args.host))
    except (OSError, ValueError) as err:
        print(f"lynis_report: {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
