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
edison session create [--session-id <id>]
```

**Purpose**: Create a session record in `{{fn:session_state_dir("active")}}/`
**When to use**: Starting a new work session

**Example:**
```bash
edison session create --session-id sess-001
```

---

### Start Session with Orchestrator

```bash
edison orchestrator start --profile <profile> [--detach] [--no-worktree]
```

**Purpose**: Create session, optional worktree, and launch the orchestrator process
**When to use**: Starting a new orchestration session end-to-end

**Example:**
```bash
edison orchestrator start --profile dev --detach
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

### Session Context (Hook-Safe Refresher)

```bash
edison session context [<session-id>] [--json]
```

**Purpose**: Print a compact, deterministic context refresher suitable for Claude Code hooks (SessionStart, PreCompact).

**Includes:**
- Project + session basics
- Constitution pointers (Agent/Orchestrator/Validator)
- Loop driver reminder (`edison session next <session-id>`)

**Optional**: When `memory.contextInjection.enabled=true`, appends “Memory Hits” from configured long-term memory providers.

---

### Close Session

```bash
edison session close <session-id>
```

**Purpose**: Verify everything is ready and transition the session to the closing state
**When to use**: When you want to stop active work and begin close-out (moves `active → closing` when guards allow)

---

### Complete Session (Promote to Validated)

```bash
edison session complete <session-id>
```

**Purpose**: Verify and promote the session to the validated/final state
**When to use**: After close-out checks are satisfied and you’re ready to finalize the session lifecycle

---

## Task Management

{{include-section:guidelines/includes/TASK_PLANNING.md#orchestrator-cli-snippet}}

### List Ready Tasks

```bash
edison task ready
```

**Purpose**: Show tasks ready to be claimed (**derived from the task graph**, not just “todo”)
**When to use**: Finding next task to work on

**Readiness rule (default)**: A task is “ready” when it’s in `{{fn:semantic_state("task","todo")}}` and all `depends_on` tasks are in `{{fn:semantic_states("task","done,validated","pipe")}}`.

Use `edison task blocked` to see why a todo task is not ready.

**Example output:**
```
TASK-123  [{{fn:semantic_state("task","todo")}}]   Implement user authentication
TASK-124  [{{fn:semantic_state("task","todo")}}]   Add email validation
```

---

### List Blocked Todo Tasks (Why Not Ready?)

```bash
edison task blocked [<task-id>] [--json]
```

**Purpose**: Explain todo tasks blocked by unmet `depends_on` dependencies (and show the “why”).

---

### Claim Task

```bash
edison task claim <task-id> [--session <session-id>]
```

**Purpose**: Claim a task from `{{fn:semantic_state("task","todo")}} → {{fn:semantic_state("task","wip")}}` and bind to session
**When to use**: Starting work on a new task

**Dependency enforcement**: Claim is fail-closed. If the task has unmet `depends_on`, the claim is blocked. Use:
```bash
edison task blocked <task-id>
edison task waves
```

**Example:**
```bash
edison task claim TASK-123 --session sess-001
```

**Effects:**
- Moves task to session scope: `{{fn:session_state_dir("active")}}/sess-001/tasks/{{fn:semantic_state("task","wip")}}/TASK-123.md`
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

### Task Done (Promote to Done)

```bash
edison task done <task-id> [--session <session-id>]
```

**Purpose**: Move task from `{{fn:semantic_state("task","wip")}} → {{fn:semantic_state("task","done")}}` with evidence checks
**When to use**: After implementation is complete, before validation

**Checks:**
- TDD evidence exists
- Commit order is correct
- Implementation report is present
- Session scope is valid

**Example:**
```bash
edison task done TASK-123 --session sess-001
```

**Effects:**
- Task moves to `{{fn:semantic_state("task","done")}}`
- Associated QA brief moves from `{{fn:semantic_state("qa","waiting")}} → {{fn:semantic_state("qa","todo")}}`

---

## QA and Validation

### Promote QA Brief

```bash
edison qa promote <task-id> --status <state>
```

**Purpose**: Advance QA brief through validation states
**When to use**: After validation passes, to promote QA state

**States**: {{fn:state_names("qa")}}

**Example:**
```bash
# Start validation
edison qa promote TASK-123 --status {{fn:semantic_state("qa","todo")}}

# Mark validation in progress
edison qa promote TASK-123 --status {{fn:semantic_state("qa","wip")}}

# Mark validation complete
edison qa promote TASK-123 --status {{fn:semantic_state("qa","done")}}

# Finalize after bundle approval
edison qa promote TASK-123 --status {{fn:semantic_state("qa","validated")}}
```

**Requirements for `{{fn:semantic_state("qa","done")}} → {{fn:semantic_state("qa","validated")}}`:**
- `{{config.validation.artifactPaths.bundleSummaryFile}}` exists
- All required validator reports present
- No blocking failures

---

### Validation Roster and Execution

```bash
# Show validation roster (auto-detected from file patterns)
edison qa validate <task-id>

# Execute validators directly via CLI engines
edison qa validate <task-id> --execute
```

**Purpose**: View and execute validators for a task
**When to use**: After task is in `{{fn:semantic_state("task","done")}}` state, to run validation

**How validators are selected:**
1. **Always-run validators**: `always_run: true` in config (critical wave)
2. **Triggered validators**: File pattern matching against modified files
3. **Orchestrator-added validators**: Extra validators you specify

---

### Adding Extra Validators (IMPORTANT)

**Orchestrators can ADD validators but cannot remove auto-detected ones.**

Sometimes auto-detection misses validators because:
- UI components living in unexpected file extensions or locations (outside the configured triggers)
- API logic in non-standard locations
- Framework-specific patterns not covered by triggers

**To add extra validators:**
```bash
# Add a validator even if it was not auto-triggered
edison qa validate TASK-123 --add-validators <validator-id> --execute

# Add multiple validators
edison qa validate TASK-123 --add-validators <validator-id-1> <validator-id-2> --execute

# Specify wave for added validators
edison qa validate TASK-123 --add-validators <validator-id> --add-to-wave critical --execute
```

**When the CLI shows "ORCHESTRATOR DECISION POINTS":**
The CLI will suggest validators that might be relevant but weren't auto-triggered.
Review these suggestions and add validators as needed.

**Example CLI output:**
```
═══ ORCHESTRATOR DECISION POINTS ═══
The following validators were NOT auto-triggered but may be relevant:
  ► Consider adding '<validator-id>' validator
    Reason: Found files matching an untriggered pattern: src/utils/helpers.<ext>
    To add: edison qa validate TASK-123 --add-validators <validator-id>
```

---

### Direct CLI Execution vs Delegation

**Validators can execute in two ways:**

1. **Direct CLI** (✓ in roster): CLI tool installed, executes immediately
2. **Delegation** (→ in roster): CLI unavailable, generates instructions for orchestrator

**For delegated validators:**
1. Read delegation instructions from evidence folder
2. Execute validation using the specified palRole
3. Save results to `validator-<id>-report.md`

**Example with mixed execution:**
```bash
edison qa validate TASK-123 --execute

# Output shows:
# ✓ global-codex: approve (2.3s)    ← Direct CLI execution
# → global-gemini: pending          ← Needs delegation

# For pending validators, follow the delegation instructions
```

---

### Trigger Validation (Orchestrator Initiates)

Orchestrators can trigger validation directly OR delegate to validator agents.

**Option 1: Direct execution (preferred when CLI available):**
```bash
edison qa validate TASK-123 --execute
```

**Option 2: Delegate to validator agent:**
```
Use Task/Delegation tool to invoke validator agent:
- Agent: code-reviewer (or specialized validator)
- Command: edison qa validate <task-id>
- Monitor: Validator writes reports to evidence directory
```

**Orchestrator checks results:**
```bash
# After validation completes, check bundle
edison qa bundle <task-id>
```

---

## Delegation Commands

Orchestrators use delegation tools (Task tool, agent invocation) to assign work to specialized agents.

**Delegation priority chain:**
1. User instruction (highest priority)
2. File pattern matching (`.<ui-ext>` → component-builder, `<api-path-glob>` → api-builder)
3. Task type (ui → component-builder, database → database-architect)
4. Default fallback (feature-implementer)

**Common delegation patterns:**

```bash
# Via Task tool (in agent context):
delegate_to_agent(
  agent="component-builder",
  task="Implement UserProfile component",
  files=["src/components/UserProfile.<ext>"]
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
edison rules show-for-context transition "wip->done"

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
edison task done TASK-123 --session sess-001

# 3. Start validation
edison qa promote TASK-123 --status {{fn:semantic_state("qa","todo")}}

# 4. Delegate to validator
# (use Task tool to delegate to code-reviewer)

# 5. After validation passes, promote QA
edison qa promote TASK-123 --status {{fn:semantic_state("qa","validated")}}

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

**Session records**: `{{fn:session_state_dir("active")}}/<session-id>/session.json`
**Task files**: `{{fn:session_state_dir("active")}}/<session-id>/tasks/<task-state>/`
**QA briefs**: `{{fn:session_state_dir("active")}}/<session-id>/qa/<qa-state>/`
**Validation round artefacts (reports)**: `{{fn:evidence_root}}/<task-id>/round-N/`
**Bundle summaries**: `{{fn:evidence_root}}/<task-id>/round-N/{{config.validation.artifactPaths.bundleSummaryFile}}`
**Command evidence snapshots**: `.project/qa/evidence-snapshots/<git-head>/<fingerprint>/{clean|dirty}/command-*.txt`

---

## Best Practices

1. **Always run `session next` first**: Before every action, check recommended next steps
2. **Read rules before acting**: Understand constraints from applicable rules
3. **Delegate 80%+ of work**: Orchestrators coordinate, agents implement
4. **Keep context minimal**: Use snippets, not full files (<50K tokens)
5. **Parallelize when possible**: Launch concurrent work for independent tasks
6. **Validate before promoting**: Ensure validation passes before moving to `{{fn:semantic_state("qa","validated")}}`
7. **Monitor session state**: Use `session status` to track progress

---

## Related Documentation

- `edison read SESSION_WORKFLOW --type guidelines/orchestrators` - Full session workflow
- `edison read DELEGATION --type guidelines/shared` - Delegation priority chain
- `edison read STATE_MACHINE_GUARDS --type guidelines/orchestrators` - State transition rules

---

**Role**: Orchestrator
**Focus**: Coordination and delegation
**DO**: Manage sessions, delegate work, coordinate validation
**DON'T**: Implement features (delegate to agents), run validators directly
