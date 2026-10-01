#!/usr/bin/env python3
"""Tests for validate-required-fields.py.

Covers the pass case (including an explicit "unknown"), the fail case with
missing/blank fields, and the no-frontmatter error case.
Run with: python3 -m pytest test_validate_required_fields.py
(or plain `python3 test_validate_required_fields.py` for a lightweight self-check).
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "validate-required-fields.py"


def _run(*args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True,
    )


def _write(root: Path, name: str, text: str) -> Path:
    p = root / name
    p.write_text(text, encoding="utf-8")
    return p


def test_passes_with_all_fields_including_explicit_unknown():
    with tempfile.TemporaryDirectory() as d:
        path = _write(
            Path(d), "doc.md",
            '---\nproject_name: "Acme"\ncustomer_name: "unknown"\n'
            'stakeholder_name: "unknown"\n---\n\nbody\n',
        )
        res = _run(str(path))
        assert res.returncode == 0, res.stderr
        data = json.loads(res.stdout)
        assert data["ok"] is True
        assert data["missing"] == []


def test_fails_when_field_missing():
    with tempfile.TemporaryDirectory() as d:
        path = _write(
            Path(d), "doc.md",
            '---\nproject_name: "Acme"\n---\n\nbody\n',
        )
        res = _run(str(path))
        assert res.returncode == 1
        data = json.loads(res.stdout)
        assert data["ok"] is False
        assert "customer_name" in data["missing"]
        assert "stakeholder_name" in data["missing"]


def test_fails_when_field_blank():
    with tempfile.TemporaryDirectory() as d:
        path = _write(
            Path(d), "doc.md",
            '---\nproject_name: "Acme"\ncustomer_name: ""\nstakeholder_name: "unknown"\n---\n\nbody\n',
        )
        res = _run(str(path))
        assert res.returncode == 1
        data = json.loads(res.stdout)
        assert "customer_name" in data["missing"]


def test_errors_when_no_frontmatter():
    with tempfile.TemporaryDirectory() as d:
        path = _write(Path(d), "doc.md", "# Just a heading\n\nno frontmatter here\n")
        res = _run(str(path))
        assert res.returncode == 2


def test_errors_when_file_missing():
    res = _run("/definitely/does/not/exist.md")
    assert res.returncode == 2


def _run_all():
    tests = [
        test_passes_with_all_fields_including_explicit_unknown,
        test_fails_when_field_missing,
        test_fails_when_field_blank,
        test_errors_when_no_frontmatter,
        test_errors_when_file_missing,
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
