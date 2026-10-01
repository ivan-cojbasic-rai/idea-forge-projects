#!/usr/bin/env python3
"""Tests for record-decision.py.

Covers: decide sets user_decision and persists it; decide refuses an
unknown path and an invalid decision; decide refuses changing an
already-executed item; complete refuses a still-pending item; complete
marks executed once decided; a route override clears needs_manual_review.
Run with: python3 -m pytest test_record-decision.py
(or plain `python3 test_record-decision.py` for a lightweight self-check).
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "record-decision.py"


def _run(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)


def _write_triage(root: Path, items) -> Path:
    path = root / "triage.json"
    path.write_text(json.dumps({"root": str(root), "items": items}), encoding="utf-8")
    return path


def test_decide_sets_user_decision():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        triage_path = _write_triage(root, [
            {"path": "a.md", "user_decision": "pending", "executed": False, "needs_manual_review": False, "route": None},
        ])
        res = _run("decide", "--path", str(triage_path), "--items", "a.md", "--decision", "archive")
        assert res.returncode == 0, res.stdout + res.stderr
        updated = json.loads(triage_path.read_text(encoding="utf-8"))
        assert updated["items"][0]["user_decision"] == "archive"


def test_decide_refuses_unknown_path():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        triage_path = _write_triage(root, [])
        res = _run("decide", "--path", str(triage_path), "--items", "ghost.md", "--decision", "keep")
        assert res.returncode == 1
        out = json.loads(res.stdout)
        assert out["errors"][0]["path"] == "ghost.md"


def test_decide_refuses_invalid_decision():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        triage_path = _write_triage(root, [
            {"path": "a.md", "user_decision": "pending", "executed": False},
        ])
        res = _run("decide", "--path", str(triage_path), "--items", "a.md", "--decision", "delete")
        assert res.returncode == 2


def test_decide_refuses_changing_executed_item():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        triage_path = _write_triage(root, [
            {"path": "a.md", "user_decision": "archive", "executed": True},
        ])
        res = _run("decide", "--path", str(triage_path), "--items", "a.md", "--decision", "keep")
        assert res.returncode == 1
        out = json.loads(res.stdout)
        assert "already executed" in out["errors"][0]["reason"]


def test_complete_refuses_pending_item():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        triage_path = _write_triage(root, [
            {"path": "a.md", "user_decision": "pending", "executed": False},
        ])
        res = _run("complete", "--path", str(triage_path), "--items", "a.md")
        assert res.returncode == 1
        out = json.loads(res.stdout)
        assert "pending" in out["errors"][0]["reason"]


def test_complete_marks_executed_after_decided():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        triage_path = _write_triage(root, [
            {"path": "a.md", "user_decision": "update", "executed": False},
        ])
        res = _run("complete", "--path", str(triage_path), "--items", "a.md")
        assert res.returncode == 0, res.stdout + res.stderr
        updated = json.loads(triage_path.read_text(encoding="utf-8"))
        assert updated["items"][0]["executed"] is True


def test_route_override_clears_needs_manual_review():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        triage_path = _write_triage(root, [
            {"path": "readme.md", "user_decision": "pending", "executed": False,
             "route": None, "needs_manual_review": True},
        ])
        res = _run("decide", "--path", str(triage_path), "--items", "readme.md",
                    "--decision", "update", "--route", "skill:bmad-document-project")
        assert res.returncode == 0, res.stdout + res.stderr
        item = json.loads(triage_path.read_text(encoding="utf-8"))["items"][0]
        assert item["route"] == "skill:bmad-document-project"
        assert item["needs_manual_review"] is False


def _run_all():
    tests = [
        test_decide_sets_user_decision,
        test_decide_refuses_unknown_path,
        test_decide_refuses_invalid_decision,
        test_decide_refuses_changing_executed_item,
        test_complete_refuses_pending_item,
        test_complete_marks_executed_after_decided,
        test_route_override_clears_needs_manual_review,
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
