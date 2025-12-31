---
id: 004-stale-sessions-resumable
title: 'Chore: stale sessions resumable'
created_at: '2025-12-28T10:00:55Z'
updated_at: '2025-12-28T10:00:55Z'
tags:
  - edison-core
  - sessions
  - recovery
depends_on:
  - 001-session-id-inference
related:
  - 002-prompts-constitutions-compaction
  - 003-validation-presets
---
# Chore: stale sessions resumable

<!-- EXTENSIBLE: Summary -->
## Summary

Sessions should become “stale” after inactivity (warn/flag), but must remain resumable. Remove hard blocks that force cleanup/migration and provide explicit, non-destructive CLIs for listing/resuming stale sessions.

<!-- /EXTENSIBLE: Summary -->

<!-- EXTENSIBLE: Wave -->
## Wave / Parallelization

- **Wave:** 2 (session lifecycle)
- **Safe to run in parallel with:** `003-validation-presets` (no shared files)
- **Do not run in parallel with:** `002-prompts-constitutions-compaction` (that task edits `src/edison/data/start/START_CONTINUE_STALE.md` and docs; coordinate to avoid merge conflicts)

<!-- /EXTENSIBLE: Wave -->

<!-- EXTENSIBLE: ProblemStatement -->
## Problem Statement

Current behavior treats “expired sessions” as unusable:
- after inactivity, some workflows refuse to operate in the session
- users/LLMs are forced into `cleanup-expired` and task migration to continue work

This is not desired. We still want to detect staleness and optionally clean up, but staleness must not hard-block continuation by default.

Additionally, Edison must never ship start prompts that reference non-existent commands for stale/resume workflows.

<!-- /EXTENSIBLE: ProblemStatement -->

<!-- EXTENSIBLE: Objectives -->
## Objectives

<!-- List specific, measurable objectives with checkboxes -->
- [ ] Replace “expired means unusable” semantics with “stale means warn/flag” (resumable by default).
- [ ] Remove hard blocks preventing claiming/completing tasks in stale sessions (unless explicitly configured).
- [ ] Add explicit session lifecycle CLIs:
  - `edison session stale --list` (non-destructive; list stale sessions and optionally their last activity)
  - `edison session resume <session-id>` (helper to continue a session; prints env guidance; in worktrees may set `.session-id` via existing `edison session me --set`)
  - `edison session cleanup-stale` (explicit destructive cleanup; restore records + close)
- [ ] Update prompts/docs to reference only real CLIs.
- [ ] Maintain backward compatibility: keep `edison session cleanup-expired` working, but ensure it is never *required* just to continue a session.

<!-- /EXTENSIBLE: Objectives -->

<!-- EXTENSIBLE: AcceptanceCriteria -->
## Acceptance Criteria

<!-- List specific criteria that must be met for task completion -->
- [ ] A “stale” session can still be used: `edison task claim`, `edison task ready`, and other session-scoped operations do not fail solely due to inactivity timeout.
- [ ] Staleness is detectable and listable via `edison session stale --list`.
- [ ] Destructive cleanup is explicit/opt-in (not an automatic forced behavior).
- [ ] `src/edison/data/start/START_CONTINUE_STALE.md` can be updated to reference only real commands and match actual behavior (this prompt update is implemented in task `002-prompts-constitutions-compaction`; this task provides the missing CLIs/semantics).
- [ ] Tests cover staleness detection and “resumable by default” semantics.
- [ ] Existing `edison session cleanup-expired` behavior remains available as an explicit destructive cleanup path (may be documented as “cleanup stale/expired” but is not required for continuation).

<!-- /EXTENSIBLE: AcceptanceCriteria -->

<!-- EXTENSIBLE: TechnicalDesign -->
## Technical Design

Constraints:
- Avoid duplicated “stale detection” logic. Continue using existing session recovery config and helpers as the canonical place.
- Keep destructive operations behind explicit commands/flags.

Implementation outline:
1) Semantics:
   - Rename semantics in UX (docs/prompt/CLI output): “expired” → “stale due to inactivity”.
   - Keep the existing detection implementation in `src/edison/core/session/lifecycle/recovery.py:is_session_expired` as the canonical detector (optionally rename later), but stop using it as a *hard blocker* in core workflows by default.
   - Add a config flag for strictness (default false), e.g. `session.recovery.blockOnStale: false`, so projects can opt into hard-blocking if they truly want it.

2) Workflow changes:
   - Update `src/edison/core/task/workflow.py:TaskQAWorkflow.claim_task()` to remove the hard refusal that throws when `is_session_expired()` is true.
   - Replace with: warn + append to session activity log (there is already `append_session_log()` in `src/edison/core/session/lifecycle/recovery.py`).
   - If `session.recovery.blockOnStale` is enabled, keep the old fail-closed behavior.

3) New CLIs:
   - Implement `edison session stale --list` using SessionRepository listing + the canonical detector to identify stale sessions (do not implement a second detector).
   - Implement `edison session resume <id>` as an ergonomic helper that:
     - validates session id exists
     - prints `export AGENTS_SESSION=<id>` guidance (primary checkout)
     - in worktrees: may optionally call the existing `edison.core.session.current.set_current_session()` (same as `edison session me --set`) to persist `.session-id`
   - Implement `edison session cleanup-stale` as the explicit destructive path (restore records + transition to closing). It may call existing `restore_records_to_global_transactional()` + the same transition used by `cleanup_expired_sessions()`; do not duplicate those internals.
   - `edison task reclaim <task-id>` (referenced by START_CONTINUE_STALE) does not exist today; decide one of:
     - implement it as a thin wrapper over existing task transitions (likely `blocked|wip` → `wip`) with strong guards, or
     - update START_CONTINUE_STALE to use existing `edison task claim`/`edison task status` flows instead.

4) Prompts/docs:
   - Ensure start prompts do not reference missing commands.

<!-- /EXTENSIBLE: TechnicalDesign -->

<!-- EXTENSIBLE: FilesToModify -->
## Files to Create/Modify

<!-- List files that will be changed -->
```
# Create
src/edison/cli/session/stale.py (or a session subcommand group)
src/edison/cli/session/resume.py
src/edison/cli/session/cleanup_stale.py

# Modify
src/edison/core/task/workflow.py
src/edison/core/session/lifecycle/recovery.py
docs/WORKFLOWS.md and/or orchestrator guidelines
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
- [ ] Creating a session and waiting past the stale threshold does not prevent continuing work in that session
- [ ] `edison session stale --list` reports stale sessions accurately
- [ ] `edison session resume <id>` provides correct guidance (and sets `.session-id` only in worktrees)
- [ ] Destructive cleanup requires explicit `cleanup-stale` command/flags

<!-- /EXTENSIBLE: VerificationChecklist -->

<!-- EXTENSIBLE: SuccessCriteria -->
## Success Criteria

Users can pause work and later resume the same session without forced cleanup/migration; cleanup remains available as an explicit opt-in.

<!-- /EXTENSIBLE: SuccessCriteria -->

<!-- EXTENSIBLE: RelatedFiles -->
## Related Files

- Stale detection + cleanup: `src/edison/core/session/lifecycle/recovery.py`
- Task claim workflow (stale block removal): `src/edison/core/task/workflow.py`
- Session config (timeout): `src/edison/data/config/session.yaml`
- Start prompt referencing stale workflow: `src/edison/data/start/START_CONTINUE_STALE.md`

<!-- /EXTENSIBLE: RelatedFiles -->

<!-- EXTENSIBLE: Notes -->
## Notes

Staleness should be a UX hint, not a forcing function. Cleanup remains valuable but must be opt-in.

<!-- /EXTENSIBLE: Notes -->
