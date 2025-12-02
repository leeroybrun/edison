# Edison CLI Reference for Orchestrators

## Overview

This guide covers CLI commands for orchestrators managing sessions, coordinating work, and delegating to specialized agents. Orchestrators make decisions, coordinate parallel work streams, and ensure proper workflow progression.

**Orchestrator responsibilities:**
- Session lifecycle management
- Task claiming and coordination
- Delegation to specialized agents
- QA promotion after validation
- Workflow state transitions

## Core Workflow Command (CRITICAL)

### Session Next

```bash
edison session next <session-id>
```

**Purpose**: Get recommended next actions for the session
**When to use**: **BEFORE EVERY ACTION** in your orchestration workflow

**This is your primary decision-making tool.**

**Output sections (read IN ORDER):**
1. 📋 **APPLICABLE RULES** - Read FIRST before taking action
2. 🎯 **RECOMMENDED ACTIONS** - Read AFTER understanding rules
3. 🤖 **DELEGATION HINT** - Follow delegation priority chain
4. 🔍 **VALIDATORS** - Auto-detected from git diff

**Example:**
```bash
edison session next sess-001
```

**Workflow loop:**
```
1. Run: edison session next <session-id>
2. Read output (rules → actions → delegation)
3. Execute recommended command
4. REPEAT from step 1
```

---

## Session Management

### Create New Session

```bash
edison session create --session-id <id>
```

**Purpose**: Create a session record in `sessions/wip/`
**When to use**: Starting a new work session

**Example:**
```bash
edison session create --session-id sess-001
```

---

### Start Session with Orchestrator

```bash
edison session start <task-id> --orchestrator <profile> [--detach]
```

**Purpose**: Create session, optional worktree, and launch orchestrator
**When to use**: Starting a new task with full session setup

**Example:**
```bash
edison session start TASK-123 --orchestrator dev --detach
```

---

### Session Status

```bash
edison session status <session-id> [--json]
```

**Purpose**: Show current session state and scope
**When to use**: Checking session progress, debugging state

**Example:**
```bash
edison session status sess-001 --json
```

**Output includes:**
- Session state (active, waiting, closing)
- Owner and timestamps
- Task scope (parent + children)
- Worktree metadata (if applicable)

---

### Complete Session

```bash
edison session complete <session-id>
```

**Purpose**: Verify everything is validated and archive the session
**When to use**: After all tasks are validated and promoted

**Requirements:**
- All tasks in session must be `validated`
- All QA briefs must be `validated`
- No pending work remains

---

## Task Management

### List Ready Tasks

```bash
edison task ready
```

**Purpose**: Show tasks ready to be claimed
**When to use**: Finding next task to work on

**Example output:**
```
TASK-123  [todo]   Implement user authentication
TASK-124  [todo]   Add email validation
```

---

### Claim Task

```bash
edison task claim <task-id> [--session <session-id>]
```

**Purpose**: Claim a task from `todo → wip` and bind to session
**When to use**: Starting work on a new task

**Example:**
```bash
edison task claim TASK-123 --session sess-001
```

**Effects:**
- Moves task to session scope: `sessions/wip/sess-001/tasks/wip/TASK-123.md`
- Stamps ownership and timestamps
- Updates session graph

---

### Task Status

```bash
edison task status <task-id> [--json]
```

**Purpose**: Inspect task state and metadata
**When to use**: Checking task progress, understanding requirements

**Example:**
```bash
edison task status TASK-123 --json
```

---

### Task Ready (Promote to Done)

```bash
edison task ready <task-id> [--session <session-id>]
```

**Purpose**: Move task from `wip → done` with evidence checks
**When to use**: After implementation is complete, before validation

**Checks:**
- TDD evidence exists
- Commit order is correct
- Implementation report is present
- Session scope is valid

**Example:**
```bash
edison task ready TASK-123 --session sess-001
```

**Effects:**
- Task moves to `done`
- Associated QA brief moves from `waiting → todo`

---

## QA and Validation

### Promote QA Brief

```bash
edison qa promote --task <task-id> --to <state>
```

**Purpose**: Advance QA brief through validation states
**When to use**: After validation passes, to promote QA state

**States**: `waiting → todo → wip → done → validated`

**Example:**
```bash
# Start validation
edison qa promote --task TASK-123 --to todo

# Mark validation in progress
edison qa promote --task TASK-123 --to wip

# Mark validation complete
edison qa promote --task TASK-123 --to done

# Finalize after bundle approval
edison qa promote --task TASK-123 --to validated
```

**Requirements for `done → validated`:**
- `bundle-approved.json` exists
- All required validator reports present
- No blocking failures

---

### Trigger Validation (Orchestrator Initiates)

Orchestrators trigger validation but don't run validators directly.

**Delegate to validator agent:**
```
Use Task/Delegation tool to invoke validator agent:
- Agent: code-reviewer (or specialized validator)
- Command: edison qa validate --task <task-id>
- Monitor: Validator writes reports to evidence directory
```

**Orchestrator checks results:**
```bash
# After validator completes, check bundle
edison qa bundle <task-id>
```

---

## Delegation Commands

Orchestrators use delegation tools (Task tool, agent invocation) to assign work to specialized agents.

**Delegation priority chain:**
1. User instruction (highest priority)
2. File pattern matching (`.tsx` → component-builder, `api/**` → api-builder)
3. Task type (ui → component-builder, database → database-architect)
4. Default fallback (feature-implementer)

**Common delegation patterns:**

```bash
# Via Task tool (in agent context):
delegate_to_agent(
  agent="component-builder-nextjs",
  task="Implement UserProfile component",
  files=["app/components/UserProfile.tsx"]
)

# Or via explicit agent file invocation
# (in Claude Code context)
```

---

## Git and Worktree Management

### Sync Git Worktree

```bash
edison session sync-git <session-id>
```

**Purpose**: Create/sync git worktree for isolated work
**When to use**: Setting up parallel development environments

---

### Conflict Check

```bash
edison session conflict-check <session-id>
```

**Purpose**: Dry-run merge against base branch
**When to use**: Before promoting to ensure no merge conflicts

---

## Rules Query

### Show Rules for Context

```bash
edison rules show-for-context <category> <context>
```

**Purpose**: Query applicable rules for current situation
**When to use**: Understanding constraints before making decisions

**Examples:**
```bash
# Delegation rules
edison rules show-for-context guidance delegation

# State transition rules
edison rules show-for-context transition "wip→done"

# Context budget rules
edison rules show-for-context context budget
```

---

## Common Workflows

### Starting a New Task

```bash
# 1. Get next action
edison session next sess-001

# 2. List ready tasks
edison task ready

# 3. Claim task
edison task claim TASK-123 --session sess-001

# 4. Delegate implementation
# (use Task tool to delegate to appropriate agent)

# 5. Monitor progress
edison session next sess-001
```

### Completing a Task

```bash
# 1. Verify implementation complete
edison task status TASK-123

# 2. Promote to done
edison task ready TASK-123 --session sess-001

# 3. Start validation
edison qa promote --task TASK-123 --to todo

# 4. Delegate to validator
# (use Task tool to delegate to code-reviewer)

# 5. After validation passes, promote QA
edison qa promote --task TASK-123 --to validated

# 6. Check session state
edison session next sess-001
```

### Parallel Work Coordination

```bash
# 1. Claim multiple independent tasks
edison task claim TASK-123 --session sess-001
edison task claim TASK-124 --session sess-001

# 2. Delegate to multiple agents concurrently
# (use Task tool with parallel invocations)

# 3. Monitor progress
edison session status sess-001

# 4. Process completions as they arrive
edison session next sess-001
```

---

## Output Locations

**Session records**: `sessions/wip/<session-id>/session.json`
**Task files**: `sessions/wip/<session-id>/tasks/{wip,done}/`
**QA briefs**: `sessions/wip/<session-id>/qa/{waiting,todo,wip,done,validated}/`
**Validation evidence**: `.project/qa/validation-evidence/<task-id>/round-N/`
**Bundle summaries**: `.project/qa/validation-evidence/<task-id>/round-N/bundle-approved.json`

---

## Best Practices

1. **Always run `session next` first**: Before every action, check recommended next steps
2. **Read rules before acting**: Understand constraints from applicable rules
3. **Delegate 80%+ of work**: Orchestrators coordinate, agents implement
4. **Keep context minimal**: Use snippets, not full files (<50K tokens)
5. **Parallelize when possible**: Launch concurrent work for independent tasks
6. **Validate before promoting**: Ensure validation passes before moving to `validated`
7. **Monitor session state**: Use `session status` to track progress

---

## Related Documentation

- `.edison/_generated/guidelines/SESSION_WORKFLOW.md` - Full session workflow
- `.edison/_generated/guidelines/DELEGATION.md` - Delegation priority chain
- `.edison/_generated/guidelines/orchestrators/STATE_MACHINE_GUARDS.md` - State transition rules

---

**Role**: Orchestrator
**Focus**: Coordination and delegation
**DO**: Manage sessions, delegate work, coordinate validation
**DON'T**: Implement features (delegate to agents), run validators directly
