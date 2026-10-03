import importlib.util
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("lynis_report", ROOT / "roles/lynis/files/lynis_report.py")
lynis_report = importlib.util.module_from_spec(spec)
sys.modules["lynis_report"] = lynis_report  # dataclasses look the module up by name
spec.loader.exec_module(lynis_report)

BEFORE = """# Lynis Report
report_version_major=1
lynis_version=3.1.7
report_datetime_start=2026-10-03 10:00:00
hardening_index=58
lynis_tests_done=240
warning[]=FIRE-4512|iptables module(s) loaded, but no rules active|-|-|
suggestion[]=SSH-7408|Consider hardening SSH configuration|AllowTcpForwarding (set YES to NO)|-|
suggestion[]=SSH-7408|Consider hardening SSH configuration|MaxAuthTries (set 6 to 3)|-|
suggestion[]=DEB-0880|Install fail2ban to automatically ban hosts|-|-|
report_datetime_end=2026-10-03 10:01:40
"""

AFTER = """lynis_version=3.1.7
hardening_index=81
lynis_tests_done=262
suggestion[]=KRNL-5830|Reboot the system|-|-|
report_datetime_end=2026-10-03 10:20:00
"""


def test_parse_reads_scores_and_findings():
    report = lynis_report.parse_report(BEFORE)
    assert report.lynis_version == "3.1.7"
    assert report.hardening_index == 58
    assert report.tests_done == 240
    assert [w.test_id for w in report.warnings] == ["FIRE-4512"]
    assert len(report.suggestions) == 3
    assert report.suggestions[2].text == "Install fail2ban to automatically ban hosts"


def test_finish_time_is_read_as_utc():
    report = lynis_report.parse_report(BEFORE)
    assert report.finished_at == 1791021700.0  # 2026-10-03 10:01:40 UTC


def test_incomplete_report_is_rejected():
    with pytest.raises(ValueError, match="hardening_index"):
        lynis_report.parse_report("lynis_version=3.1.7\n")


def test_prometheus_output_has_help_type_and_values():
    text = lynis_report.to_prometheus(lynis_report.parse_report(BEFORE))
    assert '# TYPE lynis_hardening_index gauge' in text
    assert "lynis_hardening_index 58\n" in text
    assert "lynis_warnings 1\n" in text
    assert "lynis_suggestions 3\n" in text
    assert 'lynis_info{version="3.1.7"} 1\n' in text
    assert "lynis_last_run_timestamp_seconds 1791021700\n" in text
    assert text.endswith("\n")


def test_compare_lists_resolved_suggestions_once():
    out = lynis_report.compare(lynis_report.parse_report(BEFORE), lynis_report.parse_report(AFTER), "web-01")
    assert "| web-01 Hardening index | 58 | 81 |" in out
    assert "| web-01 Suggestions | 3 | 1 |" in out
    assert "Suggestions resolved (2): DEB-0880, SSH-7408" in out


def test_cli_writes_metrics_file_atomically(tmp_path):
    report = tmp_path / "lynis-report.dat"
    report.write_text(BEFORE, encoding="utf-8")
    out = tmp_path / "lynis.prom"
    assert lynis_report.main(["prom", str(report), "--output", str(out)]) == 0
    assert "lynis_hardening_index 58" in out.read_text(encoding="utf-8")
    assert [p.name for p in tmp_path.iterdir() if p.name.startswith(".lynis-")] == []


def test_cli_reports_missing_file(tmp_path, capsys):
    assert lynis_report.main(["prom", str(tmp_path / "missing.dat")]) == 1
    assert "lynis_report:" in capsys.readouterr().err
