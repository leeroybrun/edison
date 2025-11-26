# Validation Session

## Purpose

This session is for running validators only, not implementation.

## Pre-Validation Checklist

1. ✅ Read validator constitution: `constitutions/VALIDATORS.md`
2. ✅ Load validator roster: `AVAILABLE_VALIDATORS.md`
3. ✅ Identify tasks ready for validation: `edison tasks list --status=ready`

## Validation Protocol

For each task ready for validation:

1. **Load Bundle**: Read the task's implementation report and evidence
2. **Run Validators**: Execute validation in waves
   - Wave 1: Global validators (global-codex, global-claude)
   - Wave 2: Critical validators (security, performance)
   - Wave 3: Specialized validators (triggered by file patterns)
3. **Collect Results**: Aggregate verdicts from all validators
4. **Make Decision**:
   - All pass → APPROVE
   - Any blocking fail → REJECT
   - Non-blocking issues → APPROVE with notes

## Validation Commands

```bash
# Validate a specific task
edison validate <task-id>

# Validate all ready tasks
edison validate --all-ready
```

## Session State Machine

Read the generated state machine reference in `STATE_MACHINE.md` (under `_generated`).
Follow the allowed transitions for session, task, and QA domains defined there—do
not assume defaults. Use `edison session next` to stay aligned with the configured
state machine during validation-only sessions.

Valid state transitions:
- NEW → WIP → READY → VALIDATING → COMPLETE

Transition triggers:
- NEW → WIP: claim a task (`edison tasks claim <task-id>`)
- WIP → READY: mark ready after TDD green and evidence
- READY → VALIDATING: run validators (`edison validate <task-id>`)
- VALIDATING → COMPLETE: validators approve with no blockers

State diagram: See `STATE_MACHINE.md` for the canonical diagram (no embedded copies here).

## Constitution Reference

Your full validator instructions are at: `constitutions/VALIDATORS.md`
