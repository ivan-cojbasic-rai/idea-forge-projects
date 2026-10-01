---
name: rai-product-description
description: Creates, updates, or validates a retrospective RAI product description for execs, marketing, and AI extraction. Use when the user says "create a product description", "round up this project", "generate the marketing brief for X", or wants an executive summary that feeds decks, leaflets, or one-pagers.
---

# rai-product-description

## Overview

Act as the user's synthesis partner for a project that already exists: they hold the ground truth about it — what it is, who it's for, who's paying for it — and this skill holds the craft of extracting that into one document three different readers can use without the conversation in the room. The outcome is a markdown file at `{workflow.product_description_output_path}` with a machine-parseable facts block up top and marketing-ready copy in the body, built from `{workflow.product_description_template}`. Its consumers are an executive skimming for the gist, a marketer lifting copy for a leaflet or deck, and an AI agent extracting structured facts — so nothing in it may be a guess dressed up as a fact. This is not a Product Brief (forward-looking, pre-build) or a PRD (internal, requirements-focused); it looks back at something real and speaks to people outside the build.

## Resolution rules

- Bare paths and `{skill-root}` (e.g. `assets/product-description-template.md`) resolve from this skill's installed directory.
- `{project-root}` → the project working directory.
- `rai-product-description` → the skill directory's basename.

## On Activation

1. Execute each entry in `{workflow.activation_steps_prepend}` in order (pre-flight loads, compliance checks — empty by default).
2. Load config from `{project-root}/_bmad/bmm/config.yaml` (and `.user.yaml` if present); fall back to sensible defaults for anything missing.
3. Resolve the `workflow` block: `uv run {project-root}/_bmad/scripts/resolve_customization.py --skill {skill-root} --key workflow`. On failure, merge `{skill-root}/customize.toml` → `{project-root}/_bmad/custom/rai-product-description.toml` → `{project-root}/_bmad/custom/rai-product-description.user.toml` yourself (scalars override, arrays append). Reference resolved values as `{workflow.<name>}` everywhere below.
4. Treat every entry in `{workflow.persistent_facts}` as standing context for the whole run (`file:`-prefixed entries are paths/globs whose contents load as facts; other entries are literal facts).
5. Detect intent — Create, Update, or Validate — from what the user said. Ask the one disambiguating question if unclear.
6. Resume check: glob for an existing `.memlog.md` under `{workflow.product_description_output_path}`. If found for the named project, read it once to rebuild state and offer to resume before proceeding.
7. Execute each entry in `{workflow.activation_steps_append}` in order before Create/Update/Validate begins.

## Create

Open the floor: invite the user to share everything they already know about the project — what it does, who it's for, source docs they have in mind, the customer and stakeholder. Mine this before asking anything.

Then run `uv run scripts/discover-sources.py {project-root}` to find candidate source documents (PRDs, product briefs, architecture docs, epics/stories indexes, READMEs) without reading them yourself. Present the discovered list to the user — which ones are actually relevant to this project — before pulling any of them into context; a monorepo with several products means not every discovered file belongs in this document. For each confirmed source, delegate extraction to a subagent scoped to this project's facts rather than reading the raw file yourself, so the parent conversation stays lean. If subagent delegation is unavailable in the running environment, fall back to reading confirmed sources directly and sequentially, and note the fallback in the memlog.

Bind the workspace to `{workflow.product_description_output_path}/{workflow.run_folder_pattern}/`, init `.memlog.md` there via `memlog.py`, and capture decisions as they land — which sources were used, what was confirmed vs. inferred, anything the user declined to include.

Draft section by section against `{workflow.product_description_template}`, adapting it the way the template's own header instructs: earn every section's place, don't force the shape.

## Required Facts — hard gate

The generated document must always carry three fields: **Project Name**, **Customer Name**, **Stakeholder Name**. A capable model asked for an executive summary will happily omit or infer a name it isn't sure of — that instinct is wrong here, because this document becomes marketing and compliance-adjacent material where a wrong or invented client/stakeholder name is worse than an acknowledged gap. Before drafting reaches finalize:

- If a field's value is genuinely unknown, do not leave it blank and do not guess. Ask the user directly, and require an explicit reply confirming it's unknown (not silence, not an assumption) before writing `unknown` into that field.
- Headless invocation: the confirmation must still come from outside the model. If the caller supplies a value for a field (including the literal `unknown`) as part of the invocation, that supplied value satisfies the gate — record it as an `assumption` memlog entry. A field with no supplied value and no live user to ask blocks the run rather than guessing; report it as the blocking gap.
- Run `uv run scripts/validate-required-fields.py <path-to-draft>` before finalize. It fails (exit 1) if any of the three fields is missing or blank — including when it should have been the literal string `unknown` but wasn't written at all. Fix and re-run until it passes; this is a ship gate, not advisory.

## Update

Read the memlog first — the change enters as a signal against the standing record, not a patch applied blind. If it contradicts a prior decision (a fact that was confirmed and is now different, a field that was `unknown` and is now known), surface the conflict before applying. Re-run the Required Facts gate before finalize even when only unrelated sections changed, since a stale `unknown` may now be resolvable.

## Validate

Read-only. Run `uv run scripts/validate-required-fields.py <path>` first for the presence/blank half of the Required Facts check — don't re-derive by eye what the script already answers exactly. Then read the memlog and the document for the half no script can settle: is every claim traceable to a source or an explicit user confirmation, is a present required-field value fabricated rather than sourced or user-confirmed, would a marketer or exec who wasn't in the room get what they need. Cite specific lines. Report inline; write nothing the user has to keep unless asked. Always offer to roll findings into an Update.

## Finalize

Distill the memlog: every meaningful entry is either reflected in the document or explicitly set aside as noise, then `memlog.py set-complete`. Run the Validate checks above as a mandatory pre-ship pass — a Create run does not skip the audience-fit and fabrication checks just because nobody separately asked for Validate. Apply each entry in `{workflow.doc_standards}` as a polish pass. Tell the user the document is ready, its path, and — since this feeds marketing material — that a Marketing Angles section exists and is meant to be lifted directly into decks or leaflets. Run `{workflow.on_complete}` if non-empty.
