---
id: "029-task-codebase-coherence-audit"
title: "Slash commands: task↔codebase coherence (avoid duplicate/competing implementations)"
type: docs
owner:
session_id:
parent_id:
child_ids:
depends_on:
  - "028-task-remediate-audit-slash-command"
blocks_tasks:
related:
  - "015-vendors-core-and-cli"
  - "020-docs-and-examples-vendors-skills"
claimed_at:
last_active:
continuation_id:
created_at: "2025-12-31T00:00:00Z"
updated_at: "2025-12-31T00:00:00Z"
tags:
  - tasks
  - prompts
  - commands
  - architecture
priority: high
estimated_hours:
model:
---

# Slash commands: task↔codebase coherence (avoid duplicate/competing implementations)

## Summary

Add Edison core slash commands that help ensure backlog tasks (and plan-generated tasks) are coherent against the *current* codebase:
- prevent duplicated/competing modules/APIs
- enforce “single canonical owner” boundaries
- detect likely collisions on shared surfaces (exports, registries, schemas, config roots)

This is intentionally “LLM + deterministic evidence”:
- deterministic: `edison task audit --json`, `edison task waves --json`
- LLM: interprets architecture intent and proposes unification boundaries

## Required Reading

- Existing Edison task audit commands/prompts:
  - `src/edison/data/commands/task/task-audit.md`
  - `src/edison/data/commands/task/task-backlog-coherence.md`
- Spec‑Kit analyze methodology: `/tmp/edison-vendor-commands/spec-kit/templates/commands/analyze.md`
- BMAD checklist patterns: `/tmp/edison-vendor-commands/BMAD-METHOD/src/modules/bmgd/workflows/4-production/correct-course/checklist.md`

## Objectives

- [ ] Add a new command definition: `src/edison/data/commands/task/task-codebase-coherence.md`.
- [ ] Add a new command definition: `src/edison/data/commands/plan/plan-codebase-coherence.md`.
- [ ] Both commands must instruct the LLM to:
  1) Gather deterministic backlog signals (`task audit`, `task waves`).
  2) Search the codebase for existing canonical implementations and ownership surfaces:
     - registries/services
     - schema/config roots
     - exports/wiring modules
  3) Produce a structured “coherence report” with:
     - stable findings IDs
     - severity rubric
     - evidence citations (task IDs + file paths + existing code symbols/files)
     - recommended canonical ownership assignments
     - explicit “Ask” gate before proposing edits to tasks/plans

## Output Format (STRICT)

Markdown report with:
- Executive summary
- Findings table (`ID`, `Category`, `Severity`, `Evidence`, `Recommendation`)
- Canonical ownership map:
  - `Subsystem` → `Owner task/plan item` → `Consumer tasks`
- Ask gate (approval required before any edits)

## Acceptance Criteria

- [ ] Commands clearly describe how to avoid duplicated helpers/APIs by choosing canonical owners.
- [ ] Commands remain read-only by default and require approval for any suggested edits.
- [ ] Commands are reusable across projects (no Edison-repo-specific assumptions baked into the prompt beyond “run edison task audit/waves when available”).

## Files to Create/Modify

```
# Add
src/edison/data/commands/task/task-codebase-coherence.md
src/edison/data/commands/plan/plan-codebase-coherence.md
```
