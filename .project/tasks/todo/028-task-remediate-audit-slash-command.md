---
id: "028-task-remediate-audit-slash-command"
title: "Slash command: task-remediate-audit (approval-gated remediation from deterministic audit)"
type: docs
owner:
session_id:
parent_id:
child_ids:
depends_on:
  - "006-task-group-helper"
blocks_tasks:
related:
  - "010-task-relationships-registry"
  - "011-task-relationships-mutators"
  - "012-task-relationships-consumers"
  - "026.9-wave4-slash-commands-and-start-plan-mode"
claimed_at:
last_active:
continuation_id:
created_at: "2025-12-31T00:00:00Z"
updated_at: "2025-12-31T00:00:00Z"
tags:
  - tasks
  - prompts
  - commands
  - planning
priority: high
estimated_hours:
model:
---

# Slash command: task-remediate-audit (approval-gated remediation from deterministic audit)

## Summary

Add a high-value Edison core slash command `/edison.task-remediate-audit` that turns deterministic backlog signals into a safe, approval-gated remediation plan.

It MUST:
- Ground itself in `edison task audit --json` output (deterministic evidence).
- Produce a Spec‑Kit/OpenSpec/BMAD-style structured report (severity, evidence, stable IDs).
- Propose concrete edits (frontmatter + “Files to Create/Modify”) but **never apply them** without explicit approval.

## Required Reading

- `src/edison/data/commands/task/task-audit.md` (existing audit workflow prompt)
- `src/edison/data/commands/task/task-backlog-coherence.md` (structured read-only report pattern)
- Optional vendor references (if available; do not block if missing):
  - Spec‑Kit analyze methodology: `spec-kit/templates/commands/analyze.md`
  - OpenSpec validate UX: `OpenSpec/src/commands/validate.ts`
  - BMAD checklist style: `BMAD-METHOD/.../correct-course/checklist.md`

## Objectives

- [ ] Add command definition file: `src/edison/data/commands/task/task-remediate-audit.md`.
- [ ] The command must instruct the LLM to collect:
  - `edison task audit --json --tasks-root .project/tasks`
  - optionally `edison task waves --json` (for parallelization constraints)
- [ ] The command must define a strict remediation taxonomy with stable IDs:
  - `R*` (Relationship fixes: implicit_reference → add `depends_on`/`related`/`blocks_tasks`)
  - `C*` (Collision fixes: unordered `file_overlap` → add ordering or refactor ownership)
  - `D*` (Duplicate candidates: unify/scope split/merge proposals)
- [ ] The command must implement **halt conditions** (BMAD style):
  - if audit JSON is missing/unparseable
  - if tasks root not found
  - if prerequisites fail (stop and report)
- [ ] The command must include a strict **Ask/Approval gate**:
  - “Do you want me to apply these task edits now?”
  - If approved, it must propose a minimal patch plan first (no broad rewrites).

## Patch Plan Format (REQUIRED)

The command MUST specify a machine-reviewable “proposed edits” format so an implementer can apply it safely:

### A) Frontmatter edits (preferred)

For each task, propose minimal changes as YAML fragments (not full-file rewrites):
- Add `depends_on` when ordering is required (true prerequisite or collision ordering).
- Add `related` when tasks are conceptually linked but not ordered.
- Add `blocks_tasks` only when it is truly blocking.

### B) Body edits (only when needed)

If remediation requires changing file targets, edits MUST be limited to the task’s:
- `## Files to Create/Modify` fenced code block

### C) Output format for proposed edits

For each task, output:

1) `Task: <id>`
2) `Why` (cite audit evidence fields: mentioned ids, unordered pairs, file paths, waves)
3) `Proposed frontmatter patch:` (YAML fragment)
4) `Proposed body patch:` (only if required; minimal)

## Relationship Heuristics (so LLM decisions are consistent)

When choosing relationship types:
- Prefer `depends_on` when:
  - one task’s acceptance criteria require an artifact produced by another task
  - unordered `file_overlap` indicates true competing edits and ordering resolves it
- Prefer `related` when:
  - tasks touch the same subsystem but can be implemented independently
  - the mention is conceptual (“see also”) not a prerequisite
- Prefer “no link” when:
  - it’s a non-actionable mention or historical reference

## Output Format (STRICT)

The slash command output must be a single Markdown report (no file writes) containing:
1) Executive summary (counts, top risks)
2) Findings table:
   - `ID` (stable, e.g. `R1`, `C2`)
   - `Severity` (CRITICAL/HIGH/MEDIUM/LOW)
   - `Evidence` (task IDs, file paths, wave numbers)
   - `Recommendation` (read-only)
3) Proposed edits (patch plan), in a machine-reviewable structure:
   - per task: “frontmatter changes” + “body section changes”
4) Ask gate (explicit approval required)

## Acceptance Criteria

- [ ] The command definition is composable and layered like other Edison commands (markdown definition file).
- [ ] Remediation proposals are minimal, targeted, and evidence-cited.
- [ ] No edits are applied without explicit approval.
- [ ] Methodology clearly reflects Spec‑Kit/OpenSpec/BMAD best practices (guardrails, severity rubric, structured output, halt conditions).

## Files to Create/Modify

```
# Add
src/edison/data/commands/task/task-remediate-audit.md
```
