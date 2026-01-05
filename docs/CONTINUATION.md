# Edison Continuation (FC/RL)

Edison provides a continuation system that enables autonomous agents to continue working until a session is complete. The system supports two enforcement modes: **FC (Free Continuation)** with soft prompting, and **RL (Ralph Loop)** with hard enforcement and budgets.

---

## Table of Contents

1. [Overview](#overview)
2. [Continuation Modes](#continuation-modes)
3. [Configuration](#configuration)
4. [CLI Commands](#cli-commands)
5. [Session Next Command](#session-next-command)
6. [Client Integration](#client-integration)
7. [Completion Policies](#completion-policies)
8. [Budgets and Limits](#budgets-and-limits)
9. [OpenCode Plugin Integration](#opencode-plugin-integration)

---

## Overview

The continuation system answers the question: "Should the agent keep working, or is the session complete?"

**Key concepts:**

- **Completion**: Computed by `edison session next` based on task states, blockers, and completion policy
- **Continuation**: Whether the client should inject another prompt to keep the agent working
- **Loop driver**: The command clients should run to get the next action (`edison session next <session-id>`)

**Source of truth:**
- Configuration: `src/edison/data/config/continuation.yaml`
- CLI: `edison session continuation show|set|clear`
- Computation: `edison session next --completion-only`

---

## Continuation Modes

### Off (Disabled)

No continuation prompts are injected. The agent works until it naturally stops.

```yaml
continuation:
  defaultMode: off
```

### Soft (FC - Free Continuation)

A single continuation prompt is injected when the session becomes idle. The agent is gently reminded to continue, but no enforcement budgets apply.

```yaml
continuation:
  defaultMode: soft
```

**Behavior:**
- One prompt injection per idle event
- No iteration limits or cooldowns
- Agent may choose to stop working

### Hard (RL - Ralph Loop)

Repeated continuation prompts are injected until the session is complete or budgets are exhausted. This mode enforces continued work.

```yaml
continuation:
  defaultMode: hard
  budgets:
    maxIterations: 10
    cooldownSeconds: 5
    stopOnBlocked: true
```

**Behavior:**
- Repeated prompts until completion
- Respects iteration limits and cooldowns
- Can stop on blocked sessions

---

## Configuration

### Global Configuration

Edit `src/edison/data/config/continuation.yaml` or create a project override at `.edison/config/continuation.yaml`:

```yaml
continuation:
  # Enable/disable continuation system
  enabled: true

  # Default enforcement mode: off | soft | hard
  defaultMode: soft

  # Budget settings for hard mode
  budgets:
    maxIterations: 3
    cooldownSeconds: 15
    stopOnBlocked: true

  # Completion policy for session next
  completionPolicy: parent_validated_children_done

  # Prompt injection settings
  prompts:
    inject: true
    ruleContext: continuation

  # Prompt templates
  templates:
    continuationPrompt: |
      Continue working until the Edison session is complete.
      Use the loop driver: `edison session next {sessionId}`
```

### Per-Session Override

Sessions can override continuation settings via metadata:

```bash
# Set hard mode with custom budgets
edison session continuation set <session-id> \
  --mode hard \
  --max-iterations 5 \
  --cooldown-seconds 10 \
  --stop-on-blocked

# View effective settings (defaults + override)
edison session continuation show <session-id>

# Clear override (fall back to project defaults)
edison session continuation clear <session-id>
```

---

## CLI Commands

### `edison session continuation show`

Show effective continuation settings for a session:

```bash
edison session continuation show <session-id>

# Example output:
Session: my-session
Effective mode: soft
Effective enabled: true
Budgets: maxIterations=3 cooldownSeconds=15 stopOnBlocked=true

# JSON output
edison session continuation show <session-id> --json
```

### `edison session continuation set`

Set per-session continuation override:

```bash
edison session continuation set <session-id> --mode hard
edison session continuation set <session-id> --mode soft --max-iterations 5
edison session continuation set <session-id> --mode hard --no-stop-on-blocked
```

**Options:**
- `--mode`: `off`, `soft`, or `hard`
- `--max-iterations`: Override max iteration budget (>= 1)
- `--cooldown-seconds`: Override cooldown between injections (>= 0)
- `--stop-on-blocked` / `--no-stop-on-blocked`: Stop when session is blocked

### `edison session continuation clear`

Remove per-session override and fall back to project defaults:

```bash
edison session continuation clear <session-id>
```

---

## Session Next Command

The `edison session next` command is the primary interface for continuation:

```bash
# Full output with actions, blockers, and rules
edison session next <session-id>

# Completion-only output for hooks/plugins
edison session next <session-id> --completion-only --json
```

### Output Structure

```json
{
  "sessionId": "my-session",
  "completion": {
    "policy": "parent_validated_children_done",
    "isComplete": false,
    "reasonsIncomplete": [
      {
        "code": "root_tasks_not_validated",
        "message": "Root tasks must be validated before session is complete",
        "taskIds": ["001-feature-x"]
      }
    ]
  },
  "continuation": {
    "enabled": true,
    "mode": "soft",
    "shouldContinue": true,
    "prompt": "Continue working until the Edison session is complete...",
    "loopDriver": ["edison", "session", "next", "my-session"],
    "budgets": {
      "maxIterations": 3,
      "cooldownSeconds": 15,
      "stopOnBlocked": true
    }
  },
  "actions": [...],
  "blockers": [...]
}
```

### Key Fields

| Field | Description |
|-------|-------------|
| `completion.isComplete` | Whether the session is considered complete |
| `completion.reasonsIncomplete` | Why the session is not complete |
| `continuation.shouldContinue` | Whether the client should inject a continuation prompt |
| `continuation.prompt` | The prompt to inject |
| `continuation.loopDriver` | Command to run for next action |
| `continuation.mode` | Current enforcement mode |

---

## Client Integration

### OpenCode Plugin

The OpenCode plugin implements FC/RL enforcement via the `session.idle` event:

```typescript
// Resolve session ID
const sessionId = await resolveEdisonSessionId();

// Fetch continuation from Edison
const payload = await fetchEdisonSessionNext(sessionId);
const shouldContinue = payload?.continuation?.shouldContinue;
const prompt = payload?.continuation?.prompt;
const mode = payload?.continuation?.mode;

// Check budgets (hard mode)
if (mode === "hard") {
  const { shouldInject } = shouldInjectContinuation(rlState, mode);
  if (!shouldInject) return; // Budget exhausted
}

// Inject continuation prompt
if (shouldContinue && prompt) {
  await client.tui.appendPrompt({ body: { text: prompt } });
}
```

### Claude Code Hooks

Claude Code can integrate via hooks that call `edison session next --completion-only --json`:

```python
import subprocess
import json

result = subprocess.run(
    ["edison", "session", "next", session_id, "--completion-only", "--json"],
    capture_output=True,
    text=True
)
data = json.loads(result.stdout)

if data["continuation"]["shouldContinue"]:
    inject_prompt(data["continuation"]["prompt"])
```

### Pal MCP

Pal can inject continuation prompts into composed prompts:

```yaml
continuation:
  prompts:
    inject: true
    ruleContext: continuation
```

---

## Completion Policies

The completion policy determines when a session is considered complete.

### `parent_validated_children_done` (Default)

- Root tasks (no parent in session) must be validated
- Child tasks must be done or validated

### `all_tasks_validated`

- All tasks in the session must be validated

### Completion Reasons

When a session is incomplete, reasons are provided:

| Code | Description |
|------|-------------|
| `no_tasks` | No tasks found for this session |
| `blockers` | Blockers exist that must be resolved |
| `reports_missing` | Required evidence/reports are missing |
| `root_tasks_not_validated` | Root tasks need validation |
| `child_tasks_not_done` | Child tasks need to reach done/validated |
| `tasks_not_validated` | (all_tasks_validated policy) Some tasks not validated |

---

## Budgets and Limits

Budgets prevent runaway loops in hard mode:

### `maxIterations`

Maximum number of continuation injections before stopping:

```yaml
budgets:
  maxIterations: 10
```

The client tracks iterations per OpenCode session and stops when exhausted.

### `cooldownSeconds`

Minimum seconds between continuation injections:

```yaml
budgets:
  cooldownSeconds: 5
```

Prevents rapid-fire prompts that could overwhelm the agent.

### `stopOnBlocked`

Whether to stop continuation when the session has blockers:

```yaml
budgets:
  stopOnBlocked: true
```

When enabled, continuation stops if `blockers` is non-empty.

---

## OpenCode Plugin Integration

The OpenCode plugin (`edison opencode setup`) generates a TypeScript plugin that implements full FC/RL enforcement:

```bash
# Generate plugin
edison opencode setup --yes

# Files generated:
# .opencode/plugin/edison.ts - Main plugin with FC/RL logic
# .opencode/agent/*.md - Agent definitions
# .opencode/command/*.md - Command definitions
# opencode.json - OpenCode config
```

### Plugin Features

1. **FC (soft mode)**: Single continuation injection on idle
2. **RL (hard mode)**: Repeated injection with budgets/cooldowns
3. **Session ID resolution**: Environment, context, or fallback
4. **Blockers detection**: Stop on blocked if configured
5. **Rules injection**: Injects applicable rules alongside continuation

See [OPENCODE_INTEGRATION.md](OPENCODE_INTEGRATION.md) for full plugin documentation.

---

## See Also

- [CONTEXT_WINDOW_MANAGEMENT.md](CONTEXT_WINDOW_MANAGEMENT.md) - CWAM (compaction, truncation)
- [OPENCODE_INTEGRATION.md](OPENCODE_INTEGRATION.md) - OpenCode plugin setup
- [WORKFLOWS.md](WORKFLOWS.md) - Session workflow reference
- [CONFIGURATION.md](CONFIGURATION.md) - Full configuration guide

---

**Last Updated:** 2026-01-04
**Version:** 2.0.0
