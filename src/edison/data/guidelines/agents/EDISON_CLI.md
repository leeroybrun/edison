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
edison task status <task-id>
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
edison task status TASK-123

# JSON output for parsing
edison task status TASK-123 --json
```

---

### Implementation Tracking

```bash
edison session track start --task <task-id> --type implementation
```

**Purpose**: Prepare evidence directory for implementation work
**When to use**: Before starting implementation work on a task round

**Example:**
```bash
edison session track start --task TASK-123 --type implementation
```

---

```bash
edison session track complete --task <task-id>
```

**Purpose**: Record completion of implementation work
**When to use**: After completing implementation, before validation

**Example:**
```bash
edison session track complete --task TASK-123
```

**This writes**: `{{fn:evidence_root}}/TASK-123/round-1/implementation-report.md`

---

### Context7 MCP (Documentation Lookup)

Agents have access to Context7 MCP for up-to-date library documentation.

**Resolve library ID:**
```
Use MCP tool: mcp__context7__resolve_library_id
Parameter: libraryName (e.g., library names from active packs)
```

**Fetch documentation:**
```
Use MCP tool: mcp__context7__get_library_docs
Parameters:
  - context7CompatibleLibraryID (from resolve step)
  - mode: "code" (API refs) or "info" (conceptual guides)
  - topic: (optional) specific area (e.g., routing, data-access)
  - page: (optional) pagination for large docs (1-10)
```

**When to use:**
- Looking up current API syntax for frameworks from active packs
- Understanding best practices for configured libraries
- Finding code examples for features

**Example workflow:**
1. Resolve: `mcp__context7__resolve_library_id({ libraryName: "<library-name>" })` → `/<org>/<library>`
2. Fetch: `mcp__context7__get_library_docs({ context7CompatibleLibraryID: "/<org>/<library>", mode: "code", topic: "<topic>" })`

---

## What Agents Should NOT Do

**❌ DO NOT run these commands** (orchestrator-only):
- `edison session next/start/status/close` - Session management
- `edison task claim/ready` - Task orchestration
- `edison qa promote` - QA state transitions
- Any delegation commands

**❌ DO NOT run these commands** (validator-only):
- `edison qa validate` - Run validation
- `edison qa bundle` - Create validation bundles
- Any validator execution commands

## Common Workflows

### Starting Implementation Work

```bash
# 1. Check task details
edison task status TASK-123

# 2. Prepare evidence directory
edison session track start --task TASK-123 --type implementation

# 3. Implement feature (your actual work)
# ... make code changes, write tests, etc ...

# 4. Record completion
edison session track complete --task TASK-123

# 5. Report back to orchestrator
# "Implementation complete. Ready for validation."
```

### Looking Up Library Documentation

```
// Via MCP tools (within agent context):

// Step 1: Resolve library (use names from active packs)
const libraryId = await mcp__context7__resolve_library_id({
  libraryName: "<library-name>"
})
// Returns: "/<org>/<library>"

// Step 2: Get API docs
const docs = await mcp__context7__get_library_docs({
  context7CompatibleLibraryID: libraryId,
  mode: "code",  // or "info" for conceptual guides
  topic: "<relevant-topic>",
  page: 1  // optional pagination
})

// Step 3: Use information in implementation
```

### Checking Task Before Completion

```bash
# Verify current state
edison task status TASK-123 --json

# Check validation requirements from output
# Ensure all implementation is complete
# Report to orchestrator for validation
```

---

## Output Locations

**Implementation evidence**: `{{fn:evidence_root}}/<task-id>/round-N/implementation-report.md`

**Contents:**
- Changes made
- Files modified
- Tests added
- TDD evidence
- Completion status

---

## Best Practices

1. **Always track work**: Use `edison session track start` before implementation
2. **Complete tracking**: Use `edison session track complete` when done
3. **Check task status**: Verify task details before and after work
4. **Use Context7**: Look up current documentation, don't rely on outdated info
5. **Report clearly**: Tell orchestrator when implementation is complete
6. **Stay in scope**: Implement only what's assigned, don't orchestrate or validate

---

## Related Documentation

- `{{fn:project_config_dir}}/_generated/guidelines/agents/AGENT_WORKFLOW.md` - Full agent workflow
- `{{fn:project_config_dir}}/_generated/guidelines/agents/OUTPUT_FORMAT.md` - Output format requirements
- `{{fn:project_config_dir}}/_generated/constitutions/AGENTS.md` - TDD requirements (embedded)

---

**Role**: Agent/Implementer
**Focus**: Implementation work only
**DO**: Implement, track, report completion
**DON'T**: Orchestrate, delegate, validate
