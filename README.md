# IdeaForge Agent Pack — RAI Product Specialist

A copy-paste overlay that installs the **RAI Product Specialist** agent for both
**Claude Code** and **GitHub Copilot**. The agent turns ideas into Jira-ready
work items and writes them straight into an IdeaForge project manifest
(`.ideaforge/manifest.json`), so they show up in the IdeaForge VS Code extension
and can be pushed to Jira.

> **Why this folder exists:** the live `.claude/`, `.agents/`, and `.github/`
> folders are git-ignored in this repo, so the agent files there are not tracked.
> This pack is the **tracked source of truth** for the agent definition. Edit the
> files here, then re-deploy with the copy step below.

## Prerequisite — BMAD-METHOD

The agent loads the BMAD analyst workflow
(`{project-root}/.agents/skills/bmad-agent-analyst/SKILL.md`) and overrides its
persona/output. **BMAD-METHOD must already be installed** in the target project
(its `.claude/`, `.agents/`, `.github/` folders present). This pack only adds the
RAI Product Specialist on top of that install — it does not replace BMAD.

## What's in the pack

```text
.claude/skills/rai-product-specialist/SKILL.md + customize.toml   ← Claude Code skill (BMAD-style)
.agents/skills/rai-product-specialist/SKILL.md + customize.toml   ← portable BMAD-style skill copy
.github/agents/rai-product-specialist.agent.md                     ← GitHub Copilot custom agent (self-contained, no customize.toml — Copilot can't run the BMAD resolver)
```

All three define the same agent; keep them in sync when you edit. The Claude/portable
copies split persona+config (`customize.toml`) from instructions (`SKILL.md`) per the
BMAD skill convention; the Copilot agent inlines everything into one file since it has
no equivalent resolver step.

> **Superseded:** `.claude/skills/ideaforge-product-specialist/` and
> `.agents/skills/ideaforge-product-specialist/` are the previous (simpler) agent
> definition, kept here only because removing them wasn't explicitly requested. They
> lack the mandatory project-selection flow and the IdeaForge-panel sync step that
> `rai-product-specialist` has — do not deploy both into the same target project.

## Install (copy-paste)

From this folder, copy the three dotfolders into the **root of your target
project** (the folder that already contains the BMAD-METHOD `.claude/`,
`.agents/`, and `.github/` folders). They merge with what's already there.

**Windows (PowerShell), run from inside this `agent-pack/` folder:**

```powershell
$dest = "C:\path\to\your\project"
Copy-Item -Recurse -Force .\.claude  $dest
Copy-Item -Recurse -Force .\.agents  $dest
Copy-Item -Recurse -Force .\.github  $dest
```

**macOS / Linux (bash), run from inside this `agent-pack/` folder:**

```bash
dest=/path/to/your/project
cp -R ./.claude ./.agents ./.github "$dest"/
```

Or just drag-and-drop the `.claude`, `.agents`, and `.github` folders onto the
project root in your file explorer and choose "merge".

## Use it

- **Claude Code:** invoke the skill `ideaforge-product-specialist` (e.g. type
  `/ideaforge-product-specialist`, or ask to "talk to the RAI Product Specialist").
- **GitHub Copilot:** select the **RAI Product Specialist** custom agent
  (`.github/agents/rai-product-specialist.agent.md`).

## What the agent does

- Brainstorms and breaks ideas into **Epics, Stories, Tasks, and Bugs** with
  acceptance criteria — Jira-ready.
- **Writes those work items directly into the project's `.ideaforge/manifest.json`
  `ideas[]`** (not just markdown), so the IdeaForge extension picks them up.
- Links child items to their Epic via `parentId`.
- Can **initialize a new project** (`.ideaforge/manifest.json`) on demand in an
  empty/uninitialized folder.
- Is explicitly forbidden from writing or discussing code.
