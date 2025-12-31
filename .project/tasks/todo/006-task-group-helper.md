---
id: 006-task-group-helper
title: 'Chore: task bundle helper (group tasks for validation)'
created_at: '2025-12-28T10:00:55Z'
updated_at: '2025-12-28T15:47:58Z'
tags:
  - edison-core
  - tasks
  - validation
  - ux
depends_on:
  - 027-qa-bundle-scopes-and-guards
related:
  - 002-prompts-constitutions-compaction
  - 008-cli-ergonomics-paths-aliases
---
# Chore: task bundle helper (group tasks for validation)

<!-- EXTENSIBLE: Summary -->
## Summary

Add an ergonomic helper command to group arbitrary tasks into a **validation bundle** (without creating “fake parent tasks”), so bundle validation is easy to use and discoverable.

<!-- /EXTENSIBLE: Summary -->

<!-- EXTENSIBLE: Wave -->
## Wave / Parallelization

- **Wave:** 4 (UX helpers)
- **Safe to run in parallel with:** `008-cli-ergonomics-paths-aliases` (different CLI modules)
- **Do not run in parallel with:** `002-prompts-constitutions-compaction` (both may touch `docs/WORKFLOWS.md`)

<!-- /EXTENSIBLE: Wave -->

<!-- EXTENSIBLE: ProblemStatement -->
## Problem Statement

Edison supports bundle validation, but historically it has been “hidden” behind parent/child hierarchy: users create “fake parent tasks” just to validate a set of small peer tasks as one bundle. This couples **hierarchy** (decomposition/follow-ups) to **validation grouping**.

Beta testers explicitly requested grouped validation so that many small/trivial changes can be validated as one bundle rather than independently.

<!-- /EXTENSIBLE: ProblemStatement -->

<!-- EXTENSIBLE: Objectives -->
## Objectives

<!-- List specific, measurable objectives with checkboxes -->
- [ ] Add a CLI helper to group tasks into a validation bundle **without** parent/child (no “fake parent tasks”).
- [ ] Ensure the helper uses canonical relationship mutation semantics (relationship service/registry), not manual file edits.
- [ ] Update docs/guidelines to recommend grouped validation for small/trivial sibling tasks.

<!-- /EXTENSIBLE: Objectives -->

<!-- EXTENSIBLE: AcceptanceCriteria -->
## Acceptance Criteria

<!-- List specific criteria that must be met for task completion -->
- [ ] New command exists: `edison task bundle ...` (exact subcommands up to implementation, but must be documented in `docs/WORKFLOWS.md` and CLI `--help`).
- [ ] `edison task bundle add --root <root> <member...>` sets the `bundle_root` relationship for each member deterministically (fails closed unless `--force`).
- [ ] `edison task bundle remove <member...>` clears bundle membership (deterministic, idempotent).
- [ ] `edison task bundle show <task>` prints the resolved root + the computed member list.
- [ ] After grouping, `edison qa bundle <root> --scope bundle` includes all members in the manifest (bundle scopes are implemented in `027-qa-bundle-scopes-and-guards`).
- [ ] Docs/guidelines mention this workflow as the recommended grouped validation path.
- [ ] Tests cover the CLI mutations and the QA manifest inclusion for bundle scope.

<!-- /EXTENSIBLE: AcceptanceCriteria -->

<!-- EXTENSIBLE: TechnicalDesign -->
## Technical Design

Constraints:
- Do not rely on parent/child hierarchy for validation bundling.
- Bundle membership must be represented explicitly as a task relationship (see `plan-2-validation-bundles.md`).
- Avoid duplicating relationship mutation logic: reuse the canonical `TaskRelationshipService` (or equivalent) introduced by the task relationship refactor (`010–014`).

Implementation outline:
1) CLI:
   - Add `edison task bundle` (or equivalent) that:
     - sets/clears `bundle_root` membership on tasks (no parent/child edits)
     - prints the exact bundle validation commands:
       - `edison qa bundle <root> --scope bundle`
       - `edison qa validate <root> --scope bundle --execute`
   - The command must not require a session: bundle membership is stored in task files.

2) DRY core reuse:
   - Route CLI mutations through the canonical relationship mutation surface (service/registry), not ad-hoc frontmatter edits.

3) Docs:
   - Update `docs/WORKFLOWS.md` (and/or validation guideline) to recommend: “Bundle small siblings/peers with `edison task bundle`; validate once.”

<!-- /EXTENSIBLE: TechnicalDesign -->

<!-- EXTENSIBLE: FilesToModify -->
## Files to Create/Modify

<!-- List files that will be changed -->
```
# Create
src/edison/cli/task/bundle.py (or a task subcommand bundle)

# Modify (only if needed; prefer reuse)
src/edison/core/task/relationships/** (canonical relationships registry/types/services)
docs/WORKFLOWS.md and/or orchestrator validation guidelines
src/edison/core/qa/bundler/manifest.py (add `--scope bundle` support)
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
- [ ] `edison task bundle add --root <root> <member...>` persists membership without manual editing
- [ ] `edison qa bundle <root> --scope bundle` includes all members
- [ ] Docs mention grouped validation and point to the helper command

<!-- /EXTENSIBLE: VerificationChecklist -->

<!-- EXTENSIBLE: SuccessCriteria -->
## Success Criteria

Creating a “validation bundle” becomes a 1-command operation, making grouped validation the default for many tiny peer tasks (without inventing fake hierarchy).

<!-- /EXTENSIBLE: SuccessCriteria -->

<!-- EXTENSIBLE: RelatedFiles -->
## Related Files

- Existing relationship CLIs: `src/edison/cli/task/link.py`, `src/edison/cli/task/relate.py`
- Canonical task relationship model: `src/edison/core/task/relationships/**` (introduced in `010–014`)
- Bundle manifest builder: `src/edison/core/qa/bundler/manifest.py`
- Workflows docs: `docs/WORKFLOWS.md`

<!-- /EXTENSIBLE: RelatedFiles -->

<!-- EXTENSIBLE: Notes -->
## Notes

This task is intentionally small: it should make an existing capability easy to use, not introduce new validation semantics.

<!-- /EXTENSIBLE: Notes -->
