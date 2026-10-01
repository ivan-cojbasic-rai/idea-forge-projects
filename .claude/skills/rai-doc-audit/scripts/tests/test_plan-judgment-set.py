#!/usr/bin/env python3
"""Tests for plan-judgment-set.py.

Covers: no prior run means everything needs judgment; an unchanged doc
previously confirmed "keep" carries forward; a changed commit date, a new
drift hit, or a prior non-"keep" verdict all force re-judgment.
Run with: python3 -m pytest test_plan-judgment-set.py
(or plain `python3 test_plan-judgment-set.py` for a lightweight self-check).
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "plan-judgment-set.py"


def _run(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)


def _write(root: Path, name: str, obj: dict) -> Path:
    path = root / name
    path.write_text(json.dumps(obj), encoding="utf-8")
    return path


def _discover(docs):
    return {"root": "/fake", "doc_count": len(docs), "docs": docs}


def test_no_prior_run_everything_needs_judgment():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        discover = _write(root, "discover.json", _discover([
            {"path": "a.md", "last_commit_date": "2026-01-01"},
        ]))
        drift = _write(root, "drift.json", {"flagged": []})
        res = _run("--discover", str(discover), "--drift", str(drift))
        assert res.returncode == 0, res.stderr
        data = json.loads(res.stdout)
        assert data["needs_judgment"] == ["a.md"]
        assert data["carried_forward"] == []


def test_unchanged_keep_carries_forward():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        discover = _write(root, "discover.json", _discover([
            {"path": "a.md", "last_commit_date": "2026-01-01"},
        ]))
        drift = _write(root, "drift.json", {"flagged": []})
        prior = _write(root, "prior.json", {"items": [
            {"path": "a.md", "kind": "readme", "recommended_action": "keep", "last_commit_date": "2026-01-01"},
        ]})
        res = _run("--discover", str(discover), "--drift", str(drift), "--prior-triage", str(prior))
        data = json.loads(res.stdout)
        assert data["needs_judgment"] == []
        assert len(data["carried_forward"]) == 1
        assert data["carried_forward"][0]["path"] == "a.md"


def test_changed_commit_date_forces_rejudgment():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        discover = _write(root, "discover.json", _discover([
            {"path": "a.md", "last_commit_date": "2026-02-01"},
        ]))
        drift = _write(root, "drift.json", {"flagged": []})
        prior = _write(root, "prior.json", {"items": [
            {"path": "a.md", "kind": "readme", "recommended_action": "keep", "last_commit_date": "2026-01-01"},
        ]})
        res = _run("--discover", str(discover), "--drift", str(drift), "--prior-triage", str(prior))
        data = json.loads(res.stdout)
        assert data["needs_judgment"] == ["a.md"]


def test_new_drift_hit_forces_rejudgment_despite_unchanged_date():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        discover = _write(root, "discover.json", _discover([
            {"path": "a.md", "last_commit_date": "2026-01-01"},
        ]))
        drift = _write(root, "drift.json", {"flagged": [{"path": "a.md", "legacy_hits": [{"name": "OldName"}]}]})
        prior = _write(root, "prior.json", {"items": [
            {"path": "a.md", "kind": "readme", "recommended_action": "keep", "last_commit_date": "2026-01-01"},
        ]})
        res = _run("--discover", str(discover), "--drift", str(drift), "--prior-triage", str(prior))
        data = json.loads(res.stdout)
        assert data["needs_judgment"] == ["a.md"]


def test_prior_non_keep_verdict_forces_rejudgment():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        discover = _write(root, "discover.json", _discover([
            {"path": "a.md", "last_commit_date": "2026-01-01"},
        ]))
        drift = _write(root, "drift.json", {"flagged": []})
        prior = _write(root, "prior.json", {"items": [
            {"path": "a.md", "kind": "prd", "recommended_action": "update", "last_commit_date": "2026-01-01"},
        ]})
        res = _run("--discover", str(discover), "--drift", str(drift), "--prior-triage", str(prior))
        data = json.loads(res.stdout)
        assert data["needs_judgment"] == ["a.md"]


def _run_all():
    tests = [
        test_no_prior_run_everything_needs_judgment,
        test_unchanged_keep_carries_forward,
        test_changed_commit_date_forces_rejudgment,
        test_new_drift_hit_forces_rejudgment_despite_unchanged_date,
        test_prior_non_keep_verdict_forces_rejudgment,
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
