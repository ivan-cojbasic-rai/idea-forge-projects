#!/usr/bin/env python3
"""Tests for execute-archive.py -- the only script in this skill allowed to
touch project files, so its safety checks matter most.

Covers a successful move with triage.json marked executed, --dry-run leaving
the filesystem untouched, a missing-source error that doesn't abort the rest
of the batch, refusing to overwrite an existing archive destination, skipping
already-executed items, and leaving non-"archive" decisions alone entirely.
Run with: python3 -m pytest test_execute-archive.py
(or plain `python3 test_execute-archive.py` for a lightweight self-check).
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "execute-archive.py"


def _run(*args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True,
    )


def _setup(root: Path, items):
    for item in items:
        if item.get("_create"):
            f = root / item["path"]
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text("content", encoding="utf-8")
    triage = {"root": str(root), "items": [
        {k: v for k, v in item.items() if k != "_create"} for item in items
    ]}
    triage_path = root / "triage.json"
    triage_path.write_text(json.dumps(triage), encoding="utf-8")
    return triage_path


def test_moves_confirmed_archive_item_and_marks_executed():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        triage_path = _setup(root, [
            {"path": "docs/stale.md", "user_decision": "archive", "executed": False, "_create": True},
        ])
        res = _run(str(root), str(triage_path))
        assert res.returncode == 0, res.stdout + res.stderr
        assert not (root / "docs" / "stale.md").exists()
        assert (root / ".archive" / "docs" / "stale.md").exists()
        updated = json.loads(triage_path.read_text(encoding="utf-8"))
        assert updated["items"][0]["executed"] is True


def test_dry_run_does_not_touch_filesystem():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        triage_path = _setup(root, [
            {"path": "keep-me.md", "user_decision": "archive", "executed": False, "_create": True},
        ])
        res = _run(str(root), str(triage_path), "--dry-run")
        assert res.returncode == 0, res.stdout + res.stderr
        assert (root / "keep-me.md").exists()
        assert not (root / ".archive").exists()
        updated = json.loads(triage_path.read_text(encoding="utf-8"))
        assert updated["items"][0]["executed"] is False


def test_missing_source_errors_without_aborting_batch():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        triage_path = _setup(root, [
            {"path": "gone.md", "user_decision": "archive", "executed": False},
            {"path": "present.md", "user_decision": "archive", "executed": False, "_create": True},
        ])
        res = _run(str(root), str(triage_path))
        assert res.returncode == 1
        out = json.loads(res.stdout)
        assert any(e["path"] == "gone.md" for e in out["errors"])
        assert any(m["path"] == "present.md" for m in out["moved"])
        assert (root / ".archive" / "present.md").exists()


def test_refuses_to_overwrite_existing_archive_destination():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        triage_path = _setup(root, [
            {"path": "dupe.md", "user_decision": "archive", "executed": False, "_create": True},
        ])
        collide = root / ".archive" / "dupe.md"
        collide.parent.mkdir(parents=True, exist_ok=True)
        collide.write_text("already here", encoding="utf-8")
        res = _run(str(root), str(triage_path))
        assert res.returncode == 1
        out = json.loads(res.stdout)
        assert any(e["path"] == "dupe.md" for e in out["errors"])
        assert (root / "dupe.md").exists()


def test_skips_already_executed_item():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        triage_path = _setup(root, [
            {"path": "done.md", "user_decision": "archive", "executed": True},
        ])
        res = _run(str(root), str(triage_path))
        assert res.returncode == 0, res.stdout + res.stderr
        out = json.loads(res.stdout)
        assert any(s["path"] == "done.md" for s in out["skipped"])


def test_ignores_non_archive_decisions():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        triage_path = _setup(root, [
            {"path": "pending.md", "user_decision": "pending", "executed": False, "_create": True},
            {"path": "kept.md", "user_decision": "keep", "executed": False, "_create": True},
        ])
        res = _run(str(root), str(triage_path))
        assert res.returncode == 0, res.stdout + res.stderr
        out = json.loads(res.stdout)
        assert out["moved"] == []
        assert (root / "pending.md").exists()
        assert (root / "kept.md").exists()


def _run_all():
    tests = [
        test_moves_confirmed_archive_item_and_marks_executed,
        test_dry_run_does_not_touch_filesystem,
        test_missing_source_errors_without_aborting_batch,
        test_refuses_to_overwrite_existing_archive_destination,
        test_skips_already_executed_item,
        test_ignores_non_archive_decisions,
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
