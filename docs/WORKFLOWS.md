# Edison Workflows Guide

Complete guide to Edison's operational workflows, from session creation through task completion and validation.

---

## Table of Contents

1. [Session Workflow](#session-workflow)
2. [Task State Machine](#task-state-machine)
3. [QA State Machine](#qa-state-machine)
4. [Validation Workflow](#validation-workflow)
5. [TDD Workflow](#tdd-workflow)
6. [Delegation Workflow](#delegation-workflow)
7. [Error Recovery](#error-recovery)

---

## Session Workflow

The complete lifecycle of an Edison session from creation to archival.

### 1. Start Session

```bash
# Create new session
edison session create --session-id <id>
```

**What happens:**
- Creates session record in `.project/sessions/wip/<session-id>/session.json`
- Creates git worktree (isolated branch) if worktrees enabled
- Initializes session state as `active`
- Sets up session metadata (owner, timestamps)

**Configuration:**
- Session config: `src/edison/data/config/session.yaml`
- State machine: `src/edison/data/config/state-machine.yaml`

---

### 2. Read Constitution

The orchestrator reads the generated constitution to understand available agents and validators.

**Constitution location:**
```
.edison/_generated/constitutions/ORCHESTRATORS.md
```

**What it contains:**
- Available agent roster (file-pattern based delegation)
- Validator definitions and rosters
- Quality gates and guards
- TDD requirements

---

### 3. Select Tasks

```bash
# List available tasks
edison task list --status todo

# Select 1-5 tasks for session scope
```

**Task selection criteria:**
- Priority/urgency
- Dependencies
- Estimated complexity
- Available time in session

---

### 4. Implementation Loop (Per Task)

#### a. Claim Task

```bash
# Claim task into session
edison task claim <task-id> --session <session-id>
```

**State transition:** `todo` → `wip`

**What happens:**
- Updates task state to `wip`
- Links task to session
- Records state history
- Creates task lock (prevents concurrent edits)

**Task file location:**
```
.project/tasks/wip/<task-id>.md
```

---

#### b. Delegate to Agent

**Automatic delegation based on file patterns:**

```yaml
# From delegation.yaml
filePatternRules:
  "*.tsx":
    preferredModel: claude
    preferredZenRole: component-builder-nextjs

  "**/route.ts":
    preferredModel: codex
    preferredZenRole: api-builder
    delegateVia: zen-mcp

  "**/*.test.ts":
    preferredModel: codex
    preferredZenRole: test-engineer
    delegateVia: zen-mcp
```

**Agent workflow:**
1. Agent reads constitution and guidelines
2. Implements using TDD (RED→GREEN→REFACTOR)
3. Creates implementation report at:
   ```
   .project/qa/validation-evidence/<task-id>/round-1/implementation-report.json
   ```

**Implementation report structure:**
```json
{
  "taskId": "T-001",
  "round": 1,
  "implementationApproach": "orchestrator-direct",
  "primaryModel": "codex",
  "completionStatus": "complete",
  "blockers": [],
  "followUpTasks": [],
  "tracking": {
    "processId": 12345,
    "startedAt": "2025-12-01T10:00:00Z",
    "completedAt": "2025-12-01T10:30:00Z",
    "hostname": "dev-machine"
  },
  "tddCompliance": {
    "followed": true
  }
}
```

---

#### c. Track Progress

```bash
# Start tracking implementation
edison session track start --task <id> --type implementation

# Complete tracking
edison session track complete --task <id>
```

**Heartbeat tracking:**
- Process ID recording
- Timestamp tracking
- Hostname identification
- Session association

---

#### d. Mark Ready

```bash
# Mark task as ready for validation
edison task ready <task-id>
```

**State transition:** `wip` → `done`

**What happens:**
- Validates task completion requirements:
  - All work complete
  - No pending commits
  - Evidence files present
  - TDD compliance (if enabled)
- Updates task state to `done`
- Triggers QA brief creation (if not exists)

**Guards checked:**
- `can_finish_task`
- `all_work_complete`
- `no_pending_commits`

---

### 5. Validation Loop (Per Task)

#### a. Create QA Brief

```bash
# Create QA brief for task (if not exists)
edison qa new <task-id>
```

**QA brief location:**
```
.project/qa/waiting/<task-id>-qa.md
```

**Initial state:** `waiting`

**QA brief template:**
```markdown
# QA Brief for T-001

- [ ] Unit tests green
- [ ] Lint/Type-check pass
- [ ] Evidence recorded
- [ ] TDD compliance verified

Title: [Task Title]
Description: [Task Description]
```

---

#### b. Run Validators

```bash
# Run all validators for task
edison qa validate <task-id>

# Run specific validator
edison qa run <validator-name> --task <task-id>
```

**What happens:**
1. Creates validation bundle at:
   ```
   .project/qa/validation-evidence/<task-id>/round-N/
   ```

2. Executes validators in parallel (configurable):
   - Multiple validators run concurrently
   - Each produces JSON report
   - Timeout per validator: 5 minutes (default)

3. Collects evidence files:
   ```
   validation-evidence/<task-id>/round-1/
   ├── implementation-report.json
   ├── command-test.txt
   ├── command-lint.txt
   ├── command-type-check.txt
   ├── command-build.txt
   ├── validator-*-report.json
   └── context7-*.md
   ```

**Validator configuration:**
```yaml
# From qa.yaml
orchestration:
  maxConcurrentAgents: 4
  validatorTimeout: 300
  executionMode: parallel

validation:
  requiredEvidenceFiles:
    - command-type-check.txt
    - command-lint.txt
    - command-test.txt
    - command-build.txt
```

---

#### c. Handle Results

**If approved:**
```bash
# Promote QA to validated
edison qa promote --task <task-id> --to validated
```

**State transitions:**
- QA: `done` → `validated`
- Task: `done` → `validated`

**If rejected:**
```bash
# Validators create follow-up tasks
edison task ensure_followups <task-id>
```

**State transitions:**
- QA: `done` → `waiting`
- Task: `done` → `wip`

**Follow-up tasks created at:**
```
.project/qa/validation-evidence/<task-id>/round-N/followups/
```

---

#### d. Promote QA

```bash
# Promote QA through states
edison qa promote --task <task-id> --to validated
```

**QA state progression:**
```
waiting → todo → wip → done → validated
```

---

### 6. Close Session

```bash
# Close session (validates all tasks)
edison session close <session-id>
```

**What happens:**
1. Verifies all tasks validated
2. Finalizes worktree (if applicable)
3. Archives session:
   ```
   .project/sessions/validated/<session-id>/
   ```
4. Records completion timestamp

**Guards checked:**
- `can_complete_session`
- `all_work_complete`
- `no_pending_commits`
- `ready_to_close`

**Session state progression:**
```
active → closing → validated → archived
```

---

## Task State Machine

Complete task lifecycle with transitions and guards.

```
┌─────────┐
│  todo   │ ◄─────────┐
│(initial)│           │
└────┬────┘           │
     │                │
     │ claim          │
     ▼                │
┌─────────┐           │
│   wip   │───────────┤
└────┬────┘           │
     │                │
     │ ready          │
     ▼                │
┌─────────┐           │
│  done   │───────────┤
└────┬────┘           │
     │                │
     │ validate       │
     ▼                │
┌──────────┐          │
│validated │          │
│ (final)  │          │
└──────────┘          │
                      │
┌─────────┐           │
│ blocked │───────────┘
└─────────┘
```

### State Definitions

**todo** (initial):
- Description: "Task awaiting claim"
- Allowed transitions:
  - → `wip` (guard: `can_start_task`, condition: `task_claimed`)
  - → `done` (guard: `can_finish_task`, conditions: `all_work_complete`, `no_pending_commits`)
  - → `blocked` (guard: `has_blockers`)

**wip**:
- Description: "Task in progress"
- Allowed transitions:
  - → `blocked` (guard: `has_blockers`)
  - → `done` (guard: `can_finish_task`)
  - → `todo` (guard: `always_allow`)
  - → `validated` (guard: `always_allow`)

**blocked**:
- Description: "Waiting on external blockers"
- Allowed transitions:
  - → `wip` (guard: `can_start_task`)
  - → `todo` (guard: `always_allow`)

**done**:
- Description: "Implementation complete, awaiting validation"
- Allowed transitions:
  - → `validated` (guard: `can_finish_task`)
  - → `wip` (guard: `always_allow`)

**validated** (final):
- Description: "Validated and complete"
- Allowed transitions: none

### CLI Commands

```bash
# Create task
edison task new --id <id> --title <title>

# Claim task
edison task claim <task-id> --session <session-id>

# Mark ready (wip → done)
edison task ready <task-id>

# Check status
edison task status <task-id>

# List tasks by state
edison task list --status todo
edison task list --status wip
edison task list --status done
edison task list --status validated

# Transition states (advanced)
edison task status <task-id> --set <new-state>
```

---

## QA State Machine

QA record lifecycle for task validation.

```
┌──────────┐
│ waiting  │ ◄────────┐
│(initial) │          │
└─────┬────┘          │
      │               │
      │ promote       │
      ▼               │
┌──────────┐          │
│   todo   │          │
└─────┬────┘          │
      │               │
      │ promote       │
      ▼               │
┌──────────┐          │
│   wip    │──────────┤
└─────┬────┘          │
      │               │
      │ promote       │
      ▼               │
┌──────────┐          │
│   done   │──────────┤
└─────┬────┘          │
      │               │
      │ validate      │
      ▼               │
┌──────────┐          │
│validated │          │
│ (final)  │          │
└──────────┘          │
      ▲               │
      │               │
      └───────────────┘
```

### State Definitions

**waiting** (initial):
- Description: "Pending hand-off from implementation"
- Transitions: → `todo`, → `wip`

**todo**:
- Description: "QA backlog"
- Transitions: → `wip`

**wip**:
- Description: "QA in progress"
- Transitions: → `done`, → `todo`

**done**:
- Description: "QA review complete"
- Transitions: → `validated`, → `wip`

**validated** (final):
- Description: "QA validated"
- Transitions: none

### Validation Lifecycle

From `workflow.yaml`:

```yaml
validationLifecycle:
  onApprove:
    qaState: done → validated
    taskState: done → validated
  onReject:
    qaState: wip → waiting
    taskState: done → wip
  onRevalidate:
    qaState: waiting → todo
```

### CLI Commands

```bash
# Create QA brief
edison qa new <task-id>

# Promote QA state
edison qa promote --task <task-id> --to todo
edison qa promote --task <task-id> --to wip
edison qa promote --task <task-id> --to done
edison qa promote --task <task-id> --to validated

# Run validators
edison qa validate <task-id>

# Run specific validator
edison qa run <validator-name> --task <task-id>

# Manage rounds
edison qa round list --task <task-id>
edison qa round new --task <task-id>

# Bundle management
edison qa bundle create --task <task-id>
edison qa bundle inspect --task <task-id>
```

---

## Validation Workflow

Detailed validation process with evidence collection and consensus.

### 1. Evidence Collection

**Required evidence files:**
```
.project/qa/validation-evidence/<task-id>/round-N/
├── command-test.txt          # Test output
├── command-lint.txt          # Lint output
├── command-type-check.txt    # Type check output
├── command-build.txt         # Build output
├── implementation-report.json # Agent report
└── context7-*.md             # Context7 documentation
```

**Evidence commands:**
```bash
# Tests
npm test 2>&1 | tee .project/qa/validation-evidence/T-001/round-1/command-test.txt

# Linting
npm run lint 2>&1 | tee .project/qa/validation-evidence/T-001/round-1/command-lint.txt

# Type checking
npm run type-check 2>&1 | tee .project/qa/validation-evidence/T-001/round-1/command-type-check.txt

# Build
npm run build 2>&1 | tee .project/qa/validation-evidence/T-001/round-1/command-build.txt
```

---

### 2. Validator Roster Selection

Validators are selected based on:
- Task type
- Technology stack (packs)
- File patterns
- Global validators (always run)

**Example validator roster:**
```yaml
# From pack configuration
validators:
  - name: tdd-compliance
    type: global

  - name: typescript-quality
    type: tech-specific
    filePatterns: ["**/*.ts", "**/*.tsx"]

  - name: test-coverage
    type: global
    minCoverage: 90

  - name: nextjs-best-practices
    type: tech-specific
    packs: [nextjs]
```

---

### 3. Multi-Model Validation

**Parallel execution:**
```bash
# Edison runs validators concurrently
edison qa validate <task-id>
```

**Configuration:**
```yaml
orchestration:
  maxConcurrentAgents: 4
  validatorTimeout: 300
  executionMode: parallel
```

**Validator output:**
```json
{
  "validator": "tdd-compliance",
  "taskId": "T-001",
  "round": 1,
  "status": "approved",
  "score": 95,
  "findings": [],
  "evidence": {
    "redPhase": "present",
    "greenPhase": "present",
    "refactorPhase": "present"
  }
}
```

---

### 4. Consensus Requirements

**Approval criteria:**
- All validators must approve (status: "approved")
- No blocking findings
- All required evidence present
- Minimum score thresholds met

**Rejection triggers:**
- Any validator rejects (status: "rejected")
- Missing evidence files
- Failed quality gates
- Score below threshold

---

### 5. Follow-up Creation

**On rejection:**
```bash
# Create follow-up tasks from validator findings
edison task ensure_followups <task-id>
```

**Follow-up task structure:**
```markdown
---
id: T-002
status: todo
parent_id: T-001
---

## Fix TDD Compliance Issues

Validator: tdd-compliance
Finding: Missing REFACTOR phase evidence
Severity: high

Action required: Add refactor phase evidence showing code cleanup
```

**Follow-up location:**
```
.project/qa/validation-evidence/<task-id>/round-N/followups/
└── task-<followup-id>.md
```

---

## TDD Workflow

Test-Driven Development enforcement with RED→GREEN→REFACTOR cycle.

### Phase 1: RED (Write Failing Test)

**Objective:** Write a test that fails because the feature doesn't exist yet.

```bash
# 1. Write test file
# Example: src/features/__tests__/myFeature.test.ts

# 2. Run test and capture failure
npm test 2>&1 | tee .project/qa/validation-evidence/T-001/round-1/evidence-red.txt

# 3. Verify exit code is non-zero
echo $? # Should be 1 (failure)
```

**Evidence requirements:**
- Test file exists
- Test runs and fails
- Exit code: non-zero
- Timestamp: `T_red`

---

### Phase 2: GREEN (Make Test Pass)

**Objective:** Write minimal code to make the test pass.

```bash
# 1. Implement feature
# Example: src/features/myFeature.ts

# 2. Run test and capture success
npm test 2>&1 | tee .project/qa/validation-evidence/T-001/round-1/evidence-green.txt

# 3. Verify exit code is zero
echo $? # Should be 0 (success)
```

**Evidence requirements:**
- Implementation exists
- Test passes
- Exit code: zero
- Timestamp: `T_green` (must be > `T_red`)

---

### Phase 3: REFACTOR (Clean Up)

**Objective:** Improve code quality without changing behavior.

```bash
# 1. Refactor code (improve structure, remove duplication)

# 2. Run test and capture continued success
npm test 2>&1 | tee .project/qa/validation-evidence/T-001/round-1/evidence-refactor.txt

# 3. Verify exit code is still zero
echo $? # Should be 0 (success)
```

**Evidence requirements:**
- Code changes visible in git diff
- Tests still pass
- Exit code: zero
- Timestamp: `T_refactor` (must be > `T_green`)

---

### TDD Enforcement

**Configuration:**
```yaml
# From tdd.yaml
tdd:
  enforceRedGreenRefactor: true
  requireEvidence: true
  hmacValidation: false
```

**Guards at `task ready` gate:**
- RED evidence present
- GREEN evidence present
- REFACTOR evidence present (or explicit waiver)
- Timestamp order: RED < GREEN < REFACTOR
- Exit codes correct (RED: non-zero, GREEN: zero, REFACTOR: zero)
- No `.only` in test files (blocks ready)

**Waiver for REFACTOR:**
```bash
# If no refactor needed
echo "No refactoring required - code already optimal" > \
  .project/qa/validation-evidence/T-001/round-1/refactor-waiver.txt
```

---

### TDD Evidence Validation

**Automatic checks:**
```bash
# Edison validates TDD compliance
edison task ready <task-id>
```

**Validation logic:**
1. Check evidence files exist
2. Verify timestamp ordering
3. Validate exit codes in logs
4. Check for test isolation (no `.only`)
5. Confirm coverage thresholds

**Coverage requirements:**
- Overall: 90% (configurable)
- Changed lines: 100% (configurable)

---

## Delegation Workflow

Automatic sub-agent delegation based on file patterns and task types.

### 1. File Pattern Matching

**Delegation rules from `delegation.yaml`:**

```yaml
filePatternRules:
  # React components → Claude
  "*.tsx":
    preferredModel: claude
    preferredZenRole: component-builder-nextjs
    delegateVia: zen-mcp

  # API routes → Codex
  "**/route.ts":
    preferredModel: codex
    preferredZenRole: api-builder
    delegateVia: zen-mcp

  # Tests → Codex
  "**/*.test.ts":
    preferredModel: codex
    preferredZenRole: test-engineer
    delegateVia: zen-mcp

  # Database schema → Codex
  "schema.prisma":
    preferredModel: codex
    preferredZenRole: database-architect-prisma
    delegateVia: zen-mcp
```

---

### 2. Model Selection

**Selection criteria:**
1. File pattern match (highest priority)
2. Task type hint
3. Default/fallback chain

**Fallback chain:**
```yaml
delegation:
  implementers:
    primary: codex
    fallbackChain: [gemini, claude]
    maxFallbackAttempts: 3
```

---

### 3. Sub-Agent Spawning

**Via Zen MCP Server:**

```bash
# Edison delegates to Zen MCP
# Zen spawns isolated sub-agent
```

**Zen configuration (`.mcp.json`):**
```json
{
  "mcpServers": {
    "edison-zen": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/BeehiveInnovations/zen-mcp-server.git",
        "zen-mcp-server"
      ],
      "env": {
        "ZEN_WORKING_DIR": "/path/to/project"
      }
    }
  }
}
```

**Sub-agent receives:**
- Task description
- File context
- Guidelines (from pack)
- Constitution
- TDD requirements

---

### 4. Result Collection

**Sub-agent produces:**
```
.project/qa/validation-evidence/<task-id>/round-1/
├── implementation-report.json
├── evidence-red.txt
├── evidence-green.txt
├── evidence-refactor.txt
└── command-*.txt
```

**Implementation report:**
```json
{
  "taskId": "T-001",
  "round": 1,
  "implementationApproach": "delegated-zen-mcp",
  "primaryModel": "codex",
  "zenRole": "api-builder",
  "completionStatus": "complete",
  "filesModified": [
    "src/app/api/users/route.ts",
    "src/app/api/users/__tests__/route.test.ts"
  ],
  "tddCompliance": {
    "followed": true,
    "phases": ["RED", "GREEN", "REFACTOR"]
  }
}
```

---

### Task Type Delegation

**Task type rules:**

```yaml
taskTypeRules:
  ui-component:
    preferredModel: claude
    preferredZenRole: component-builder-nextjs
    delegation: required

  api-route:
    preferredModel: codex
    preferredZenRole: api-builder
    delegation: required

  full-stack-feature:
    preferredModel: multi
    preferredModels: [gemini, codex]
    preferredZenRole: feature-implementer
    delegation: partial  # Multi-model orchestration
```

---

## Error Recovery

Handling session timeouts, stale locks, and worktree issues.

### 1. Session Recovery Commands

**Check session health:**
```bash
# Validate session state
edison session validate <session-id>

# Check for timeouts
edison session verify <session-id>
```

**Recover stale session:**
```bash
# Move to recovery state
edison session status <session-id> --set recovery

# Resume from recovery
edison session status <session-id> --set active
```

**Session timeout:**
```yaml
# From workflow.yaml
timeouts:
  sessionTimeout: 2h
  staleTaskThreshold: 4h
```

**Recovery config:**
```yaml
# From session.yaml
recovery:
  timeoutHours: 8
  staleCheckIntervalHours: 1
  clockSkewAllowanceSeconds: 300
  defaultTimeoutMinutes: 60
```

---

### 2. Stale Lock Cleanup

**Remove stale task locks:**
```bash
# Clean all stale locks
edison task cleanup_stale_locks

# Check lock status
edison task status <task-id>
```

**Lock file location:**
```
.project/tasks/.locks/<task-id>.lock
```

**Lock contains:**
```json
{
  "taskId": "T-001",
  "sessionId": "sess-123",
  "processId": 12345,
  "hostname": "dev-machine",
  "timestamp": "2025-12-01T10:00:00Z"
}
```

---

### 3. Worktree Repair

**Check worktree health:**
```bash
# List worktrees
git worktree list

# Verify session worktree
edison session verify <session-id>
```

**Remove stale worktree:**
```bash
# Remove worktree
git worktree remove .project/sessions/wip/<session-id>/worktree

# Prune references
git worktree prune
```

**Recreate worktree:**
```bash
# Session creates new worktree on recovery
edison session status <session-id> --set active
```

**Worktree configuration:**
```yaml
# From session.yaml
worktree:
  uuidSuffixLength: 6
  timeouts:
    health_check: 10
    fetch: 60
    checkout: 30
    worktree_add: 30
    clone: 60
    install: 300
    branch_check: 10
    prune: 10
```

---

### 4. Transaction Recovery

**Session transaction:**
```bash
# Check transaction status
ls -la .project/sessions/_tx/

# Clean stale transactions
find .project/sessions/_tx/ -mtime +1 -delete
```

**Transaction settings:**
```yaml
# From session.yaml
transaction:
  minDiskHeadroom: 5242880  # 5MB

# From qa.yaml
transaction:
  maxAgeHours: 24
  autoCleanup: true
```

---

### 5. Recovery Workflow

**Session recovery state machine:**
```
active → recovery → active
active → recovery → closing
```

**Recovery steps:**
1. Detect timeout/failure
2. Transition to recovery state
3. Cleanup stale resources (locks, worktrees)
4. Verify session integrity
5. Resume or close session

**Manual recovery:**
```bash
# 1. Check session status
edison session status <session-id>

# 2. Move to recovery
edison session status <session-id> --set recovery

# 3. Clean up locks
edison task cleanup_stale_locks

# 4. Verify worktree
git worktree list

# 5. Resume or close
edison session status <session-id> --set active
# OR
edison session close <session-id>
```

---

## Quick Reference

### Common Command Sequences

**Start new work session:**
```bash
edison session create --session-id sess-feature-123
edison task claim T-001 --session sess-feature-123
edison session track start --task T-001 --type implementation
```

**Complete and validate task:**
```bash
edison task ready T-001
edison qa new T-001
edison qa validate T-001
edison qa promote --task T-001 --to validated
```

**Close session:**
```bash
edison session track complete --task T-001
edison session close sess-feature-123
```

---

### State Transition Quick Reference

**Task states:**
- `todo` → `wip` (claim)
- `wip` → `done` (ready)
- `done` → `validated` (validation approved)
- `done` → `wip` (validation rejected)

**QA states:**
- `waiting` → `todo` (revalidate)
- `todo` → `wip` (promote)
- `wip` → `done` (promote)
- `done` → `validated` (approve)
- `wip` → `waiting` (reject)

**Session states:**
- `active` → `closing` (close)
- `closing` → `validated` (verified)
- `validated` → `archived` (archive)
- `active` → `recovery` (timeout/error)

---

### Evidence File Checklist

For each task validation round:
- [ ] `implementation-report.json`
- [ ] `command-test.txt`
- [ ] `command-lint.txt`
- [ ] `command-type-check.txt`
- [ ] `command-build.txt`
- [ ] `evidence-red.txt` (TDD RED phase)
- [ ] `evidence-green.txt` (TDD GREEN phase)
- [ ] `evidence-refactor.txt` (TDD REFACTOR phase)
- [ ] `context7-*.md` (optional documentation)

---

### Configuration Files Reference

- **State machine:** `src/edison/data/config/state-machine.yaml`
- **Workflow:** `src/edison/data/config/workflow.yaml`
- **Session:** `src/edison/data/config/session.yaml`
- **QA:** `src/edison/data/config/qa.yaml`
- **TDD:** `src/edison/data/config/tdd.yaml`
- **Delegation:** `src/edison/data/config/delegation.yaml`
- **MCP:** `.mcp.json` (project-specific)

---

## See Also

- [ZEN_SETUP.md](ZEN_SETUP.md) - Zen MCP Server setup
- [README.md](../README.md) - Edison overview
- State machine config: `src/edison/data/config/state-machine.yaml`
- Workflow config: `src/edison/data/config/workflow.yaml`

---

**Last Updated:** 2025-12-01
**Version:** 1.0.0
