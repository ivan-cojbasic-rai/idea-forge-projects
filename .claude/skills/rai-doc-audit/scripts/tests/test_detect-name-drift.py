#!/usr/bin/env python3
"""Tests for detect-name-drift.py.

Covers legacy-name hit detection with line/snippet capture, frontmatter
project-field mismatch detection, clean files being omitted from output,
and the CLI's error path when --legacy is empty.
Run with: python3 -m pytest test_detect-name-drift.py
(or plain `python3 test_detect-name-drift.py` for a lightweight self-check).
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

DISCOVER = Path(__file__).resolve().parent.parent / "discover-docs.py"
DRIFT = Path(__file__).resolve().parent.parent / "detect-name-drift.py"


def _run(script, *args):
    return subprocess.run(
        [sys.executable, str(script), *args],
        capture_output=True, text=True,
    )


def _discover(root: Path) -> Path:
    out = root / "_discover.json"
    res = _run(DISCOVER, str(root), "-o", str(out))
    assert res.returncode == 0, res.stderr
    return out


def test_finds_legacy_name_hit_with_snippet():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        (root / "prd.md").write_text(
            "---\ntitle: PRD\nproject: NewName\n---\n\n# PRD - OldName\n", encoding="utf-8"
        )
        discover_out = _discover(root)
        res = _run(DRIFT, str(root), "--input", str(discover_out),
                    "--current", "NewName", "--legacy", "OldName")
        assert res.returncode == 0, res.stderr
        data = json.loads(res.stdout)
        assert data["flagged_count"] == 1
        hit = data["flagged"][0]["legacy_hits"][0]
        assert hit["name"] == "OldName"
        assert "OldName" in hit["snippet"]


def test_frontmatter_project_mismatch_flagged():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        (root / "brief.md").write_text(
            "---\ntitle: Brief\nproject: OldName\n---\n\nno legacy words in body\n", encoding="utf-8"
        )
        discover_out = _discover(root)
        res = _run(DRIFT, str(root), "--input", str(discover_out),
                    "--current", "NewName", "--legacy", "SomeOtherName")
        data = json.loads(res.stdout)
        assert data["flagged_count"] == 1
        assert data["flagged"][0]["frontmatter_project_mismatch"] is True


def test_clean_file_not_flagged():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        (root / "clean.md").write_text(
            "---\ntitle: Clean\nproject: NewName\n---\n\nnothing stale here\n", encoding="utf-8"
        )
        discover_out = _discover(root)
        res = _run(DRIFT, str(root), "--input", str(discover_out),
                    "--current", "NewName", "--legacy", "OldName")
        data = json.loads(res.stdout)
        assert data["flagged_count"] == 0


def test_empty_legacy_list_errors():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        discover_out = _discover(root)
        res = _run(DRIFT, str(root), "--input", str(discover_out),
                    "--current", "NewName", "--legacy", "  ")
        assert res.returncode == 2


def _run_all():
    tests = [
        test_finds_legacy_name_hit_with_snippet,
        test_frontmatter_project_mismatch_flagged,
        test_clean_file_not_flagged,
        test_empty_legacy_list_errors,
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
