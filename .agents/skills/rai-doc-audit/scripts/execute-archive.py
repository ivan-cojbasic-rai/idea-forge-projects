#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""Move every triage.json item with user_decision == "archive" and
executed == false into {root}/.archive/, preserving its relative path.

The only script in this skill allowed to touch project files, and it never
deletes: archive is always a move, never a removal, so the action stays
reversible even after the user has confirmed it. Refuses anything ambiguous
(missing file, already archived, decision not yet "archive") with an error
that names the fix rather than guessing. Re-run render-report.py afterward
to refresh the human-readable view.
"""

import argparse
import json
import shutil
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", help="Project root (files move relative to this)")
    parser.add_argument("triage_json", help="Path to triage.json")
    parser.add_argument("--archive-dir", default=".archive", help="Destination dir, relative to root (default .archive)")
    parser.add_argument("--dry-run", action="store_true", help="Report what would move without moving it")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    triage_path = Path(args.triage_json)
    try:
        triage = json.loads(triage_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": f"could not read {triage_path}: {exc}"}), file=sys.stderr)
        return 2

    archive_root = root / args.archive_dir
    moved, skipped, errors = [], [], []

    for item in triage.get("items", []):
        if item.get("user_decision") != "archive":
            continue
        if item.get("executed"):
            skipped.append({"path": item["path"], "reason": "already executed"})
            continue

        src = root / item["path"]
        if not src.is_file():
            errors.append({"path": item["path"],
                            "reason": f"file not found at {src} -- was it already moved outside this script?"})
            continue

        dest = archive_root / item["path"]
        if dest.exists():
            errors.append({"path": item["path"],
                            "reason": f"archive destination already exists at {dest} -- resolve the collision by hand"})
            continue

        if args.dry_run:
            moved.append({"path": item["path"], "to": str(dest.relative_to(root)), "dry_run": True})
            continue

        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dest))
        item["executed"] = True
        item["archived_to"] = str(dest.relative_to(root)).replace("\\", "/")
        moved.append({"path": item["path"], "to": item["archived_to"]})

    if not args.dry_run and moved:
        triage_path.write_text(json.dumps(triage, indent=2), encoding="utf-8")

    print(json.dumps({"ok": not errors, "moved": moved, "skipped": skipped, "errors": errors}, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
