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
edison qa validate <task-id> [--scope <auto|hierarchy|bundle>] [--round <N>] [--session <session-id>] [--execute]
```

**Purpose**: Validate validator reports for a task or bundle
**When to use**: After implementation is complete and task is in `{{fn:semantic_state("task","done")}}` state

**Options:**
- `--scope`: Validation cluster selection (default: config or `auto`)
- `--round`: Round number (defaults to latest)
- `--session`: Session context (optional; used for worktree-aware file context when available)
- `--execute`: Execute validators and write reports (otherwise shows roster)

**Example:**
```bash
# Validate latest round
edison qa validate TASK-123

# Validate specific round
edison qa validate TASK-123 --round 2

# Validate a hierarchy cluster (root + descendants)
edison qa validate TASK-123 --scope hierarchy

# Validate a bundle_root cluster (root + bundle_root members)
edison qa validate TASK-123 --scope bundle
```

**Input location**: `{{fn:evidence_root}}/<task-id>/round-N/`
**Output**: `{{config.validation.artifactPaths.bundleSummaryFile}}` or validation error report

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
edison qa bundle <task-id> [--scope <auto|hierarchy|bundle>]
```

**Purpose**: Inspect evidence paths and cluster tasks before validation
**When to use**: Before running validation, to understand scope

**Example:**
```bash
edison qa bundle TASK-123
```

**Output:**
- Evidence directory structure
- Cluster task list (resolved root + members)
- Required validators
- Existing reports

---

### Start Validation Round

```bash
edison qa round prepare <task-id>
```

**Purpose**: Prepare the active QA round directory (round-N) for validation artifacts.
**When to use**: Before running validators so you have the correct round directory ready.

**Record round status in the QA brief (history only):**
```bash
edison qa round set-status <task-id> --status <approve|reject|blocked|pending> [--note "..."]
```

**Summarize validator results into the canonical validation summary:**
```bash
edison qa round summarize-verdict <task-id> --preset <preset>
```

> Note: `set-status` updates QA history only. `prepare` manages the round directory and report scaffolding.

**Statuses:**
- `approve` - All checks pass
- `reject` - Issues found, requires fixes
- `blocked` - Validation could not be completed (missing access, tool failure, etc.)
- `pending` - Round in progress

**Example:**
```bash
edison qa round set-status TASK-123 --status approve --note "global-codex, global-claude"
```

---

## Validation Report Format

Validator report format is defined in:
- `guidelines/validators/OUTPUT_FORMAT.md` (canonical human + JSON requirements)
- `edison read validator-report.schema.yaml --type schemas/reports` (exact schema; YAML)

---

## Validator Types

### Global Validators (Always Run)

**Global validators** are defined in validator configuration:
- Check the current global validators: run `edison read AVAILABLE_VALIDATORS`
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
edison task status TASK-123

# Task should be in '{{fn:semantic_state("task","done")}}' state with {{config.validation.artifactPaths.implementationReportFile}}

# 2. Inspect validation bundle
edison qa bundle TASK-123

# Review evidence directory and required validators

# 3. Run validation
edison qa validate TASK-123

# This checks all required validator reports exist

# 4. If issues found, record round status
edison qa round TASK-123 --status reject

# 5. After fixes, re-validate
edison qa validate TASK-123 --round 2

# 6. Record approval
edison qa round TASK-123 --status approve

# 7. Orchestrator promotes QA to validated
# (validators don't do this - orchestrator does)
```

### Bundle Validation (Multiple Tasks)

```bash
# 1. Inspect cluster selection
edison qa bundle TASK-123 --scope auto

# 2. Validate the resolved cluster (runs once at root)
edison qa validate TASK-123 --scope auto --execute

# 3. Output: {{config.validation.artifactPaths.bundleSummaryFile}}
# Contains aggregated validation status for all tasks
```

### Incremental Validation (Rounds)

```bash
# Round 1: Initial validation
edison qa validate TASK-123 --round 1

# Issues found - developer fixes

# Round 2: Re-validate after fixes
edison qa validate TASK-123 --round 2

# Continue until approve
```

---

## Output Locations

**Validator reports**: `{{fn:evidence_root}}/<task-id>/round-N/validator-<id>-report.md`
**Bundle summary**: `{{fn:evidence_root}}/<task-id>/round-N/{{config.validation.artifactPaths.bundleSummaryFile}}`
**Implementation report**: `{{fn:evidence_root}}/<task-id>/round-N/{{config.validation.artifactPaths.implementationReportFile}}`

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
- [ ] Type checking passes (per active stack)
- [ ] API contracts are validated
- [ ] Documentation is adequate

### Framework-Specific (Based on Active Packs)

Check active pack guidelines for framework-specific validation criteria:
- **Frontend Frameworks**: Routing patterns, component architecture
- **UI Libraries**: Component patterns, state management
- **Database Tools**: Schema design, migration strategy
- **Styling Systems**: Design tokens, responsive patterns

Refer to active pack validators and focus areas: run `edison read AVAILABLE_VALIDATORS`.

---

## Best Practices

1. **Be thorough but fair**: Find real issues, not nitpicks
2. **Provide actionable feedback**: Specific file/line references
3. **Use correct severities**: Reserve `blocking` for critical issues
4. **Write clear summaries**: Help developers understand findings
5. **Track continuations**: Use `continuationId` for multi-round validation
6. **Check all evidence**: Review `{{config.validation.artifactPaths.implementationReportFile}}` first
7. **Validate bundles holistically**: Check integration, not just individual tasks

---

## What Validators Should NOT Do

**❌ DO NOT run these commands** (orchestrator-only):
- `edison session next/start/status/close` - Session management
- `edison task claim/ready` - Task claiming and promotion
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

- `edison read VALIDATOR_GUIDELINES --type guidelines/validators` - Full validator guidelines
- `edison read VALIDATOR_WORKFLOW --type guidelines/validators` - Validation workflow
- `edison read OUTPUT_FORMAT --type guidelines/validators` - Report format requirements
- `edison read code-quality --type guidelines/validators` - Code quality standards
- `edison read testing --type guidelines/validators` - Testing requirements

---

**Role**: Validator
**Focus**: Code review and quality assurance
**DO**: Validate work, generate reports, identify issues
**DON'T**: Claim tasks, manage sessions, implement features
