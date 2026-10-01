#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""Find every markdown doc in a project tree and lift deterministic facts about it.

Broader than a single-run source-discovery script: this globs the whole tree
for `*.md`, not a fixed list of known doc shapes, because a repo-wide staleness
audit needs to see everything before deciding what matters. For each file it
extracts frontmatter scalars (title/status/updated/project), assigns a
best-guess `kind_hint` from filename/path patterns (never authoritative --
the caller judges the real kind), and looks up the file's last commit date
from git. No interpretation of content beyond frontmatter and filename.
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

DEFAULT_EXCLUDED_DIR_NAMES = {
    ".git", "node_modules", ".venv", "venv", "dist", "build",
    "__pycache__", ".next", "target", "_bmad", ".claude", ".vscode",
    ".github", ".idea", ".pytest_cache", ".mypy_cache", ".tox",
    "site-packages", "egg-info", ".archive",
}

# kind_hints where more than one instance in a repo is usually a red flag
# (a second architecture.md or product-brief is exactly the kind of drift
# this audit exists to catch) rather than expected repetition (README,
# story, skill-doc legitimately recur many times).
SINGLETON_EXPECTED_KINDS = {
    "prd", "architecture", "product-brief", "project-overview",
    "epics", "stories-index",
}

# (regex against the POSIX-style relative path, kind_hint) -- first match wins.
KIND_PATTERNS = [
    (re.compile(r"\.memlog\.md$"), "memlog"),
    (re.compile(r"(^|/)\.analysis/"), "analysis-report"),
    (re.compile(r"(^|/)prd\.md$", re.I), "prd"),
    (re.compile(r"(^|/)product-brief.*\.md$", re.I), "product-brief"),
    (re.compile(r".*-distillate\.md$", re.I), "distillate"),
    (re.compile(r"(^|/)architecture(-[\w-]+)?\.md$", re.I), "architecture"),
    (re.compile(r"(^|/)epics\.md$", re.I), "epics"),
    (re.compile(r"(^|/)stories/index\.md$", re.I), "stories-index"),
    (re.compile(r"(^|/)stories/.+\.md$", re.I), "story"),
    (re.compile(r"(^|/)spec-.*\.md$", re.I), "spec"),
    (re.compile(r"(^|/)project-overview\.md$", re.I), "project-overview"),
    (re.compile(r"(^|/)project-roundup.*\.md$", re.I), "project-roundup"),
    (re.compile(r"(^|/)skills?/[^/]+/SKILL\.md$", re.I), "skill-doc"),
    (re.compile(r"(^|/)README\.md$", re.I), "readme"),
]


def is_excluded(path: Path, root: Path, extra_excluded: set) -> bool:
    rel = path.relative_to(root)
    names = extra_excluded | DEFAULT_EXCLUDED_DIR_NAMES
    return any(part in names for part in rel.parts[:-1])


def kind_hint(rel_posix: str) -> str:
    for pattern, kind in KIND_PATTERNS:
        if pattern.search(rel_posix):
            return kind
    return "other"


def parse_frontmatter_scalars(text: str) -> dict:
    """Pull simple `key: value` scalars out of a leading YAML frontmatter block."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    scalars = {}
    for line in lines[1:]:
        stripped = line.strip()
        if stripped == "---":
            break
        if not stripped or stripped.startswith("#") or stripped.startswith("-"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and value and not key.startswith(" "):
            scalars[key] = value
    return scalars


def last_commit_date(root: Path, rel_posix: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%ad", "--date=short", "--", rel_posix],
            cwd=root, capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    date = result.stdout.strip()
    return date or None


def discover(root: Path, extra_excluded: set) -> list:
    docs = []
    for path in root.glob("**/*.md"):
        if not path.is_file() or is_excluded(path, root, extra_excluded):
            continue
        rel_posix = str(path.relative_to(root)).replace("\\", "/")
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            text = ""
        fm = parse_frontmatter_scalars(text[:2000])
        docs.append({
            "path": rel_posix,
            "kind_hint": kind_hint(rel_posix),
            "title": fm.get("title"),
            "status": fm.get("status"),
            "updated": fm.get("updated"),
            "frontmatter_project": fm.get("project") or fm.get("project_name"),
            "last_commit_date": last_commit_date(root, rel_posix),
            "size_bytes": path.stat().st_size,
        })
    docs.sort(key=lambda d: d["path"])

    by_kind = {}
    for doc in docs:
        if doc["kind_hint"] in SINGLETON_EXPECTED_KINDS:
            by_kind.setdefault(doc["kind_hint"], []).append(doc["path"])
    for doc in docs:
        siblings = by_kind.get(doc["kind_hint"], [])
        doc["possible_duplicates"] = [p for p in siblings if p != doc["path"]]

    return docs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", help="Project root to search")
    parser.add_argument("--exclude-dirs", default="", help="Comma-separated extra directory names to exclude")
    parser.add_argument("-o", "--output", help="Output file (default stdout)")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(json.dumps({"error": f"not a directory: {root}"}), file=sys.stderr)
        return 2

    extra_excluded = {d.strip() for d in args.exclude_dirs.split(",") if d.strip()}

    if args.verbose:
        print(f"Scanning {root} ...", file=sys.stderr)

    docs = discover(root, extra_excluded)
    result = {"root": str(root), "doc_count": len(docs), "docs": docs}

    output = json.dumps(result, indent=2)
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
    else:
        print(output)

    if args.verbose:
        print(f"Found {len(docs)} doc(s).", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
