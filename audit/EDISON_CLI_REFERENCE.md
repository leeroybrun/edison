# Edison CLI Command Reference

**Generated from audit on:** 2025-12-01
**Status:** Verified against actual CLI implementation

---

## Overview

Edison provides a hierarchical CLI organized by domains. Each domain groups related commands.

```
edison <domain> <command> [options]
```

---

## Domains

| Domain | Purpose |
|--------|---------|
| `init` | Project initialization (root-level command) |
| `session` | Session lifecycle management |
| `task` | Task management |
| `qa` | Quality assurance and validation |
| `compose` | Artifact composition |
| `config` | Configuration management |
| `git` | Git and worktree management |
| `rules` | Rule management |
| `mcp` | MCP server configuration |
| `orchestrator` | Orchestrator management |

---

## Root Commands

### Initialize Project

```bash
edison init [project_path] [options]
```

| Option | Description |
|--------|-------------|
| `--non-interactive` | Skip questionnaire, use bundled defaults |
| `--advanced` | Include advanced configuration questions |
| `--force` | Overwrite existing config files |
| `--merge` | Merge with existing config files |
| `--reconfigure` | Re-run questionnaire on existing project |
| `--skip-mcp` | Skip MCP configuration |
| `--skip-compose` | Skip running initial composition |

**Example:**
```bash
edison init .
edison init . --non-interactive
edison init /path/to/project --advanced --force
```

---

## Session Domain

### Create Session

```bash
edison session create --session-id <id> [options]
```

| Option | Description |
|--------|-------------|
| `--session-id`, `--id` | Session identifier (required) |
| `--owner` | Session owner (default: system) |
| `--mode` | Session mode (default: start) |
| `--no-worktree` | Skip worktree creation |
| `--install-deps` | Install dependencies in worktree |

**Example:**
```bash
edison session create --session-id sess-001
edison session create --id sess-001 --owner claude --no-worktree
```

### Session Status

```bash
edison session status <session_id> [--json]
```

**Example:**
```bash
edison session status sess-001
edison session status sess-001 --json
```

### Session Next (Recommended Actions)

```bash
edison session next <session_id> [options]
```

| Option | Description |
|--------|-------------|
| `--limit` | Maximum actions to return |
| `--scope` | Restrict to domain: tasks, qa, session |

**Example:**
```bash
edison session next sess-001
edison session next sess-001 --limit 5 --scope tasks
```

### Session Close

```bash
edison session close <session_id> [options]
```

### Session Verify

```bash
edison session verify <session_id> [options]
```

### Session Validate

```bash
edison session validate <session_id> [options]
```

### Session Me

```bash
edison session me [options]
```

Shows or updates current session identity/context.

### Session Track (Nested)

```bash
edison session track <subcommand> [options]
```

#### Track Start

```bash
edison session track start --task <task-id> --type <type> [options]
```

| Option | Description |
|--------|-------------|
| `--task` | Task ID (required) |
| `--type` | Type: implementation, validation (required) |
| `--model` | Model name |
| `--validator` | Validator name |
| `--round` | Validation round number |

**Example:**
```bash
edison session track start --task 100-feature --type implementation --model claude
```

#### Track Complete

```bash
edison session track complete --task <task-id> [options]
```

**Example:**
```bash
edison session track complete --task 100-feature
```

#### Track Heartbeat

```bash
edison session track heartbeat --task <task-id> [options]
```

#### Track Active

```bash
edison session track active [options]
```

Lists active tracking sessions.

### Session Recovery (Nested)

```bash
edison session recovery <subcommand> [options]
```

Commands: `repair`, `recover`, `recover-timed-out`, `recover-validation-tx`, `clear-locks`, `clean-worktrees`

---

## Task Domain

### Create Task

```bash
edison task new --id <priority> --slug <slug> [options]
```

| Option | Description |
|--------|-------------|
| `--id` | Priority slot (required) |
| `--slug` | Task slug (required) |
| `--wave` | Wave identifier |
| `--type` | Task type: feature, bug, chore |
| `--owner` | Owner name |
| `--session` | Session to create task in |
| `--parent` | Parent task ID |

**Example:**
```bash
edison task new --id 150 --slug auth-feature
edison task new --id 151 --slug login-ui --wave wave1 --type feature --session sess-001
```

### Claim Task

```bash
edison task claim <record_id> [options]
```

| Option | Description |
|--------|-------------|
| `--session` | Session to claim into |
| `--type` | Record type: task, qa |
| `--owner` | Owner name |
| `--reclaim` | Allow reclaiming from another session |
| `--force` | Force claim even with warnings |

**Example:**
```bash
edison task claim 150-auth-feature --session sess-001
edison task claim 150-auth-feature --session sess-001 --owner claude
```

### Task Status

```bash
edison task status <record_id> [options]
```

| Option | Description |
|--------|-------------|
| `--status` | Transition to: todo, wip, done, validated, waiting |
| `--type` | Record type: task, qa |
| `--dry-run` | Preview transition without changes |
| `--force` | Force transition even when guards fail |

**Example:**
```bash
edison task status 150-auth-feature
edison task status 150-auth-feature --status done
edison task status 150-auth-feature --status done --dry-run
```

### Task Ready

```bash
edison task ready [record_id] [options]
```

Without `record_id`: Lists tasks ready to be claimed (in todo state).
With `record_id`: Marks task as ready/complete (moves from wip to done).

| Option | Description |
|--------|-------------|
| `--session` | Filter by session |

**Example:**
```bash
edison task ready  # List ready tasks
edison task ready 150-auth-feature --session sess-001  # Mark task ready
```

### Task List

```bash
edison task list [options]
```

Lists tasks across queues.

### Task Link

```bash
edison task link <parent> <child> [options]
```

Link parent-child tasks.

### Task Split

```bash
edison task split <task_id> [options]
```

Split task into subtasks.

### Task Ensure Followups

```bash
edison task ensure_followups [options]
```

Generate required follow-up tasks.

---

## QA Domain

### Create QA Brief

```bash
edison qa new <task_id> [options]
```

Creates new QA brief for a task.

**Example:**
```bash
edison qa new 150-auth-feature
```

### QA Validate

```bash
edison qa validate <task_id> [options]
```

| Option | Description |
|--------|-------------|
| `--session` | Session ID context |
| `--round` | Validation round number |
| `--validators` | Specific validator IDs to run |
| `--blocking-only` | Only run blocking validators |

**Example:**
```bash
edison qa validate 150-auth-feature
edison qa validate 150-auth-feature --blocking-only
```

### QA Bundle

```bash
edison qa bundle <task_id> [options]
```

Create or inspect QA validation bundle.

### QA Promote

```bash
edison qa promote --task <task_id> --to <state> [options]
```

Promote QA brief between states: waiting → todo → wip → done → validated

**Example:**
```bash
edison qa promote --task 150-auth-feature --to todo
edison qa promote --task 150-auth-feature --to validated
```

### QA Round

```bash
edison qa round --task <task_id> --status <status> [options]
```

Manage QA rounds. Statuses: approved, needs-work, blocked

### QA Run

```bash
edison qa run [options]
```

Run a specific validator.

### QA Audit

```bash
edison qa audit [options]
```

Audit guidelines quality.

---

## Compose Domain

### Compose All

```bash
edison compose all [options]
```

Compose all artifacts (agents, validators, constitutions, guidelines, start prompts).

**Example:**
```bash
edison compose all
edison compose all --dry-run
```

### Compose Commands

```bash
edison compose commands [options]
```

Compose CLI commands from configuration.

### Compose Hooks

```bash
edison compose hooks [options]
```

Compose Claude Code hooks from configuration.

### Compose Settings

```bash
edison compose settings [options]
```

Compose IDE settings files from configuration.

### Compose Validate

```bash
edison compose validate [options]
```

Validate composition configuration and outputs.

---

## Config Domain

### Config Show

```bash
edison config show [options]
```

Show current configuration.

### Config Validate

```bash
edison config validate [options]
```

Validate project configuration.

### Config Configure

```bash
edison config configure [options]
```

Interactive configuration menu.

---

## Git Domain

### Git Status

```bash
edison git status [options]
```

Show Edison-aware git status.

### Git Worktree Commands

```bash
edison git worktree-create <session_id>
edison git worktree-list
edison git worktree-health <session_id>
edison git worktree-archive <session_id>
edison git worktree-restore <session_id>
edison git worktree-cleanup <session_id>
```

---

## Rules Domain

### Rules List

```bash
edison rules list [options]
```

List all available rules.

### Rules Show

```bash
edison rules show <rule_id> [options]
```

Show specific rule.

### Rules Show For Context

```bash
edison rules show-for-context <category> <context> [options]
```

Show rules applicable to specific contexts.

### Rules Check

```bash
edison rules check [options]
```

Check rules applicable to a specific context or transition.

---

## MCP Domain

### MCP Configure

```bash
edison mcp configure [options]
```

Configure .mcp.json for all MCP servers.

### MCP Setup

```bash
edison mcp setup [options]
```

Setup MCP servers defined in mcp.yaml.

---

## Orchestrator Domain

### Orchestrator Start

```bash
edison orchestrator start <task_id> [options]
```

Start an orchestrator session with optional worktree.

### Orchestrator Profiles

```bash
edison orchestrator profiles [options]
```

List available orchestrator profiles.

---

## Common Flags

Most commands support these common flags:

| Flag | Description |
|------|-------------|
| `--json` | Output as JSON |
| `--repo-root` | Override repository root path |

---

## Typical Workflow

```bash
# 1. Initialize project
edison init . --non-interactive

# 2. Generate artifacts
edison compose all

# 3. Create session
edison session create --session-id sess-001

# 4. Create task
edison task new --id 100 --slug my-feature

# 5. Claim task
edison task claim 100-my-feature --session sess-001

# 6. Check next actions
edison session next sess-001

# 7. Track implementation
edison session track start --task 100-my-feature --type implementation

# 8. (Do implementation work)

# 9. Complete tracking
edison session track complete --task 100-my-feature

# 10. Mark task ready
edison task ready 100-my-feature --session sess-001

# 11. Create QA brief (if not auto-created)
edison qa new 100-my-feature

# 12. Validate
edison qa validate 100-my-feature

# 13. Promote QA
edison qa promote --task 100-my-feature --to validated

# 14. Close session
edison session close sess-001
```
