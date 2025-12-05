# Validation - Include-Only File

<!-- WARNING: This file is for {{include-section:}} only. DO NOT read directly. -->

<!-- SECTION: overview -->
## Validation Overview (All Roles)

### Purpose
Validation runs after implementation is complete and before a task can advance beyond `done/`. QA briefs are the canonical validation record.

### Validator Categories
- **Global (blocking)**: Always run first, must approve
- **Critical (blocking)**: Always run, any failure blocks
- **Specialized (triggered)**: Only run if file patterns match, blocking if `blocksOnFail=true`

### Wave Order (Mandatory)
```
Wave 1: Global Validators → Wave 2: Critical Validators → Wave 3: Specialized Validators
```

Launch in parallel per wave up to configured concurrency cap.

### Verdicts
- `approve` - Validator passed the task
- `reject` - Validator found blocking issues
- `blocked` - Validator couldn't complete validation

### Bundle-First Rule
Before any validator wave, run:
```bash
edison qa bundle <root-task>
```
Paste manifest into QA brief. Validators must load only what the bundle lists.
<!-- /SECTION: overview -->

<!-- SECTION: orchestrator-waves -->
## Validator Orchestration (Orchestrators)

### Wave Execution Model
```
┌─────────────────────────────────────────────────────────────┐
│ Wave 1: Critical Validators (Parallel)                       │
│ ┌────────────────┐ ┌────────────────┐ ┌────────────────┐   │
│ │ global-codex   │ │ global-claude  │ │ global-gemini  │   │
│ │ (blocking)     │ │ (blocking)     │ │ (consensus)    │   │
│ └────────────────┘ └────────────────┘ └────────────────┘   │
│ ┌────────────────┐ ┌────────────────┐                      │
│ │ security       │ │ performance    │  → Any blocking      │
│ │ (blocking)     │ │ (blocking)     │    failure stops     │
│ └────────────────┘ └────────────────┘                      │
└─────────────────────────────────────────────────────────────┘
                          ↓ (if pass)
┌─────────────────────────────────────────────────────────────┐
│ Wave 2: Comprehensive Validators (Parallel, Triggered)       │
│ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐    │
│ │ react  │ │ nextjs │ │  api   │ │ prisma │ │testing │    │
│ └────────┘ └────────┘ └────────┘ └────────┘ └────────┘    │
│ (triggered by file patterns - e.g., *.tsx triggers react)   │
└─────────────────────────────────────────────────────────────┘
```

### Validator Auto-Detection (File Pattern Triggers)

**How validators are selected:**
1. **Always-run validators** (`always_run: true`): Always execute
2. **Pattern-triggered validators**: Match file patterns against modified files

**Pattern examples:**
- `react`: Triggers on `**/*.tsx`, `**/*.jsx`, `**/components/**/*`
- `nextjs`: Triggers on `app/**/*.tsx`, `**/route.ts`, `**/layout.tsx`
- `api`: Triggers on `**/api/**/*.ts`, `**/route.ts`
- `prisma`: Triggers on `schema.prisma`, `prisma/**/*`, `**/*.sql`

**View detected roster:**
```bash
edison qa validate <task-id>  # Shows auto-detected validators
```

### Adding Extra Validators (CRITICAL)

**Orchestrators CAN add validators but CANNOT remove auto-detected ones.**

**When to add validators:**
- React logic in `.js` files (not caught by `.tsx` trigger)
- API patterns in non-standard locations
- Framework code in unexpected directories
- Task context suggests specific validation needed

**How to add:**
```bash
# Add single validator
edison qa validate <task-id> --add-validators react --execute

# Add multiple validators
edison qa validate <task-id> --add-validators react api --execute

# Specify wave for added validators
edison qa validate <task-id> --add-validators react --add-to-wave critical --execute
```

**CLI shows decision points:**
When validators might be relevant but weren't triggered, the CLI displays:
```
═══ ORCHESTRATOR DECISION POINTS ═══
► Consider adding 'react' validator
  Reason: Found .js files that may contain React: src/helpers.js
  To add: --add-validators react
```

### Consensus Rules

**Global Validators:**
- All blocking global validators must approve
- Non-blocking (gemini, auggie) provide consensus reinforcement
- Disagreement → review specific feedback for root cause

**Critical Validators:**
- ANY blocking failure stops the wave
- Must fix ALL issues before re-validation

**Specialized Validators:**
- Only triggered if file patterns match
- Blocking determined by `blocking: true/false` in config

### Validation Sequence (Strict Order)
1. Automation evidence captured (`command-type-check.txt`, etc.)
2. Context7 refreshes for all `context7_packages`
3. **Auto-detect validators from modified files**
4. **Add orchestrator-specified extra validators**
5. Run validators in waves (parallel within wave)
6. Store artefacts under `.project/qa/validation-evidence/<task-id>/round-<N>/`
7. Move QA/task only after ALL blocking validators approve

### Rejection Handling
1. Task stays/returns to `wip/`
2. QA moves to `waiting/`
3. Add "Round N" section to QA with findings
4. Spawn follow-up tasks in `tasks/todo/`
5. After fixes: Run validation Round N+1

### Bundle Approval
- Generate `bundle-approved.json` in evidence directory
- Contains `approved` (overall) and `tasks[]` (per-task)
- Promotion blocked until `approved=true`
<!-- /SECTION: orchestrator-waves -->

<!-- SECTION: validator-workflow -->
## Validation Execution (Validators)

### Workflow Steps

1. **Intake**
   - Open QA brief and bundle manifest
   - Confirm task/QA state matches manifest
   - If QA missing or duplicated, halt and notify orchestrator

2. **Load Context**
   - Read implementation report and evidence files
   - Load git diff
   - Note automation outputs and Context7 markers

3. **Prepare Checks**
   - Map changed files to required validators
   - Verify your validator role/model matches config
   - Set up local services QA specifies

4. **Execute**
   - Run prescribed commands/tests
   - Capture output to `round-<N>/` evidence directory

5. **Findings**
   - Document issues with severity, category, location
   - Note follow-up tasks needed
   - Mark blocking vs non-blocking

6. **Verdict**
   - `approve` - All blocking issues resolved
   - `reject` - Blocking issues remain
   - `blocked` - Could not complete validation
   - Never self-approve when evidence is missing

7. **Report**
   - Write validator report JSON (see OUTPUT_FORMAT)
   - Update QA brief with findings and verdict
   - Include model used

8. **Handoff**
   - If rejected/blocked: QA returns to `waiting/`, follow-ups created
   - If approved: Signal readiness for bundle approval
<!-- /SECTION: validator-workflow -->
