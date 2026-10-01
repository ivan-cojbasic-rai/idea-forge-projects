#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""Ship gate: confirm a product description's frontmatter carries the three
required fields -- project_name, customer_name, stakeholder_name -- and that
none is blank. A value of "unknown" passes (it means the user was asked and
explicitly confirmed the gap); a missing key or an empty string does not,
because those mean nobody was ever asked.

Exit 0: all three fields present and non-empty.
Exit 1: one or more fields missing or blank -- see JSON output for which.
Exit 2: file not found or has no frontmatter block to check.
"""

import argparse
import json
import sys
from pathlib import Path

REQUIRED_FIELDS = ("project_name", "customer_name", "stakeholder_name")


def parse_frontmatter_scalars(text: str) -> dict:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
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
        if key and not key.startswith(" "):
            scalars[key] = value
    return scalars


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", help="Path to the drafted document")
    parser.add_argument("-o", "--output", help="Output file (default stdout)")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    doc_path = Path(args.path)
    if not doc_path.is_file():
        print(json.dumps({"error": f"file not found: {doc_path}"}), file=sys.stderr)
        return 2

    text = doc_path.read_text(encoding="utf-8", errors="ignore")
    fm = parse_frontmatter_scalars(text)
    if fm is None:
        print(json.dumps({"error": "no YAML frontmatter block found"}), file=sys.stderr)
        return 2

    missing = [f for f in REQUIRED_FIELDS if not fm.get(f)]
    result = {
        "path": str(doc_path),
        "required_fields": {f: fm.get(f) for f in REQUIRED_FIELDS},
        "missing": missing,
        "ok": not missing,
    }

    output = json.dumps(result, indent=2)
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
    else:
        print(output)

    if missing:
        for field in missing:
            print(
                f"missing or blank '{field}' -- ask the user for it, or get "
                f"explicit confirmation it is unknown and write \"{field}: unknown\"",
                file=sys.stderr,
            )
        return 1

    if args.verbose:
        print("All required fields present.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
