# Delegation Awareness

<!-- MANDATORY: All agents MUST read this before implementation -->
<!-- Generated from pre-Edison agent content extraction -->

## Purpose

This project uses configuration-driven model selection managed by the orchestrator. Sub-agents must understand their role within this delegation system. Critically, sub-agents NEVER re-delegate to other models - only the orchestrator handles delegation decisions.

## Requirements

### Configuration-Driven Delegation

**Delegation Config**: `.edison/delegation/config.json` (single source of truth for model selection)

The orchestrator uses this configuration to assign tasks to the most appropriate agent based on:
- File patterns being modified
- Task type classification
- Model strengths (Claude for UI, Codex for precision, etc.)

### Your Role as a Sub-Agent

**You are a sub-agent** assigned by the orchestrator. Your workflow is:

1. **READ** `.edison/delegation/config.json` to understand your scope
2. **EXECUTE** if the task matches your role
3. **IF MISMATCH**: Return `MISMATCH` with brief rationale
4. **NEVER re-delegate** from within a sub-agent (orchestrator handles delegation)

### The MISMATCH Pattern

If you receive a task outside your scope, return a MISMATCH:

```markdown
## MISMATCH

**Assigned Task**: Implement lead notes API endpoint
**My Role**: component-builder (UI specialist)
**Issue**: This task requires API route implementation

**Suggested Split**:
- API route (backend endpoint files) → api-builder
- UI components (frontend files) → component-builder (me)

**Rationale**: API-first tasks should be assigned to api-builder for better error handling and test patterns.
```

**CRITICAL**: Do NOT attempt to implement outside your scope. Return MISMATCH and let the orchestrator reassign.

### Why Sub-Agents Never Re-Delegate

```
❌ WRONG: Sub-agent calling another model
───────────────────────────────────────
Orchestrator → component-builder → api-builder (NO!)

✅ CORRECT: Orchestrator handles all delegation
───────────────────────────────────────
Orchestrator → component-builder (UI work)
           └→ api-builder (API work)
```

**Reasons**:
1. **Single responsibility**: Orchestrator owns delegation decisions
2. **Context preservation**: Orchestrator maintains session context
3. **Cost control**: Prevents runaway model calls
4. **Audit trail**: All delegation decisions traceable
5. **Consistency**: Config is applied uniformly

### Agent Scope Reference

| Agent | Scope | File Patterns |
|-------|-------|---------------|
| **api-builder** | API routes, backend logic | File patterns defined in pack configuration |
| **component-builder** | UI components | File patterns defined in pack configuration |
| **database-architect** | Schema, migrations | File patterns defined in pack configuration |
| **test-engineer** | Tests, coverage | File patterns defined in pack configuration |
| **feature-implementer** | Full-stack features | Mixed (coordinates multiple scopes) |
| **code-reviewer** | Review only | All files (review, not implement) |

### Reading the Delegation Config

```pseudocode
// Example: Reading your scope
config = load_json('.edison/delegation/config.json')

// Check file pattern rules
filePatterns = config.filePatternRules
// Example: { '<pattern>': { preferredModel: 'model-name', agent: 'agent-name' } }

// Check task type rules
taskTypes = config.taskTypeRules
// Example: { 'task-type': { preferredModel: 'model-name', agent: 'agent-name' } }

// Check your defaults
myDefaults = config.subAgentDefaults['your-agent-name']
// Example: { defaultModel: 'model-name', implementDirectly: true }
```

### Workflow Decision Tree

```
Receive task from orchestrator
        ↓
Read delegation config
        ↓
Does task match my scope?
    ├── YES → Implement directly
    │         └── Return complete results
    └── NO  → Return MISMATCH
              └── Include suggested split
              └── Orchestrator will reassign
```

### Special Case: code-reviewer

The **code-reviewer** agent is unique:
- **ALWAYS** reviews directly (expert judgment required)
- **NEVER** delegates to other models
- **NEVER** implements fixes (report only)

Code review requires human-like judgment that cannot be delegated.

### Special Case: feature-implementer

The **feature-implementer** agent handles full-stack work:
- Coordinates across multiple scopes
- May implement UI directly
- Returns MISMATCH for pure API or DB work
- Verifies integration after orchestrator reassigns

## Evidence Required

When returning results, include delegation decision:

```json
{
  "delegationDecision": {
    "scope": "component-builder",
    "taskMatched": true,
    "implementedDirectly": true,
    "rationale": "Task involves UI component implementation"
  }
}
```

Or for MISMATCH:

```json
{
  "delegationDecision": {
    "scope": "component-builder",
    "taskMatched": false,
    "mismatch": true,
    "suggestedAgent": "api-builder",
    "rationale": "Task requires API route implementation"
  }
}
```

## CLI Commands

```bash
# View delegation config
cat .edison/delegation/config.json

# Check which agent handles a file pattern (orchestrator tool)
edison delegation check "<path-to-file>"

# View agent scope (orchestrator tool)
edison agents scope api-builder
```

## References

- Delegation guide: `.edison/core/guidelines/DELEGATION.md`
- Extended patterns: `.edison/core/guides/extended/DELEGATION_GUIDE.md`
- Config schema: `.edison/delegation/config.schema.json`

---

**Version**: 1.0 (Extracted from pre-Edison agents)
**Applies to**: ALL agents (implementing and reviewing)
**Critical Rule**: Sub-agents NEVER re-delegate - orchestrator owns delegation
