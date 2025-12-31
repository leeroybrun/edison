---
id: 040-opencode-plugin-idle-enforcement-truncation
title: "OpenCode plugin: idle-based FC/RL enforcement + CWAM reminders + tool-output truncation"
owner: leeroy
created_at: '2025-12-31T10:12:22Z'
updated_at: '2025-12-31T10:12:22Z'
tags:
  - opencode
  - plugin
  - continuation
  - cwam
depends_on:
  - 034-session-next-completion-continuation-contract
  - 035-session-continuation-cli
  - 039-opencode-adapter-generate-plugin
---
# OpenCode plugin: idle-based FC/RL enforcement + CWAM reminders + tool-output truncation

<!-- EXTENSIBLE: Summary -->
## Summary

Implement the actual behavior inside the generated OpenCode plugin (`.opencode/plugin/edison.ts`):
- **Forced Continuation (FC)**: on OpenCode `session.idle`, if Edison says work remains and mode is `soft`, inject a one-shot continuation prompt.
- **Ralph Loop (RL)**: if mode is `hard`, repeatedly inject continuation prompts on idle with budgets/cooldowns until Edison says complete.
- **CWAM**: add minimal reassurance nudges and protect context by optionally truncating huge tool outputs (config-driven).

<!-- /EXTENSIBLE: Summary -->

<!-- EXTENSIBLE: ProblemStatement -->
## Problem Statement

OpenCode is the only targeted client that can truly implement RL/FC because it provides:
- `session.idle` events and
- an official `session.prompt` injection API.

We want to use this power safely:
- The plugin must be thin: query Edison for truth (`session next`) and inject what Edison tells it.
- Avoid brittle hacks from other plugins (no transcript regex completion markers; no internal message-store mutation).
- Fail-open: plugin should never crash sessions or disrupt tool execution.

<!-- /EXTENSIBLE: ProblemStatement -->

<!-- EXTENSIBLE: Objectives -->
## Objectives

- [ ] Implement `session.idle` handler that:
  - resolves the Edison session id (see design below),
  - calls `edison session next <sid> --json` (or `--completion-only --json`) to fetch `continuation`,
  - injects `continuation.prompt` via OpenCode `context.client.session.prompt()` when needed.
- [ ] Implement RL budgets and throttling:
  - max iterations
  - cooldown between injections
  - stop if Edison reports blocked/no actionable next step (config-driven)
- [ ] Implement CWAM reminders:
  - optionally append a reassurance line when nearing configured thresholds or when output is large
- [ ] Implement optional tool-output truncation in `tool.execute.after`:
  - truncate only when output is huge and/or configured headroom is low
  - preserve headers and include a truncation notice
  - never break tool execution (only modify displayed output text)

<!-- /EXTENSIBLE: Objectives -->

<!-- EXTENSIBLE: AcceptanceCriteria -->
## Acceptance Criteria

- [ ] In OpenCode, when the session goes idle and Edison continuation is enabled + incomplete, a continuation prompt is injected automatically.
- [ ] RL (hard mode) stops when Edison reports complete, or when budgets are exhausted, with a clear toast (if enabled).
- [ ] Tool-output truncation is configurable and does not crash tool execution; output includes a clear “[truncated]” marker.
- [ ] No transcript regex completion markers; completion is exclusively Edison-native (from `session next` contract).
- [ ] No reading/writing OpenCode internal message storage; use official OpenCode APIs only.

<!-- /EXTENSIBLE: AcceptanceCriteria -->

<!-- EXTENSIBLE: TechnicalDesign -->
## Technical Design

### A) Location / source of truth

This code should live in the template created in task `039-*`:
- `src/edison/data/templates/opencode/plugin/edison.ts.template`

and be rendered to:
- `.opencode/plugin/edison.ts`

### B) Edison session id resolution (inside OpenCode plugin)

Preferred resolution order (fail-open):
1) `process.env.AGENTS_SESSION` if present
2) call `edison session context --json --repo-root <repoRoot>` and read `sessionId`
3) call `edison session me --json` and read `current_session` (if the user configured it)
4) if no session id is found: do nothing (optionally toast a hint: “Set current session: edison session me --set <sid>”)

### C) Calling Edison reliably

Use OpenCode’s `context.$` shell API to run commands with deterministic repo root:
- always pass `--repo-root <repoRoot>`
- parse stdout as JSON when using `--json`

The plugin must treat Edison as authoritative and avoid re-implementing completion logic.

### D) RL state (iteration counters)

Do not write iteration counters into Edison session files.

Keep ephemeral per-OpenCode-session state in memory:
- `Map<opencodeSessionId, { iteration, lastInjectedAt, errors… }>`

This is sufficient for MVP; persistence across OpenCode restarts can be added later if needed.

### E) Tool output truncation (CWAM technical behavior)

Implement a conservative truncation strategy:
- Config: `context_window.truncation.maxChars` (and/or a rough tokens estimate)
- Preserve first N header lines, keep a maximum size, append a truncation note.
- Only truncate when:
  - output exceeds `maxChars`, or
  - (if usage/headroom data is available) remaining headroom is below threshold.

Fail-open: if any step fails, do not truncate; return original output.

<!-- /EXTENSIBLE: TechnicalDesign -->

<!-- EXTENSIBLE: FilesToModify -->
## Files to Create/Modify

```
# Modify
src/edison/data/templates/opencode/plugin/edison.ts.template
```

<!-- /EXTENSIBLE: FilesToModify -->

<!-- EXTENSIBLE: TDDEvidence -->
## TDD Evidence

### RED Phase
<!-- Link to failing test output -->
- Test file: 
- Output: 

### GREEN Phase
<!-- Link to passing test output -->
- Output: 

### REFACTOR Phase
<!-- Notes on refactoring performed -->
- Notes: 

<!-- /EXTENSIBLE: TDDEvidence -->

<!-- EXTENSIBLE: VerificationChecklist -->
## Verification Checklist

- [ ] Tests pass locally
- [ ] Linting passes
- [ ] Type checking passes
- [ ] Documentation updated
- [ ] TDD evidence captured

<!-- /EXTENSIBLE: VerificationChecklist -->

<!-- EXTENSIBLE: SuccessCriteria -->
## Success Criteria

<!-- Define what success looks like -->

<!-- /EXTENSIBLE: SuccessCriteria -->

<!-- EXTENSIBLE: RelatedFiles -->
## Related Files

- Plan: `.project/plans/2025-12-31-continuation-ralph-loop-cwam-opencode.md`
- OpenCode adapter/template generation: `src/edison/core/adapters/platforms/opencode.py`
- Edison continuation contract: `src/edison/core/session/next/compute.py`

<!-- /EXTENSIBLE: RelatedFiles -->

<!-- EXTENSIBLE: Notes -->
## Notes

- Keep the plugin thin: it should not embed Edison rules/prose beyond what Edison returns in `continuation.prompt`.
- If OpenCode API changes, treat it as adapter churn; keep core Edison logic stable.

<!-- /EXTENSIBLE: Notes -->
