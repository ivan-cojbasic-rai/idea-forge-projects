#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""Patch a live decision, or a completion mark, onto one or more triage.json
items -- the only sanctioned way this skill mutates triage.json outside of
execute-archive.py's own archive bookkeeping.

Two subcommands: `decide` records the user's confirmed keep/update/archive
call for an item (refusing an unknown path, an invalid decision, or a
decision change on an already-executed item, each with a fix named in the
error); `complete` marks an item executed once its confirmed action has
actually happened outside this script (the routed skill finished an update,
for instance) -- execute-archive.py already does this itself for the
archive branch, so `complete` exists for the update branch. Never edit
triage.json by hand; every mutation goes through here or execute-archive.py.
"""

import argparse
import json
import sys
from pathlib import Path

VALID_DECISIONS = {"keep", "update", "archive"}


def load_triage(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_triage(path: Path, triage: dict) -> None:
    path.write_text(json.dumps(triage, indent=2), encoding="utf-8")


def find_item(triage: dict, item_path: str):
    for item in triage.get("items", []):
        if item["path"] == item_path:
            return item
    return None


def cmd_decide(args) -> int:
    triage_path = Path(args.path)
    triage = load_triage(triage_path)

    if args.decision not in VALID_DECISIONS:
        print(json.dumps({"error": f"invalid decision '{args.decision}'",
                           "fix": f"use one of {sorted(VALID_DECISIONS)}"}), file=sys.stderr)
        return 2

    updated, errors = [], []
    for item_path in [p.strip() for p in args.items.split(",") if p.strip()]:
        item = find_item(triage, item_path)
        if item is None:
            errors.append({"path": item_path, "reason": "not found in triage.json -- check the path is repo-relative and matches discovery output exactly"})
            continue
        if item.get("executed"):
            errors.append({"path": item_path, "reason": "already executed -- its decision is final, cannot change"})
            continue
        item["user_decision"] = args.decision
        if args.route is not None:
            item["route"] = args.route
            item["needs_manual_review"] = False
        updated.append(item_path)

    if updated:
        save_triage(triage_path, triage)
    print(json.dumps({"ok": not errors, "updated": updated, "errors": errors}, indent=2))
    return 1 if errors else 0


def cmd_complete(args) -> int:
    triage_path = Path(args.path)
    triage = load_triage(triage_path)

    updated, errors = [], []
    for item_path in [p.strip() for p in args.items.split(",") if p.strip()]:
        item = find_item(triage, item_path)
        if item is None:
            errors.append({"path": item_path, "reason": "not found in triage.json"})
            continue
        if item.get("user_decision") == "pending":
            errors.append({"path": item_path, "reason": "user_decision is still pending -- run 'decide' before 'complete'"})
            continue
        if item.get("executed"):
            errors.append({"path": item_path, "reason": "already marked executed"})
            continue
        item["executed"] = True
        updated.append(item_path)

    if updated:
        save_triage(triage_path, triage)
    print(json.dumps({"ok": not errors, "updated": updated, "errors": errors}, indent=2))
    return 1 if errors else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_decide = sub.add_parser("decide", help="record a confirmed decision")
    p_decide.add_argument("--path", required=True, help="Path to triage.json")
    p_decide.add_argument("--items", required=True, help="Comma-separated doc path(s) to update")
    p_decide.add_argument("--decision", required=True, help="keep | update | archive")
    p_decide.add_argument("--route", help="Override the route (e.g. when the user names a skill for a needs-manual-review item)")
    p_decide.set_defaults(func=cmd_decide)

    p_complete = sub.add_parser("complete", help="mark item(s) executed after their confirmed action has actually happened")
    p_complete.add_argument("--path", required=True, help="Path to triage.json")
    p_complete.add_argument("--items", required=True, help="Comma-separated doc path(s) to mark executed")
    p_complete.set_defaults(func=cmd_complete)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
