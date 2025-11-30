# Edison State Machine Guards

This document defines the canonical task and QA state machines and how guards are enforced across the Edison core CLIs.

## Domains and States

- Task: `todo → wip ↔ blocked → done → validated` (reopen: `done → wip`, `wip → todo` allowed)
- QA: `waiting → todo → wip → done → validated` (reopen: `done → wip`)

The authoritative definition lives in `.edison/core/defaults.yaml` under `statemachine` and is loaded by `lib/task.validate_state_transition`.

## Enforcement Points

- `tasks/status`: Calls `validate_state_transition` before any move and gates `… → done` via `tasks/ready`.
- `tasks/ready`: Enforces completion requirements (implementation report, evidence files, validator config/TDD rules) and fails closed.
- Pre-commit hook: `.git/hooks/pre-commit` invokes `edison git-hooks precommit-check` to block invalid staged renames under `.project/tasks/` and `.project/qa/`.

## Failure Mode (Fail-Closed)

- Any missing config, missing status, or concurrent lock results in a clear error and the transition is denied.
- Errors include helpful context and list the violated rules where applicable.

## Examples

- Allowed: `task todo → wip`, `qa waiting → todo`, `task done → validated` (with approvals).
- Blocked: `task todo → validated`, `qa todo → validated`, non-adjacent skips.

See tests under `tests/unit/framework/test_state_machine_guards.py` covering valid/invalid paths and edge cases.

