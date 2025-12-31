---
id: 025-delegation-role-bootstrap-env-snippets
title: "Core: Add role/bootstrap env snippets to delegation outputs (pal-mcp + validator delegation)"
created_at: "2025-12-28T20:05:00Z"
updated_at: "2025-12-28T20:05:00Z"
tags:
  - edison-core
  - delegation
  - pal-mcp
  - compaction
  - hooks
depends_on:
  - 021-actor-identity-core
  - 023-env-and-process-events-fallback-for-role
---

# Core: Add role/bootstrap env snippets to delegation outputs (pal-mcp + validator delegation)

## Summary

Ensure that whenever Edison generates a delegated “run this as role X” instruction (task delegation or validator delegation), Edison also outputs the **exact env exports** required so the spawned process can self-identify its role and session:

- `AGENTS_SESSION=<session_id>`
- `EDISON_ACTOR_KIND=agent|validator`
- `EDISON_ACTOR_ID=<agentId|validatorId>` (optional, for debug)

This removes “orchestrator must remember to set env vars” as a failure mode.

## Problem Statement

Even with a robust actor identity resolver, delegated flows (e.g. `pal-mcp` “run this validator”) often happen in a new shell/process where:
- hooks may run but actor role is unknown
- env vars are not set
- the LLM/human forgets which constitution to read

Edison already knows the intended role at delegation time, so Edison should emit the bootstrap snippet automatically.

## Objectives

- [ ] Update validator delegation instructions (Pal MCP engine) to include a “Role Context” block with export commands.
- [ ] Update task delegation hints to include a role context block when Edison recommends `pal-mcp call … --role …`.
- [ ] Keep this minimal: do not duplicate constitution text; only set identity + point to constitutions via the existing `edison session context`/`edison session whoami` mechanisms.

## Technical Design

### Validator delegation

Modify:
- `src/edison/core/qa/engines/delegated.py` (`PalMCPEngine._build_delegation_instructions`)

Add to the “Context” section:
- `- **Role Context**: set env vars before executing`

And include a fenced block:
```bash
export AGENTS_SESSION="<session_id>"
export EDISON_ACTOR_KIND="validator"
export EDISON_ACTOR_ID="<validator.id>"
```

Notes:
- Always include `AGENTS_SESSION` (it already exists in the instructions today).
- `EDISON_ACTOR_ID` is optional but recommended for debugging and for future per-validator constitution/prompt routing.

### Task delegation (agent selection)

Modify:
- `src/edison/core/session/delegation.py`

When returning the `action` dict for `delegation.plan`, include either:
- a new field `env`: `{ "AGENTS_SESSION": ..., "EDISON_ACTOR_KIND": "agent", "EDISON_ACTOR_ID": <subagent id> }`, and ensure any consumer that renders the command shows it, OR
- a new field `shellExports`: list of `export ...` lines (keeps consumers simple).

If Edison has a canonical place that renders delegation hints for humans (e.g. `edison session next` output), ensure it prints the exports above the `pal-mcp call …` command.

## Acceptance Criteria

- [ ] Delegated validator instructions include the role bootstrap env exports.
- [ ] Task delegation hints include role bootstrap env exports (or a canonical equivalent field) so they can be surfaced in `edison session next`.
- [ ] No constitution content is duplicated; only identity bootstrapping and references to `edison read … --type constitutions` are present.

## Special Consideration: Claude Code Task Tool Subagents

### Verified Findings from Real-World Testing (2025-12-28)

Live testing in a Claude Code 2.0.76 session confirmed the following:

| Test | Result |
|------|--------|
| Subagents have unique bash PIDs | ✅ Yes (different per subagent) |
| Subagents share same `claude` process | ✅ Yes (all share parent PID 94617) |
| Edison env vars set automatically | ❌ No (`EDISON_*`, `AGENTS_SESSION` not present) |
| `edison session context` works in subagents | ✅ Yes (CLI available and functional) |
| `SubagentStart` hook available | ❌ **No** - Still a feature request ([#14859](https://github.com/anthropics/claude-code/issues/14859)) |
| `SubagentStop` hook available | ✅ Yes (fires after subagent completes) |

### Critical Limitation: No SubagentStart Hook

There is **no way to inject role context into a subagent at launch time via hooks**. The `SubagentStart` hook does not exist (as of Claude Code 2.0.76). Only `SubagentStop` exists, which fires too late for role injection.

**Consequence:** The orchestrator MUST embed role context in the Task tool prompt itself. There is no hook-based alternative for subagents.

### Recommended Compaction-Resistant Prompt Preamble

Since subagent context may compact and hooks cannot inject at start, use this format designed to survive summarization:

```markdown
<!-- EDISON_ACTOR_CONTEXT:START - DO NOT REMOVE -->
## Actor Identity

| Field | Value |
|-------|-------|
| Role | agent |
| Agent ID | feature-implementer |
| Constitution | `.edison/_generated/constitutions/AGENTS.md` |
| Recovery Command | `edison read AGENTS --type constitutions` |
| Session | `<session_id>` (auto-inferred - do not pass to commands) |

**If uncertain after compaction:** Run `edison session whoami` to verify your role.
<!-- EDISON_ACTOR_CONTEXT:END -->
```

**Why this format:**
1. **HTML comments** act as anchors that summarizers tend to preserve
2. **Table format** is more likely to be kept intact than prose
3. **Explicit recovery command** provides fallback if role is lost
4. **"DO NOT REMOVE"** signals importance to compaction summarizers

### Compaction Survival Strategy

Claude Code's compaction uses a summarizer that:
- May lose detailed prose instructions
- Tends to preserve structured data (tables, code blocks)
- Reloads CLAUDE.md on session restart (but NOT in subagent contexts)
- Does NOT fire `SessionStart` hook for subagents (only for main agent)

**Best practices for Edison delegation to subagents:**
1. Keep subagent tasks focused and short (avoid needing compaction)
2. Embed role context prominently at the START of the prompt
3. Use structured format (tables, code blocks) over prose
4. Include explicit recovery instructions

### Process Architecture Confirmed

```
Main Agent
  └── Bash (PID 13015) ─┐
Subagent 1              │
  └── Bash (PID 13279) ─┼── All children of same claude process (PID 94617)
Subagent 2              │
  └── Bash (PID 13386) ─┘
```

All agents share the same `claude` parent process. Only the bash shell PIDs differ.

### Implementation Approaches by Delegation Type

| Delegation Type | Primary Method | Fallback |
|-----------------|----------------|----------|
| Edison PAL MCP (separate process) | Env var exports in delegation output | process-events PID lookup |
| Claude Code Task tool subagent | Prompt preamble (compaction-resistant) | Manual `edison session whoami` |
| Validator delegation | Env var exports + prompt preamble | Same as above |

**Both approaches should be implemented:** env vars for process-based delegation, prompt preamble for in-context delegation.

## Files to Modify

```
src/edison/core/qa/engines/delegated.py
src/edison/core/session/delegation.py
src/edison/core/session/next/output.py (only if needed to render the new fields)
tests/**/*
```

