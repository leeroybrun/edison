# Edison State Machine Guards

This document defines the canonical task and QA state machines and how guards are enforced across the Edison core CLIs.

## Domains and States

### Task

State names: {{fn:state_names("task")}}

{{fn:state_diagram("task")}}

### QA

State names: {{fn:state_names("qa")}}

{{fn:state_diagram("qa")}}

The authoritative definition lives in the composed state machine (run `edison read STATE_MACHINE`) and is loaded by `lib/task.validate_state_transition`.

## Enforcement Points

- `tasks/status`: Calls `validate_state_transition` before any move and gates `… → done` via `tasks/ready`.
- `tasks/ready`: Enforces completion requirements (implementation report, evidence files, validator config/TDD rules) and fails closed.
- Pre-commit hook: `.git/hooks/pre-commit` invokes `edison git-hooks precommit-check` to block invalid staged renames under `{{fn:tasks_root}}/` and `{{fn:qa_root}}/`.

## Failure Mode (Fail-Closed)

- Any missing config, missing status, or concurrent lock results in a clear error and the transition is denied.
- Errors include helpful context and list the violated rules where applicable.

## Examples

- Allowed: `task {{fn:semantic_state("task","todo")}} → {{fn:semantic_state("task","wip")}}`, `qa {{fn:semantic_state("qa","waiting")}} → {{fn:semantic_state("qa","todo")}}`, `task {{fn:semantic_state("task","done")}} → {{fn:semantic_state("task","validated")}}` (with approvals).
- Blocked: `task {{fn:semantic_state("task","todo")}} → {{fn:semantic_state("task","validated")}}`, `qa {{fn:semantic_state("qa","todo")}} → {{fn:semantic_state("qa","validated")}}`, non-adjacent skips.

See tests under `tests/unit/framework/test_state_machine_guards.py` covering valid/invalid paths and edge cases.
