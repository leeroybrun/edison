---
id: 037-claude-hooks-stop-continuation-cwam
title: "Claude: Stop hook for continuation (FC/RL assist) + CWAM nudges"
owner: leeroy
created_at: '2025-12-31T10:12:19Z'
updated_at: '2025-12-31T10:12:19Z'
tags:
  - claude
  - hooks
  - continuation
  - cwam
depends_on:
  - 033-continuation-config-rules-session-schema
  - 034-session-next-completion-continuation-contract
---
# Claude: Stop hook for continuation (FC/RL assist) + CWAM nudges

<!-- EXTENSIBLE: Summary -->
## Summary

Add Claude Code hook templates/config so that when the assistant stops, Edison can inject:
- a continuation nudge (Forced Continuation) when work remains, and/or
- a CWAM reassurance line around compaction/stop (minimal).

Claude Code lacks a true “idle re-prompt loop”; this task is best-effort via Stop hooks.

<!-- /EXTENSIBLE: Summary -->

<!-- EXTENSIBLE: ProblemStatement -->
## Problem Statement

We want continuation/CWAM to work across clients. Claude Code supports hooks; we should use them as thin adapters that surface Edison state.

Hook environments are constrained (bash, minimal dependencies). We must avoid:
- parsing large JSON with jq requirements,
- duplicating completion logic in shell,
- printing very long `session next` outputs on every stop.

<!-- /EXTENSIBLE: ProblemStatement -->

<!-- EXTENSIBLE: Objectives -->
## Objectives

- [ ] Add a new Stop hook definition (e.g., `stop-continuation`) to `src/edison/data/config/hooks.yaml`.
- [ ] Implement a hook template that retrieves a small Edison continuation payload and prints it only when needed.
- [ ] When the session is incomplete and continuation mode is not `off`, emit the Edison-generated `continuation.prompt`.
- [ ] Add an optional CWAM line at compaction/stop when enabled (rule-based; no hardcoded “1M context” assumptions).

<!-- /EXTENSIBLE: Objectives -->

<!-- EXTENSIBLE: AcceptanceCriteria -->
## Acceptance Criteria

- [ ] Hook is fail-open (never blocks/throws even if Edison is unavailable).
- [ ] When the session is complete, the Stop hook emits nothing (or only a single minimal “complete” line if configured).
- [ ] When incomplete and continuation enabled, the Stop hook emits a compact prompt that points to `edison session next <sid>` and (when present) the next blocking command.
- [ ] CWAM text is sourced from Edison rules/context, not duplicated prose inside the shell template.

<!-- /EXTENSIBLE: AcceptanceCriteria -->

<!-- EXTENSIBLE: TechnicalDesign -->
## Technical Design

### A) Hook definitions

Modify `src/edison/data/config/hooks.yaml`:
- Add a Stop hook, e.g. `stop-continuation`:
  - type: Stop
  - enabled: configurable (recommend enabled=true but minimal output)
  - template: `stop-continuation.sh.template`
  - config: `max_length`, `notify`, etc.

### B) Hook template strategy (no jq dependency)

Preferred approach: add a small text-mode output path in Edison, so the hook can do:
- `edison session next <sid> --completion-only --text` (prints only continuation prompt, empty if not needed)

If the core chooses JSON-only, the hook may use a tiny Python one-liner to extract `continuation.prompt`, but avoid requiring `jq`.

### C) CWAM at compaction

Extend existing compaction reminder template to optionally include a CWAM reassurance line (config-driven).

Do not hardcode provider-specific limits (“1M context”). Keep it generic.

<!-- /EXTENSIBLE: TechnicalDesign -->

<!-- EXTENSIBLE: FilesToModify -->
## Files to Create/Modify

```
# Create
src/edison/data/templates/hooks/stop-continuation.sh.template

# Modify
src/edison/data/config/hooks.yaml
src/edison/data/templates/hooks/compaction-reminder.sh.template
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
- Hook composer: `src/edison/core/adapters/components/hooks.py`
- Session next contract: `src/edison/core/session/next/compute.py`

<!-- /EXTENSIBLE: RelatedFiles -->

<!-- EXTENSIBLE: Notes -->
## Notes

- This task should not attempt a true RL loop in Claude; only inject prompts on Stop events.

<!-- /EXTENSIBLE: Notes -->
