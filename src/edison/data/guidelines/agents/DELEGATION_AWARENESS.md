# Delegation Awareness

<!-- MANDATORY: All agents MUST read this before implementation -->

## Purpose

This project uses configuration-driven model selection managed by the orchestrator. Sub-agents must understand their role within this delegation system. Critically, sub-agents NEVER re-delegate to other models - only the orchestrator handles delegation decisions.

## Requirements

### Configuration-Driven Delegation

**Delegation Roster**: `.edison/_generated/AVAILABLE_AGENTS.md` (single source of truth for agent routing hints and model bindings presented to LLMs)

The orchestrator uses this configuration to assign tasks to the most appropriate agent based on:
- File patterns being modified
- Task type classification
- Model/role preferences defined in the config (do not assume defaults)

### Your Role as a Sub-Agent

**You are a sub-agent** assigned by the orchestrator. Your workflow is:

1. **READ** `.edison/_generated/AVAILABLE_AGENTS.md` to understand the active roster and routing hints
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
// Example: Reading the roster
roster = read_markdown('.edison/_generated/AVAILABLE_AGENTS.md')

// Find your assigned agent entry and its scope hints (as rendered in the roster)
// Then follow the orchestrator's instructions for your slice.
```

### Workflow Decision Tree

```
Receive task from orchestrator
        ↓
Read delegation roster (AVAILABLE_AGENTS)
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
# Show merged delegation config (for humans; do not hardcode paths in prompts)
edison config show delegation --format yaml

# Check which agent handles a file pattern (orchestrator tool)
edison delegation check "<path-to-file>"

# View agent scope (orchestrator tool)
edison agents scope api-builder
```

> **Note**: Delegation config has migrated from JSON to YAML format for consistency with other Edison configuration.

## References

- Delegation guide: `.edison/_generated/guidelines/shared/DELEGATION.md`
- Schema: `.edison/_generated/schemas/config/delegation-config.schema.json`

---

**Version**: 1.0 (Extracted from pre-Edison agents)
**Applies to**: ALL agents (implementing and reviewing)
**Critical Rule**: Sub-agents NEVER re-delegate - orchestrator owns delegation
