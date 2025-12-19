# Validation Session

{{include:start/includes/WORKTREE_CONFINEMENT.md}}

## Purpose

This session is for running validators only, not implementation.

## Pre-Validation Checklist

1. ✅ Read validator constitution: `{{PROJECT_EDISON_DIR}}/_generated/constitutions/VALIDATORS.md`
2. ✅ Load validator roster: `{{PROJECT_EDISON_DIR}}/_generated/AVAILABLE_VALIDATORS.md`
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

{{include:start/includes/SESSION_STATE_MACHINE.md}}

## Constitution Reference

Your full validator instructions are at: `{{PROJECT_EDISON_DIR}}/_generated/constitutions/VALIDATORS.md`
