#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""Render triage.json (the audit's structured working artifact) into a
human-readable triage-report.md.

Pure formatting: triage.json already carries every judgment call (kind,
recommended_action, reasoning, decisions); this script only projects it into
markdown so the doc stays a byproduct of the data, not a second copy the
model has to keep in sync by hand. Re-run after any edit to triage.json.
"""

import argparse
import json
import sys
from pathlib import Path

ACTION_ORDER = ["archive", "update", "keep"]
ACTION_LABELS = {
    "archive": "Archive (move to .archive/)",
    "update": "Update (routed to a specialist skill)",
    "keep": "Keep as-is",
}


def render_item(item: dict) -> str:
    marker = " _(carried forward)_" if item.get("carried_forward") else ""
    if item.get("needs_manual_review"):
        marker += " ⚠ **needs manual review — no specialist skill configured for this kind**"
    lines = [f"- **{item['path']}**  _(kind: {item.get('kind', 'unknown')}, "
             f"last commit: {item.get('last_commit_date') or 'unknown'})_{marker}"]
    reasoning = item.get("reasoning")
    if reasoning:
        lines.append(f"  - Reasoning: {reasoning}")
    route = item.get("route")
    if route:
        lines.append(f"  - Route: `{route}`")
    signals = item.get("signals") or {}
    signal_bits = []
    if signals.get("name_drift"):
        names = sorted({h["name"] for h in signals["name_drift"]})
        signal_bits.append(f"legacy names present: {', '.join(names)}")
    if signals.get("frontmatter_project_mismatch"):
        signal_bits.append("frontmatter project mismatch")
    if signals.get("contradiction_notes"):
        signal_bits.append(f"contradiction: {signals['contradiction_notes']}")
    if signals.get("possible_duplicates"):
        signal_bits.append(f"possible duplicate of: {', '.join(signals['possible_duplicates'])}")
    if signal_bits:
        lines.append(f"  - Signals: {'; '.join(signal_bits)}")
    decision = item.get("user_decision", "pending")
    executed = item.get("executed", False)
    status = "executed" if executed else ("confirmed" if decision != "pending" else "pending confirmation")
    lines.append(f"  - Status: {status}"
                  + (f" (decision: {decision})" if decision != "pending" else ""))
    return "\n".join(lines)


def render(triage: dict) -> str:
    items = triage.get("items", [])
    counts = {a: 0 for a in ACTION_ORDER}
    for item in items:
        action = item.get("recommended_action", "keep")
        counts[action] = counts.get(action, 0) + 1

    out = ["# Documentation Audit — Triage Report", ""]
    out.append(f"Root: `{triage.get('root', '?')}`  ")
    out.append(f"Docs discovered: {len(items)}  ")
    summary = ", ".join(f"{counts.get(a, 0)} {ACTION_LABELS[a].split(' (')[0].lower()}" for a in ACTION_ORDER)
    carried = sum(1 for i in items if i.get("carried_forward"))
    review = sum(1 for i in items if i.get("needs_manual_review"))
    out.append(f"Summary: {summary} ({carried} carried forward unchanged, {review} need manual review)")
    out.append("")

    proposed_structure = triage.get("proposed_structure")
    if proposed_structure:
        out.append("## Proposed folder structure")
        out.append("")
        out.append(proposed_structure)
        out.append("")

    for action in ACTION_ORDER:
        group = [i for i in items if i.get("recommended_action", "keep") == action]
        if not group:
            continue
        out.append(f"## {ACTION_LABELS[action]} ({len(group)})")
        out.append("")
        for item in sorted(group, key=lambda i: i["path"]):
            out.append(render_item(item))
        out.append("")

    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("triage_json", help="Path to triage.json")
    parser.add_argument("-o", "--output", help="Output .md path (default: triage-report.md beside triage.json)")
    args = parser.parse_args()

    triage_path = Path(args.triage_json)
    try:
        triage = json.loads(triage_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": f"could not read {triage_path}: {exc}"}), file=sys.stderr)
        return 2

    report = render(triage)
    output_path = Path(args.output) if args.output else triage_path.parent / "triage-report.md"
    output_path.write_text(report, encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(output_path)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
