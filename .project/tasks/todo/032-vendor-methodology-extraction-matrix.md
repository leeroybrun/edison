---
id: "032-vendor-methodology-extraction-matrix"
title: "Planning: vendor methodology extraction matrix (Spec‑Kit/OpenSpec/BMAD → Edison commands/CLIs)"
type: docs
owner:
session_id:
parent_id:
child_ids:
depends_on:
  - "028-task-remediate-audit-slash-command"
  - "26.12-wave4-plan-analysis-and-correct-course"
  - "031-commands-definition-validation-and-lint"
blocks_tasks:
related:
  - "020-docs-and-examples-vendors-skills"
claimed_at:
last_active:
continuation_id:
created_at: "2025-12-31T00:00:00Z"
updated_at: "2025-12-31T00:00:00Z"
tags:
  - docs
  - prompts
  - commands
  - vendors
priority: medium
estimated_hours:
model:
---

# Planning: vendor methodology extraction matrix (Spec‑Kit/OpenSpec/BMAD → Edison commands/CLIs)

## Summary

To ensure we truly “extract and integrate all good ideas” from Spec‑Kit/OpenSpec/BMAD, we need a canonical mapping artifact that:
- enumerates the specific patterns we’re adopting (guardrails, checklists, severity rubrics, validator UX, bounded clarification loops)
- maps each pattern to Edison features:
  - deterministic CLIs
  - slash-command prompts
  - constitutions/guidelines
- identifies gaps (patterns not yet implemented or planned)

This prevents drift and prevents repeating “we were inspired by X” without actually capturing it in Edison’s backlog.

## Required Reading

- Spec‑Kit templates:
  - `spec-kit/templates/commands/analyze.md`
  - `spec-kit/templates/commands/plan.md`
  - `spec-kit/templates/commands/tasks.md`
  - `spec-kit/templates/commands/clarify.md`
- OpenSpec validate UX:
  - `OpenSpec/src/commands/validate.ts`
- BMAD checklist/correct-course workflow:
  - `BMAD-METHOD/.../correct-course/checklist.md`

## Objectives

- [ ] Create a canonical planning doc under `.project/plans/`, e.g.:
  - `.project/plans/vendor-methodology-extraction-matrix.md`
- [ ] The doc must include:
  - a “Patterns” section listing each adopted pattern with a short description
  - a mapping table: `Vendor source` → `Pattern` → `Edison artifact(s)` → `Status (planned/implemented)` → `Owner task`
  - a “Gaps” section that points to missing Edison tasks (create new tasks if required)
- [ ] Update related tasks (if needed) so every adopted pattern has an implementation owner.

## Acceptance Criteria

- [ ] Every major vendor pattern we care about is mapped to at least one Edison task.
- [ ] The mapping doc clearly separates:
  - deterministic CLI responsibilities
  - LLM prompt responsibilities (slash commands)
  - constitution/guideline responsibilities
- [ ] Gaps are explicit and actionable (new tasks exist for missing pieces).

## Files to Create/Modify

```
# Add
.project/plans/vendor-methodology-extraction-matrix.md
```
