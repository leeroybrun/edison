# Configuration-Driven Model Delegation System

**Version**: 1.0.0
**Purpose**: Enable strategic model selection for implementation tasks while preserving Claude Code's sub-agent architecture.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [How It Works](#how-it-works)
- [Configuration Structure](#configuration-structure)
- [Usage Guide](#usage-guide)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)
- [Migration Strategy](#migration-strategy)

---

## Overview

### The Problem

Different AI models excel at different tasks:
- **Claude Sonnet 4.5**: Superior architecture thinking, UI/UX design, integration
- **Codex (ChatGPT PRO)**: Precision work, API security, refactoring, tests
- **Gemini 2.5 Pro**: Rapid iteration, multimodal analysis, broad context

**Previously**: All implementation done by Claude Sonnet (orchestrator + sub-agents)
**Challenge**: Not leveraging optimal models for specific task types

### The Solution

**Configuration-driven delegation system** that:
1. ✅ Preserves Claude Code's Task tool + sub-agent architecture (entry points stay the same)
2. ✅ Enables sub-agents to delegate specific work to Codex/Gemini via Zen MCP
3. ✅ Supports mixed implementations (UI with Claude, backend with Codex in same task)
4. ✅ Maintains orchestrator as delegator (NOT implementer)
5. ✅ Gives sub-agents final decision authority (config suggests, sub-agent decides)

---

## Architecture

### Two-Level Delegation Hierarchy

```
┌─────────────────────────────────────────────────────────────┐
│ LEVEL 1: ORCHESTRATOR (Strategic)                          │
│                                                             │
│ Reads: config.json                                          │
│ Does:  - Select sub-agent type                             │
│        - Suggest preferred model                            │
│        - Provide task context                               │
│ Tool:  Task(subagent_type='...', prompt='...')             │
│                                                             │
│ NEVER implements directly (exception: <10 line edits)      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ LEVEL 2: SUB-AGENT (Tactical)                              │
│                                                             │
│ Reads: config.json + orchestrator suggestion                │
│ Does:  - Make FINAL model decision                         │
│        - Implement directly (Claude)                        │
│        - OR delegate to Codex/Gemini (Zen MCP)             │
│        - OR mixed (partial direct, partial delegate)       │
│ Tool:  mcp__edison-zen__clink(cli_name='...', role='...', working_directory='<session worktree>') │
│                                                             │
│ Has autonomy to override config based on context           │
└─────────────────────────────────────────────────────────────┘
```

### Model Access Methods

| Model | Access Method | When Used |
|-------|---------------|-----------|
| **Claude Sonnet 4.5** | Direct (sub-agent implements) | UI components, architecture, integration |
| **Codex (ChatGPT PRO)** | Zen MCP (`mcp__edison-zen__clink`) | API routes, database schemas, security, tests |
| **Gemini 2.5 Pro** | Zen MCP (`mcp__edison-zen__clink`) | Rapid iteration, multimodal, research |

---

## How It Works

### Orchestrator Workflow

```typescript
// 1. Read task requirements
// Task: "Implement lead export API endpoint with CSV/Excel formats"

// 2. Read config.json to determine routing
const config = readDelegationConfig()

// 3. Match task to rules
const match = config.taskTypeRules['api-route']
// Returns: { preferredModel: 'codex', subAgentType: 'api-builder' }

// 4. Delegate to sub-agent with suggestion
Task({
  subagent_type: 'api-builder',
  prompt: `
    Implement lead export API endpoint:
    - CSV export format
    - Excel export format
    - Streaming for large datasets

    SUGGESTED MODEL: codex (API routes, security, precision work)
    (You have final decision - use your judgment based on task details)
  `
})

// 5. WAIT for sub-agent completion
// 6. Verify results
// 7. Integrate
```

### Sub-Agent Workflow

```typescript
// 1. Receive task from orchestrator
// Includes: task details + model suggestion

// 2. Read config.json for delegation guidance
const config = readDelegationConfig()
const myDefaults = config.subAgentDefaults['api-builder']
// Returns: { defaultModel: 'codex', zenMcpUsage: 'always' }

// 3. Make FINAL decision
// Factors: orchestrator suggestion, file patterns, task complexity, own judgment

// 4A. OPTION 1: Implement directly (if using Claude)
// Write code directly using Edit/Write tools

// 4B. OPTION 2: Delegate to Codex/Gemini (if using other model)
const worktreePath = SessionContext.build_zen_environment(sessionId).ZEN_WORKING_DIR
const result = await mcp__edison-zen__clink({
  cli_name: 'codex',
  role: 'default',
  working_directory: worktreePath,
  prompt: `Implement lead export API endpoint:
    - File: ${PROJECT_ROOT}/apps/example-app/src/app/api/v1/resources/export/route.ts
    - CSV format: streaming, proper escaping
    - Excel format: using exceljs library
    - Tests: route.test.ts with TDD
  `,
  absolute_file_paths: [
    '${PROJECT_ROOT}/apps/example-app/src/app/api/v1/resources/export/route.ts'
  ]
})

// 4C. OPTION 3: Mixed implementation
// - Implement validation schema directly (Claude)
// - Delegate route handler to Codex (precision + security)
// - Implement tests directly (Claude)

// 5. Return results to orchestrator
```

---

## Configuration Structure

### File: `.edison/delegation/config.json`

**Six Major Sections**:

#### 1. `models{}` - Model Registry
Defines available models with capabilities, strengths, weaknesses.

```json
{
  "models": {
    "codex": {
      "provider": "zen-mcp",
      "strengths": ["precision", "security", "refactoring"],
      "optimalFor": ["API routes", "Database schemas", "Tests"]
    }
  }
}
```

#### 2. `filePatternRules{}` - File-Level Routing
Maps file patterns to preferred models.

```json
{
  "filePatternRules": {
    "*.tsx": {
      "preferredModel": "claude",
      "reason": "UI/UX thinking, component design"
    },
    "**/route.ts": {
      "preferredModel": "codex",
      "reason": "API security, precise validation"
    }
  }
}
```

#### 3. `taskTypeRules{}` - Task-Level Routing
Maps task types to sub-agents and models.

```json
{
  "taskTypeRules": {
    "api-route": {
      "preferredModel": "codex",
      "subAgentType": "api-builder"
    },
    "ui-component": {
      "preferredModel": "claude",
      "subAgentType": "component-builder-nextjs"
    }
  }
}
```

#### 4. `subAgentDefaults{}` - Sub-Agent Behavior
Defines default model and delegation patterns per sub-agent.

```json
{
  "subAgentDefaults": {
    "api-builder": {
      "defaultModel": "codex",
      "implementDirectly": false,
      "zenMcpUsage": "always"
    }
  }
}
```

#### 5. `orchestratorGuidance{}` - Orchestrator Rules
**CRITICAL**: Enforces delegation-first architecture.

```json
{
  "orchestratorGuidance": {
    "alwaysDelegateToSubAgent": true,
    "neverImplementDirectly": true,
    "exceptions": {
      "tinyEdits": { "maxLines": 10 }
    }
  }
}
```

#### 6. `zenMcpIntegration{}` - Zen MCP Usage
How to call Codex/Gemini via Zen MCP server.

```json
{
  "zenMcpIntegration": {
    "enabled": true,
    "availableModels": {
      "codex": {
        "cliName": "codex",
        "tool": "mcp__edison-zen__clink"
      }
    }
  }
}
```

---

## Usage Guide

### For Orchestrator (`.edison/AGENTS.md`)

#### Decision Priority Chain

When selecting model for a task:

1. **Orchestrator explicit instruction** (highest priority)
   - User says "use Codex for this task"

2. **File pattern rules** (`filePatternRules{}`)
   - Task involves `route.ts` → prefer Codex

3. **Task type rules** (`taskTypeRules{}`)
   - Task type is "api-route" → prefer Codex

4. **Sub-agent defaults** (`subAgentDefaults{}`)
   - api-builder defaults to Codex

5. **Sub-agent judgment** (lowest priority, but FINAL authority)
   - Sub-agent overrides based on specific context

#### Orchestrator Template

```typescript
// Read config
const config = readDelegationConfig()

// Match task to rules
const filePattern = matchFilePattern(taskFiles, config.filePatternRules)
const taskType = matchTaskType(taskDescription, config.taskTypeRules)

// Determine suggestion
const suggestedModel = filePattern?.preferredModel || taskType?.preferredModel

// Delegate with suggestion
Task({
  subagent_type: taskType.subAgentType,
  prompt: `
    [Task details]

    SUGGESTED MODEL: ${suggestedModel}
    REASON: ${filePattern?.reason || taskType?.description}

    You have final decision authority - use your judgment.
  `
})
```

### For Sub-Agents (`.edison/agents/*.md`)

#### Reading Config

**FIRST STEP in every sub-agent execution**:

```typescript
// Read delegation config
const config = readDelegationConfig()
const myDefaults = config.subAgentDefaults['api-builder']
const orchestratorSuggestion = extractSuggestion(orchestratorPrompt)
```

#### Decision Making

```typescript
// Factors to consider:
1. Orchestrator suggestion (what they recommended)
2. File patterns (what files I'm working with)
3. Task complexity (simple vs complex)
4. My own capabilities (what I'm good at)
5. Config defaults (what's recommended for my agent type)

// Final decision:
if (shouldDelegateToCodex) {
  // Use Zen MCP
} else if (shouldDelegateToGemini) {
  // Use Zen MCP
} else {
  // Implement directly
}
```

#### Implementation Patterns

**Pattern 1: Full Direct Implementation**

```typescript
// Sub-agent implements all code directly
Edit({ file_path: '...', old_string: '...', new_string: '...' })
Write({ file_path: '...', content: '...' })
```

**Pattern 2: Full Delegation**

```typescript
// Sub-agent delegates all work to Codex
const worktreePath = SessionContext.build_zen_environment(sessionId).ZEN_WORKING_DIR
const result = await mcp__edison-zen__clink({
  cli_name: 'codex',
  role: 'default',
  working_directory: worktreePath,
  prompt: 'Implement API route...',
  absolute_file_paths: ['...']
})

// Verify results
// Report back to orchestrator
```

**Pattern 3: Mixed Implementation**

```typescript
// Sub-agent implements some, delegates some
// 1. Implement validation schema (Claude - good at types)
Write({ file_path: '.../schema.ts', content: '...' })

// 2. Delegate route handler (Codex - API security)
const worktreePath = SessionContext.build_zen_environment(sessionId).ZEN_WORKING_DIR
const routeResult = await mcp__edison-zen__clink({
  cli_name: 'codex',
  working_directory: worktreePath,
  prompt: 'Implement route handler using schema...'
})

// 3. Implement tests (Claude - TDD familiarity)
Write({ file_path: '.../route.test.ts', content: '...' })
```

---

## Examples

See [examples/](./examples/) directory:
- [example-1-ui-component.md](./examples/example-1-ui-component.md) - Direct implementation
- [example-2-api-route.md](./examples/example-2-api-route.md) - Full delegation to Codex
- [example-3-full-stack-feature.md](./examples/example-3-full-stack-feature.md) - Mixed implementation

---

## Troubleshooting

### Issue: Sub-Agent Not Reading Config

**Symptom**: Sub-agent implements directly when should delegate

**Solution**:
1. Check sub-agent file has delegation awareness section
2. Verify config.json is readable
3. Check orchestrator provided suggestion in prompt

### Issue: Wrong Model Selected

**Symptom**: Codex used for UI, Claude used for API

**Solution**:
1. Review filePatternRules and taskTypeRules in config
2. Check orchestrator suggestion in Task prompt
3. Verify sub-agent decision logic

### Issue: Orchestrator Implementing Directly

**Symptom**: Orchestrator uses Edit/Write instead of Task tool

**Solution**:
1. Check if edit is <10 lines (allowed exception)
2. Review `.edison/AGENTS.md` - "DELEGATE MAXIMUM WORK" section
3. Verify orchestratorGuidance.alwaysDelegateToSubAgent: true

---

## Migration Strategy

### Phase 1: Infrastructure (Current)
- ✅ Create config.json
- ✅ Create config.schema.json
- ✅ Create README.md
- ⏳ Create example files

### Phase 2: Orchestrator Awareness
- Update `.edison/AGENTS.md` with delegation guidance
- Update `docs/project/ORCHESTRATION_GUIDE.md` with workflow
- Update `docs/archive/agents/CODEX_DELEGATION_GUIDE.md` with patterns (legacy deep-dive)

### Phase 3: Sub-Agent Delegation
- Update all 6 sub-agent files (`.edison/agents/*.md`)
- Add "Delegation Awareness" sections
- Add Zen MCP usage patterns

### Phase 4: Testing & Optimization
- Test with real tasks
- Measure performance (time, quality)
- Optimize config based on results

---

## Key Principles

1. **Orchestrator Delegates, Doesn't Implement**
   - Exception: <10 line edits only
   - Always use Task tool to call sub-agents

2. **Sub-Agents Have Final Authority**
   - Config suggests, sub-agent decides
   - Can override based on context

3. **Mixed Implementations Are Valid**
   - UI with Claude, backend with Codex = OK
   - File-level granularity

4. **Preserve Claude Code Architecture**
   - Task tool remains entry point
   - Sub-agents remain primary interface
   - Zen MCP is delegation mechanism, not replacement

---

## References

- **Config**: [config.json](./config.json)
- **Schema**: [config.schema.json](./config.schema.json)
- **Examples**: [examples/](./examples/)
- **Orchestrator Guide**: [../../../.edison/AGENTS.md](../../../.edison/AGENTS.md)
- **Codex Delegation**: [../../../docs/archive/agents/CODEX_DELEGATION_GUIDE.md](../../../docs/archive/agents/CODEX_DELEGATION_GUIDE.md)
- **Zen MCP**: Multi-model delegation via `mcp__edison-zen__clink` (ALWAYS pass `working_directory` from `SessionContext.build_zen_environment(sessionId)`)

---

**Version**: 1.0.0
**Last Updated**: 2025-10-29
**Status**: Phase 1 Complete (Infrastructure)
