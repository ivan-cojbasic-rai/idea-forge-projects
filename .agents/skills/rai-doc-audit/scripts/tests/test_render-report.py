#!/usr/bin/env python3
"""Tests for render-report.py.

Covers grouping by recommended_action, the proposed_structure section
appearing only when present, per-item signal/route/status rendering, and
the default output path (triage-report.md beside triage.json).
Run with: python3 -m pytest test_render-report.py
(or plain `python3 test_render-report.py` for a lightweight self-check).
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "render-report.py"


def _run(*args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True,
    )


def _write_triage(root: Path, **overrides) -> Path:
    triage = {
        "root": str(root),
        "items": [
            {"path": "a.md", "kind": "prd", "last_commit_date": "2026-01-01",
             "recommended_action": "update", "route": "skill:bmad-prd",
             "reasoning": "stale name", "signals": {"name_drift": [{"name": "OldName"}]},
             "user_decision": "pending", "executed": False},
            {"path": "b.md", "kind": "readme", "last_commit_date": "2026-01-02",
             "recommended_action": "keep", "route": None, "reasoning": "current",
             "signals": {}, "user_decision": "pending", "executed": False},
        ],
    }
    triage.update(overrides)
    path = root / "triage.json"
    path.write_text(json.dumps(triage), encoding="utf-8")
    return path


def test_groups_by_recommended_action():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        triage_path = _write_triage(root)
        res = _run(str(triage_path))
        assert res.returncode == 0, res.stderr
        report = (root / "triage-report.md").read_text(encoding="utf-8")
        assert "## Update (routed to a specialist skill)" in report
        assert "## Keep as-is" in report
        assert report.index("a.md") < report.index("## Keep as-is")


def test_proposed_structure_omitted_when_absent():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        triage_path = _write_triage(root)
        _run(str(triage_path))
        report = (root / "triage-report.md").read_text(encoding="utf-8")
        assert "Proposed folder structure" not in report


def test_proposed_structure_included_when_present():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        triage_path = _write_triage(root, proposed_structure="Consolidate into docs/.")
        _run(str(triage_path))
        report = (root / "triage-report.md").read_text(encoding="utf-8")
        assert "Consolidate into docs/." in report


def test_route_and_signals_rendered_for_flagged_item():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        triage_path = _write_triage(root)
        _run(str(triage_path))
        report = (root / "triage-report.md").read_text(encoding="utf-8")
        assert "skill:bmad-prd" in report
        assert "OldName" in report


def test_custom_output_path_respected():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        triage_path = _write_triage(root)
        custom_out = root / "custom-report.md"
        res = _run(str(triage_path), "-o", str(custom_out))
        assert res.returncode == 0, res.stderr
        assert custom_out.exists()


def _run_all():
    tests = [
        test_groups_by_recommended_action,
        test_proposed_structure_omitted_when_absent,
        test_proposed_structure_included_when_present,
        test_route_and_signals_rendered_for_flagged_item,
        test_custom_output_path_respected,
    ]
    failures = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except AssertionError as e:
            failures += 1
            print(f"FAIL {t.__name__}: {e}")
        except Exception as e:
            failures += 1
            print(f"ERROR {t.__name__}: {e}")
    return failures


if __name__ == "__main__":
    sys.exit(1 if _run_all() else 0)
