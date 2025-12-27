<!-- TaskID: 2111-vinf-001-validator-readme -->
<!-- Priority: 2111 -->
<!-- Wave: wave-edison-migration -->
<!-- Type: documentation -->
<!-- Owner: _unassigned_ -->
<!-- Status: todo -->
<!-- Created: 2025-12-02 -->
<!-- ClaimedAt: _unassigned_ -->
<!-- LastActive: _unassigned_ -->
<!-- ContinuationID: _none_ -->
<!-- Model: claude -->
<!-- ParallelGroup: wave2-groupB -->
<!-- EstimatedHours: 2 -->

# VINF-001: Create Validator README with Architecture

## Summary
Create a comprehensive validator README.md based on the OLD system's 503-line README. This document provides architecture overview, execution flow, and troubleshooting guidance.

## Problem Statement
The OLD system had a comprehensive validator README (503 lines) that is MISSING from Edison. This documentation is critical for understanding:
- Validator architecture (9 validators)
- Execution flow and ordering
- Configuration guidance
- Troubleshooting procedures

## Dependencies
- None

## Objectives
- [x] Create comprehensive README.md
- [x] Include architecture diagram
- [x] Include execution flow
- [x] Include troubleshooting section

## Source Files

### Reference - Old README
```
/Users/leeroy/Documents/Development/wilson-pre-edison/.agents/validators/README.md
```

### Output Location
```
/Users/leeroy/Documents/Development/edison/src/edison/data/validators/README.md
```

## Precise Instructions

### Step 1: Analyze Old README
```bash
wc -l /Users/leeroy/Documents/Development/wilson-pre-edison/.agents/validators/README.md
cat /Users/leeroy/Documents/Development/wilson-pre-edison/.agents/validators/README.md | head -150
```

### Step 2: Create README

Create `/Users/leeroy/Documents/Development/edison/src/edison/data/validators/README.md`:

```markdown
# Edison Validator Framework

This document describes the validator architecture, execution flow, and troubleshooting procedures.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    VALIDATOR FRAMEWORK                   │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌───────────────────┐   ┌───────────────────┐         │
│  │   GLOBAL (2-3)    │   │   CRITICAL (2)    │         │
│  │  Always run first │   │  Must pass        │         │
│  ├───────────────────┤   ├───────────────────┤         │
│  │ • codex-global    │   │ • security        │         │
│  │ • claude-global   │   │ • performance     │         │
│  │ • gemini-global   │   │                   │         │
│  └───────────────────┘   └───────────────────┘         │
│                                                          │
│  ┌───────────────────────────────────────────┐          │
│  │           SPECIALIZED (5-7)               │          │
│  │  Triggered by file patterns               │          │
│  ├───────────────────────────────────────────┤          │
│  │ • api       (**/api/**/*.ts)             │          │
│  │ • database  (schema.prisma, *.sql)       │          │
│  │ • nextjs    (app/**/*.tsx)               │          │
│  │ • react     (**/*.tsx)                   │          │
│  │ • testing   (**/*.test.ts)               │          │
│  │ • tailwind  (**/*.tsx)                   │          │
│  └───────────────────────────────────────────┘          │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## Validator Categories

### Global Validators
**Always run** regardless of file changes. Provide overall quality check.

| Validator | Model | Blocking | Purpose |
|-----------|-------|----------|---------|
| codex-global | Codex | Yes | Code quality, patterns, bugs |
| claude-global | Claude | Yes | Logic, design, architecture |
| gemini-global | Gemini | No | Second opinion, consensus |

**Consensus Model**: Global validators use multi-model consensus. Disagreement escalates to human review.

### Critical Validators
**Must pass** for task promotion. Block on failure.

| Validator | Model | Blocking | Purpose |
|-----------|-------|----------|---------|
| security | Codex | Yes | Security vulnerabilities, auth |
| performance | Codex | Yes | Performance issues, budgets |

### Specialized Validators
**Triggered by file patterns**. Provide domain-specific validation.

| Validator | Triggers | Blocking | Purpose |
|-----------|----------|----------|---------|
| api | **/api/**/*.ts | No | REST conventions, auth |
| database | schema.prisma | Yes | Schema design, migrations |
| nextjs | app/**/*.tsx | No | App Router patterns |
| react | **/*.tsx | No | Component quality |
| testing | **/*.test.ts | Yes | Test quality, coverage |

## Execution Flow

### 1. Trigger Detection
```
1. Orchestrator runs: edison validate <task-id>
2. Framework reads: git diff --name-only for changed files
3. File patterns matched against validator triggers
4. Validator list assembled
```

### 2. Execution Order
```
Phase 1: Global validators (parallel)
  ├─ codex-global
  ├─ claude-global
  └─ gemini-global

Phase 2: Critical validators (parallel, after Phase 1)
  ├─ security
  └─ performance

Phase 3: Specialized validators (parallel, after Phase 2)
  ├─ api (if triggered)
  ├─ database (if triggered)
  ├─ nextjs (if triggered)
  ├─ react (if triggered)
  └─ testing (if triggered)
```

### 3. Result Aggregation
```
All validators complete
  ├─ Any blocking validator REJECTED → Overall REJECTED
  ├─ All blocking validators APPROVED → Check warnings
  │     ├─ Any warnings → APPROVED_WITH_WARNINGS
  │     └─ No warnings → APPROVED
  └─ Generate bundle report
```

## Configuration

### Validator Config File
Location: `.edison/config/validators.yml`

```yaml
validators:
  global:
    - id: codex-global
      model: codex
      blocksOnFail: true
      alwaysRun: true
    - id: claude-global
      model: claude
      blocksOnFail: true
      alwaysRun: true

  critical:
    - id: security
      model: codex
      blocksOnFail: true
      triggers: ["*"]
    - id: performance
      model: codex
      blocksOnFail: true
      triggers: ["*"]

  specialized:
    - id: api
      model: codex
      blocksOnFail: false
      triggers: ["**/api/**/*.ts", "**/route.ts"]
```

### Project Overrides
Location: `.edison/overlays/validators/`

Create overlay files to add project-specific rules:
```
.edison/overlays/validators/
├── api.md          # Wilson API patterns
├── database.md     # Wilson schema patterns
└── security.md     # Wilson auth patterns
```

## Available Validators Reference

See `.edison/_generated/AVAILABLE_VALIDATORS.md` for current roster.

## Validation Report Format

### Individual Validator Output
```json
{
  "validator": "api",
  "status": "APPROVED_WITH_WARNINGS",
  "filesChecked": ["apps/api/src/routes/leads.ts"],
  "findings": [...],
  "summary": {
    "errors": 0,
    "warnings": 2,
    "info": 1
  }
}
```

### Bundle Report
```json
{
  "taskId": "task-123",
  "validatedAt": "2025-12-02T10:00:00Z",
  "overall": "APPROVED_WITH_WARNINGS",
  "validators": {
    "codex-global": { "status": "APPROVED" },
    "claude-global": { "status": "APPROVED" },
    "api": { "status": "APPROVED_WITH_WARNINGS" }
  },
  "findings": [...],
  "filesChanged": 5,
  "coverage": {
    "statements": 87.5
  }
}
```

## Troubleshooting

### Validator Not Running
**Symptom**: Expected validator doesn't appear in results.

**Check**:
1. File patterns match changed files?
   ```bash
   git diff --name-only
   edison validate --dry-run <task-id>
   ```
2. Validator enabled in config?
   ```bash
   cat .edison/config/validators.yml | grep <validator-id>
   ```

### Validator Timeout
**Symptom**: Validator hangs or times out.

**Check**:
1. Model availability?
2. File too large for context?
3. Network issues?

**Fix**:
```bash
# Run single validator with verbose logging
edison validate --only=api --verbose <task-id>
```

### Inconsistent Results
**Symptom**: Same files, different results.

**Causes**:
- Model non-determinism (expected)
- Context7 refresh needed
- Config changed between runs

**Fix**:
```bash
# Force Context7 refresh
mcp__context7__get-library-docs(...)

# Run with fixed seed (if supported)
edison validate --seed=42 <task-id>
```

### Blocking Validator Too Strict
**Symptom**: Valid code rejected.

**Options**:
1. Add project overlay to relax rules
2. Mark rule as warning instead of error
3. Use `--skip-validator=<id>` (not recommended)

### Missing Validator Output
**Symptom**: Validator runs but no report generated.

**Check**:
1. Output directory exists?
2. Write permissions?
3. JSON parsing errors?

**Fix**:
```bash
mkdir -p .project/qa/validation-evidence/<task-id>/round-1/
edison validate <task-id> --output-dir=...
```

## Context7 Integration

Validators SHOULD refresh Context7 before validation:

```
mcp__context7__get-library-docs({
  context7CompatibleLibraryID: "/prisma/prisma",
  topic: "best-practices"
})
```

This ensures validation uses current framework patterns.

## Adding Custom Validators

### 1. Create Validator File
```bash
touch .edison/validators/custom.md
```

### 2. Define Frontmatter
```yaml
---
id: custom
type: specialized
model: codex
triggers:
  - "**/custom/**/*"
blocksOnFail: false
---
```

### 3. Add Validation Rules
Follow the VR-XXX-NNN format for rule IDs.

### 4. Register in Config
```yaml
# .edison/config/validators.yml
specialized:
  - id: custom
    model: codex
    triggers: ["**/custom/**/*"]
```

### 5. Run Composition
```bash
edison compose validators
```

## Best Practices

1. **Start with global validators** - they catch most issues
2. **Use blocking sparingly** - only for truly critical checks
3. **Layer rules** - core → pack → project for flexibility
4. **Keep validators focused** - single responsibility
5. **Include Context7** - always fetch current docs
6. **Document findings** - clear messages and suggestions
7. **Test validators** - validate the validators!
```

## Verification Checklist
- [ ] README created at Edison path
- [ ] Architecture diagram included
- [ ] Execution flow documented
- [ ] Configuration section complete
- [ ] Troubleshooting section included
- [ ] Context7 integration documented

## Success Criteria
A comprehensive validator README exists that enables understanding of the entire validation framework.

## Related Issues
- Audit ID: CG-021
- Audit ID: Wave 5 validator findings
