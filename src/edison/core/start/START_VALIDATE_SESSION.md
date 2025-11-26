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
   - Wave 1: Global validators (codex-global, claude-global)
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

## Constitution Reference

Your full validator instructions are at: `constitutions/VALIDATORS.md`
