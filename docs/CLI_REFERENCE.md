# Edison CLI Reference

**Complete Command Reference for the Edison Framework**

**Last Updated:** 2025-12-27

---

## Table of Contents

1. [Overview](#overview)
2. [Installation & Setup](#installation--setup)
3. [Common Flags & Options](#common-flags--options)
4. [Environment Variables](#environment-variables)
5. [Exit Codes](#exit-codes)
6. [Root Commands](#root-commands)
7. [Session Domain](#session-domain)
8. [Task Domain](#task-domain)
9. [QA Domain](#qa-domain)
10. [Compose Domain](#compose-domain)
11. [Config Domain](#config-domain)
12. [Git Domain](#git-domain)
13. [Rules Domain](#rules-domain)
14. [MCP Domain](#mcp-domain)
15. [Orchestrator Domain](#orchestrator-domain)
16. [Import Domain](#import-domain)
17. [Debug Domain](#debug-domain)
18. [Typical Workflows](#typical-workflows)

---

## Overview

Edison provides a hierarchical CLI organized by domains. Each domain groups related commands for managing different aspects of your project.

### Command Structure

```bash
edison <domain> <command> [options]
```

### Available Domains

| Domain | Purpose |
|--------|---------|
| `init` | Project initialization (root-level command) |
| `session` | Session lifecycle management |
| `task` | Task creation and workflow management |
| `qa` | Quality assurance and validation |
| `compose` | Artifact composition and generation |
| `config` | Configuration management |
| `git` | Git and worktree operations |
| `rules` | Rule management and checking |
| `mcp` | MCP server configuration |
| `orchestrator` | Orchestrator session management |
| `import` | Import tasks from external systems (SpecKit, OpenSpec) |
| `debug` | Debug and introspection utilities |

---

## Installation & Setup

### Installing Edison

```bash
pip install edison-framework
```

### Verifying Installation

```bash
edison --version
```

### Getting Help

```bash
# General help
edison --help

# Domain help
edison session --help

# Command help
edison session create --help
```

---

## Common Flags & Options

Most Edison commands support these common flags:

| Flag | Description |
|------|-------------|
| `--json` | Output results as JSON instead of human-readable text |
| `--repo-root <path>` | Override the repository root path (defaults to current directory) |
| `--dry-run` | Show what would be done without making changes (where applicable) |
| `--force` | Force operation without confirmation prompts (where applicable) |

### Using JSON Output

JSON output is useful for scripting and integration with other tools:

```bash
# JSON output for parsing
edison session status sess-001 --json | jq '.state'

# Human-readable output (default)
edison session status sess-001
```

---

## Environment Variables

Edison respects the following environment variables for configuration:

### General Configuration

- `EDISON_<section>__<key>` - Override any config value using double underscore notation
  - Example: `EDISON_database__url` overrides `database.url` in config
  - Example: `EDISON_tdd_enforceRedGreenRefactor=false` disables TDD enforcement (use only for exceptional bootstrapping/emergency recovery; never to bypass tests for executable behavior changes)
  - Example: `EDISON_paths__project_config_dir=custom` sets custom config directory
  - Example: `EDISON_paths__user_config_dir=~/.edison` sets the user config directory

### Session Management

- `EDISON_SESSION_ID` - Current session context (set automatically by session commands)

### Testing & Development

- `EDISON_ASSUME_YES` - Automatically answer "yes" to confirmation prompts (value: "1" or "true")
- `EDISON_FORCE_DISK_FULL` - Simulate disk full condition for testing
- `EDISON_FORCE_PERMISSION_ERROR` - Simulate permission errors for testing

### Configuration Precedence

Edison loads configuration in this order (later overrides earlier):

1. Bundled defaults (from edison package)
2. Pack config files (active packs across bundled/user/project pack roots)
3. User config files (`~/.edison/config/*.yml` by default)
4. Project config files (`.edison/config/*.yml`)
5. Project-local config files (`.edison/config.local/*.yml`, uncommitted; per-user per-project)
6. Environment variables (`EDISON_*`)

---

## Exit Codes

Edison commands follow standard Unix exit code conventions:

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | General error (validation failed, resource not found, etc.) |
| `130` | Interrupted by user (Ctrl+C) |

### Command-Specific Exit Codes

Some commands have additional meanings:

- **session verify/validate**: `1` = verification failed, session not ready to close
- **task status**: `1` = transition blocked by state machine guards
- **qa validate**: `1` = validation failed, blocking issues found

---

## Root Commands
### init

Initialize Edison in a repository (setup wizard).

Key behaviors:
- Writes `.edison/` structure and config overrides under `.edison/config/`.
- If worktrees are enabled (and sharedState mode is `meta`), it will run the equivalent of:
  - `edison git worktree-meta-init`
  before running initial composition. This ensures `.project/*`, `.edison/_generated`, and tool dirs are
  symlinked to the meta worktree before any generation happens.

Examples:

```bash
# Interactive wizard
edison init

# Non-interactive (no prompts): write recommended defaults and detected values
edison init --non-interactive

# Non-interactive + enable worktrees and meta init
edison init --non-interactive --enable-worktrees

# Skip meta init even if worktrees are enabled
edison init --skip-worktree-meta-init
```

Worktrees note:
- The setup wizard asks for the shared-state mode (`meta` / `primary` / `external`).
- If you choose `external`, you will be asked for `worktrees.sharedState.externalPath`.


### init - Initialize Project

Initialize an Edison project with interactive setup wizard or use bundled defaults.

```bash
edison init [project_path] [options]
```

**Arguments:**

- `project_path` - Project directory to initialize (defaults to current directory)

**Options:**

| Option | Description |
|--------|-------------|
| `--non-interactive` | Skip questionnaire, use bundled defaults (no config files written) |
| `--advanced` | Include advanced configuration questions in interactive mode |
| `--force` | Overwrite existing config files without prompting |
| `--merge` | Merge with existing config files instead of skipping them |
| `--reconfigure` | Re-run questionnaire on an existing project |
| `--skip-mcp` | Skip MCP configuration during initialization |
| `--mcp-script` | Use script-based MCP command variant when available |
| `--skip-compose` | Skip running initial composition after setup |

**When to Use:**

- First-time setup of Edison in a project
- Reconfiguring an existing Edison project
- Creating a minimal setup without custom overrides

**Examples:**

```bash
# Interactive setup (basic mode)
edison init .

# Non-interactive setup with defaults
edison init . --non-interactive

# Advanced setup with all questions
edison init /path/to/project --advanced

# Force overwrite existing config
edison init . --force

# Reconfigure existing project
edison init . --reconfigure

# Setup without MCP or composition
edison init . --skip-mcp --skip-compose
```

**What It Does:**

1. Creates `.edison/` directory structure
2. Runs setup questionnaire (unless `--non-interactive`)
3. Writes config files to `.edison/config/` (only values that differ from defaults)
4. Configures `.mcp.json` for MCP servers (unless `--skip-mcp`)
5. Runs initial composition to generate artifacts (unless `--skip-compose`)

**Exit Codes:**

- `0` - Initialization successful
- `1` - Error during setup (invalid path, permission denied, etc.)
- `130` - User cancelled interactive setup

---

## Session Domain

Sessions are the primary unit of work in Edison. Each session represents a unit of work (implementation, validation, etc.) and can have its own worktree, state, and associated tasks.

### session create - Create Session

Create a new Edison session with optional worktree and dependency installation.

```bash
edison session create --session-id <id> [options]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--session-id`, `--id` | Session identifier (required, e.g., `sess-001`) |
| `--owner` | Session owner (default: `system`) |
| `--mode` | Session mode (default: `start`) |
| `--worktree` | Explicitly enable worktree creation (default behavior; accepted for compatibility) |
| `--no-worktree` | Skip worktree creation |
| `--install-deps` | Install dependencies in worktree (if creating worktree) |
| `--json` | Output as JSON |
| `--repo-root` | Override repository root path |

**When to Use:**

- Starting a new work session
- Creating isolated worktree for parallel work
- Beginning implementation or validation work

**Examples:**

```bash
# Create basic session
edison session create --session-id sess-001

# Create session without worktree
edison session create --id sess-001 --no-worktree

# Create session with worktree (explicit; same as default)
edison session create --id sess-001 --worktree

# Create session with dependencies installed
edison session create --id sess-001 --install-deps

# Create session for specific owner
edison session create --id sess-001 --owner alice

# Get JSON output for scripting
edison session create --id sess-001 --json
```

**Output:**

```
✓ Created session: sess-001
  Path: /path/to/.edison/.sessions/sess-001
  Owner: system
  Mode: start
  Worktree: /path/to/.worktrees/sess-001
  Branch: edison/sess-001
```

**Exit Codes:**

- `0` - Session created successfully
- `1` - Error (session already exists, invalid ID, etc.)

---

### session list - List Sessions

List sessions across states.

```bash
edison session list [options]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--status <state>` | Filter by session status/state (accepts semantic state like `active` or directory alias like `wip`) |
| `--all` | Include terminal/final session states (e.g., `validated`/`archived`) |
| `--owner <owner>` | Filter by session owner |
| `--json` | Output as JSON |
| `--repo-root` | Override repository root path |

**Examples:**

```bash
# Default: excludes terminal sessions
edison session list
edison session list --all
edison session list --status wip
edison session list --status active
```

---

### session status - Display Session Status

Display the current status and metadata of a session.

```bash
edison session status [session_id] [--json]
```

**Arguments:**

- `session_id` - Session ID (optional, uses current session if not specified)

**Options:**

| Option | Description |
|--------|-------------|
| `--json` | Output as JSON |

**When to Use:**

- Checking current session state
- Verifying session configuration
- Debugging session issues

**Examples:**

```bash
# Show status of specific session
edison session status sess-001

# Show status of current session
edison session status

# Get JSON output
edison session status sess-001 --json
```

**Notes:**

- JSON output includes `tasks` / `qa` computed from the session directory layout.
  The directory layout is the source of truth for task/QA state.
- Use `edison session show <session-id>` to inspect the raw `session.json` persisted on disk.

**Output:**

```
Session: sess-001
Status: active
Task: 100-auth-feature
Owner: alice
```

**Exit Codes:**

- `0` - Status retrieved successfully
- `1` - Error (session not found, no current session, etc.)

---

### session show - Show Raw Session JSON

Print the session JSON record exactly as stored on disk.

```bash
edison session show <session_id> [options]
```

**Arguments:**

- `session_id` - Session identifier (e.g., `sess-001`)

**Options:**

| Option | Description |
|--------|-------------|
| `--json` | Output as JSON (includes parsed session + raw content) |
| `--repo-root` | Override repository root path |

**When to Use:**

- Debugging session metadata (worktree/branch linkage, state transitions)
- Inspecting persisted session record for recovery

---

### session next - Recommended Next Actions

Compute and display recommended next actions for a session based on current state.

```bash
edison session next <session_id> [options]
```

**Arguments:**

- `session_id` - Session identifier (required)

**Options:**

| Option | Description |
|--------|-------------|
| `--limit` | Maximum number of actions to return (0 = use default from manifest) |
| `--scope` | Restrict planning to specific domain: `tasks`, `qa`, or `session` |
| `--json` | Output as JSON |
| `--repo-root` | Override repository root path |

**When to Use:**

- Determining what to work on next
- Getting guidance on workflow progression
- Understanding available actions in current state

**Examples:**

```bash
# Get all recommended actions
edison session next sess-001

# Limit to top 5 actions
edison session next sess-001 --limit 5

# Show only task-related actions
edison session next sess-001 --scope tasks

# Get JSON output for automation
edison session next sess-001 --json
```

**Exit Codes:**

- `0` - Actions computed successfully
- `1` - Error (session not found, invalid scope, etc.)

---

### session close - Close Session

Validate and transition a session into closing/archival state.

```bash
edison session close <session_id> [options]
```

**Arguments:**

- `session_id` - Session identifier (required)

**Options:**

| Option | Description |
|--------|-------------|
| `--force` | Force closing even when verification fails |
| `--skip-validation` | Skip guard checks and move directly to closing (not recommended) |
| `--json` | Output as JSON |

**When to Use:**

- Completing a work session
- Archiving finished work
- Cleaning up after task completion

**Examples:**

```bash
# Close session with validation
edison session close sess-001

# Force close despite validation failures
edison session close sess-001 --force

# Skip validation entirely
edison session close sess-001 --skip-validation

# Get JSON output
edison session close sess-001 --json
```

**What It Does:**

1. Runs session health verification (unless `--skip-validation`)
2. Checks all tasks and QA records are in valid states
3. Transitions session to `closing` state
4. Returns error if verification fails (unless `--force`)

**Exit Codes:**

- `0` - Session closed successfully
- `1` - Verification failed or error occurred

---

### session verify - Verify Session Health

Verify a session against closing-phase guards without closing it.

```bash
edison session verify <session_id> --phase <phase> [--json]
```

**Arguments:**

- `session_id` - Session identifier (required)

**Options:**

| Option | Description |
|--------|-------------|
| `--phase` | Lifecycle phase to verify (currently only `closing` supported, required) |
| `--json` | Output as JSON |

**When to Use:**

- Pre-flight check before closing session
- Debugging why session won't close
- Validating session readiness

**Examples:**

```bash
# Verify session can be closed
edison session verify sess-001 --phase closing

# Get detailed JSON output
edison session verify sess-001 --phase closing --json
```

**Output:**

```
Session sess-001 failed closing verification:
  - Task 100-feature is in state 'wip', expected 'done' or 'validated'
  - QA record QA-100-feature missing evidence

State mismatches: 1
Missing evidence: 1
```

**Exit Codes:**

- `0` - Verification passed
- `1` - Verification failed or error occurred

---

### session validate - Validate and Score Session

Validate session health and optionally record validation scores.

```bash
edison session validate <session_id> [options]
```

**Arguments:**

- `session_id` - Session identifier (required)

**Options:**

| Option | Description |
|--------|-------------|
| `--dimension` | Specific dimension to validate |
| `--track-scores` | Track validation scores |
| `--check-regression` | Check for score regression |
| `--show-trend` | Show score trend over time |
| `--json` | Output as JSON |

**When to Use:**

- Validating session quality
- Tracking validation metrics over time
- Checking for regressions

**Examples:**

```bash
# Basic validation
edison session validate sess-001

# Validate specific dimension
edison session validate sess-001 --dimension completeness

# Track scores and check for regression
edison session validate sess-001 --track-scores --check-regression

# Show historical trend
edison session validate sess-001 --show-trend --json
```

**Exit Codes:**

- `0` - Validation passed
- `1` - Validation failed or error occurred

---

### session me - Session Identity

Show or update current session identity/context.

```bash
edison session me [options]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--json` | Output as JSON |

**When to Use:**

- Checking current session context
- Viewing session identity information

**Examples:**

```bash
# Show current session identity
edison session me

# Get JSON output
edison session me --json
```

**Exit Codes:**

- `0` - Success
- `1` - Error occurred

---

### session track - Track Work with Heartbeats

Track implementation or validation work with heartbeat updates.

```bash
edison session track <subcommand> [options]
```

#### track start - Start Tracking

Start tracking work on a task.

```bash
edison session track start --task <task-id> --type <type> [options]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--task` | Task ID (required) |
| `--type` | Type of work: `implementation` or `validation` (required) |
| `--model` | Execution backend/model identifier (required for validation) |
| `--validator` | Validator identifier (required for validation) |
| `--round` | Evidence round number (optional) |
| `--run-id` | Stable run UUID (optional; autogenerated when omitted) |
| `--process-id` | OS PID to record (optional; defaults to current process) |
| `--continuation-id` | Continuation/resume identifier (optional) |
| `--json` | Output as JSON |
| `--repo-root` | Override repository root path |

**Examples:**

```bash
# Start tracking implementation
edison session track start --task 100-feature --type implementation

# Start tracking validation with model
edison session track start --task 100-feature --type validation --model claude --round 1

# Track with validator
edison session track start --task 100-feature --type validation --validator qa-001 --model claude
```

#### track complete - Complete Tracking

Mark work as complete.

```bash
edison session track complete --task <task-id> [options]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--task` | Task ID (required) |
| `--validator` | Validator identifier (optional; completes only that validator) |
| `--round` | Evidence round number (optional) |
| `--run-id` | Run UUID (optional; must match when used with --validator) |
| `--process-id` | OS PID to record (optional; updates tracking processId) |
| `--status` | Implementation completion status (implementation only) |
| `--json` | Output as JSON |
| `--repo-root` | Override repository root path |

**Examples:**

```bash
# Complete tracking
edison session track complete --task 100-feature
```

#### track heartbeat - Send Heartbeat

Send a heartbeat to indicate work is still active.

```bash
edison session track heartbeat --task <task-id> [options]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--task` | Task ID (required) |
| `--validator` | Validator identifier (optional) |
| `--round` | Evidence round number (optional) |
| `--run-id` | Run UUID (optional; updates only matching records) |
| `--process-id` | OS PID to record (optional; updates tracking processId) |
| `--json` | Output as JSON |
| `--repo-root` | Override repository root path |

**Examples:**

```bash
# Send heartbeat
edison session track heartbeat --task 100-feature
```

#### track active - List Active Sessions

List all active tracking sessions.

```bash
edison session track active [options]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--json` | Output as JSON |
| `--repo-root` | Override repository root path |

**Examples:**

```bash
# List active tracking
edison session track active
```

#### track sweep - Detect Stopped Processes

Detect processes that are no longer running (best-effort, local host only) and append
`process.detected_stopped` events to the append-only process events JSONL stream.

```bash
edison session track sweep [options]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--json` | Output as JSON |
| `--repo-root` | Override repository root path |

**Notes:**
- `edison session track processes` also performs best-effort stop detection by default; use `track sweep` for an explicit “update the log now” pass.
- Once a run has a stop event, Edison treats it as `stopped` and will not keep re-checking its liveness.

#### track processes - List Tracked Processes

List tracked processes computed from the append-only JSONL process events stream.

```bash
edison session track processes [options]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--all` | Include stopped processes (default: active only) |
| `--json` | Output as JSON |
| `--repo-root` | Override repository root path |

**Notes:**
- `track processes` derives a “process index” from the append-only JSONL stream (no mutable index file).
- For runs still marked `active`, Edison performs best-effort PID liveness checks (local host only). If a PID is detected as not running, Edison appends a `process.detected_stopped` event so future listings don’t need to re-check it.

**Examples:**

```bash
# List active tracked processes (JSON)
edison session track processes --json
```

---

### session recovery - Session Recovery Commands

Recover and repair session state issues.

```bash
edison session recovery <subcommand> [options]
```

**Available Subcommands:**

- `repair` - Repair corrupted session state
- `recover` - Recover from general failures
- `recover-timed-out` - Recover timed-out sessions
- `recover-validation-tx` - Recover failed validation transactions
- `clear-locks` - Clear stale locks
- `clean-worktrees` - Clean up orphaned worktrees

**When to Use:**

- Recovering from crashes or interruptions
- Cleaning up stale resources
- Repairing corrupted state

---

## Task Domain

Tasks are units of work tracked through a state machine (todo → wip → done → validated).

### task new - Create New Task

Create a new task file using the project template.

```bash
edison task new --id <priority> --slug <slug> [options]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--id` | Priority slot (required, e.g., `150`) |
| `--slug` | Task slug (required, e.g., `auth-gate`) |
| `--wave` | Wave identifier (e.g., `wave1`) |
| `--type` | Task type: `feature`, `bug`, or `chore` (default: `feature`) |
| `--owner` | Owner name |
| `--session` | Session to create task in (creates in session todo queue) |
| `--parent` | Parent task ID for follow-up linking |
| `--continuation-id` | Continuation ID for downstream tools |
| `--json` | Output as JSON |
| `--repo-root` | Override repository root path |

**When to Use:**

- Creating new work items
- Breaking down larger features into subtasks
- Planning work in waves or sprints

**Examples:**

```bash
# Create basic task
edison task new --id 150 --slug auth-feature

# Create task with wave and type
edison task new --id 151 --slug login-ui --wave wave1 --type feature

# Create task in session
edison task new --id 152 --slug logout --session sess-001 --owner alice

# Create follow-up task
edison task new --id 153 --slug auth-tests --parent 150-auth-feature
```

**Task ID Format:**

Tasks are created with ID format: `<priority>[-<wave>]-<slug>`

- `--id 150 --slug auth` → `150-auth`
- `--id 150 --wave wave1 --slug auth` → `150-wave1-auth`

**Exit Codes:**

- `0` - Task created successfully
- `1` - Error (duplicate ID, invalid format, etc.)

---

### task claim - Claim Task

Claim a task or QA record into a session, moving it to `wip` state.

```bash
edison task claim <record_id> [options]
```

**Arguments:**

- `record_id` - Task or QA identifier (e.g., `150-wave1-auth-gate`)

**Options:**

| Option | Description |
|--------|-------------|
| `--session` | Session to claim into (auto-detects if not provided) |
| `--type` | Record type: `task` or `qa` (auto-detects if not provided) |
| `--owner` | Owner name (defaults to git user or system user) |
| `--status` | Target status after claim (default: `wip`) |
| `--reclaim` | Allow reclaiming from another active session |
| `--force` | Force claim even with warnings |
| `--json` | Output as JSON |
| `--repo-root` | Override repository root path |

**When to Use:**

- Starting work on a task
- Moving task from todo to wip state
- Assigning task to current session

**Examples:**

```bash
# Claim task into current session
edison task claim 150-auth-feature

# Claim into specific session
edison task claim 150-auth-feature --session sess-001

# Claim with explicit owner
edison task claim 150-auth-feature --session sess-001 --owner alice

# Reclaim from another session
edison task claim 150-auth-feature --session sess-002 --reclaim

# Force claim despite warnings
edison task claim 150-auth-feature --force
```

**What It Does:**

1. Validates record exists and is in `todo` state
2. Checks session is active
3. Updates record state to `wip`
4. Associates record with session
5. Records state transition in history

**Exit Codes:**

- `0` - Task claimed successfully
- `1` - Error (task not found, already claimed, invalid state, etc.)

---

### task status - Task Status Management

Inspect or transition task/QA status with state-machine guards.

```bash
edison task status <record_id> [options]
```

**Arguments:**

- `record_id` - Task or QA identifier (e.g., `150-wave1-auth-gate`)

**Options:**

| Option | Description |
|--------|-------------|
| `--status` | Transition to this status: `todo`, `wip`, `done`, `validated`, or `waiting` |
| `--type` | Record type: `task` or `qa` (auto-detects if not provided) |
| `--dry-run` | Preview transition without making changes |
| `--force` | Force transition even when guards fail |
| `--json` | Output as JSON |
| `--repo-root` | Override repository root path |

**When to Use:**

- Checking current task status
- Moving task through workflow states
- Testing if a transition is allowed

**Examples:**

```bash
# Show current status
edison task status 150-auth-feature

# Transition to done
edison task status 150-auth-feature --status done

# Dry-run to check if transition is allowed
edison task status 150-auth-feature --status done --dry-run

# Force transition (bypass guards)
edison task status 150-auth-feature --status validated --force

# Get JSON output
edison task status 150-auth-feature --json
```

**State Machine:**

Valid transitions:
- `waiting` → `todo`
- `todo` → `wip`
- `wip` → `done`
- `done` → `validated`
- Any state → `waiting` (for blocked tasks)

**Exit Codes:**

- `0` - Status retrieved or transition successful
- `1` - Error or transition blocked by guards

---

### task show - Show Raw Task Markdown

Print the task Markdown exactly as stored on disk.

```bash
edison task show <task_id> [options]
```

**Arguments:**

- `task_id` - Task identifier (e.g., `150-wave1-auth-gate`)

**Options:**

| Option | Description |
|--------|-------------|
| `--json` | Output as JSON (includes parsed task + raw content) |
| `--repo-root` | Override repository root path |

**When to Use:**

- Reading the full task brief, including YAML frontmatter
- Debugging task parsing / composition issues

---

### task waves - Plan Parallelizable Work (Waves)

Compute topological “waves” of parallelizable **todo** tasks based on `depends_on`.

```bash
edison task waves [options]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--session` | Optional session filter (only tasks with matching `session_id`) |
| `--cap` | Optional max parallel cap override (defaults to `orchestration.maxConcurrentAgents` when available) |
| `--json` | Output as JSON |
| `--repo-root` | Override repository root path |

**When to Use:**

- Picking the next set of tasks that can run in parallel
- Avoiding manual dependency scanning across many task files

**Examples:**

```bash
# Show wave plan (human output)
edison task waves

# Machine-readable plan
edison task waves --json

# Override cap (e.g., local throughput limit)
edison task waves --cap 2 --json
```

**Notes:**

- Tasks in **Wave 1** are parallelizable “start now” candidates.
- If a wave exceeds the cap, the JSON payload includes `batches` to chunk the wave deterministically.
- Use `edison task blocked <task-id> --json` to explain why a task is blocked.

---

### task ready - List Ready Tasks

List tasks ready to be claimed (in `todo` state).

Note: `edison task ready <task-id>` is a deprecated compatibility alias for task completion.
Prefer `edison task done <task-id>`.

```bash
edison task ready [record_id] [options]
```

**Arguments:**

- `record_id` - (Deprecated) Task ID to complete (optional; omit to list ready tasks)

**Options:**

| Option | Description |
|--------|-------------|
| `--session` | Filter by or specify session |
| `--json` | Output as JSON |
| `--repo-root` | Override repository root path |

**When to Use:**

- Listing available work

**Examples:**

```bash
# List all ready tasks (in todo state)
edison task ready

# Mark task as complete (wip → done) (preferred)
edison task done 150-auth-feature --session sess-001

# List ready tasks as JSON
edison task ready --json
```

**Without record_id:**
Lists all tasks in `todo` state that are ready to be claimed.

**With record_id (deprecated):**
Completes the task by delegating to `edison task done`.

**Exit Codes:**

- `0` - Success
- `1` - Error (task not found, invalid state, etc.)

---

### task done - Complete Task

Complete a task by moving it from `wip` to `done` with guard enforcement (evidence, Context7 when detected, and TDD readiness gates).

```bash
edison task done <task-id> [options]
```

**Arguments:**

- `task-id` - Task ID to complete (supports unique prefix shorthand like `12007`)

**Options:**

| Option | Description |
|--------|-------------|
| `--session` | Session completing the task (required) |
| `--skip-context7` | Bypass Context7 checks for verified false positives only (requires `--skip-context7-reason`) |
| `--skip-context7-reason <text>` | Justification for Context7 bypass (required when `--skip-context7` is set) |
| `--json` | Output as JSON |
| `--repo-root` | Override repository root path |

**Examples:**

```bash
# Complete a task
edison task done 150-auth-feature --session sess-001

# Complete a task using shorthand (unique prefix)
edison task done 150 --session sess-001
```

**Bundle note (recommended for small related tasks):**

- If the task is a bundle member (via `bundle_root`) and the bundle root has an **approved** bundle summary,
  Edison can accept required command evidence from the **bundle root round** to avoid redundant evidence files
  for each member task.

**Exit Codes:**

- `0` - Success
- `1` - Error (blocked by guards, not found, ambiguous shorthand, etc.)

---

### task list - List Tasks

List tasks across queues with optional filtering.

```bash
edison task list [options]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--status <state>` | Filter by task/QA state |
| `--session <session-id>` | Filter to a specific session (shows all states for that session) |
| `--type <task|qa>` | Record type (default: `task`) |
| `--all` | Include terminal/final states (e.g., `validated`) |
| `--json` | Output as JSON |
| `--repo-root` | Override repository root path |

**When to Use:**

- Getting overview of all tasks
- Finding tasks by status
- Auditing task queue

**Examples:**

```bash
# Default: excludes terminal tasks
edison task list
edison task list --all

# Filter by state
edison task list --status wip
edison task list --status validated

# List QA briefs across queues
edison task list --type qa

# Get JSON output
edison task list --json
```

---

### task link - Link Tasks

Link parent-child relationships between tasks.

```bash
edison task link <parent> <child> [options]
```

**Arguments:**

- `parent` - Parent task ID
- `child` - Child task ID

**Options:**

| Option | Description |
|--------|-------------|
| `--json` | Output as JSON |
| `--repo-root` | Override repository root path |

**When to Use:**

- Creating task hierarchies
- Linking follow-up tasks
- Building dependency graphs

**Examples:**

```bash
# Link child task to parent
edison task link 150-auth-feature 151-login-ui
```

---

### task relate - Link Related Tasks (Non-Blocking)

Create or remove a **non-blocking** relationship between two tasks (stored in task frontmatter as `related`).

```bash
edison task relate <task-a> <task-b> [--remove] [options]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--remove` | Remove the relation instead of adding it |
| `--json` | Output as JSON |
| `--repo-root` | Override repository root path |

**When to Use:**

- Grouping related work in planning (affects `edison task waves` within-wave ordering)
- Cross-referencing tasks that touch the same area, without creating blocking dependencies

**Examples:**

```bash
# Add relation
edison task relate 150-auth-feature 151-login-ui

# Remove relation
edison task relate 150-auth-feature 151-login-ui --remove
```

---

### task bundle - Group Tasks for Bundle Validation

Group arbitrary tasks into a **validation bundle** (without creating “fake parent tasks”).

```bash
edison task bundle <subcommand> ...
```

**Subcommands:**

- `add --root <root> <member...>` - Set `bundle_root` on each member task
- `remove <member...>` - Clear `bundle_root` on each member task
- `show <task>` - Show the resolved root + member list for a task

**Examples:**

```bash
# Create a validation bundle
edison task bundle add --root 150-auth-feature 151-login-ui 152-login-api

# Validate once at the bundle root
edison qa validate 150-auth-feature --scope bundle --execute
```

---

### task split - Split Task

Split a task into multiple subtasks.

```bash
edison task split <task_id> [options]
```

**Arguments:**

- `task_id` - Task ID to split

**Options:**

| Option | Description |
|--------|-------------|
| `--json` | Output as JSON |
| `--repo-root` | Override repository root path |

**When to Use:**

- Breaking down large tasks
- Creating subtask structure
- Distributing work

**Examples:**

```bash
# Split task into subtasks
edison task split 150-auth-feature
```

---

### task ensure_followups - Ensure Follow-ups

Generate required follow-up tasks based on rules.

```bash
edison task ensure_followups [options]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--json` | Output as JSON |
| `--repo-root` | Override repository root path |

**When to Use:**

- Automatically creating dependent tasks
- Enforcing workflow policies
- Generating test tasks for features

**Examples:**

```bash
# Generate all required follow-ups
edison task ensure_followups
```

---

### task allocate_id - Allocate Task ID

Allocate next available task ID in priority sequence.

```bash
edison task allocate_id [options]
```

**When to Use:**

- Getting next available priority slot
- Automating task creation
- Avoiding ID conflicts

---

### task mark_delegated - Mark Task Delegated

Mark a task as delegated to another system or user.

```bash
edison task mark_delegated <task_id> [options]
```

**When to Use:**

- Tracking externally assigned work
- Delegating to other teams
- Handoff workflows

---

### task cleanup_stale_locks - Clean Up Stale Locks

Remove stale task locks from interrupted sessions.

```bash
edison task cleanup_stale_locks [options]
```

**When to Use:**

- Recovering from crashes
- Cleaning up after failed sessions
- Resolving lock conflicts

**Examples:**

```bash
# Clean up all stale locks
edison task cleanup_stale_locks
```

---

## QA Domain

Quality Assurance commands for validation, evidence collection, and approval workflows.

### qa list - List QA Briefs

List QA briefs across queues.

```bash
edison qa list [options]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--status <state>` | Filter by QA state |
| `--session <session-id>` | Filter to a specific session (shows all states for that session) |
| `--all` | Include terminal/final states (e.g., `validated`) |
| `--json` | Output as JSON |
| `--repo-root` | Override repository root path |

**Examples:**

```bash
# Default: excludes terminal QA briefs
edison qa list
edison qa list --all
edison qa list --status wip
```

### qa new - Create QA Brief

Create a new QA brief for a task.

```bash
edison qa new <task_id> [options]
```

**Arguments:**

- `task_id` - Task identifier (required)

**Options:**

| Option | Description |
|--------|-------------|
| `--owner` | Validator owner (default: `_unassigned_`) |
| `--session` | Session ID for context |
| `--json` | Output as JSON |
| `--repo-root` | Override repository root path |

**When to Use:**

- Ensuring a QA record exists before validation begins
- Assigning/recording validator ownership and session context

**Examples:**

```bash
# Create QA brief for task
edison qa new 150-auth-feature

# Create with session context
edison qa new 150-auth-feature --session sess-001 --owner alice
```

**What It Does:**

1. Ensures a QA Markdown record exists for the task (QA id is `<task_id>-qa`)
2. Stores the record in session scope when a session is resolved, otherwise in global QA directories
3. Returns the QA path (and parsed metadata in `--json` mode)

**Exit Codes:**

- `0` - QA brief created successfully
- `1` - Error (task not found, round exists, etc.)

---

### qa show - Show Raw QA Markdown

Print the QA Markdown exactly as stored on disk.

```bash
edison qa show <qa_id> [options]
```

**Arguments:**

- `qa_id` - QA identifier (e.g., `150-wave1-auth-gate-qa`)

**Options:**

| Option | Description |
|--------|-------------|
| `--json` | Output as JSON (includes parsed QA + raw content) |
| `--repo-root` | Override repository root path |

**When to Use:**

- Reading the full QA brief, including YAML frontmatter
- Debugging QA parsing / composition issues

---

### qa validate - Run Validators

Run validators against a task (optionally using a bundle/hierarchy scope).

```bash
edison qa validate <task_id> [options]
```

**Arguments:**

- `task_id` - Task identifier to validate (required)

**Options:**

| Option | Description |
|--------|-------------|
| `--scope` | Bundle scope: `auto`, `hierarchy`, or `bundle` (recommended for validating small related tasks together) |
| `--session` | Session ID context |
| `--round` | Validation round number (default: use current active round; fails closed if none) |
| `--wave` | Specific wave to validate (e.g., `critical`, `comprehensive`) |
| `--preset` | Validation preset override (project-defined; e.g., `fast`, `standard`, `strict`, `deep`, `bundle`) |
| `--validators` | Specific validator IDs to run (space-separated) |
| `--add-validators` | Extra validators to add: `react` (default wave) or `critical:react` (specific wave) |
| `--blocking-only` | Only run blocking validators |
| `--execute` | Execute validators directly (default: show roster only) |
| `--sequential` | Run validators sequentially instead of in parallel |
| `--dry-run` | Show what would be executed without running |
| `--max-workers` | Maximum parallel workers (default: 4) |
| `--json` | Output as JSON |
| `--repo-root` | Override repository root path |

**When to Use:**

- Validating task completion
- Running specific validators
- Quality gate checks
- Direct CLI validation when tools are installed

**Examples:**

```bash
# Show validation roster (without executing)
edison qa validate 150-auth-feature

# Execute validators directly via CLI engines
edison qa validate 150-auth-feature --execute

# Prepare a new round (creates/initializes round artifacts)
edison qa round prepare 150-auth-feature

# Validate a bundle of related tasks (defined via `bundle_root`)
edison qa validate 150-auth-feature --scope bundle --execute

# Validate a parent/meta task plus its children (work decomposition)
# Note: presets are project-defined; use a preset tuned for meta/bundle validation if available.
edison qa validate <parent-task> --scope hierarchy --preset bundle --execute

# Show what would be executed
edison qa validate 150-auth-feature --dry-run

# Run only blocking validators
edison qa validate 150-auth-feature --execute --blocking-only

# Run specific wave
edison qa validate 150-auth-feature --execute --wave critical

# Run specific validators
edison qa validate 150-auth-feature --execute --validators global-codex security

# Add extra validators (orchestrator feature)
edison qa validate 150-auth-feature --add-validators react api --execute

# Add validators with specific waves using [WAVE:]VALIDATOR syntax
edison qa validate 150-auth-feature --add-validators critical:react comprehensive:api --execute
```

**Validator Auto-Detection:**

Validators are automatically selected based on:
1. **Always-run validators**: `always_run: true` in config
2. **File pattern triggers**: Match modified files against trigger patterns
3. **Preset policy**: Validators included by the resolved preset (explicit, `validation.defaultPreset`, or inferred via `validation.presetInference`)

**Adding Extra Validators (Orchestrator Feature):**

Orchestrators can ADD validators that weren't auto-triggered:
- Use `--add-validators react api` to add validators (default wave: `comprehensive`)
- Use `--add-validators critical:react` to specify a wave with the `[WAVE:]VALIDATOR` syntax (overrides the validator’s configured wave for execution ordering)
- Cannot remove auto-detected validators (only add)

The CLI shows "ORCHESTRATOR DECISION POINTS" when validators might be relevant
but weren't auto-triggered (e.g., React logic in `.js` files).

**Execution Modes:**

- **Roster Only** (default): Shows validator roster without executing
- **Execute** (`--execute`): Runs validators directly via CLIEngine when available
- **Dry Run** (`--dry-run`): Shows execution plan without running

**Validator Categories:**

- **Always Required**: Core validators that always run (`always_run: true`)
- **Triggered Blocking**: Pattern-triggered blocking validators
- **Triggered Optional**: Pattern-triggered non-blocking validators
- **Orchestrator Added**: Extra validators specified via `--add-validators`

**Direct vs Delegation:**

- ✓ = CLI tool available, will execute directly
- → = CLI unavailable, will generate delegation instructions
- + = Added by orchestrator (not auto-detected)

**Exit Codes:**

- `0` - Validation successful (all blocking validators passed)
- `1` - Validation failed (blocking validator failed or error)

---

### qa bundle - Create QA Bundle

Create or inspect QA validation bundle for a task.

```bash
edison qa bundle <task_id> [options]
```

**Arguments:**

- `task_id` - Task identifier (required)

**Options:**

| Option | Description |
|--------|-------------|
| `--scope` | Bundle scope: `auto`, `hierarchy`, or `bundle` |
| `--session` | Session ID context |
| `--json` | Output as JSON |
| `--repo-root` | Override repository root path |

**When to Use:**

- Packaging validation artifacts
- Preparing for approval
- Inspecting validation status

**Examples:**

```bash
# Create QA bundle
edison qa bundle 150-auth-feature

# Create bundle manifest for a validation bundle (task + bundle_root members)
edison qa bundle 150-auth-feature --scope bundle

# Get JSON output
edison qa bundle 150-auth-feature --json
```

---

### qa promote - Promote QA Brief

Promote QA brief between states in the workflow.

```bash
edison qa promote --task <task_id> --to <state> [options]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--task` | Task identifier (required) |
| `--to` | Target state: `waiting`, `todo`, `wip`, `done`, or `validated` (required) |
| `--json` | Output as JSON |
| `--repo-root` | Override repository root path |

**QA States:**

- `waiting` → `todo` → `wip` → `done` → `validated`

**When to Use:**

- Moving QA through workflow
- Approving validation
- Transitioning QA states

**Examples:**

```bash
# Move QA to todo
edison qa promote --task 150-auth-feature --to todo

# Approve and validate
edison qa promote --task 150-auth-feature --to validated

# Get JSON output
edison qa promote --task 150-auth-feature --to done --json
```

**Exit Codes:**

- `0` - Promotion successful
- `1` - Invalid transition or error

---

### qa round - Manage QA Rounds

Manage QA validation rounds and round-scoped reports.

```bash
edison qa round <subcommand> ...
```

**Subcommands:**

| Subcommand | Description |
|------------|-------------|
| `prepare` | Create/ensure an active `round-N/` and initialize `implementation-report.md` + `validation-summary.md` |
| `summarize-verdict` | Compute approval from existing validator reports and write `validation-summary.md` (no validator execution) |
| `set-status` | Append a round record to the QA brief (status/notes only) |

**When to Use:**

- Starting a new validation cycle for a task/bundle (use `prepare`)
- Capturing a deterministic “verdict summary” after validators run (use `summarize-verdict`)
- Recording round status/notes in the QA brief (use `set-status`)

**Examples:**

```bash
# Prepare a new active round (creates round-N/ + reports)
edison qa round prepare 150-auth-feature

# Run validators in the prepared round
edison qa validate 150-auth-feature --execute

# Summarize the validator verdicts and write validation-summary.md
edison qa round summarize-verdict 150-auth-feature

# Record a status update in the QA brief (optional)
edison qa round set-status 150-auth-feature --status reject --note "Fix lint + rerun"
```

---

### qa run - Run Specific Validator

Run a specific validator by ID using the unified engine system.

```bash
edison qa run <validator_id> --task <task_id> [options]
```

**Arguments:**

- `validator_id` - Validator identifier (e.g., `global-codex`, `security`)

**Options:**

| Option | Description |
|--------|-------------|
| `--task` | Task identifier to validate (required) |
| `--session` | Session ID context |
| `--round` | Validation round number |
| `--wave` | Execute all validators in a wave |
| `--worktree` | Path to git worktree |
| `--dry-run` | Show what would be executed without running |
| `--json` | Output as JSON |
| `--repo-root` | Override repository root path |

**Execution Flow:**

1. **Engine Selection**: Uses CLIEngine if CLI tool is available, otherwise falls back to PalMCPEngine
2. **Direct Execution**: CLIEngine executes the CLI tool directly (codex, claude, gemini, auggie, coderabbit)
3. **Delegation**: PalMCPEngine generates delegation instructions if CLI unavailable
4. **Evidence**: Results saved to validation evidence directory

**When to Use:**

- Testing individual validators
- Debugging validation failures
- Running custom validators
- Verifying engine availability

**Examples:**

```bash
# Run specific validator
edison qa run global-codex --task 150-auth-feature

# Run with specific session and round
edison qa run security --task 150-auth-feature --session sess-001 --round 2

# Run all validators in a wave
edison qa run --wave critical --task 150-auth-feature

# Dry run to see what would execute
edison qa run global-claude --task 150-auth-feature --dry-run
```

**Exit Codes:**

- `0` - Validator executed successfully (regardless of pass/fail verdict)
- `1` - Error (validator not found, engine unavailable, etc.)

---

### qa audit - Audit Guidelines

Audit quality of guidelines and documentation.

```bash
edison qa audit [options]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--json` | Output as JSON |
| `--repo-root` | Override repository root path |

**When to Use:**

- Checking guideline quality
- Validating documentation
- Quality assurance of QA itself

**Examples:**

```bash
# Run audit
edison qa audit

# Get JSON output
edison qa audit --json
```

---

## Compose Domain

Artifact composition and generation for agents, validators, guidelines, and constitutions.

### compose all - Compose All Artifacts

Compose all artifacts including agents, validators, constitutions, guidelines, and start prompts.

```bash
edison compose all [options]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--agents` | Only compose agents |
| `--validators` | Only compose validators |
| `--constitutions` | Only compose constitutions (and supporting rosters) |
| `--guidelines` | Only compose guidelines |
| `--start` | Only compose start prompts |
| `--platforms` | Target platforms (comma-separated: `claude`, `cursor`, `pal`) |
| `--claude` | Sync to Claude Code after composing |
| `--cursor` | Sync to Cursor after composing |
| `--pal` | Sync to Pal MCP after composing |
| `--dry-run` | Show what would be done without making changes |
| `--json` | Output as JSON |
| `--repo-root` | Override repository root path |

**When to Use:**

- After config changes
- Initial project setup
- Regenerating all artifacts
- Syncing to IDE/platforms

**Examples:**

```bash
# Compose everything
edison compose all

# Only compose agents
edison compose all --agents

# Compose and sync to Claude Code
edison compose all --claude

# Compose and sync to all platforms
edison compose all --claude --cursor --pal

# Dry-run to preview
edison compose all --dry-run

# Compose specific artifacts
edison compose all --agents --validators --guidelines
```

**What It Does:**

1. **Constitutions**: Generates role-specific constitutions and rosters
2. **Agents**: Composes agents from layered sources (core + packs + project)
3. **Guidelines**: Composes guidelines with concatenation and deduplication
4. **Validators**: Composes validators from section-based templates
5. **Start Prompts**: Composes start prompts with project overlays
6. **Platform Sync**: Optionally syncs to Claude Code, Cursor, or Pal MCP

**Generated Files:**

All artifacts are written to `.edison/_generated/`:
- `agents/` - Agent definitions
- `validators/` - Validator definitions
- `guidelines/` - Guideline documents
- `constitutions/` - Role constitutions
- `start/` - Start prompts
- `AVAILABLE_AGENTS.md` - Agent roster
- `AVAILABLE_VALIDATORS.md` - Validator roster
- `STATE_MACHINE.md` - State machine documentation

**Exit Codes:**

- `0` - Composition successful
- `1` - Error during composition

---

### compose commands - Compose CLI Commands

Compose CLI commands from configuration.

```bash
edison compose commands [options]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--dry-run` | Show what would be done |
| `--json` | Output as JSON |
| `--repo-root` | Override repository root path |

**When to Use:**

- Generating custom CLI commands
- Updating command definitions

---

### compose hooks - Compose Claude Code Hooks

Compose Claude Code hooks from configuration.

```bash
edison compose hooks [options]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--dry-run` | Show what would be done |
| `--json` | Output as JSON |
| `--repo-root` | Override repository root path |

**When to Use:**

- Updating Claude Code hooks
- Syncing hook definitions

---

### compose coderabbit - Compose CodeRabbit Configuration

Compose `.coderabbit.yaml` configuration from layered sources (Core → Packs → User → Project).

```bash
edison compose coderabbit [options]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--output` | Custom output directory (default: repo root) |
| `--dry-run` | Show composed config without writing |
| `--json` | Output as JSON |
| `--repo-root` | Override repository root path |

**When to Use:**

- Generating CodeRabbit configuration for AI-powered code reviews
- Updating CodeRabbit settings after enabling new packs
- Customizing code review instructions per project

**Configuration Sources:**

1. **Core template**: `src/edison/data/templates/configs/coderabbit.yaml`
2. **Pack overlays**: `src/edison/data/packs/{pack}/configs/coderabbit.yaml`
3. **Project overrides**: `.edison/configs/coderabbit.yaml`

**Special Merging:**

The `path_instructions` array is **appended** across layers (not replaced), allowing packs to add technology-specific review instructions.

**Examples:**

```bash
# Compose and write to repo root
edison compose coderabbit

# Preview without writing
edison compose coderabbit --dry-run

# Output to custom directory
edison compose coderabbit --output ./config

# Get JSON output
edison compose coderabbit --json
```

**Output:**

Creates `.coderabbit.yaml` with merged configuration including:
- Review profile settings (chill, balanced, assertive)
- Auto-review configuration
- Knowledge base settings
- Path-specific review instructions from all active packs

**Exit Codes:**

- `0` - Configuration composed successfully
- `1` - Error during composition

---

### compose settings - Compose IDE Settings

Compose IDE settings files from configuration.

```bash
edison compose settings [options]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--dry-run` | Show what would be done |
| `--json` | Output as JSON |
| `--repo-root` | Override repository root path |

**When to Use:**

- Generating IDE configuration
- Syncing settings across team

---

### compose validate - Validate Composition

Validate composition configuration and outputs.

```bash
edison compose validate [options]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--json` | Output as JSON |
| `--repo-root` | Override repository root path |

**When to Use:**

- Checking composition configuration
- Validating generated artifacts
- Debugging composition issues

**Examples:**

```bash
# Validate composition
edison compose validate

# Get JSON output
edison compose validate --json
```

---

## Config Domain

Configuration management and inspection.

### config show - Show Configuration

Display the merged configuration from bundled defaults, project overrides, and environment variables.

```bash
edison config show [key] [options]
```

**Arguments:**

- `key` - Specific configuration key to show (optional, e.g., `project.name`)

**Options:**

| Option | Description |
|--------|-------------|
| `--format` | Output format: `json`, `yaml`, or `table` (default: `table`) |
| `--json` | Output as JSON (overrides `--format`) |
| `--repo-root` | Override repository root path |

**When to Use:**

- Inspecting current configuration
- Debugging config issues
- Understanding effective settings

**Examples:**

```bash
# Show all configuration (table format)
edison config show

# Show specific key
edison config show project.name

# Output as JSON
edison config show --json

# Output as YAML
edison config show --format yaml

# Show nested key
edison config show database.url
```

**Output (Table Format):**

```
Edison Configuration
============================================================

[project]
  name: my-project
  owner: alice

[paths]
  project_config_dir: .edison
  tasks_dir: .edison/tasks
  ...

[database]
  enabled: true
  url: sqlite:///.edison/.sessions/sessions.db
  ...
```

**Exit Codes:**

- `0` - Configuration shown successfully
- `1` - Error (key not found, invalid format, etc.)

---

### config validate - Validate Configuration

Validate project configuration files.

```bash
edison config validate [options]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--json` | Output as JSON |
| `--repo-root` | Override repository root path |

**When to Use:**

- Checking config file syntax
- Validating after manual edits
- Pre-commit validation

**Examples:**

```bash
# Validate configuration
edison config validate

# Get JSON output
edison config validate --json
```

**Exit Codes:**

- `0` - Configuration valid
- `1` - Validation errors found

---

### config configure - Interactive Configuration

Interactive configuration menu for updating settings.

```bash
edison config configure [options]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--json` | Output as JSON |
| `--repo-root` | Override repository root path |

**When to Use:**

- Updating configuration interactively
- Guided configuration changes
- First-time setup customization

**Examples:**

```bash
# Launch interactive configuration
edison config configure
```

---

## Git Domain

Git operations and worktree management.

### git status - Git Status

Show Edison-aware git status with optional filtering.

```bash
edison git status [options]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--session` | Filter to files in session worktree |
| `--task` | Filter to files related to a task |
| `--json` | Output as JSON |
| `--repo-root` | Override repository root path |

**When to Use:**

- Checking git status with Edison context
- Viewing session-specific changes
- Filtering by task

**Examples:**

```bash
# Show git status
edison git status

# Show status for session
edison git status --session sess-001

# Show status for task
edison git status --task 150-auth-feature

# Get JSON output
edison git status --json
```

**Output:**

```
Branch: main
Clean: false

Staged (2 files):
  + src/auth.py
  + tests/test_auth.py

Modified (1 files):
  M src/config.py
```

---

### git worktree-create - Create Worktree

Create a git worktree for a session.

```bash
edison git worktree-create [session_id] [options]
```

**Arguments:**

- `session_id` - Session identifier (optional, defaults to current session when omitted)

**When to Use:**

- Creating isolated workspace
- Parallel development
- Manual worktree setup

**Examples:**

```bash
# Create worktree for session
edison git worktree-create sess-001

# In a session context (AGENTS_SESSION / worktree .session-id), session_id is optional
edison git worktree-create
```

---

### git worktree-list - List Worktrees

List all git worktrees.

```bash
edison git worktree-list [options]
```

**When to Use:**

- Viewing all worktrees
- Checking worktree status

**Examples:**

```bash
# List worktrees
edison git worktree-list
```

---

### git worktree-health - Check Worktree Health

Check health status of a worktree.

```bash
edison git worktree-health <session_id> [options]
```

**Arguments:**

- `session_id` - Session identifier (required)

**When to Use:**

- Diagnosing worktree issues
- Validating worktree state

**Examples:**

```bash
# Check worktree health
edison git worktree-health sess-001
```

---

### git worktree-archive - Archive Worktree

Archive a worktree (preserves for later restoration).

```bash
edison git worktree-archive <session_id> [options]
```

**Arguments:**

- `session_id` - Session identifier (required)

**When to Use:**

- Temporarily removing worktree
- Freeing disk space
- Preserving state for later

**Examples:**

```bash
# Archive worktree
edison git worktree-archive sess-001
```

---

### git worktree-restore - Restore Worktree

Restore an archived worktree.

```bash
edison git worktree-restore [session_id] [options]
```

**Arguments:**

- `session_id` - Session identifier (optional, defaults to current session when omitted)

**When to Use:**

- Restoring archived worktree
- Resuming paused work

**Examples:**

```bash
# Restore worktree
edison git worktree-restore sess-001

# In a session context (AGENTS_SESSION / worktree .session-id), session_id is optional
edison git worktree-restore
```

---

### git worktree-cleanup - Clean Up Worktree

Clean up and remove a worktree.

```bash
edison git worktree-cleanup <session_id> [options]
```

**Arguments:**

- `session_id` - Session identifier (required)

**When to Use:**

- Removing finished worktree
- Cleaning up after session close
- Reclaiming disk space

**Examples:**

```bash
# Clean up worktree
edison git worktree-cleanup sess-001
```

---

## Rules Domain

Rule management and checking.

### rules list - List Rules

List all available rules in the system.

```bash
edison rules list [options]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--json` | Output as JSON |
| `--repo-root` | Override repository root path |

**When to Use:**

- Viewing available rules
- Discovering rule IDs
- Auditing rule coverage

**Examples:**

```bash
# List all rules
edison rules list

# Get JSON output
edison rules list --json
```

---

### rules show - Show Rule

Show details of a specific rule.

```bash
edison rules show <rule_id> [options]
```

**Arguments:**

- `rule_id` - Rule identifier (required)

**Options:**

| Option | Description |
|--------|-------------|
| `--json` | Output as JSON |
| `--repo-root` | Override repository root path |

**When to Use:**

- Inspecting rule details
- Understanding rule logic
- Debugging rule application

**Examples:**

```bash
# Show specific rule
edison rules show task-todo-to-wip

# Get JSON output
edison rules show task-todo-to-wip --json
```

---

### rules show-for-context - Show Rules for Context

Show rules applicable to specific contexts.

```bash
edison rules show-for-context <category> <context> [options]
```

**Arguments:**

- `category` - Rule category (e.g., `transition`, `validation`)
- `context` - Context value (e.g., `task`, `qa`)

**Options:**

| Option | Description |
|--------|-------------|
| `--json` | Output as JSON |
| `--repo-root` | Override repository root path |

**When to Use:**

- Finding context-specific rules
- Understanding applicable guards
- Validation planning

**Examples:**

```bash
# Show rules for task transitions
edison rules show-for-context transition task

# Show validation rules for QA
edison rules show-for-context validation qa
```

---

### rules check - Check Rules

Check rules applicable to a specific context or transition.

```bash
edison rules check [options]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--json` | Output as JSON |
| `--repo-root` | Override repository root path |

**When to Use:**

- Testing rule application
- Validating transitions
- Debugging guard failures

**Examples:**

```bash
# Check rules
edison rules check
```

---

### rules migrate - Migrate Rules

Migrate rules to new format or schema.

```bash
edison rules migrate [options]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--json` | Output as JSON |
| `--repo-root` | Override repository root path |

**When to Use:**

- Upgrading rule definitions
- Schema migrations
- Rule format updates

**Examples:**

```bash
# Migrate rules
edison rules migrate
```

---

## MCP Domain

Model Context Protocol server configuration.

### mcp configure - Configure MCP Servers

Configure `.mcp.json` entries for all managed MCP servers.

```bash
edison mcp configure [project_path] [options]
```

**Arguments:**

- `project_path` - Target project path (defaults to current directory)

**Options:**

| Option | Description |
|--------|-------------|
| `--dry-run` | Show what would be done without making changes |
| `--config-file` | Override target MCP config file path |
| `--server` | Limit configuration to specified MCP server ID (repeatable) |
| `--json` | Output as JSON |

**When to Use:**

- Setting up MCP servers
- Updating `.mcp.json` configuration
- Configuring specific servers

**Examples:**

```bash
# Configure all MCP servers
edison mcp configure

# Configure specific project
edison mcp configure /path/to/project

# Configure only specific servers
edison mcp configure --server pal --server cline

# Dry-run to preview changes
edison mcp configure --dry-run

# Use custom config file
edison mcp configure --config-file ~/.mcp/config.json
```

**What It Does:**

1. Reads MCP server definitions from `.edison/config/mcp.yml`
2. Generates `.mcp.json` entries for each server
3. Merges with existing `.mcp.json` (preserves non-Edison entries)
4. Validates server configurations

**Exit Codes:**

- `0` - Configuration successful
- `1` - Invalid configuration or error

---

### mcp setup - Setup MCP Servers

Setup MCP servers defined in `mcp.yaml`.

```bash
edison mcp setup [options]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--json` | Output as JSON |
| `--repo-root` | Override repository root path |

**When to Use:**

- Installing MCP server dependencies
- Initial MCP setup
- Resetting MCP environment

**Examples:**

```bash
# Setup all MCP servers
edison mcp setup

# Get JSON output
edison mcp setup --json
```

---

## Orchestrator Domain

Orchestrator session management for automated workflows.

### orchestrator start - Start Orchestrator

Start an orchestrator session with optional worktree.

```bash
edison orchestrator start [options]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--profile`, `-p` | Orchestrator profile name (default: from config) |
| `--prompt` | Initial prompt text to send to orchestrator |
| `--prompt-file` | Path to file containing initial prompt |
| `--no-worktree` | Skip worktree creation |
| `--detach` | Detach orchestrator process (run in background) |
| `--dry-run` | Show what would be done without starting |
| `--json` | Output as JSON |
| `--repo-root` | Override repository root path |

**When to Use:**

- Starting automated workflows
- Launching orchestrator with prompt
- Background orchestrator processes

**Examples:**

```bash
# Start orchestrator with default profile
edison orchestrator start

# Start with specific profile
edison orchestrator start --profile validation

# Start with initial prompt
edison orchestrator start --prompt "Implement auth feature"

# Start with prompt from file
edison orchestrator start --prompt-file ./prompts/task-001.md

# Start without worktree
edison orchestrator start --no-worktree

# Start in background
edison orchestrator start --detach

# Dry-run to preview
edison orchestrator start --dry-run
```

**What It Does:**

1. Creates new session (auto-generated ID)
2. Creates worktree (unless `--no-worktree`)
3. Loads orchestrator profile configuration
4. Launches orchestrator process
5. Sends initial prompt (if provided)
6. Detaches if requested

**Output:**

```
Started session: orch-20251201-143022
  Worktree: /path/to/.worktrees/orch-20251201-143022
  Orchestrator PID: 12345
```

**Exit Codes:**

- `0` - Orchestrator started successfully
- `1` - Error starting orchestrator

---

### orchestrator profiles - List Profiles

List available orchestrator profiles.

```bash
edison orchestrator profiles [options]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--json` | Output as JSON |
| `--repo-root` | Override repository root path |

**When to Use:**

- Viewing available profiles
- Discovering profile configurations
- Selecting profile for start

**Examples:**

```bash
# List profiles
edison orchestrator profiles

# Get JSON output
edison orchestrator profiles --json
```

---

## Import Domain

Import tasks from external task management systems into Edison.

### import speckit - Import SpecKit Tasks

Import or sync tasks from GitHub's SpecKit SDD (Spec-Driven Development) tool.

```bash
edison import speckit <source> [options]
```

**Arguments:**

| Argument | Description |
|----------|-------------|
| `source` | Path to SpecKit feature folder or tasks.md file |

**Options:**

| Option | Description |
|--------|-------------|
| `--prefix` | Custom task ID prefix (default: folder name) |
| `--dry-run` | Preview changes without writing files |
| `--no-qa` | Skip creating QA records for imported tasks |
| `--json` | Output as JSON |
| `--repo-root` | Override repository root path |

**When to Use:**

- Importing SpecKit-generated tasks into Edison
- Re-syncing after specs have changed
- Converting external task lists to Edison format

**Examples:**

```bash
# Import tasks from a SpecKit feature folder
edison import speckit specs/auth-feature/

# Import with custom task prefix
edison import speckit specs/authentication/ --prefix auth

# Preview what would be imported
edison import speckit specs/payment/ --dry-run

# Import without creating QA records
edison import speckit specs/feature/ --no-qa

# Get JSON output for scripting
edison import speckit specs/feature/ --json
```

**What It Does:**

1. Parses SpecKit tasks.md checklist format
2. Detects available spec documents (spec.md, plan.md, etc.)
3. Creates Edison tasks with links to spec docs
4. Optionally creates QA records for each task
5. On re-sync: updates changed tasks, flags removed tasks

**SpecKit Task Format:**

```markdown
## Phase 1: Setup

- [ ] T001 Create project structure
- [ ] T002 [P] Initialize dependencies
- [x] T003 Already completed task

## Phase 2: User Story 1

- [ ] T010 [US1] Create User model in src/models/user.py
- [ ] T011 [P] [US1] Create UserService
```

**Sync Behavior:**

| Scenario | Action |
|----------|--------|
| New task in SpecKit | Create Edison task |
| Existing task changed | Update metadata |
| Task in wip/done | Preserve Edison state |
| Task removed from SpecKit | Flag with `removed-from-spec` tag |

**Output:**

```
SpecKit Import: auth-feature
Prefix: auth

Created (2 tasks):
  + auth-T001
  + auth-T002
```

**Exit Codes:**

- `0` - Import successful
- `1` - Error during import

For detailed documentation, see [SPECKIT_INTEGRATION.md](SPECKIT_INTEGRATION.md).

---

### import openspec - Import OpenSpec Changes

Import or sync OpenSpec change folders (by change-id) into Edison.

```bash
edison import openspec <source> [options]
```

**Arguments:**

| Argument | Description |
|----------|-------------|
| `source` | Path to repo root (contains `openspec/`), `openspec/`, or `openspec/changes/` |

**Options:**

| Option | Description |
|--------|-------------|
| `--prefix` | Task ID prefix (default: `openspec`) |
| `--include-archived` | Include `openspec/changes/archive/*` |
| `--dry-run` | Preview changes without writing files |
| `--no-qa` | Skip creating QA records for imported tasks |
| `--json` | Output as JSON |
| `--repo-root` | Override repository root path |

**When to Use:**

- Tracking OpenSpec proposals as Edison tasks
- Keeping Edison in sync with `openspec/changes/`

**Examples:**

```bash
# Import changes from a repo with openspec/
edison import openspec .

# Import from an explicit changes directory
edison import openspec openspec/changes

# Include archived changes
edison import openspec . --include-archived

# Use a custom task prefix
edison import openspec . --prefix spec

# Preview changes
edison import openspec . --dry-run
```

**Sync Behavior:**

| Scenario | Action |
|----------|--------|
| New change-id | Create Edison task |
| Existing change-id changed | Update title/description/tags (only in `todo`) |
| Task in wip/done | Preserve Edison state |
| Change-id removed | Flag with `removed-from-openspec` tag |

For detailed documentation, see [OPENSPEC_INTEGRATION.md](OPENSPEC_INTEGRATION.md).

---

## Debug Domain

Debug and introspection utilities.

### debug resolve - Explain Layer Resolution

Explain how a composable entity resolves across layers (core → packs → user → project).

```bash
edison debug resolve <type> <name> [--packs <pack>...] [--json] [--repo-root <path>]
```

**Arguments:**

| Argument | Description |
|----------|-------------|
| `type` | Composable type (e.g. `agents`, `validators`, `guidelines`) |
| `name` | Entity name (e.g. `shared/VALIDATION`) |

**Options:**

| Option | Description |
|--------|-------------|
| `--packs` | Override active packs (space-separated or comma-separated) |
| `--json` | Output as JSON |
| `--repo-root` | Override repository root path |

**Examples:**

```bash
# Human-readable output
edison debug resolve validators global --packs python

# Machine-readable output
edison debug resolve guidelines shared/VALIDATION --json | jq '.applied_layers'
```

## Typical Workflows

### Complete Task Workflow

Full workflow from initialization through task completion:

```bash
# 1. Initialize project (first-time only)
edison init . --non-interactive

# 2. Generate artifacts
edison compose all

# 3. Create session
edison session create --session-id sess-001

# 4. Create task
edison task new --id 100 --slug auth-feature

# 5. Claim task
edison task claim 100-auth-feature --session sess-001

# 6. Check recommended next actions
edison session next sess-001

# 7. Track implementation work
edison session track start --task 100-auth-feature --type implementation

# 8. (Do implementation work)
# ... write code, make commits ...

# 9. Complete tracking
edison session track complete --task 100-auth-feature

# 10. Mark task done (wip → done)
edison task done 100-auth-feature --session sess-001

# 11. Create QA brief
edison qa new 100-auth-feature

# 12. Run validation
edison qa validate 100-auth-feature

# 13. Promote QA to validated
edison qa promote --task 100-auth-feature --to validated

# 14. Verify session can close
edison session verify sess-001 --phase closing

# 15. Close session
edison session close sess-001
```

---

### Quick Start Workflow

Minimal workflow for getting started:

```bash
# Initialize with defaults
edison init . --non-interactive

# Create session and start work
edison session create --id work-001
edison task new --id 100 --slug my-task
edison task claim 100-my-task --session work-001

# ... do work ...

# Complete and validate
edison task done 100-my-task --session work-001
edison qa validate 100-my-task
edison session close work-001
```

---

### Orchestrator Workflow

Automated workflow with orchestrator:

```bash
# Initialize project
edison init .

# Compose artifacts
edison compose all

# Start orchestrator with prompt
edison orchestrator start --profile default --prompt-file ./tasks/task-100.md

# Orchestrator handles the rest automatically
```

---

### Configuration Update Workflow

Updating configuration and regenerating:

```bash
# Edit configuration files
vim .edison/config/project.yml

# Validate changes
edison config validate

# View merged configuration
edison config show

# Regenerate artifacts
edison compose all

# Sync to IDE platforms
edison compose all --claude --cursor
```

---

### Multi-Session Parallel Work

Working on multiple tasks in parallel:

```bash
# Create multiple sessions with worktrees
edison session create --id session-feature-a
edison session create --id session-feature-b

# Work in first session
edison task new --id 100 --slug feature-a
edison task claim 100-feature-a --session session-feature-a

# Work in second session (different worktree)
edison task new --id 101 --slug feature-b
edison task claim 101-feature-b --session session-feature-b

# Each session has isolated worktree
cd .worktrees/session-feature-a  # Work on feature A
cd .worktrees/session-feature-b  # Work on feature B
```

---

### Recovery Workflow

Recovering from errors or interruptions:

```bash
# Check what went wrong
edison session status sess-001

# Clean up stale locks
edison task cleanup_stale_locks

# Repair session state
edison session recovery repair sess-001

# Clean orphaned worktrees
edison session recovery clean-worktrees

# Resume work
edison task claim 100-feature --session sess-001 --reclaim
```

---

## Appendix: Configuration File Locations

### Project Structure

```
my-project/
├── .edison/                      # Edison project root
│   ├── config/                   # Configuration overrides
│   │   ├── project.yml           # Project metadata
│   │   ├── paths.yml             # Path configuration
│   │   ├── packs.yml             # Active packs
│   │   ├── database.yml          # Database config
│   │   ├── worktrees.yml         # Worktree settings
│   │   ├── tdd.yml               # TDD settings
│   │   ├── validation.yaml       # Validation configuration
│   │   ├── mcp.yml               # MCP servers
│   │   └── ...
│   ├── _generated/               # Generated artifacts
│   │   ├── agents/               # Agent definitions
│   │   ├── validators/           # Validators
│   │   ├── guidelines/           # Guidelines
│   │   ├── constitutions/        # Constitutions
│   │   └── start/                # Start prompts
│   ├── tasks/                    # Task definitions
│   ├── .sessions/                # Session data
│   │   └── sessions.db           # Session database
│   ├── scripts/                  # Helper scripts
│   │   └── pal/                  # Pal MCP scripts
│   └── .gitignore
├── .mcp.json                     # MCP configuration
└── .worktrees/                   # Session worktrees
    ├── sess-001/
    └── sess-002/
```

---

## Appendix: State Machine Reference

### Task States

```
waiting → todo → wip → done → validated
   ↑       ↓      ↓      ↓
   └───────┴──────┴──────┘
      (can return to waiting if blocked)
```

### QA States

```
waiting → todo → wip → done → validated
```

### Session States

```
active → closing → closed → archived
```

---

## Getting More Help

### Documentation

- Official Docs: (URL to be added)
- GitHub: (URL to be added)

### Command Help

```bash
# General help
edison --help

# Domain help
edison <domain> --help

# Command help
edison <domain> <command> --help
```

### Version Information

```bash
edison --version
```

### Debugging

Enable JSON output for detailed information:

```bash
edison <domain> <command> --json | jq .
```

Use `--dry-run` to preview operations:

```bash
edison <domain> <command> --dry-run
```

---

**End of CLI Reference**
