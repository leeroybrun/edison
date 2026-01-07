# Edison OpenCode Integration

Edison provides first-class integration with OpenCode through a generated TypeScript plugin. This plugin enables FC/RL continuation enforcement, context window management, and non-interactive environment handling.

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Setup Command](#setup-command)
4. [Generated Artifacts](#generated-artifacts)
5. [Plugin Architecture](#plugin-architecture)
6. [Features](#features)
7. [Configuration](#configuration)
8. [Customization](#customization)
9. [Troubleshooting](#troubleshooting)

---

## Overview

The Edison OpenCode integration provides:

- **FC/RL Continuation**: Automatic continuation prompt injection
- **CWAM**: Context window anxiety management (truncation, compaction)
- **Non-Interactive Mode**: Environment injection and banned command warnings
- **Session Context**: Session ID resolution and context injection
- **Rules Injection**: State-aware rule injection alongside continuation

**Source of truth:**
- Setup command: `edison opencode setup`
- Configuration: `src/edison/data/config/opencode.yaml`
- Plugin template: `src/edison/data/templates/opencode/plugin/edison.ts.template`

---

## Quick Start

```bash
# 1. Ensure you have an Edison project
ls .edison/config  # Should exist

# 2. Generate OpenCode artifacts
edison opencode setup --all --yes

# 3. Verify generated files
ls .opencode/
# plugin/edison.ts
# agent/
# command/
# package.json

ls opencode.json  # Config file in repo root

# 4. Start OpenCode - it auto-discovers the plugin
opencode
```

---

## Setup Command

The `edison opencode setup` command generates all OpenCode artifacts:

```bash
# Preview changes (dry run)
edison opencode setup --dry-run

# Generate just the plugin
edison opencode setup --yes

# Generate everything
edison opencode setup --all --yes

# Generate specific artifacts
edison opencode setup --agents --yes
edison opencode setup --commands --yes
edison opencode setup --config --yes
edison opencode setup --plugin-deps --yes

# Force overwrite modified files
edison opencode setup --all --force --yes
```

### Options

| Option | Description |
|--------|-------------|
| `--yes` | Apply changes without confirmation |
| `--force` | Overwrite modified files |
| `--dry-run` | Show what would be done |
| `--all` | Generate all artifacts |
| `--agents` | Generate agent definitions |
| `--commands` | Generate command definitions |
| `--config` | Generate opencode.json |
| `--plugin-deps` | Generate .opencode/package.json |
| `--json` | JSON output |

---

## Generated Artifacts

### Plugin (`.opencode/plugin/edison.ts`)

The main TypeScript plugin implementing all Edison features:

```typescript
export const Edison = async ({ client }: { client: any }) => {
  return {
    event: async ({ event }) => { /* FC/RL, compaction */ },
    toolExecuteBefore: async ({ tool, args }) => { /* Non-interactive */ },
    toolExecuteAfter: async ({ result }) => { /* Truncation */ },
    "experimental.session.compacting": async (input, output) => { /* CWAM */ },
  };
};
```

### Agent Definitions (`.opencode/agent/`)

Markdown files defining Edison-aware agents:

```
.opencode/agent/
  edison-orchestrator.md  - Session orchestration agent
  edison-agent.md         - Implementation agent
  edison-validator.md     - Validation agent
```

### Command Definitions (`.opencode/command/`)

Markdown files defining Edison commands:

```
.opencode/command/
  edison-session-next.md    - Get next actions
  edison-session-status.md  - Show session status
  edison-task-claim.md      - Claim a task
  edison-task-ready.md      - List ready-to-claim tasks
  edison-task-done.md       - Mark task done
```

### Configuration (`opencode.json`)

OpenCode project configuration:

```json
{
  "$schema": "./.opencode/schema/opencode-config.schema.json",
  "plugins": {
    "directory": ".opencode/plugin"
  },
  "agents": {
    "directory": ".opencode/agent"
  },
  "commands": {
    "directory": ".opencode/command"
  }
}
```

### Dependencies (`.opencode/package.json`)

Plugin dependencies for npm/bun:

```json
{
  "name": "edison-opencode-plugin",
  "private": true,
  "dependencies": {}
}
```

---

## Plugin Architecture

### Session ID Resolution

The plugin resolves Edison session ID using priority order:

1. `AGENTS_SESSION` environment variable
2. `edison session context --json` command
3. Fallback to null (fail-open)

```typescript
async function resolveEdisonSessionId(): Promise<string | null> {
  // Priority 1: Environment variable
  const envSession = process.env.AGENTS_SESSION;
  if (envSession) return envSession;

  // Priority 2: Session context
  const proc = Bun.spawn(["edison", "session", "context", "--json"], ...);
  const data = JSON.parse(await proc.stdout.text());
  return data?.sessionId || null;
}
```

### Event Handling

The plugin handles OpenCode events:

| Event | Handler |
|-------|---------|
| `session.idle` | FC/RL continuation injection |
| `session.error` | Token-limit recovery compaction |
| `session.compacted` | Context re-injection after compaction |

### Tool Hooks

The plugin hooks into tool execution:

| Hook | Purpose |
|------|---------|
| `toolExecuteBefore` | Non-interactive env injection, banned command warnings |
| `toolExecuteAfter` | Output truncation, token usage tracking |

### Compaction Hook

The experimental compaction hook injects summary-shape guidance:

```typescript
"experimental.session.compacting": async (input, output) => {
  const rulesPayload = await fetchEdisonRulesInject("compaction");
  if (rulesPayload?.injection) {
    output.context.push(rulesPayload.injection);
  }
}
```

---

## Features

### FC/RL Continuation

See [CONTINUATION.md](CONTINUATION.md) for full documentation.

**Soft Mode (FC):**
- Single continuation injection on idle
- No iteration tracking

**Hard Mode (RL):**
- Repeated injection until complete
- Respects budgets and cooldowns

### Context Window Management (CWAM)

See [CONTEXT_WINDOW_MANAGEMENT.md](CONTEXT_WINDOW_MANAGEMENT.md) for full documentation.

**Features:**
- Output truncation (configurable limit)
- Preemptive compaction (threshold-based)
- Recovery compaction (error-triggered)
- Summary-shape guidance injection

### Non-Interactive Environment

The plugin handles non-interactive environments:

```typescript
// Inject non-interactive env vars
const mergedEnv = {
  ...args.env,
  ...NON_INTERACTIVE_CONFIG.env,
};

// Warn on banned commands
if (isCommandBanned(command)) {
  warningMessage = `[Edison] WARNING: Command may hang in non-interactive environment...`;
}
```

**Configuration:**

```yaml
# src/edison/data/config/execution.yaml
execution:
  nonInteractive:
    enabled: true
    env:
      EDITOR: "cat"
      GIT_EDITOR: "true"
      PAGER: "cat"
    bannedCommandPatterns:
      - "^vim"
      - "^nano"
      - "^less"
    onMatch: warn  # or block
```

### Rules Injection

Applicable rules are injected alongside continuation prompts:

```typescript
const taskState = await getCurrentTaskState();
if (taskState) {
  const rulesPayload = await fetchEdisonRulesInject(taskState);
  if (rulesPayload?.injection) {
    rulesInjection = rulesPayload.injection;
  }
}

const fullPrompt = rulesInjection
  ? `${rulesInjection}\n\n${continuationPrompt}`
  : continuationPrompt;
```

---

## Configuration

### OpenCode Configuration

Edit `src/edison/data/config/opencode.yaml`:

```yaml
opencode:
  paths:
    plugin: ".opencode/plugin"
    agents: ".opencode/agent"
    commands: ".opencode/command"
    config: "opencode.json"
    packageJson: ".opencode/package.json"

  agentTemplates:
    - edison-orchestrator
    - edison-agent
    - edison-validator

  commandTemplates:
    - edison-session-next
    - edison-session-status
    - edison-task-claim
    - edison-task-ready
    - edison-task-done

  pluginTemplate: "templates/opencode/plugin/edison.ts.template"

  configTemplates:
    opencode: "templates/opencode/opencode.json.template"
    package: "templates/opencode/package.json.template"
```

### Plugin Constants

Plugin behavior is controlled by constants in the generated plugin:

```typescript
const RL_CONFIG = {
  maxIterations: 10,
  cooldownSeconds: 5,
  stopOnBlocked: true,
};

const TRUNCATION_CONFIG = {
  enabled: true,
  maxChars: 50000,
  preserveHeaderLines: 10,
  truncationNotice: "\n\n[... output truncated by Edison plugin ...]\n",
};

const COMPACTION_CONFIG = {
  preemptive: {
    enabled: true,
    threshold: 0.70,
    cooldownSeconds: 120,
    estimatedTokenLimit: 100000,
  },
  recovery: {
    enabled: true,
    maxAttempts: 3,
    errorPatterns: [...],
  },
  hooks: {
    compactingEnabled: true,
    compactedEnabled: true,
  },
};
```

---

## Customization

### Custom Agent Templates

Create custom agent templates in `src/edison/data/templates/opencode/agent/`:

```markdown
# My Custom Agent

This agent specializes in...

## Instructions

1. Read the Edison constitution
2. Follow TDD workflow
3. ...

## Commands

- `edison task show <id>` - View task details
- `edison task ready` - List ready-to-claim tasks
- `edison task done <id>` - Mark task done
```

Add to configuration:

```yaml
opencode:
  agentTemplates:
    - edison-orchestrator
    - edison-agent
    - edison-validator
    - my-custom-agent  # Your custom agent
```

### Custom Command Templates

Create custom command templates in `src/edison/data/templates/opencode/command/`:

````markdown
# My Custom Command

Runs `edison my-custom-command`.

## Usage

```bash
edison my-custom-command <args>
```

## Examples

```bash
edison my-custom-command --option value
```
````

Add to configuration:

```yaml
opencode:
  commandTemplates:
    - edison-session-next
    - edison-session-status
    - edison-task-claim
    - edison-task-ready
    - edison-task-done
    - my-custom-command  # Your custom command
```

### Plugin Modifications

For advanced customization, you can modify the plugin after generation:

1. Generate the base plugin: `edison opencode setup --yes`
2. Edit `.opencode/plugin/edison.ts`
3. Re-run with `--force` to regenerate (will overwrite your changes)

Or, maintain a fork of the plugin template in your project.

---

## Troubleshooting

### Plugin Not Loading

```bash
# Verify opencode.json exists and is valid
cat opencode.json

# Verify plugin exists
ls -la .opencode/plugin/edison.ts

# Check OpenCode logs
opencode --debug
```

### Edison Commands Failing

```bash
# Verify Edison is installed and working
edison --version
edison session status

# Check if in Edison project
ls .edison/config

# Verify session exists
edison session list
```

### Session ID Not Resolved

```bash
# Set environment variable explicitly
export AGENTS_SESSION=my-session
opencode

# Or verify session context
edison session context --json
```

### Continuation Not Injecting

```bash
# Check continuation is enabled
edison session continuation show <session-id>

# Verify session is not complete
edison session next <session-id> --completion-only --json

# Check for blockers
edison session next <session-id> --json | jq '.blockers'
```

### Truncation Not Working

```bash
# Verify truncation is enabled in config
cat .edison/config/context_window.yaml

# Check plugin constants
grep "TRUNCATION_CONFIG" .opencode/plugin/edison.ts
```

### Compaction Issues

```bash
# Check compaction config
cat .edison/config/context_window.yaml

# Verify hooks are enabled
grep "compactingEnabled\|compactedEnabled" .opencode/plugin/edison.ts
```

---

## See Also

- [CONTINUATION.md](CONTINUATION.md) - FC/RL continuation system
- [CONTEXT_WINDOW_MANAGEMENT.md](CONTEXT_WINDOW_MANAGEMENT.md) - CWAM documentation
- [CAPABILITY_MATRIX.md](CAPABILITY_MATRIX.md) - Feature comparison across clients
- [CONFIGURATION.md](CONFIGURATION.md) - Full configuration guide
- [WORKFLOWS.md](WORKFLOWS.md) - Session workflow reference

---

**Last Updated:** 2026-01-04
**Version:** 2.0.0
