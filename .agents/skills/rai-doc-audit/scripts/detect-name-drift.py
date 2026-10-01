#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""Flag docs that still carry a legacy project name, or whose frontmatter
project field disagrees with the current name.

Deterministic text search only -- no judgment about whether a hit matters
(e.g. a name inside a code block or a historical "formerly known as" note is
still reported; the caller decides what it means). Consumes the JSON emitted
by discover-docs.py so the file list and frontmatter are read once, not twice.
"""

import argparse
import json
import re
import sys
from pathlib import Path


def find_hits(text: str, legacy_names: list) -> list:
    hits = []
    lines = text.splitlines()
    for name in legacy_names:
        pattern = re.compile(re.escape(name), re.I)
        for i, line in enumerate(lines, start=1):
            if pattern.search(line):
                snippet = line.strip()
                if len(snippet) > 160:
                    snippet = snippet[:157] + "..."
                hits.append({"name": name, "line": i, "snippet": snippet})
    return hits


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", help="Project root (must match discover-docs.py's root)")
    parser.add_argument("--input", required=True, help="Path to discover-docs.py JSON output")
    parser.add_argument("--current", required=True, help="Current project name")
    parser.add_argument("--legacy", required=True, help="Comma-separated legacy project names")
    parser.add_argument("-o", "--output", help="Output file (default stdout)")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    legacy_names = [n.strip() for n in args.legacy.split(",") if n.strip()]
    if not legacy_names:
        print(json.dumps({"error": "no legacy names supplied"}), file=sys.stderr)
        return 2

    try:
        discovered = json.loads(Path(args.input).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": f"could not read --input: {exc}"}), file=sys.stderr)
        return 2

    flagged = []
    for doc in discovered.get("docs", []):
        file_path = root / doc["path"]
        try:
            text = file_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        legacy_hits = find_hits(text, legacy_names)
        fm_project = doc.get("frontmatter_project")
        fm_mismatch = bool(fm_project) and fm_project.strip().lower() != args.current.strip().lower()
        if legacy_hits or fm_mismatch:
            flagged.append({
                "path": doc["path"],
                "legacy_hits": legacy_hits,
                "frontmatter_project": fm_project,
                "frontmatter_project_mismatch": fm_mismatch,
            })

    result = {
        "root": str(root),
        "current_name": args.current,
        "legacy_names": legacy_names,
        "flagged_count": len(flagged),
        "flagged": flagged,
    }

    output = json.dumps(result, indent=2)
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
