#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""Diff a fresh discover-docs.py sweep against the most recently completed
audit run to decide which docs actually need (re-)judgment.

A doc only carries its prior verdict forward when ALL of: the prior run
judged it "keep", its last_commit_date hasn't changed, and it has no
current name-drift hits -- any of those failing means something could have
changed, so it goes back into the judgment pool. This exists so a repeat
audit doesn't re-litigate hundreds of unchanged, already-confirmed docs
through subagent delegation every time it runs; only what's new or changed
costs judgment. Comparison only, no interpretation of doc content.
"""

import argparse
import json
import sys
from pathlib import Path


def load_json(path_str: str) -> dict:
    return json.loads(Path(path_str).read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--discover", required=True, help="Path to discover-docs.py JSON output")
    parser.add_argument("--drift", required=True, help="Path to detect-name-drift.py JSON output")
    parser.add_argument("--prior-triage", help="Path to the most recently completed run's triage.json, if any")
    parser.add_argument("-o", "--output", help="Output file (default stdout)")
    args = parser.parse_args()

    try:
        discovered = load_json(args.discover)
        drift = load_json(args.drift)
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": f"could not read input: {exc}"}), file=sys.stderr)
        return 2

    drifted_paths = {f["path"] for f in drift.get("flagged", [])}

    prior_by_path = {}
    if args.prior_triage:
        try:
            prior = load_json(args.prior_triage)
        except (OSError, json.JSONDecodeError) as exc:
            print(json.dumps({"error": f"could not read --prior-triage: {exc}"}), file=sys.stderr)
            return 2
        prior_by_path = {i["path"]: i for i in prior.get("items", [])}

    needs_judgment = []
    carried_forward = []

    for doc in discovered.get("docs", []):
        path = doc["path"]
        prior_item = prior_by_path.get(path)
        eligible = (
            prior_item is not None
            and prior_item.get("recommended_action") == "keep"
            and prior_item.get("last_commit_date") == doc.get("last_commit_date")
            and path not in drifted_paths
        )
        if eligible:
            carried_forward.append({
                "path": path,
                "kind": prior_item.get("kind"),
                "last_commit_date": doc.get("last_commit_date"),
                "reasoning": f"Carried forward: no changes since it was last confirmed keep "
                             f"({prior_item.get('last_commit_date') or 'unknown date'}).",
            })
        else:
            needs_judgment.append(path)

    result = {
        "prior_run_used": args.prior_triage or None,
        "needs_judgment": needs_judgment,
        "carried_forward": carried_forward,
        "needs_judgment_count": len(needs_judgment),
        "carried_forward_count": len(carried_forward),
    }

    output = json.dumps(result, indent=2)
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
