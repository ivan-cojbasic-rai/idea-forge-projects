#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""Assemble triage.json from discover-docs.py facts, detect-name-drift.py
signals, the resolved doc-type routing table, carried-forward verdicts
(from plan-judgment-set.py), and fresh subagent judgments.

Pure merge and lookup -- kind, recommended_action, and reasoning are the
only genuinely judged fields, and they arrive pre-decided in --judgments;
this script does not evaluate or second-guess them. It only cross-references
already-computed JSON and fills in what a route lookup or a dict merge
settles deterministically, so a model never hand-assembles the array (and
never fat-fingers a route code) at repo scale. Refuses with a named error
when a discovered path has neither a carried-forward verdict nor a fresh
judgment, rather than silently omitting it.
"""

import argparse
import json
import sys
from pathlib import Path


def load_json(path_str: str) -> dict:
    return json.loads(Path(path_str).read_text(encoding="utf-8"))


def parse_routes(routes_str: str) -> dict:
    routes = {}
    for pair in routes_str.split(","):
        pair = pair.strip()
        if not pair:
            continue
        code, _, route = pair.partition("=")
        if code and route:
            routes[code.strip()] = route.strip()
    return routes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", help="Project root (stored in triage.json for later stages)")
    parser.add_argument("--discover", required=True, help="Path to discover-docs.py JSON output")
    parser.add_argument("--drift", required=True, help="Path to detect-name-drift.py JSON output")
    parser.add_argument("--routes", default="", help="Comma-separated code=route pairs, e.g. 'prd=skill:bmad-prd,architecture=skill:bmad-architecture'")
    parser.add_argument("--judgments", required=True, help="JSON file: list of {path, kind, recommended_action, reasoning}, one per doc in the needed-judgment set")
    parser.add_argument("--carried", help="carried_forward array from plan-judgment-set.py JSON output, as its own JSON file")
    parser.add_argument("--proposed-structure", default="", help="Free-text description of the target folder layout")
    parser.add_argument("-o", "--output", required=True, help="Output triage.json path")
    args = parser.parse_args()

    try:
        discovered = load_json(args.discover)
        drift = load_json(args.drift)
        judgments = json.loads(Path(args.judgments).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": f"could not read input: {exc}"}), file=sys.stderr)
        return 2

    carried = []
    if args.carried:
        try:
            carried_data = json.loads(Path(args.carried).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(json.dumps({"error": f"could not read --carried: {exc}"}), file=sys.stderr)
            return 2
        carried = carried_data.get("carried_forward", carried_data) if isinstance(carried_data, dict) else carried_data

    routes = parse_routes(args.routes)
    drift_by_path = {f["path"]: f for f in drift.get("flagged", [])}
    judgments_by_path = {j["path"]: j for j in judgments}
    carried_by_path = {c["path"]: c for c in carried}

    items = []
    missing = []
    for doc in discovered.get("docs", []):
        path = doc["path"]
        drift_info = drift_by_path.get(path, {})
        signals = {
            "name_drift": drift_info.get("legacy_hits", []),
            "frontmatter_project_mismatch": drift_info.get("frontmatter_project_mismatch", False),
            "possible_duplicates": doc.get("possible_duplicates", []),
        }

        if path in carried_by_path:
            c = carried_by_path[path]
            items.append({
                "path": path, "kind": c.get("kind", doc["kind_hint"]),
                "last_commit_date": doc.get("last_commit_date"), "signals": signals,
                "recommended_action": "keep", "route": None, "needs_manual_review": False,
                "reasoning": c["reasoning"], "user_decision": "keep", "executed": False,
                "carried_forward": True,
            })
        elif path in judgments_by_path:
            j = judgments_by_path[path]
            action = j.get("recommended_action", "keep")
            route = routes.get(j.get("kind")) if action == "update" else None
            items.append({
                "path": path, "kind": j.get("kind", doc["kind_hint"]),
                "last_commit_date": doc.get("last_commit_date"), "signals": signals,
                "recommended_action": action, "route": route,
                "needs_manual_review": action == "update" and route is None,
                "reasoning": j.get("reasoning", ""), "user_decision": "pending", "executed": False,
                "carried_forward": False,
            })
        else:
            missing.append(path)

    if missing:
        print(json.dumps({
            "error": "some discovered paths have neither a carried-forward verdict nor a fresh judgment",
            "missing_paths": missing,
            "fix": "add each to --judgments or confirm it belongs in --carried",
        }), file=sys.stderr)
        return 2

    triage = {
        "root": str(Path(args.root).resolve()),
        "proposed_structure": args.proposed_structure,
        "items": items,
    }

    Path(args.output).write_text(json.dumps(triage, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "output": args.output, "item_count": len(items),
                       "carried_forward_count": len(carried_by_path),
                       "needs_manual_review_count": sum(1 for i in items if i["needs_manual_review"])}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
