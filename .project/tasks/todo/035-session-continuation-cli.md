---
id: 035-session-continuation-cli
title: "CLI: Per-session continuation controls (`edison session continuation …`)"
owner: leeroy
created_at: '2025-12-31T10:12:17Z'
updated_at: '2025-12-31T10:12:17Z'
tags:
  - edison-cli
  - session
  - continuation
  - schema
depends_on:
  - 033-continuation-config-rules-session-schema
---
# CLI: Per-session continuation controls (`edison session continuation …`)

<!-- EXTENSIBLE: Summary -->
## Summary

Add a dedicated CLI surface to manage per-session continuation settings (FC/RL mode and budgets) in a schema-valid way.

This avoids inventing new orchestration concepts: we are only setting session metadata that `session next` will consume.

<!-- /EXTENSIBLE: Summary -->

<!-- EXTENSIBLE: ProblemStatement -->
## Problem Statement

We need an explicit, Edison-owned way to enable Ralph Loop (hard continuation) for a specific session, and to disable/tune continuation when needed.

This must:
- be stored in the session record (schema-valid) so all clients see the same mode,
- not overload existing commands like `session status` or `session context`,
- not require manual file edits under `.project/sessions/*` (forbidden by Edison rules).

<!-- /EXTENSIBLE: ProblemStatement -->

<!-- EXTENSIBLE: Objectives -->
## Objectives

- [ ] Add `edison session continuation show <session-id>` (read-only) showing effective mode and budgets (including defaults and overrides).
- [ ] Add `edison session continuation set <session-id> --mode off|soft|hard [budgets…]` to persist overrides into `session.meta.continuation`.
- [ ] Add `edison session continuation clear <session-id>` to remove the override and fall back to project defaults.
- [ ] Validate values against config and schema (e.g., maxIterations >= 1, cooldownSeconds >= 0).
- [ ] Ensure this CLI does not perform state transitions; it only edits session metadata via the repository API.

<!-- /EXTENSIBLE: Objectives -->

<!-- EXTENSIBLE: AcceptanceCriteria -->
## Acceptance Criteria

- [ ] `edison session continuation show <sid>` works in both text and `--json` mode.
- [ ] `set` writes a schema-valid `meta.continuation` object into the session record.
- [ ] `clear` removes session-specific overrides (or sets them to null) and returns to project defaults.
- [ ] Worktree enforcement rules are respected (mutating command must run in session worktree when required by Edison policy).

<!-- /EXTENSIBLE: AcceptanceCriteria -->

<!-- EXTENSIBLE: TechnicalDesign -->
## Technical Design

### Command shape

Prefer a command group under `src/edison/cli/session/continuation/`:
- `src/edison/cli/session/continuation/__init__.py` (group summary)
- `src/edison/cli/session/continuation/show.py`
- `src/edison/cli/session/continuation/set.py`
- `src/edison/cli/session/continuation/clear.py`

Rationale: consistent with other grouped commands (`session track`, `session recovery`, etc.).

### Persistence model

Use `SessionRepository` to load/update/save the session entity:
- Read and write `session.meta.continuation` fields (as defined by schema extension in task `033-*`).
- Do not introduce ad-hoc keys under `meta` because session schema is strict (`additionalProperties: false`).

### Effective config resolution

`show` should display both:
- project defaults from `continuation.*` config, and
- per-session override from session meta (if set),
as well as the merged effective result.

This ensures humans understand what the OpenCode plugin / hooks will do.

<!-- /EXTENSIBLE: TechnicalDesign -->

<!-- EXTENSIBLE: FilesToModify -->
## Files to Create/Modify

```
# Create
src/edison/cli/session/continuation/__init__.py
src/edison/cli/session/continuation/show.py
src/edison/cli/session/continuation/set.py
src/edison/cli/session/continuation/clear.py

# Modify
src/edison/core/session/persistence/repository.py  # only if helper methods needed (prefer not)
src/edison/data/schemas/domain/session.schema.yaml  # already handled by task 033, listed for awareness
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
- Session model: `src/edison/core/session/core/models.py` (meta fields)
- CLI dispatcher (command group support): `src/edison/cli/_dispatcher.py`

<!-- /EXTENSIBLE: RelatedFiles -->

<!-- EXTENSIBLE: Notes -->
## Notes

- This CLI is not a “runner” and must not auto-execute any state transitions; RL/FC is enforced by clients (OpenCode/Claude hooks) based on `session next` output.

<!-- /EXTENSIBLE: Notes -->
