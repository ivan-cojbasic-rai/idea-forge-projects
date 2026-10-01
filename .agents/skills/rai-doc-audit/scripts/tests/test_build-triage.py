#!/usr/bin/env python3
"""Tests for build-triage.py.

Covers: route lookup by kind, needs_manual_review when a judged kind has no
route, carried-forward items rendered as pre-confirmed "keep", signals
(name-drift, duplicates) merged in from the discover/drift inputs, and the
named-error path when a discovered doc has neither a judgment nor a
carried-forward entry.
Run with: python3 -m pytest test_build-triage.py
(or plain `python3 test_build-triage.py` for a lightweight self-check).
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "build-triage.py"


def _run(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)


def _write(root: Path, name: str, obj) -> Path:
    path = root / name
    path.write_text(json.dumps(obj), encoding="utf-8")
    return path


def test_route_looked_up_by_kind():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        discover = _write(root, "discover.json", {"docs": [
            {"path": "prd.md", "kind_hint": "prd", "last_commit_date": "2026-01-01", "possible_duplicates": []},
        ]})
        drift = _write(root, "drift.json", {"flagged": []})
        judgments = _write(root, "judgments.json", [
            {"path": "prd.md", "kind": "prd", "recommended_action": "update", "reasoning": "stale name"},
        ])
        out = root / "triage.json"
        res = _run(str(root), "--discover", str(discover), "--drift", str(drift),
                    "--routes", "prd=skill:bmad-prd", "--judgments", str(judgments), "-o", str(out))
        assert res.returncode == 0, res.stdout + res.stderr
        triage = json.loads(out.read_text(encoding="utf-8"))
        item = triage["items"][0]
        assert item["route"] == "skill:bmad-prd"
        assert item["needs_manual_review"] is False


def test_needs_manual_review_when_kind_unrouted():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        discover = _write(root, "discover.json", {"docs": [
            {"path": "readme.md", "kind_hint": "readme", "last_commit_date": "2026-01-01", "possible_duplicates": []},
        ]})
        drift = _write(root, "drift.json", {"flagged": []})
        judgments = _write(root, "judgments.json", [
            {"path": "readme.md", "kind": "readme", "recommended_action": "update", "reasoning": "outdated setup steps"},
        ])
        out = root / "triage.json"
        res = _run(str(root), "--discover", str(discover), "--drift", str(drift),
                    "--routes", "prd=skill:bmad-prd", "--judgments", str(judgments), "-o", str(out))
        assert res.returncode == 0, res.stdout + res.stderr
        item = json.loads(out.read_text(encoding="utf-8"))["items"][0]
        assert item["route"] is None
        assert item["needs_manual_review"] is True


def test_carried_forward_item_is_pre_confirmed_keep():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        discover = _write(root, "discover.json", {"docs": [
            {"path": "old.md", "kind_hint": "readme", "last_commit_date": "2026-01-01", "possible_duplicates": []},
        ]})
        drift = _write(root, "drift.json", {"flagged": []})
        judgments = _write(root, "judgments.json", [])
        carried = _write(root, "carried.json", {"carried_forward": [
            {"path": "old.md", "kind": "readme", "reasoning": "Carried forward: no changes."},
        ]})
        out = root / "triage.json"
        res = _run(str(root), "--discover", str(discover), "--drift", str(drift),
                    "--judgments", str(judgments), "--carried", str(carried), "-o", str(out))
        assert res.returncode == 0, res.stdout + res.stderr
        item = json.loads(out.read_text(encoding="utf-8"))["items"][0]
        assert item["recommended_action"] == "keep"
        assert item["user_decision"] == "keep"
        assert item["carried_forward"] is True


def test_signals_merged_from_drift_and_duplicates():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        discover = _write(root, "discover.json", {"docs": [
            {"path": "arch.md", "kind_hint": "architecture", "last_commit_date": "2026-01-01",
             "possible_duplicates": ["docs/arch.md"]},
        ]})
        drift = _write(root, "drift.json", {"flagged": [
            {"path": "arch.md", "legacy_hits": [{"name": "OldName"}], "frontmatter_project_mismatch": True},
        ]})
        judgments = _write(root, "judgments.json", [
            {"path": "arch.md", "kind": "architecture", "recommended_action": "keep", "reasoning": "fine"},
        ])
        out = root / "triage.json"
        res = _run(str(root), "--discover", str(discover), "--drift", str(drift),
                    "--judgments", str(judgments), "-o", str(out))
        item = json.loads(out.read_text(encoding="utf-8"))["items"][0]
        assert item["signals"]["frontmatter_project_mismatch"] is True
        assert item["signals"]["possible_duplicates"] == ["docs/arch.md"]
        assert len(item["signals"]["name_drift"]) == 1


def test_missing_judgment_errors_by_name():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        discover = _write(root, "discover.json", {"docs": [
            {"path": "orphan.md", "kind_hint": "other", "last_commit_date": "2026-01-01", "possible_duplicates": []},
        ]})
        drift = _write(root, "drift.json", {"flagged": []})
        judgments = _write(root, "judgments.json", [])
        out = root / "triage.json"
        res = _run(str(root), "--discover", str(discover), "--drift", str(drift),
                    "--judgments", str(judgments), "-o", str(out))
        assert res.returncode == 2
        err = json.loads(res.stderr)
        assert "orphan.md" in err["missing_paths"]


def _run_all():
    tests = [
        test_route_looked_up_by_kind,
        test_needs_manual_review_when_kind_unrouted,
        test_carried_forward_item_is_pre_confirmed_keep,
        test_signals_merged_from_drift_and_duplicates,
        test_missing_judgment_errors_by_name,
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
