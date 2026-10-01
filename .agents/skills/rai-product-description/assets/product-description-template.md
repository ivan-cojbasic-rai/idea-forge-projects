# RAI Product Description Template

A comprehensive, AI-consumable project summary that serves three audiences at once: an executive skimming for the gist, a marketer pulling copy for a leaflet or pitch deck, and an AI agent extracting structured facts for a downstream artifact. Unlike a Product Brief (forward-looking, written *before* a build to pitch a direction) or a PRD (internal, requirements-focused, for builders), this document looks *back* at a project that exists — what it is, what was actually delivered, and why it matters — and is written for external and cross-functional consumption.

Adapt aggressively. Drop sections that do not earn their place, add sections the project needs, reorder freely. Three rules that do not bend: keep the **Facts** block machine-parseable, keep the **Marketing Angles** section literal reusable copy (not commentary about copy), and never leave `project_name`, `customer_name`, or `stakeholder_name` blank — an explicitly confirmed `"unknown"` is fine, silence is not.

## When to use this vs. other documents

- **Product Brief** — before you build, to pitch a direction and align on scope.
- **PRD** — during the build, internal, requirements-and-acceptance-criteria focused.
- **RAI Product Description (this template)** — after there's something real to show, to explain it to people who did not live through the build: executives, marketing, sales, new stakeholders, or an AI assembling a leaflet/deck/one-pager from it.

## Default Structure

```markdown
---
title: "Product Description: {Project Name}"
status: "current" # current | needs-update
updated: "{date}"
project_name: "{Project Name, or 'unknown' if explicitly confirmed unknown}"
customer_name: "{Customer Name, or 'unknown' if explicitly confirmed unknown}"
stakeholder_name: "{Stakeholder Name, or 'unknown' if explicitly confirmed unknown}"
one_liner: "{One sentence: what this is, in plain language}"
category: "{Product category / domain}"
stage: "{Concept | MVP | Beta | GA | Sunset}"
target_market: "{Who buys or sponsors this: e.g. Enterprise (Named anchor client), SMB, Internal tool}"
primary_stack: ["{tech}", "{tech}", "..."]
key_differentiators: ["{short phrase}", "{short phrase}", "..."]
source_documents:
  - "{path to PRD, product brief, architecture doc, etc.}"
---

# Product Description: {Project Name}

## Executive Summary

[2-3 paragraphs. What this is, what problem it solves, why it matters, why now, and — since this is a round-up, not a pitch — what actually exists today. Should stand alone: a reader who stops here understands the project.]

## At a Glance

[A compact fact table for fast human scanning and clean AI extraction. Not narrative — pure facts. Project Name, Customer Name, and Stakeholder Name are mandatory rows; write "Unknown (confirmed)" rather than omitting the row if the user explicitly confirmed the value is unknown.]

| | |
|---|---|
| **Project Name** | |
| **Customer Name** | |
| **Stakeholder Name** | |
| **Category** | |
| **Stage** | |
| **Target Market / Anchor Client** | |
| **Primary Users** | |
| **Core Tech Stack** | |
| **Key Integrations** | |
| **Team Size / Timeline** | |

## The Problem

[What pain exists, who feels it, how they cope today, the cost of the status quo. Specific scenarios, not abstractions.]

## The Solution

[What was built and how it solves the problem. Experience and outcome first; implementation detail belongs in Architecture below.]

## Current State — What's Actually Delivered

[The section a Product Brief cannot have: this project already exists. State plainly what is built and working today vs. what is planned/in-progress vs. explicitly out of scope. Cite evidence where possible (shipped components, working commits, deployed environments). This is what keeps the document honest and keeps AI extraction from overclaiming maturity.]

- **Delivered:** [...]
- **In progress:** [...]
- **Explicitly out of scope:** [...]

## Key Capabilities

[A structured, marketing-usable feature list. Each capability gets a short bold name and a one-line benefit statement — this is the section a leaflet or slide pulls from directly.]

- **{Capability name}** — {one-line benefit statement, outcome-oriented, not implementation-oriented}
- **{Capability name}** — {...}

## What Makes This Different

[Differentiators. Why this approach over alternatives, the unfair advantage. Be honest — if the moat is execution speed or domain access, say so. Do not fabricate technical moats.]

## Who This Serves

[Primary users — vivid but brief: who they are, what they need, what success looks like for them. Secondary users / downstream consumers if relevant. Note who the system is deliberately invisible to, if applicable.]

## Architecture & Tech Stack Summary

[Enough technical credibility for a technical buyer or partner to trust the project, without dragging in implementation detail that belongs in the architecture doc. Major components, key integrations, notable technical decisions worth bragging about (e.g., provider-agnostic abstractions, security posture).]

## Outcomes & Success Metrics

[How we know this is working — targets set, and actuals where known. Mix of user-facing signals and business objectives. Measurable, not vague.]

## Marketing Angles & Talking Points

[Literal, reusable copy — headline options, key phrases, proof points, and likely objections with responses. This section exists so a human or AI can lift text directly into a leaflet, deck, or one-pager without re-deriving it from the narrative sections above.]

- **Headline options:** [...]
- **Proof points:** [...]
- **Anticipated objections & responses:** [...]

## Vision / Roadmap

[Where this goes if it succeeds — 1-3 year horizon. Inspiring but grounded; distinguish committed roadmap from aspiration.]

## Source Documents

[Traceability back to the artifacts this round-up synthesizes — PRD, product brief(s), architecture doc, epics/stories. Lets a reader (or an AI) go deeper on any claim made above.]

- [...]
```
