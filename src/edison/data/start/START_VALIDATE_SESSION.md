# Validation Session

{{include:start/includes/WORKTREE_CONFINEMENT.md}}
{{include-section:guidelines/includes/EXECUTION_WRAPPER.md#principles}}

## Purpose

This session is for running validators only, not implementation.

## Pre-Validation Checklist

1. ✅ Read validator constitution: run `edison read VALIDATORS --type constitutions`
2. ✅ Load validator roster: run `edison read AVAILABLE_VALIDATORS`
3. ✅ Identify tasks ready for validation: `edison task list --status=done`
4. ✅ Verify evidence is complete: `edison evidence status <task-id>` for each task

## Validation Protocol

For each task ready for validation:

1. **Verify Evidence**: Check `edison evidence status <task-id>`
   - All required evidence files must exist
   - All command evidence must show `exitCode: 0`
   - If evidence is missing or failing, task is not ready for validation
2. **Load Bundle**: Read the task's implementation report and evidence
3. **Run Validators**: Execute validation in waves
   - Wave 1: Global validators (global-codex, global-claude)
   - Wave 2: Critical validators (security, performance)
   - Wave 3: Specialized validators (triggered by file patterns)
4. **Collect Results**: Aggregate verdicts from all validators
5. **Make Decision**:
   - All pass → APPROVE
   - Any blocking fail → REJECT
   - Non-blocking issues → APPROVE with notes

{{include-section:guidelines/includes/EVIDENCE_WORKFLOW.md#validator-check}}

## Validation Commands

```bash
# Validate a specific task
edison qa validate <task-id>

# Validate all ready tasks
edison qa validate --all-ready
```

{{include:start/includes/SESSION_STATE_MACHINE.md}}

## Constitution Reference

Your full validator instructions: run `edison read VALIDATORS --type constitutions`
