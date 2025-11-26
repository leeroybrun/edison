# Edison CLI Reference for Agents/Implementers

## Overview

This guide covers CLI commands relevant to agents and implementers working on assigned tasks. Agents focus on implementation work and should NOT perform orchestration (session management, delegation) or validation (running validators, creating bundles).

**Agent responsibilities:**
- Implement assigned features/fixes
- Track implementation progress
- Check task status
- Look up technical documentation
- Report completion to orchestrator

## Commands

### Task Status

```bash
scripts/tasks/status <task-id>
```

**Purpose**: Check the current state of your assigned task
**When to use**:
- At the start of work to understand task details
- To verify task status before reporting completion
- To check validation requirements

**Example output:**
```json
{
  "task_id": "TASK-123",
  "status": "wip",
  "owner": "claude-agent-001",
  "claimedAt": "2025-11-24T10:30:00Z",
  "validation_required": ["global-codex", "testing"]
}
```

**Common usage:**
```bash
# Check current task
scripts/tasks/status TASK-123

# JSON output for parsing
scripts/tasks/status TASK-123 --json
```

---

### Implementation Tracking

```bash
scripts/track start --task <task-id> --type implementation --round <N>
```

**Purpose**: Prepare evidence directory for implementation work
**When to use**: Before starting implementation work on a task round

**Example:**
```bash
scripts/track start --task TASK-123 --type implementation --round 1
```

---

```bash
scripts/track complete --task <task-id> --type implementation --round <N> --model <model>
```

**Purpose**: Record completion of implementation work
**When to use**: After completing implementation, before validation

**Example:**
```bash
scripts/track complete --task TASK-123 --type implementation --round 1 --model claude
```

**This writes**: `.project/qa/validation-evidence/TASK-123/round-1/implementation-report.json`

---

### Context7 MCP (Documentation Lookup)

Agents have access to Context7 MCP for up-to-date library documentation.

**Resolve library ID:**
```
Use MCP tool: mcp__context7__resolve-library-id
Parameter: libraryName (e.g., library names from active packs)
```

**Fetch documentation:**
```
Use MCP tool: mcp__context7__get-library-docs
Parameters:
  - context7CompatibleLibraryID (from resolve step)
  - mode: "code" (API refs) or "info" (conceptual guides)
  - topic: (optional) specific area (e.g., routing, data-access)
  - page: pagination for large docs
```

**When to use:**
- Looking up current API syntax for frameworks from active packs
- Understanding best practices for configured libraries
- Finding code examples for features

**Example workflow:**
1. Resolve: `resolve-library-id("<library-name>")` → `/<org>/<library>`
2. Fetch: `get-library-docs("/<org>/<library>", mode="code", topic="<topic>")`

---

## What Agents Should NOT Do

**❌ DO NOT run these commands** (orchestrator-only):
- `scripts/session next/start/status/close` - Session management
- `scripts/tasks/claim/ready` - Task orchestration
- `scripts/qa/promote` - QA state transitions
- Any delegation commands

**❌ DO NOT run these commands** (validator-only):
- `scripts/validators/validate` - Run validation
- `scripts/qa/bundle` - Create validation bundles
- Any validator execution commands

## Common Workflows

### Starting Implementation Work

```bash
# 1. Check task details
scripts/tasks/status TASK-123

# 2. Prepare evidence directory
scripts/track start --task TASK-123 --type implementation --round 1

# 3. Implement feature (your actual work)
# ... make code changes, write tests, etc ...

# 4. Record completion
scripts/track complete --task TASK-123 --type implementation --round 1 --model claude

# 5. Report back to orchestrator
# "Implementation complete. Ready for validation."
```

### Looking Up Library Documentation

```bash
# Via MCP tools (within agent context):

# Step 1: Resolve library (use names from active packs)
resolve-library-id("<library-name>") → "/<org>/<library>"

# Step 2: Get API docs
get-library-docs(
  context7CompatibleLibraryID="/<org>/<library>",
  mode="code",
  topic="<relevant-topic>"
)

# Step 3: Use information in implementation
```

### Checking Task Before Completion

```bash
# Verify current state
scripts/tasks/status TASK-123 --json

# Check validation requirements from output
# Ensure all implementation is complete
# Report to orchestrator for validation
```

---

## Output Locations

**Implementation evidence**: `.project/qa/validation-evidence/<task-id>/round-N/implementation-report.json`

**Contents:**
- Changes made
- Files modified
- Tests added
- TDD evidence
- Completion status

---

## Best Practices

1. **Always track work**: Use `scripts/track start` before implementation
2. **Complete tracking**: Use `scripts/track complete` when done
3. **Check task status**: Verify task details before and after work
4. **Use Context7**: Look up current documentation, don't rely on outdated info
5. **Report clearly**: Tell orchestrator when implementation is complete
6. **Stay in scope**: Implement only what's assigned, don't orchestrate or validate

---

## Related Documentation

- `.edison/core/guidelines/agents/AGENT_WORKFLOW.md` - Full agent workflow
- `.edison/core/guidelines/agents/OUTPUT_FORMAT.md` - Output format requirements
- `.edison/core/guidelines/TDD.md` - TDD requirements for implementation

---

**Role**: Agent/Implementer
**Focus**: Implementation work only
**DO**: Implement, track, report completion
**DON'T**: Orchestrate, delegate, validate
