#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""Find candidate source documents for a product description in a project tree.

Deterministic file discovery only: it globs for known document shapes (PRD,
product brief, architecture, epics/stories index, project overview, README)
and lifts simple frontmatter scalars (title, status, updated, project) with a
hand-rolled parser -- no interpretation of content, no external dependency.
The caller decides which candidates are actually relevant before reading them.
"""

import argparse
import json
import sys
from pathlib import Path

EXCLUDED_DIR_NAMES = {
    ".git", "node_modules", ".venv", "venv", "dist", "build",
    "__pycache__", ".next", "target", "_bmad", ".claude", ".vscode",
    ".github", ".idea", ".pytest_cache", ".mypy_cache", ".tox",
    "site-packages", "egg-info",
}

# (glob pattern relative to root, candidate kind)
PATTERNS = [
    ("**/prd.md", "prd"),
    ("**/product-brief*.md", "product-brief"),
    ("**/architecture.md", "architecture"),
    ("**/architecture-*.md", "architecture"),
    ("**/epics.md", "epics"),
    ("**/stories/INDEX.md", "stories-index"),
    ("**/project-overview.md", "project-overview"),
    ("**/project-roundup*.md", "prior-roundup"),
    ("**/*-distillate.md", "distillate"),
    ("**/README.md", "readme"),
]


def is_excluded(path: Path, root: Path) -> bool:
    rel = path.relative_to(root)
    return any(part in EXCLUDED_DIR_NAMES for part in rel.parts[:-1])


def parse_frontmatter_scalars(text: str) -> dict:
    """Pull simple `key: value` scalars out of a leading YAML frontmatter block.

    Deliberately does not parse lists, nested maps, or multi-line values --
    those are display-only extras here, not a general YAML parser.
    """
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


def discover(root: Path) -> list:
    seen = set()
    candidates = []
    for pattern, kind in PATTERNS:
        for path in root.glob(pattern):
            if not path.is_file() or path in seen or is_excluded(path, root):
                continue
            seen.add(path)
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                text = ""
            fm = parse_frontmatter_scalars(text[:2000])
            candidates.append({
                "path": str(path.relative_to(root)).replace("\\", "/"),
                "kind": kind,
                "title": fm.get("title"),
                "status": fm.get("status"),
                "updated": fm.get("updated"),
                "project": fm.get("project") or fm.get("project_name"),
            })
    candidates.sort(key=lambda c: (c["kind"], c["path"]))
    return candidates


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", help="Project root to search")
    parser.add_argument("-o", "--output", help="Output file (default stdout)")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(json.dumps({"error": f"not a directory: {root}"}), file=sys.stderr)
        return 2

    if args.verbose:
        print(f"Scanning {root} ...", file=sys.stderr)

    candidates = discover(root)
    result = {"root": str(root), "candidate_count": len(candidates), "candidates": candidates}

    output = json.dumps(result, indent=2)
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
    else:
        print(output)

    if args.verbose:
        print(f"Found {len(candidates)} candidate(s).", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
