# Edison State Machine Guards

This document defines the canonical task and QA state machines and how guards are enforced across the Edison core CLIs.

## Domains and States

### Task

State names: {{fn:state_names("task")}}

{{fn:state_diagram("task")}}

### QA

State names: {{fn:state_names("qa")}}

{{fn:state_diagram("qa")}}

The authoritative definition lives in `{{fn:project_config_dir}}/_generated/STATE_MACHINE.md` and is loaded by `lib/task.validate_state_transition`.

## Enforcement Points

- `tasks/status`: Calls `validate_state_transition` before any move and gates `… → done` via `tasks/ready`.
- `tasks/ready`: Enforces completion requirements (implementation report, evidence files, validator config/TDD rules) and fails closed.
- Pre-commit hook: `.git/hooks/pre-commit` invokes `edison git-hooks precommit-check` to block invalid staged renames under `{{fn:tasks_root}}/` and `{{fn:qa_root}}/`.

## Failure Mode (Fail-Closed)

- Any missing config, missing status, or concurrent lock results in a clear error and the transition is denied.
- Errors include helpful context and list the violated rules where applicable.

## Examples

- Allowed: `task todo → wip`, `qa waiting → todo`, `task done → validated` (with approvals).
- Blocked: `task todo → validated`, `qa todo → validated`, non-adjacent skips.

See tests under `tests/unit/framework/test_state_machine_guards.py` covering valid/invalid paths and edge cases.
