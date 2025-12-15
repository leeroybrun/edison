# Validation Session

## Purpose

This session is for running validators only, not implementation.

## Pre-Validation Checklist

1. ✅ Read validator constitution: `.edison/_generated/constitutions/VALIDATORS.md`
2. ✅ Load validator roster: `.edison/_generated/AVAILABLE_VALIDATORS.md`
3. ✅ Identify tasks ready for validation: `edison task list --status=done`

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
edison qa validate <task-id>

# Validate all ready tasks
edison qa validate --all-ready
```

## Session State Machine

Read the generated state machine reference in `.edison/_generated/STATE_MACHINE.md`.
Follow the allowed transitions for session, task, and QA domains defined there—do
not assume defaults. Use `edison session next` to stay aligned with the configured
state machine.

Valid task state transitions:
- todo → wip → done → validated

Transition triggers (high level):
- todo → wip: claim a task (`edison task claim <task-id>`)
- wip → done: mark done after TDD green and evidence
- done → validated: validate via the QA workflow (`edison qa validate …`)

Task states can also transition to blocked if blockers are encountered.

State diagram: See `.edison/_generated/STATE_MACHINE.md` for the canonical diagram (no embedded copies here).

## Constitution Reference

Your full validator instructions are at: `.edison/_generated/constitutions/VALIDATORS.md`