#!/usr/bin/env python3
"""Tests for discover-docs.py.

Covers repo-wide *.md globbing, excluded-directory filtering (default and
--exclude-dirs), kind_hint pattern matching, frontmatter scalar extraction,
and the CLI's error path on a missing root.
Run with: python3 -m pytest test_discover-docs.py
(or plain `python3 test_discover-docs.py` for a lightweight self-check).
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "discover-docs.py"


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
    (root / "_bmad-output" / "planning-artifacts" / "build.memlog.md").write_text(
        "- (note) something\n", encoding="utf-8"
    )
    (root / "node_modules" / "somepkg").mkdir(parents=True)
    (root / "node_modules" / "somepkg" / "README.md").write_text("noise", encoding="utf-8")
    (root / "vendor-extra").mkdir(parents=True)
    (root / "vendor-extra" / "README.md").write_text("also noise", encoding="utf-8")
    (root / "README.md").write_text("# Real readme\n", encoding="utf-8")
    (root / ".archive" / "docs").mkdir(parents=True)
    (root / ".archive" / "docs" / "old-architecture.md").write_text("archived", encoding="utf-8")
    (root / "docs2").mkdir(parents=True)
    (root / "docs2" / "architecture.md").write_text("# Architecture 2\n", encoding="utf-8")
    (root / "architecture.md").write_text("# Architecture 1\n", encoding="utf-8")


def test_finds_prd_with_frontmatter_and_kind_hint():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        _build_tree(root)
        res = _run(str(root))
        assert res.returncode == 0, res.stderr
        data = json.loads(res.stdout)
        prd = next(c for c in data["docs"] if c["path"].endswith("prd.md"))
        assert prd["kind_hint"] == "prd"
        assert prd["title"] == "PRD"
        assert prd["frontmatter_project"] == "Acme"


def test_memlog_kind_hint_matches_suffix_not_just_dotfile():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        _build_tree(root)
        res = _run(str(root))
        data = json.loads(res.stdout)
        memlog = next(c for c in data["docs"] if c["path"].endswith("build.memlog.md"))
        assert memlog["kind_hint"] == "memlog"


def test_excludes_node_modules_by_default():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        _build_tree(root)
        res = _run(str(root))
        data = json.loads(res.stdout)
        paths = {c["path"] for c in data["docs"]}
        assert not any("node_modules" in p for p in paths)


def test_exclude_dirs_flag_adds_extra_exclusions():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        _build_tree(root)
        res = _run(str(root), "--exclude-dirs", "vendor-extra")
        data = json.loads(res.stdout)
        paths = {c["path"] for c in data["docs"]}
        assert not any("vendor-extra" in p for p in paths)
        assert "README.md" in paths


def test_archive_dir_excluded_by_default():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        _build_tree(root)
        res = _run(str(root))
        data = json.loads(res.stdout)
        paths = {c["path"] for c in data["docs"]}
        assert not any(".archive" in p for p in paths)


def test_possible_duplicates_flagged_for_singleton_expected_kind():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        _build_tree(root)
        res = _run(str(root))
        data = json.loads(res.stdout)
        by_path = {c["path"]: c for c in data["docs"]}
        arch1 = by_path["architecture.md"]
        arch2 = by_path["docs2/architecture.md"]
        assert arch1["possible_duplicates"] == ["docs2/architecture.md"]
        assert arch2["possible_duplicates"] == ["architecture.md"]
        # README recurs legitimately -- not a singleton-expected kind, no duplicate flag.
        readme = by_path["README.md"]
        assert readme["possible_duplicates"] == []


def test_missing_root_errors():
    res = _run("/definitely/does/not/exist")
    assert res.returncode == 2
    assert "error" in json.loads(res.stdout or res.stderr or "{}") or res.stderr


def _run_all():
    tests = [
        test_finds_prd_with_frontmatter_and_kind_hint,
        test_memlog_kind_hint_matches_suffix_not_just_dotfile,
        test_excludes_node_modules_by_default,
        test_exclude_dirs_flag_adds_extra_exclusions,
        test_archive_dir_excluded_by_default,
        test_possible_duplicates_flagged_for_singleton_expected_kind,
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
