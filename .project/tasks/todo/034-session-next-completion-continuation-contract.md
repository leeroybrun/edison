---
id: 034-session-next-completion-continuation-contract
title: "Core: `session next` completion + continuation JSON contract (FC/RL backbone)"
owner: leeroy
created_at: '2025-12-31T10:12:17Z'
updated_at: '2025-12-31T10:12:17Z'
tags:
  - edison-core
  - session-next
  - continuation
  - rules
depends_on:
  - 033-continuation-config-rules-session-schema
---
# Core: `session next` completion + continuation JSON contract (FC/RL backbone)

<!-- EXTENSIBLE: Summary -->
## Summary

Extend `edison session next <session-id> --json` to expose a stable, client-consumable contract:
- `completion`: whether the session is complete under Edison policy, and why not
- `continuation`: whether clients should nudge (FC) or loop (RL), and the exact prompt to inject

This is the backbone for Forced Continuation (FC) and Ralph Loop (RL) across clients.

<!-- /EXTENSIBLE: Summary -->

<!-- EXTENSIBLE: ProblemStatement -->
## Problem Statement

We want FC/RL to work across multiple clients without duplicating logic.

The only scalable approach is: **Edison computes completion and next actions**, clients only render/inject.

Today, `session next` produces actions/blockers but does not provide a stable “are we done?” signal nor a standardized continuation prompt payload. Without this, each client would implement its own completion logic (guaranteed drift).

<!-- /EXTENSIBLE: ProblemStatement -->

<!-- EXTENSIBLE: Objectives -->
## Objectives

- [ ] Add a deterministic `completion` object to the `session next --json` payload.
- [ ] Add a deterministic `continuation` object to the `session next --json` payload, derived from config + rules + completion result.
- [ ] Implement configurable completion policies (at least):
  - `parent_validated_children_done` (recommended default)
  - `all_tasks_validated` (strict)
- [ ] Ensure human-readable `session next` output includes a small “Completion/Continuation” summary (configurable; no spam).
- [ ] (Optional but recommended) Add a `--completion-only` flag for `edison session next` so hooks/plugins can query cheaply without printing full plans.

<!-- /EXTENSIBLE: Objectives -->

<!-- EXTENSIBLE: AcceptanceCriteria -->
## Acceptance Criteria

- [ ] `edison session next <sid> --json` includes `completion` and `continuation` top-level keys with stable structure.
- [ ] `completion.isComplete` is true only when the chosen policy conditions are satisfied and there are no blockers/reportsMissing.
- [ ] `completion.reasonsIncomplete` is non-empty and actionable when incomplete.
- [ ] `continuation.prompt` is short, deterministic, and points to the loop driver and next blocking action when available.
- [ ] Output remains fail-open: if completion computation errors, `session next` still returns actions and sets a conservative incomplete state with a reason.

<!-- /EXTENSIBLE: AcceptanceCriteria -->

<!-- EXTENSIBLE: TechnicalDesign -->
## Technical Design

### A) Where to implement

Primary:
- `src/edison/core/session/next/compute.py` (build JSON payload)

Rendering:
- `src/edison/core/session/next/output.py` (human output)

Config:
- read from the new config domains introduced in task `033-*` (`continuation.*` and rules via RulesEngine).

### B) Completion policy algorithm (read-only)

Inputs already available in `compute_next`:
- session tasks via `TaskRepository.find_by_session(session_id)`
- task/QA status inference helpers (`infer_task_status`, `infer_qa_status`)
- computed blockers and missing reports (`blockers`, `reportsMissing`)

Policy `parent_validated_children_done` (default):
- Determine task graph roots in *session scope*:
  - root = task has no `parentId` in session scope
- Completion requires:
  - every root task state is `validated`
  - every non-root task state is `done` or `validated`
  - no `blockers`
  - no `reportsMissing`

Policy `all_tasks_validated`:
- Completion requires all session tasks are `validated` + no blockers/reportsMissing.

Do not mutate anything. Do not call existing `session verify` logic because it currently mutates (restores records and transitions session state).

### C) Continuation payload derivation

Compute `continuation.mode` by merging:
- project default `continuation.defaultMode`
- per-session override (`session.meta.continuation.mode`)
- per-platform override (client may pass platform identifier via flag later if needed)

Compute `continuation.shouldContinue`:
- true if `mode != off` and `completion.isComplete == false`

Compute `continuation.prompt`:
- Compose from config template + dynamic values:
  - session id
  - loop driver command
  - next blocking action command (if any)
  - one CWAM line if enabled (pull from rules context `context_window`)

### D) Optional `--completion-only` flag

Add a CLI flag that returns only:
- `sessionId`
- `completion`
- `continuation`

This enables:
- Claude hooks (bash) to call a small payload
- OpenCode plugin to poll quickly

<!-- /EXTENSIBLE: TechnicalDesign -->

<!-- EXTENSIBLE: FilesToModify -->
## Files to Create/Modify

```
# Modify
src/edison/core/session/next/compute.py
src/edison/core/session/next/output.py
src/edison/cli/session/next.py
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
- Session context refresher: `src/edison/core/session/context_payload.py`
- Workflow semantics: `src/edison/data/config/workflow.yaml` (task/qa/session states and validation lifecycle)

<!-- /EXTENSIBLE: RelatedFiles -->

<!-- EXTENSIBLE: Notes -->
## Notes

- Guardrail: do not add new “runner” commands; continuation must be expressed as `session next` payload + thin client adapters.
- Completion policy must be configurable; do not hardcode “all tasks validated” vs “parent validated; children done”.

<!-- /EXTENSIBLE: Notes -->
