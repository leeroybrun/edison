# Mandatory Workflow

<!-- MANDATORY: All agents MUST read this before implementation -->
<!-- Generated from pre-Edison agent content extraction -->

## Purpose

This document defines the mandatory workflow that ALL implementing agents must follow. Failure to follow this workflow will result in guard failures and blocked task promotion. The workflow ensures consistent task claiming, implementation, and completion across all sub-agents.

## Requirements

<!-- section: workflow -->
### Workflow Overview

**YOU MUST FOLLOW** the implementer runbook and orchestrator playbook before ANY implementation work.

**Key Principle**: Agents do NOT operate autonomously. They receive tasks from the orchestrator, implement within their scope, and return results for validation.

### The Claim-Implement-Ready Cycle

Every task follows this three-phase workflow:

#### Phase 1: Claim Task

```bash
# Claim the task assigned by orchestrator
edison task claim <task-id>
```

**What this does**:
- Moves task from `todo/` to `sessions/wip/<session-id>/`
- Associates task with your session
- Locks task from other sessions

**Rules**:
- Only claim tasks assigned to you by the orchestrator
- Never claim tasks already claimed by other sessions
- One task at a time (complete current before claiming new)

#### Phase 2: Implement

Follow the implementation workflow:

1. **Read task requirements** - Understand acceptance criteria
2. **Check delegation config** - Verify you're the right agent
3. **Query Context7** - For post-training packages (CRITICAL)
4. **Follow TDD** - Write tests FIRST (RED-GREEN-REFACTOR)
5. **Implement** - Complete ALL requirements
6. **Verify** - Tests pass, type-check passes, lint passes, build passes

**Key Commands During Implementation**:
```bash
# Create new QA evidence round
edison qa new <task-id>

# Run project automation (commands come from the active pack / project config)
<test-command>
<type-check-command>
<lint-command>
<build-command>
```

#### Phase 3: Mark Ready for Validation

```bash
# Mark task ready for validation
edison task ready <task-id>
```

**What this does**:
- Signals orchestrator that implementation is complete
- Triggers validation workflow
- Moves task to validation queue

**Rules**:
- ONLY mark ready when ALL work is COMPLETE
- NEVER mark ready with TODOs, skipped tests, or failing tests
- NEVER mark ready if you encountered blockers

### State Machine

Tasks follow a strict state machine:

```
todo → wip → validating → done
             ↓
           blocked → wip (after fixes)
```

**State Transitions**:
- `todo` → `wip`: When claimed by agent
- `wip` → `validating`: When marked ready
- `validating` → `done`: When ALL validators pass
- `validating` → `blocked`: When validators find issues
- `blocked` → `wip`: When agent addresses issues

## Evidence Required

Every implementation round must provide:

1. **Implementation Report JSON** (per `.edison/_generated/guidelines/agents/OUTPUT_FORMAT.md`)
2. **TDD Evidence** - Proof that tests were written first
3. **Test Results** - All tests passing
4. **Build Verification** - Type-check, lint, build all pass
5. **Evidence Paths** - Reference artefacts in `.project/qa/validation-evidence/<task-id>/`

## CLI Commands

### Task Management
```bash
# List tasks ready to claim
edison task ready

# Claim a task
edison task claim <task-id>

# Check task status
edison task status <task-id>

# Mark task ready for validation
edison task ready <task-id>
```

### QA and Evidence
```bash
# Create new QA evidence round
edison qa new <task-id>

# Check QA status
edison qa status <task-id>
```

### Validation
```bash
# Orchestrator runs validation (agents do NOT run this)
edison qa validate <task-id>
```

## Critical Rules

1. **NEVER bypass the workflow** - Always claim before implementing
2. **NEVER mark ready prematurely** - Only when 100% complete
3. **NEVER implement without tests** - TDD is mandatory
4. **ALWAYS provide evidence** - No evidence = incomplete work
5. **ALWAYS check delegation** - Verify you're the right agent

<!-- /section: workflow -->

## References

- Extended workflow: `.edison/_generated/guidelines/agents/AGENT_WORKFLOW.md`
- Output format: `.edison/_generated/guidelines/agents/OUTPUT_FORMAT.md`
- Session workflow: `.edison/_generated/guidelines/orchestrators/SESSION_WORKFLOW.md`

---

**Version**: 1.0 (Extracted from pre-Edison agents)
**Applies to**: ALL implementing agents (api-builder, component-builder, database-architect, feature-implementer, test-engineer)
