#!/usr/bin/env python3
"""Tests for discover-sources.py.

Covers pattern matching, excluded-directory filtering, frontmatter scalar
extraction, and the CLI's error path on a missing root.
Run with: python3 -m pytest test_discover_sources.py
(or plain `python3 test_discover_sources.py` for a lightweight self-check).
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "discover-sources.py"


def _run(*args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True,
    )


def _build_tree(root: Path):
    (root / "_bmad-output" / "planning-artifacts").mkdir(parents=True)
    (root / "_bmad-output" / "planning-artifacts" / "prd.md").write_text(
        '---\ntitle: "PRD"\nproject: "Acme"\n---\n\nbody\n', encoding="utf-8"
    )
    (root / "node_modules" / "somepkg").mkdir(parents=True)
    (root / "node_modules" / "somepkg" / "README.md").write_text("noise", encoding="utf-8")
    (root / "README.md").write_text("# Real readme\n", encoding="utf-8")


def test_finds_prd_and_extracts_frontmatter():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        _build_tree(root)
        res = _run(str(root))
        assert res.returncode == 0, res.stderr
        data = json.loads(res.stdout)
        paths = {c["path"] for c in data["candidates"]}
        assert "_bmad-output/planning-artifacts/prd.md" in paths
        prd = next(c for c in data["candidates"] if c["kind"] == "prd")
        assert prd["title"] == "PRD"
        assert prd["project"] == "Acme"


def test_excludes_node_modules():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        _build_tree(root)
        res = _run(str(root))
        data = json.loads(res.stdout)
        paths = {c["path"] for c in data["candidates"]}
        assert not any("node_modules" in p for p in paths)


def test_includes_top_level_readme():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        _build_tree(root)
        res = _run(str(root))
        data = json.loads(res.stdout)
        paths = {c["path"] for c in data["candidates"]}
        assert "README.md" in paths


def test_missing_root_errors():
    res = _run("/definitely/does/not/exist")
    assert res.returncode == 2
    assert "error" in json.loads(res.stdout or res.stderr or "{}") or res.stderr


def _run_all():
    tests = [
        test_finds_prd_and_extracts_frontmatter,
        test_excludes_node_modules,
        test_includes_top_level_readme,
        test_missing_root_errors,
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
