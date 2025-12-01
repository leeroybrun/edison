# Edison CLI Reference for Validators

## Overview

This guide covers CLI commands for validators who review implementation work, run validation checks, and produce validation reports. Validators focus on code quality, correctness, and compliance with project standards.

**Validator responsibilities:**
- Run validation checks on completed work
- Generate structured validation reports (JSON)
- Create validation bundles
- Assess code quality and test coverage
- Report blocking vs. advisory issues

## Commands

### Run Validation

```bash
edison validators validate --task <task-id> [--round <N>] [--session <session-id>]
```

**Purpose**: Validate validator reports for a task or bundle
**When to use**: After implementation is complete and task is in `done` state

**Options:**
- `--task`: Task ID (parent task in bundle mode)
- `--round`: Round number (defaults to latest)
- `--session`: Session ID for bundle mode (validates children)
- `--continuation-id`: Enforce continuationId across reports

**Example:**
```bash
# Validate latest round
edison validators validate --task TASK-123

# Validate specific round
edison validators validate --task TASK-123 --round 2

# Bundle mode (validate children in session)
edison validators validate --task TASK-123 --session sess-001

# Enforce continuation tracking
edison validators validate --task TASK-123 --continuation-id CONT-abc123
```

**Input location**: `.project/qa/validation-evidence/<task-id>/round-N/`
**Output**: `bundle-approved.json` or validation error report

---

### Check QA Status

```bash
edison qa status [--json]
```

**Purpose**: Check QA state and validation requirements
**When to use**: Understanding what needs validation

**Example:**
```bash
edison qa status --json
```

---

### Create Validation Bundle

```bash
edison qa bundle <task-id>
```

**Purpose**: Inspect evidence paths and child tasks before validation
**When to use**: Before running validation, to understand scope

**Example:**
```bash
edison qa bundle TASK-123
```

**Output:**
- Evidence directory structure
- Child task list
- Required validators
- Existing reports

---

### Start Validation Round

```bash
edison qa round --task <task-id> --status <status>
```

**Purpose**: Record validator outcomes for a validation round
**When to use**: After running validation checks

**Statuses:**
- `approved` - All checks pass
- `needs-work` - Issues found, requires fixes
- `blocked` - Blocking issues prevent progression

**Example:**
```bash
edison qa round --task TASK-123 --status approved
```

---

## Validation Report Format

Validators produce JSON reports in this structure:

**Location**: `.project/qa/validation-evidence/<task-id>/round-N/<validator-name>.json`

**Required fields:**
```json
{
  "validator": "<validator-name>",
  "task_id": "TASK-123",
  "round": 1,
  "timestamp": "2025-11-24T12:00:00Z",
  "status": "approved",
  "model": "<model-name>",
  "continuationId": "CONT-abc123",
  "issues": [
    {
      "severity": "blocking",
      "category": "testing",
      "description": "Missing test coverage for edge cases",
      "file": "src/utils/validator.ts",
      "line": 45,
      "suggestion": "Add tests for null and undefined inputs"
    }
  ],
  "summary": "Code quality is good. Identified 1 blocking issue requiring attention.",
  "metrics": {
    "files_reviewed": 8,
    "issues_found": 1,
    "test_coverage": 85.5
  }
}
```

**Issue severities:**
- `blocking` - Must be fixed before promotion
- `warning` - Should be fixed, not blocking
- `advisory` - Nice to have, optional

---

## Validator Types

### Global Validators (Always Run)

**Global validators** are defined in validator configuration:
- Check `{{PROJECT_EDISON_DIR}}/_generated/AVAILABLE_VALIDATORS.md` for current global validators
- Typically includes multiple models for diverse perspectives
- Most global validators are blocking

### Critical Validators

**security**: Security vulnerabilities (blocking)
**performance**: Performance issues (blocking)

### Specialized Validators (Triggered by File Patterns)

**api**: API endpoint validation
- Triggers: File patterns defined in validator configuration

**frontend-framework**: UI framework patterns
- Triggers: File patterns defined in validator configuration

**testing**: Test quality
- Triggers: File patterns defined in validator configuration

**ui-framework**: UI component patterns
- Triggers: File patterns defined in validator configuration

**database**: Database schema
- Triggers: File patterns defined in validator configuration

**styling**: Styling patterns
- Triggers: File patterns defined in validator configuration

---

## Common Workflows

### Full Validation Workflow

```bash
# 1. Check task is ready for validation
edison tasks status TASK-123

# Task should be in 'done' state with implementation-report.json

# 2. Inspect validation bundle
edison qa bundle TASK-123

# Review evidence directory and required validators

# 3. Run validation
edison validators validate --task TASK-123

# This checks all required validator reports exist

# 4. If issues found, record round status
edison qa round --task TASK-123 --status needs-work

# 5. After fixes, re-validate
edison validators validate --task TASK-123 --round 2

# 6. Record approval
edison qa round --task TASK-123 --status approved

# 7. Orchestrator promotes QA to validated
# (validators don't do this - orchestrator does)
```

### Bundle Validation (Multiple Tasks)

```bash
# 1. Check bundle scope
edison qa bundle TASK-123 --session sess-001

# Shows parent task + child tasks in session

# 2. Validate all tasks in bundle
edison validators validate --task TASK-123 --session sess-001

# Validates parent + all children

# 3. Output: bundle-approved.json
# Contains aggregated validation status for all tasks
```

### Incremental Validation (Rounds)

```bash
# Round 1: Initial validation
edison validators validate --task TASK-123 --round 1

# Issues found - developer fixes

# Round 2: Re-validate after fixes
edison validators validate --task TASK-123 --round 2

# Continue until approved
```

---

## Output Locations

**Validator reports**: `.project/qa/validation-evidence/<task-id>/round-N/<validator>.json`
**Bundle summary**: `.project/qa/validation-evidence/<task-id>/round-N/bundle-approved.json`
**Implementation report**: `.project/qa/validation-evidence/<task-id>/round-N/implementation-report.json`

---

## Validation Checklist

Before approving a task, validators should check:

### Code Quality
- [ ] Follows project coding standards
- [ ] No syntax errors or linting issues
- [ ] Proper error handling
- [ ] Code is readable and maintainable

### Testing
- [ ] Tests exist for new functionality
- [ ] Tests follow TDD patterns
- [ ] Test coverage meets requirements
- [ ] Tests are meaningful (not just coverage)

### Security
- [ ] No hardcoded secrets
- [ ] Input validation present
- [ ] Authentication/authorization correct
- [ ] No SQL injection vulnerabilities

### Best Practices
- [ ] Follows pack-specific guidelines
- [ ] TypeScript types are correct
- [ ] API contracts are validated
- [ ] Documentation is adequate

### Framework-Specific (Based on Active Packs)

Check active pack guidelines for framework-specific validation criteria:
- **Frontend Frameworks**: Routing patterns, component architecture
- **UI Libraries**: Component patterns, state management
- **Database Tools**: Schema design, migration strategy
- **Styling Systems**: Design tokens, responsive patterns

Refer to `{{PROJECT_EDISON_DIR}}/_generated/AVAILABLE_VALIDATORS.md` for active pack validators and their specific focus areas.

---

## Best Practices

1. **Be thorough but fair**: Find real issues, not nitpicks
2. **Provide actionable feedback**: Specific file/line references
3. **Use correct severities**: Reserve `blocking` for critical issues
4. **Write clear summaries**: Help developers understand findings
5. **Track continuations**: Use `continuationId` for multi-round validation
6. **Check all evidence**: Review implementation-report.json first
7. **Validate bundles holistically**: Check integration, not just individual tasks

---

## What Validators Should NOT Do

**❌ DO NOT run these commands** (orchestrator-only):
- `edison session next/start/status/close` - Session management
- `edison tasks claim/ready` - Task claiming and promotion
- `edison qa promote` - QA state transitions (orchestrator does this after validation)

**❌ DO NOT run these commands** (agent-only):
- `edison track start/complete` - Implementation tracking
- Task implementation commands

**✅ DO run:**
- Validation commands
- Bundle inspection commands
- QA status checks
- Report generation

---

## Related Documentation

- `.edison/_generated/guidelines/validators/VALIDATOR_GUIDELINES.md` - Full validator guidelines
- `.edison/_generated/guidelines/validators/VALIDATOR_WORKFLOW.md` - Validation workflow
- `.edison/_generated/guidelines/validators/OUTPUT_FORMAT.md` - Report format requirements
- `.edison/_generated/guidelines/validators/code-quality.md` - Code quality standards
- `.edison/_generated/guidelines/validators/testing.md` - Testing requirements

---

**Role**: Validator
**Focus**: Code review and quality assurance
**DO**: Validate work, generate reports, identify issues
**DON'T**: Claim tasks, manage sessions, implement features
