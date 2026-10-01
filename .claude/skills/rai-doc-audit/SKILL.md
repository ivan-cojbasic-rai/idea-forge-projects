---
name: rai-doc-audit
description: Audits repo-wide docs for staleness and drift. Use when the user says "audit the docs", "clean up documentation", "check for stale docs", or "reorganize the docs".
---

# rai-doc-audit

## Overview

Act as the user's documentation-triage partner for a project that has drifted -- renamed, restructured, grown docs in more places than any one folder tracks. The outcome is a triage report and its structured twin (`triage.json`) at `{workflow.audit_output_path}/{workflow.run_folder_pattern}/`, covering every markdown doc in the repo with a judged kind, a staleness verdict, and a recommended action: keep, route to a specialist skill for update, or archive. Its consumer is the user deciding what happens to years of accumulated documentation, and downstream of that, whatever skill next reads these docs and needs them current and unambiguous. The bar: every recommendation traces to a concrete signal -- a stale date, a legacy name, a cross-doc contradiction -- never a guess dressed as a verdict, and nothing moves or gets handed to another skill until the user has confirmed that specific item. This skill never edits doc content and never hard-deletes; it discovers, judges, and routes, and archive always means a reversible move to `.archive/`.

## Resolution rules

- Bare paths and `{skill-root}` (e.g. `scripts/discover-docs.py`) resolve from this skill's installed directory.
- `{project-root}` → the project working directory.
- `rai-doc-audit` → the skill directory's basename.

## On Activation

1. Execute `{workflow.activation_steps_prepend}` in order.
2. Load `{project-root}/_bmad/bmm/config.yaml` (+ `.user.yaml`) for `{user_name}`, `{communication_language}`, `{project_name}`, `{planning_artifacts}`, `{project_knowledge}`, `{date}`; missing keys take neutral defaults, never block.
3. Resolve `{workflow.*}`: `uv run {project-root}/_bmad/scripts/resolve_customization.py --skill {skill-root} --key workflow`. On failure, merge `{skill-root}/customize.toml` → `{project-root}/_bmad/custom/rai-doc-audit.toml` → `{project-root}/_bmad/custom/rai-doc-audit.user.toml` yourself (scalars override, arrays append, `doc_routes` entries matched and replaced by `code`). Reference resolved values as `{workflow.<name>}` everywhere below; never hardcode a path beside a declared scalar.
4. Load each `{workflow.persistent_facts}` entry as standing context for the run (`file:`-prefixed entries resolve as path/glob contents, other entries are literal facts).
5. Resume check: glob `{workflow.audit_output_path}/*/triage.json`. If a prior run has any item with `user_decision` still `"pending"`, or confirmed but `executed: false`, surface it and offer to resume before starting a fresh sweep.
6. Execute `{workflow.activation_steps_append}`.

## Discover

Open the floor before scanning anything: ask whether the user already has a target folder structure or consolidation decision in mind (retire a folder, merge two locations, a rename in flight) and honor it as the goal the triage proposes against, rather than inventing one from scratch. Then run `uv run scripts/discover-docs.py {project-root} --exclude-dirs "{workflow.excluded_dirs}"` and feed its output to `uv run scripts/detect-name-drift.py {project-root} --input <discover-output> --current "{workflow.current_project_name}" --legacy "{workflow.legacy_project_names}"`. Both are deterministic; don't re-derive their output by reading files yourself.

If a fully completed prior run exists under `{workflow.audit_output_path}` (distinct from the resume case above, which continues an unfinished one), run `uv run scripts/plan-judgment-set.py --discover <discover-output> --drift <drift-output> --prior-triage <that run's triage.json>` to split discovered docs into `needs_judgment` and `carried_forward` -- an unchanged doc that was already confirmed `keep` doesn't need re-judging every run. With no prior run, everything discovered needs judgment.

## Classify and judge

Delegate each path in `needs_judgment` -- individually, or as a small cluster of closely related docs (a service's README plus its own docs folder) -- to a subagent: it reads the file, confirms or corrects the discovery script's `kind_hint`, and returns `{path, kind, recommended_action, reasoning}`. Specify that exact return shape and "return ONLY that" in every subagent prompt, or the parent context fills with prose. Pass each doc's `possible_duplicates` (already computed by discover-docs.py for kinds like architecture or product-brief, where a second instance is drift rather than expected repetition) into its subagent's prompt so it judges against the named counterpart instead of in isolation. Parallelize across docs so a repo-scale audit doesn't serialize one file at a time; if subagents aren't available, fall back to reading sequentially yourself and note the fallback. Collect every return into one `judgments.json` array. Never re-read a file yourself once a subagent has returned its facts.

## Propose

Bind the workspace to `{workflow.audit_output_path}/{workflow.run_folder_pattern}/`. Write a one-line proposed folder-structure description against whatever the user named at Discover, or your own proposal if they didn't. Then run `uv run scripts/build-triage.py {project-root} --discover <discover-output> --drift <drift-output> --routes "<{workflow.doc_routes} rendered as code=route,code=route>" --judgments judgments.json --carried <plan-judgment-set output> --proposed-structure "<your text>" -o <workspace>/triage.json` to assemble it -- the script fills `route` from the routing table and flags an `update` item `needs_manual_review` when its kind has no configured route, rather than leaving Execute to assume one exists. Run `uv run scripts/render-report.py <triage.json>` to produce `triage-report.md`; it is a projection of the JSON, so re-render it after any script call that changes `triage.json`, and never hand-edit either file directly.

## Confirm

Walk the report with the user, item by item or by group, their call. For each decision, run `uv run scripts/record-decision.py decide --path <triage.json> --items <path[,path...]> --decision <keep|update|archive>` (add `--route <skill:...>` when the user names one for a `needs_manual_review` item). Nothing changes away from `"pending"` without an explicit reply covering that item -- a batch "archive everything under docs/" is fine when the user states it that broadly, but silence is not consent. If no user is available to confirm (a headless run), leave every item `"pending"` and proceed to Finalize; nothing archives or routes without an explicit confirmed decision.

## Execute

For confirmed `archive` items, run `uv run scripts/execute-archive.py {project-root} <triage.json>` (offer `--dry-run` first on a large batch) -- it is the only thing in this skill that touches project files. For confirmed `update` items with a route, invoke that skill now if the user wants to proceed immediately, or leave it as a named follow-up if they'd rather batch it later; once the routed skill has actually finished, run `uv run scripts/record-decision.py complete --path <triage.json> --items <path>` so the item stops resurfacing as pending on the next run. For a confirmed `update` item flagged `needs_manual_review`, say so plainly and ask the user to fix it by hand or name a skill to route to.

## Finalize

Summarize what moved, what got routed and to where, what needs manual review, and what's still pending, pointing at the triage report's path. Run `{workflow.on_complete}` if non-empty.
