---
id: 008-cli-ergonomics-paths-aliases
title: 'Chore: CLI ergonomics (paths + aliases)'
created_at: '2025-12-28T11:30:00Z'
updated_at: '2025-12-28T11:30:00Z'
tags:
  - edison-core
  - cli-ux
  - tasks
  - qa
depends_on:
  - 002-prompts-constitutions-compaction
---
# Chore: CLI ergonomics (paths + aliases)

<!-- EXTENSIBLE: Summary -->
## Summary

Improve CLI discoverability and reduce “where did my file go?” confusion by (1) printing the exact file path of claimed/updated records and (2) adding small ergonomic aliases (e.g. `edison task done <id>`).

This is intentionally a UX-only improvement: it must reuse existing canonical persistence and state-transition logic (no new workflow semantics).

<!-- /EXTENSIBLE: Summary -->

<!-- EXTENSIBLE: Wave -->
## Wave / Parallelization

- **Wave:** 4 (UX helpers)
- **Safe to run in parallel with:** `006-task-group-helper` (different CLI modules)
- **Do not run in parallel with:** tasks that change task claim/status output formats (coordinate if any future tasks do so)

<!-- /EXTENSIBLE: Wave -->

<!-- EXTENSIBLE: ProblemStatement -->
## Problem Statement

Beta testers were confused after claiming tasks because the record did not appear where they expected (they looked under `.project/tasks/wip/` but Edison uses session-scoped storage for claimed records).

Two concrete friction points:
- `edison task claim` output does not show the resolved file path of the claimed task/QA record.
- There is no simple `edison task done <id>` convenience command (must use `edison task status <id> --status done`), which makes it easier for LLMs to drift into ad-hoc tracking instead of updating Edison state.

Important: documentation fixes for where records live are handled elsewhere (see task `002-prompts-constitutions-compaction`). This task focuses on CLI outputs and ergonomic aliases so the “happy path” is discoverable at the moment of action.

<!-- /EXTENSIBLE: ProblemStatement -->

<!-- EXTENSIBLE: Objectives -->
## Objectives

- [ ] Update `edison task claim` to print the exact claimed record path (and include it in `--json` output).
- [ ] Update `edison task status` (inspect mode) to print the record’s on-disk path (and include it in `--json` output).
- [ ] Add `edison task done <task-id>` as an alias for `edison task status <task-id> --status done` (and document in `--help`).
- [ ] Keep all behavior DRY: do not duplicate repository path resolution or transition logic.

<!-- /EXTENSIBLE: Objectives -->

<!-- EXTENSIBLE: AcceptanceCriteria -->
## Acceptance Criteria

- [ ] `edison task claim <task-id>` (human output) prints:
  - claimed record id/type/state/session
  - **Path:** the resolved task file path (session-scoped path when claimed into a session)
- [ ] `edison task claim <task-id> --json` includes a `path` field that is a repo-root-relative path when possible.
- [ ] `edison task claim <task-id>-qa` (claiming QA) also prints/includes the correct QA record path.
- [ ] `edison task status <task-id>` (no `--status`) prints/includes the record path.
- [ ] New alias `edison task done <task-id>` exists and produces the same transition as `edison task status <task-id> --status done`.
- [ ] Unit tests cover the path fields and alias behavior (avoid brittle tests that depend on host filesystem outside a temp repo).

<!-- /EXTENSIBLE: AcceptanceCriteria -->

<!-- EXTENSIBLE: TechnicalDesign -->
## Technical Design

Constraints:
- Do not introduce alternate path resolution logic. Reuse repository APIs (`TaskRepository.get_path()`, `QARepository.get_path()`) or the existing session-scoped mixin behavior.
- Do not re-implement claim/transition semantics. Reuse `TaskQAWorkflow.claim_task()` and repository transitions.

Implementation outline:
1) `task claim` output:
   - After claiming, call `TaskRepository.get_path(task_id)` / `QARepository.get_path(qa_id)` to obtain the authoritative path.
   - Include `path` in the JSON output and print it in the human output.
   - Ensure the path printed matches the session-scoped storage behavior (i.e., it should point into `.project/sessions/.../<sessionId>/...` when claimed).

2) `task status` output (inspect mode):
   - Add `path` to the output payload and print it for human mode.

3) `task done` alias:
   - Implement as a thin CLI wrapper that delegates to the existing status transition path (do not fork logic).
   - Preferred implementation patterns:
     - Add a new CLI module `src/edison/cli/task/done.py` that internally imports and invokes `task.status.main()` with the correct args, OR
     - Extend the CLI dispatcher to register `done` as an alias to `status --status done`.

<!-- /EXTENSIBLE: TechnicalDesign -->

<!-- EXTENSIBLE: FilesToModify -->
## Files to Create/Modify

```
# Modify
src/edison/cli/task/claim.py
src/edison/cli/task/status.py

# Create (one option)
src/edison/cli/task/done.py

# Modify (depending on CLI dispatch structure)
src/edison/cli/task/__init__.py

# Tests
tests/**/*
```

<!-- /EXTENSIBLE: FilesToModify -->

<!-- EXTENSIBLE: TDDEvidence -->
## TDD Evidence

### RED Phase
- Test file:
- Output:

### GREEN Phase
- Output:

### REFACTOR Phase
- Notes:

<!-- /EXTENSIBLE: TDDEvidence -->

<!-- EXTENSIBLE: VerificationChecklist -->
## Verification Checklist

- [ ] `pytest -q` passes
- [ ] `edison task claim <id>` prints a `Path:` line
- [ ] `edison task claim <id> --json` includes `path`
- [ ] `edison task status <id> --json` includes `path`
- [ ] `edison task done <id>` transitions to semantic done

<!-- /EXTENSIBLE: VerificationChecklist -->

<!-- EXTENSIBLE: SuccessCriteria -->
## Success Criteria

After claiming a task, an LLM can immediately locate the record file without guessing the session-scoped directory structure, and can complete a task using a memorable alias command.

<!-- /EXTENSIBLE: SuccessCriteria -->

<!-- EXTENSIBLE: RelatedFiles -->
## Related Files

- Session-scoped record storage: `src/edison/core/entity/session_scoped.py`, `src/edison/core/session/paths.py`
- Task workflow claim: `src/edison/core/task/workflow.py`
- Docs drift fix (separate task): `.project/tasks/todo/002-prompts-constitutions-compaction.md`

<!-- /EXTENSIBLE: RelatedFiles -->

<!-- EXTENSIBLE: Notes -->
## Notes

This task intentionally does not change where records live; it only makes the location obvious at the moment Edison moves/uses the record.

<!-- /EXTENSIBLE: Notes -->
