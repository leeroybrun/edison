# Delegation Patterns (Shared)

> For orchestrators delegating work and agents receiving delegated work.

## Delegation Principles

### When to Delegate
- **Multi-skill work**: Task spans multiple domains (backend + frontend + data)
- **Time-sensitive**: Parallelizable independent work within concurrency cap
- **Specialized expertise**: Security, performance, database, UX requiring focused skill
- **Non-trivial scope**: Task requires >30 minutes or multiple files
- **Scale**: Large refactors or features splittable into independent slices

### When NOT to Delegate
- **Trivial edits**: Single-line fixes, typos, obvious renames (faster to do than brief)
- **Config prohibits**: Task flagged `neverImplementDirectly: false` or similar
- **Already focused**: You are the assigned specialist for this exact work
- **Coordination overhead**: Briefing cost exceeds implementation cost

### Why Delegate
- **Leverage specialization**: Right expert for the right task
- **Maximize throughput**: Parallel execution within concurrency limits
- **Maintain quality**: Focused agents produce better results
- **Preserve independence**: Separate implementers from validators

## Clear Task Definition

### Task Brief Must Include

#### 1. Core Context
- **Task ID**: Unique identifier for tracking
- **Task Type**: Feature, bug fix, refactor, test, documentation
- **Priority**: Critical, high, normal, low
- **Scope Boundaries**: What's IN scope and OUT of scope

#### 2. Requirements
- **Acceptance Criteria**: Explicit, testable conditions for completion
- **Constraints**: TDD required, no mocks, no hardcoded values, no legacy code
- **Dependencies**: Blocking tasks, required data, external systems
- **File Scope**: Specific files/directories to modify or create

#### 3. Technical Guidance
- **Patterns**: Which existing patterns to follow (provide file references)
- **Integration Points**: APIs, databases, external services to integrate
- **Configuration**: YAML files to read/update, no hardcoded values
- **Error Handling**: Expected error scenarios and handling strategy

#### 4. Deliverables
- **Code Changes**: Specific files expected
- **Tests**: Test files and coverage requirements (≥90%)
- **Evidence**: Commands to run and expected outputs
- **Documentation**: Implementation report location and format

### Task Brief Template

```markdown
# Task: <brief-title>

**ID**: <task-id>
**Type**: feature|bugfix|refactor|test|docs
**Priority**: critical|high|normal|low
**Assigned To**: <agent-role>
**Estimated Effort**: <time-estimate>

## Scope

**In Scope:**
- <specific-item-1>
- <specific-item-2>

**Out of Scope:**
- <explicitly-excluded-item-1>
- <explicitly-excluded-item-2>

## Requirements

### Acceptance Criteria
1. <testable-criterion-1>
2. <testable-criterion-2>
3. <testable-criterion-3>

### Constraints
- [ ] TDD (RED-GREEN-REFACTOR cycle required)
- [ ] No mocks (test real behavior)
- [ ] No hardcoded values (all config from YAML)
- [ ] No legacy code (clean implementation)
- [ ] Follow existing patterns in <reference-file>

### Dependencies
- Requires: <task-id-or-resource>
- Blocks: <task-id>

## Technical Guidance

**Patterns to Follow:**
- See: `<path-to-reference-implementation>`
- Config: `<path-to-yaml-config>`

**Integration:**
- Database: <connection-details>
- APIs: <endpoint-specifications>
- External: <service-details>

## Deliverables

**Code:**
- `<path-to-file-1>` - <purpose>
- `<path-to-file-2>` - <purpose>

**Tests:**
- `<path-to-test-1>` - <coverage-requirement>
- Coverage: ≥90% on changed files

**Evidence:**
```bash
# Commands to run
<command-1>
<command-2>
```

**Report:**
- Implementation report: `<path-to-report.json>`
```

## Context Passing

### What Context to Provide

#### Essential Context (Always Include)
1. **Session Context**: Session ID, owner, parent task
2. **Project Standards**: Link to CRITICAL_PRINCIPLES.md or constitution
3. **Relevant Code**: Code snippets (NOT full files) showing patterns
4. **Configuration**: Relevant YAML sections (NOT entire config files)
5. **Dependencies**: Related task IDs and their status

#### Supplemental Context (Include When Relevant)
1. **Historical Context**: Why this approach was chosen
2. **Previous Attempts**: What was tried and why it didn't work
3. **Performance Requirements**: Latency, throughput, resource constraints
4. **Security Requirements**: Auth, validation, data protection needs
5. **User Impact**: Who will be affected and how

### What NOT to Include
- ❌ Full file contents (use snippets instead)
- ❌ Entire configuration files (extract relevant sections)
- ❌ Irrelevant historical decisions
- ❌ Speculative future requirements
- ❌ Personal preferences not codified in standards

### Context Budget Guidelines
- **Snippets over files**: Share 10-20 lines, not 500-line files
- **References over duplication**: Point to canonical docs, don't copy
- **Relevant only**: If it doesn't inform THIS task, omit it
- **Minimize tokens**: Preserve context budget for implementation

## Output Requirements

### Implementation Report (Required)

Every task must produce an implementation report:

```json
{
  "taskId": "<task-id>",
  "agent": "<agent-role>",
  "status": "completed|blocked|needs-clarification",
  "summary": "<1-2 sentence summary>",

  "changes": {
    "filesCreated": ["<path>"],
    "filesModified": ["<path>"],
    "filesDeleted": ["<path>"]
  },

  "tddCompliance": {
    "testFirst": true,
    "redPhaseEvidence": "<path-or-commit>",
    "greenPhaseEvidence": "<path-or-commit>",
    "refactorPhase": true,
    "coveragePercent": 92
  },

  "validation": {
    "typeCheck": "pass",
    "lint": "pass",
    "tests": "pass",
    "commandOutputs": {
      "typeCheck": "<path-to-output>",
      "lint": "<path-to-output>",
      "test": "<path-to-output>"
    }
  },

  "delegations": [
    {
      "subtaskId": "<subtask-id>",
      "agent": "<sub-agent-role>",
      "model": "<model-used>",
      "outcome": "success|failed|blocked"
    }
  ],

  "followUps": [
    {
      "type": "blocking|non-blocking",
      "description": "<what-needs-doing>",
      "suggestedAgent": "<agent-role>"
    }
  ],

  "blockers": [],
  "notes": "<additional-context>"
}
```

### Evidence Files (Required)

- **Test Outputs**: RED phase failure, GREEN phase pass, REFACTOR phase pass
- **Automation Outputs**: Type check, lint, test, build results
- **Coverage Reports**: Coverage percentage and detailed report
- **Context7 Evidence**: If post-training packages used (HMAC-stamped)

### Agent Response Format

```markdown
# Implementation Report: <task-title>

## Summary
<1-2 sentence summary of what was implemented>

## Changes Made
- Created: `<file-path>` - <purpose>
- Modified: `<file-path>` - <what-changed>
- Deleted: `<file-path>` - <why-removed>

## TDD Compliance
✅ RED: Test written first, failed with: <error-message>
✅ GREEN: Implementation passes all tests
✅ REFACTOR: Code cleaned, tests still pass
✅ Coverage: 92% (threshold: 90%)

## Validation Results
✅ Type Check: PASS
✅ Lint: PASS
✅ Tests: PASS (12 passed, 0 failed)
✅ Build: PASS

## Evidence
- Test outputs: `<path-to-evidence>`
- Coverage report: `<path-to-coverage>`
- Implementation report: `<path-to-report.json>`

## Follow-Ups
None / See report JSON for details

## Notes
<any-important-context-for-orchestrator>
```

## Parallel Delegation

### When to Parallelize
- **Independent work**: No shared state or dependencies between tasks
- **Time-sensitive**: Deadline requires concurrent execution
- **Capacity available**: Within configured concurrency cap
- **Clear boundaries**: Each task has well-defined scope

### Parallel Delegation Pattern

```pseudocode
// Check concurrency limit
maxConcurrent = config.get("delegation.maxConcurrentSubAgents")
currentActive = countActiveSubAgents()

if (taskCount <= maxConcurrent - currentActive) {
  // Launch all tasks in parallel
  tasks = splitIntoParallelTasks(workScope)
  results = await Promise.all(tasks.map(t => delegateToAgent(t)))
} else {
  // Batch: launch what fits, queue remainder
  batch1 = tasks.slice(0, maxConcurrent - currentActive)
  batch2 = tasks.slice(maxConcurrent - currentActive)

  results1 = await Promise.all(batch1.map(t => delegateToAgent(t)))
  results2 = await Promise.all(batch2.map(t => delegateToAgent(t)))

  results = [...results1, ...results2]
}
```

### Parallel Task Structure
- **Link to parent**: All child tasks reference same parent for validation bundling
- **Independence marker**: Explicitly note no dependencies between siblings
- **Coordination protocol**: Define how to handle conflicts if any arise
- **Completion criteria**: Parent cannot complete until all children validated

## Result Synthesis

### Combining Parallel Results

#### 1. Collect All Outputs
- Gather implementation reports from all sub-agents
- Collect evidence files from all tasks
- Check for blockers or failures in any task

#### 2. Validate Consistency
- **No conflicts**: Same file not modified by multiple agents
- **Integration points**: APIs/interfaces match between tasks
- **Configuration**: No conflicting YAML changes
- **Tests**: All test suites pass independently and together

#### 3. Create Unified Report

```json
{
  "parentTaskId": "<parent-id>",
  "childTasks": ["<child-1>", "<child-2>", "<child-3>"],
  "overallStatus": "completed|partial|failed",

  "aggregatedResults": {
    "totalFiles": 15,
    "filesCreated": 8,
    "filesModified": 7,
    "filesDeleted": 0,
    "coveragePercent": 91
  },

  "delegations": [
    {"taskId": "<child-1>", "agent": "<agent-1>", "status": "success"},
    {"taskId": "<child-2>", "agent": "<agent-2>", "status": "success"},
    {"taskId": "<child-3>", "agent": "<agent-3>", "status": "success"}
  ],

  "integration": {
    "conflictsDetected": false,
    "integrationTestsPassed": true,
    "crossTaskDependenciesResolved": true
  },

  "followUps": "<aggregated-follow-ups>"
}
```

#### 4. Run Integration Validation
- Execute full test suite (not just individual task tests)
- Run type check across entire codebase
- Verify build succeeds with all changes
- Check for integration issues between tasks

## Error Handling

### When Sub-Agent Fails

#### 1. Assess Failure Type
- **Blocked**: Missing dependency, awaiting external input
- **Scope mismatch**: Task outside agent's expertise (MISMATCH pattern)
- **Technical failure**: Tests fail, cannot implement requirement
- **Incomplete**: Partial work, ran out of context/time

#### 2. Response Strategy

**For Blocked:**
```markdown
- Identify blocker source
- Create blocking follow-up task
- Pause current task until blocker resolved
- Update parent task status
```

**For Scope Mismatch:**
```markdown
- Accept MISMATCH response from agent
- Re-evaluate task assignment using delegation config
- Re-delegate to appropriate agent
- Record mismatch in activity log
```

**For Technical Failure:**
```markdown
- Analyze root cause (not symptoms)
- Determine if issue is in requirements or implementation
- If requirements: revise and re-brief
- If implementation: provide targeted guidance and retry
- Escalate if repeated failures
```

**For Incomplete:**
```markdown
- Extract completed portions
- Create new task for remaining work
- Ensure context continuity
- Re-assign with adjusted scope
```

### Delegation Error Patterns

❌ **Anti-Pattern**: Re-delegate infinitely
✅ **Correct**: Max 1 re-delegation, then escalate

❌ **Anti-Pattern**: Fix sub-agent's work yourself
✅ **Correct**: Provide feedback and re-delegate (maintain independence)

❌ **Anti-Pattern**: Ignore MISMATCH signals
✅ **Correct**: Respect agent scope boundaries

## Anti-Patterns

### 1. Delegation Without Context
❌ "Implement the login feature"
✅ "Implement JWT-based login following pattern in auth/helpers.<ext>, config from .edison/config/auth.yml"

### 2. Over-Delegating Trivial Work
❌ Delegating a one-line typo fix
✅ Fix directly (faster than briefing)

### 3. Under-Specifying Requirements
❌ "Make it work"
✅ "Must pass authentication, return 401 for invalid tokens, support refresh tokens per config"

### 4. Ignoring Agent Boundaries
❌ Forcing component-builder to implement API routes
✅ Split task: API route → api-builder, UI component → component-builder

### 5. Insufficient Context Passing
❌ "Use the existing pattern"
✅ "Follow pattern in src/api/users/route.<ext> lines 45-67 (auth + validation)"

### 6. No Output Requirements
❌ "Let me know when done"
✅ "Provide implementation report at .edison/tasks/<id>/report.json, evidence files, and test outputs"

### 7. Parallelizing Dependent Work
❌ Running schema migration and API implementation simultaneously
✅ Sequential: schema → migration → API

### 8. Sub-Agent Re-Delegation
❌ Agent delegating to another agent
✅ Return MISMATCH to orchestrator, let orchestrator re-delegate

### 9. Mixing Implementer and Validator Roles
❌ Same agent implements and validates
✅ Separate agents for independence

### 10. Context Budget Waste
❌ Including 3000-line files in delegation prompt
✅ Include 20-line relevant snippet with file reference
