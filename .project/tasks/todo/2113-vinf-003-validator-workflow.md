<!-- TaskID: 2113-vinf-003-validator-workflow -->
<!-- Priority: 2113 -->
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
<!-- EstimatedHours: 1 -->

# VINF-003: Restore VALIDATOR_WORKFLOW Detailed Content

## Summary
Restore the detailed VALIDATOR_WORKFLOW.md content from the OLD system's 52-line file. The current Edison version is severely condensed (11 lines) and missing critical information.

## Problem Statement
Current Edison VALIDATOR_WORKFLOW.md:
- Only 11 lines (vs 52 in OLD)
- Missing: Mandatory preload checklist
- Missing: TRACKING section with commands
- Missing: Auto-stamped fields explanation
- Missing: 8-step runbook with state transitions

## Dependencies
- None

## Objectives
- [x] Restore mandatory preload checklist
- [x] Restore tracking section
- [x] Restore 8-step runbook
- [x] Add state transition guidance

## Source Files

### Reference - Old Workflow
```
/Users/leeroy/Documents/Development/wilson-pre-edison/.agents/validators/VALIDATOR_WORKFLOW.md
```

### File to Update
```
/Users/leeroy/Documents/Development/edison/src/edison/data/validators/VALIDATOR_WORKFLOW.md
```

## Precise Instructions

### Step 1: Review Current File
```bash
cat /Users/leeroy/Documents/Development/edison/src/edison/data/validators/VALIDATOR_WORKFLOW.md
wc -l /Users/leeroy/Documents/Development/edison/src/edison/data/validators/VALIDATOR_WORKFLOW.md
```

### Step 2: Review Old File
```bash
cat /Users/leeroy/Documents/Development/wilson-pre-edison/.agents/validators/VALIDATOR_WORKFLOW.md
```

### Step 3: Update Workflow

Replace or update content to include:

```markdown
# Validator Workflow

This document defines the step-by-step workflow for running validation on a task.

## Mandatory Preloads

Before starting validation, load these files:

1. **Constitution**: `.edison/_generated/constitutions/VALIDATORS.md`
2. **Output Format**: `.edison/_generated/validators/OUTPUT_FORMAT.md`
3. **Available Validators**: `.edison/_generated/AVAILABLE_VALIDATORS.md`
4. **Task Context**: Read the task file and implementation report

## Tracking Commands

### Start Tracking
```bash
edison session track start --type=validation --task=<task-id>
```

This creates a tracking record with:
- processId (auto-generated UUID)
- startedAt (auto-stamped)
- model (from config)

### Complete Tracking
```bash
edison session track complete --task=<task-id> --status=<status>
```

This updates:
- completedAt (auto-stamped)
- durationMs (calculated)
- status (APPROVED/REJECTED/APPROVED_WITH_WARNINGS)

### Heartbeat (Long Validations)
```bash
edison session track heartbeat --task=<task-id>
```

Send every 30 seconds for validations > 1 minute.

## Auto-Stamped Fields

These fields are automatically populated:

| Field | Source | Format |
|-------|--------|--------|
| processId | Generated | UUID v4 |
| startedAt | System | ISO 8601 |
| completedAt | System | ISO 8601 |
| durationMs | Calculated | Integer |
| model | Config | String |
| validatorVersion | Package | SemVer |

Do NOT manually set these fields.

## 8-Step Runbook

### Step 1: Receive Validation Request
```
Input: Task ID
Action: Parse task ID, locate task file
Output: Task context loaded
```

### Step 2: Check Prerequisites
```
Verify:
- Task exists and is in 'wip' or 'done' state
- Implementation report exists
- Changed files are committed
```

### Step 3: Start Tracking
```bash
edison session track start --type=validation --task=<task-id>
```

### Step 4: Determine Triggered Validators
```
1. Get changed files: git diff --name-only
2. Match against validator triggers
3. Always include: global validators
4. Add: critical validators
5. Add: matching specialized validators
```

### Step 5: Execute Validators
```
For each validator in determined list:
  1. Load validator constitution
  2. Refresh Context7 (if needed)
  3. Analyze changed files
  4. Apply validation rules
  5. Generate findings
  6. Calculate status
  7. Write output (JSON + Markdown)
```

### Step 6: Aggregate Results
```
1. Collect all validator outputs
2. Determine overall status:
   - Any REJECTED → Overall REJECTED
   - Any WARNINGS → APPROVED_WITH_WARNINGS
   - All clean → APPROVED
3. Generate bundle report
```

### Step 7: Complete Tracking
```bash
edison session track complete --task=<task-id> --status=<overall-status>
```

### Step 8: Report Results
```
1. Write bundle to validation-evidence directory
2. Update task metadata
3. Log summary to console
4. Exit with appropriate code (0=pass, 1=fail)
```

## State Transitions

```
Task States:
  wip → (validation) → wip (if REJECTED)
  wip → (validation) → validated (if APPROVED)
  done → (validation) → validated (if APPROVED)

Session States:
  active → (validation) → active (if REJECTED)
  active → (validation) → validated (if all tasks APPROVED)
```

## Validation Waves

For large changes, validation may run in waves:

### Wave 1: Global
- codex-global
- claude-global
- gemini-global

### Wave 2: Critical (after Wave 1 passes)
- security
- performance

### Wave 3: Specialized (after Wave 2 passes)
- All triggered specialized validators

**Early Exit**: If Wave 1 or 2 fails with REJECTED, skip remaining waves.

## Model Binding

Each validator MUST run on its designated model:

```yaml
validator-model-bindings:
  codex-global: codex
  claude-global: claude
  gemini-global: gemini
  security: codex
  performance: codex
  api: codex
  database: codex
  nextjs: codex
  react: codex
  testing: codex
```

Wrong model usage should:
1. Log warning
2. Continue with assigned model
3. Note discrepancy in report

## Evidence Directory Structure

```
.project/qa/validation-evidence/<task-id>/
└── round-1/
    ├── codex-global.json
    ├── codex-global.md
    ├── claude-global.json
    ├── claude-global.md
    ├── security.json
    ├── security.md
    ├── api.json (if triggered)
    ├── api.md (if triggered)
    └── bundle.json (aggregated)
```

## Re-validation

If validation fails:
1. Agent fixes issues
2. Orchestrator requests re-validation
3. Round number increments (round-2, round-3, etc.)
4. Previous round evidence preserved

## Context7 Before Validation

RECOMMENDED: Refresh Context7 for relevant libraries before validation:

```
mcp__context7__get-library-docs({
  context7CompatibleLibraryID: "/prisma/prisma",
  topic: "best-practices"
})
```

This ensures validation uses current patterns.
```

## Verification Checklist
- [ ] Mandatory preloads section exists
- [ ] Tracking commands documented
- [ ] Auto-stamped fields explained
- [ ] 8-step runbook complete
- [ ] State transitions documented
- [ ] Validation waves explained
- [ ] Model binding documented
- [ ] Evidence directory structure shown

## Success Criteria
VALIDATOR_WORKFLOW.md is comprehensive and matches the detail level of the OLD system while incorporating Edison-specific commands.

## Related Issues
- Audit ID: CG-020
- Audit ID: Wave 5 validator findings
