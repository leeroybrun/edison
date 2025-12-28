---
id: 006-task-group-helper
title: 'Chore: task group helper'
created_at: '2025-12-28T10:00:55Z'
updated_at: '2025-12-28T10:00:55Z'
tags:
  - edison-core
  - tasks
  - validation
  - ux
depends_on:
  - 002-prompts-constitutions-compaction
  - 014-task-relationships-cleanup
---
# Chore: task group helper

<!-- EXTENSIBLE: Summary -->
## Summary

Add an ergonomic helper command to group child tasks under a parent task so grouped/bundle validation is easy to use and discoverable.

<!-- /EXTENSIBLE: Summary -->

<!-- EXTENSIBLE: Wave -->
## Wave / Parallelization

- **Wave:** 4 (UX helpers)
- **Safe to run in parallel with:** `008-cli-ergonomics-paths-aliases` (different CLI modules)
- **Do not run in parallel with:** `002-prompts-constitutions-compaction` (both may touch `docs/WORKFLOWS.md`)

<!-- /EXTENSIBLE: Wave -->

<!-- EXTENSIBLE: ProblemStatement -->
## Problem Statement

Edison already supports grouped validation via parent/child + `edison qa bundle` / `edison qa validate`, but it’s not discoverable and can be tedious to set up manually.

Beta testers explicitly requested grouped validation so that many small/trivial changes can be validated as one bundle rather than independently.

<!-- /EXTENSIBLE: ProblemStatement -->

<!-- EXTENSIBLE: Objectives -->
## Objectives

<!-- List specific, measurable objectives with checkboxes -->
- [ ] Add a CLI helper to create/link a parent task and attach children deterministically (parent/child is the single bundling mechanism; do not add a second bundle system).
- [ ] Ensure the helper uses existing linking/persistence (no manual file moves).
- [ ] Update docs/guidelines to recommend grouped validation for small/trivial sibling tasks.

<!-- /EXTENSIBLE: Objectives -->

<!-- EXTENSIBLE: AcceptanceCriteria -->
## Acceptance Criteria

<!-- List specific criteria that must be met for task completion -->
- [ ] New command exists, e.g. `edison task group <parent> <child...>` (exact naming up to implementation, but must be documented in `docs/WORKFLOWS.md` and CLI `--help`).
- [ ] Grouping updates parent/child relationships using canonical repository semantics (TaskRepository / existing `edison task link` behavior), not manual file editing/moves.
- [ ] Helper supports an ergonomic “create parent” path (optional but strongly preferred), e.g.:
  - `edison task group --create-parent --title "<title>" <child...>`
  - or `edison task group create "<title>" <child...>`
- [ ] After grouping, `edison qa bundle <parent>` includes the children in the manifest.
- [ ] Docs/guidelines mention this workflow as the recommended grouped validation path.
- [ ] Unit tests cover linking behavior and manifest inclusion.

<!-- /EXTENSIBLE: AcceptanceCriteria -->

<!-- EXTENSIBLE: TechnicalDesign -->
## Technical Design

Constraints:
- Do not introduce a second “bundle system”. Use existing parent/child linking and existing bundler.
- Avoid duplicating linking logic; reuse existing semantics:
  - linking is stored in task frontmatter (`parent_id` + `child_ids`)
  - `edison task link` already implements cycle/overwrite protection

Implementation outline:
1) CLI:
   - Add `edison task group` as a thin wrapper that:
     - resolves/creates the parent task id
     - links each child using shared linking logic (keep DRY with `task link`)
     - prints the exact bundle validation commands (`edison qa bundle <parent>`, `edison qa validate <parent> ...`)
   - The command must not require a session: grouping is stored in task files.

2) DRY core reuse:
   - Prefer factoring the linking logic currently embedded in `src/edison/cli/task/link.py` into a small reusable helper (so `task link` and `task group` share validation/cycle detection), OR route both through a new `TaskLinkService` in core.

3) Docs:
   - Update `docs/WORKFLOWS.md` (and/or validation guideline) to recommend: “Bundle small siblings under a parent; validate once.”

<!-- /EXTENSIBLE: TechnicalDesign -->

<!-- EXTENSIBLE: FilesToModify -->
## Files to Create/Modify

<!-- List files that will be changed -->
```
# Create
src/edison/cli/task/group.py (or a task subcommand group)

# Modify (only if needed; prefer reuse)
src/edison/core/task/workflow.py
src/edison/cli/task/link.py (only if extracting a shared helper to avoid duplication)
src/edison/core/task/linking.py (optional new helper, to keep `link`/`group` DRY)
docs/WORKFLOWS.md and/or orchestrator validation guidelines
src/edison/core/qa/bundler/manifest.py (should already work; modify only if needed)
tests/**/*
```

<!-- /EXTENSIBLE: FilesToModify -->

<!-- EXTENSIBLE: TDDEvidence -->
## TDD Evidence

### RED Phase
<!-- Link to failing test output -->
- Test file: 
- Output: 

### GREEN Phase
<!-- Link to passing test output -->
- Output: 

### REFACTOR Phase
<!-- Notes on refactoring performed -->
- Notes: 

<!-- /EXTENSIBLE: TDDEvidence -->

<!-- EXTENSIBLE: VerificationChecklist -->
## Verification Checklist

- [ ] `pytest -q` passes
- [ ] `edison task group <parent> <child...>` links tasks without manual editing
- [ ] `edison qa bundle <parent>` includes all children
- [ ] Docs mention grouped validation and point to the helper command

<!-- /EXTENSIBLE: VerificationChecklist -->

<!-- EXTENSIBLE: SuccessCriteria -->
## Success Criteria

Creating a “bundle parent” becomes a 1-command operation, making grouped validation the default for many tiny sibling tasks.

<!-- /EXTENSIBLE: SuccessCriteria -->

<!-- EXTENSIBLE: RelatedFiles -->
## Related Files

- Existing parent/child linking CLI: `src/edison/cli/task/link.py`
- Task linking fields (single source of truth): `src/edison/core/task/models.py`
- Bundle manifest builder: `src/edison/core/qa/bundler/manifest.py`
- Workflows docs: `docs/WORKFLOWS.md`

<!-- /EXTENSIBLE: RelatedFiles -->

<!-- EXTENSIBLE: Notes -->
## Notes

This task is intentionally small: it should make an existing capability easy to use, not introduce new validation semantics.

<!-- /EXTENSIBLE: Notes -->
