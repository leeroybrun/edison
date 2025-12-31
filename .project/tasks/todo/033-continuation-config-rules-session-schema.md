---
id: 033-continuation-config-rules-session-schema
title: "Core: Continuation + CWAM config, rules, and session schema extension"
owner: leeroy
created_at: '2025-12-31T10:12:16Z'
updated_at: '2025-12-31T10:12:16Z'
tags:
  - edison-core
  - rules
  - config
  - schema
depends_on: []
---
# Core: Continuation + CWAM config, rules, and session schema extension

<!-- EXTENSIBLE: Summary -->
## Summary

This task adds the **foundations** for three Edison-wide features:

- **Forced Continuation (FC)** and **Ralph Loop (RL)** as an Edison-native continuation system
- **Context Window Anxiety Management (CWAM)** as Edison rules + config (single-source prose, config-driven knobs)
- **Session schema support** so per-session continuation mode can be stored in `session.meta` (schema-valid; no ad-hoc fields)

Context: See the plan `.project/plans/2025-12-31-continuation-ralph-loop-cwam-opencode.md`.

<!-- /EXTENSIBLE: Summary -->

<!-- EXTENSIBLE: ProblemStatement -->
## Problem Statement

We want to implement “keep going / don’t stop early” behaviors across multiple clients (Codex CLI, Pal, Claude hooks, OpenCode).

To keep Edison coherent and avoid “kitchen sink” duplication, these behaviors must be:
- Authored once (rules + config), not copied into multiple prompts/templates by hand.
- Driven by existing Edison primitives (`session next`, `session context`, rules engine, adapter architecture).
- Persisted per session (so RL can be opt-in), without breaking session schema validation (session schema is strict).

Without this foundation, downstream tasks would either:
- hardcode thresholds/prompts in multiple places (drift), or
- store settings in ad-hoc session metadata fields (schema-invalid), or
- introduce new “status/runner/context” commands that duplicate existing Edison concepts.

<!-- /EXTENSIBLE: ProblemStatement -->

<!-- EXTENSIBLE: Objectives -->
## Objectives

- [ ] Add **new config domains** (core defaults) for `continuation` and `context_window` (CWAM), designed for composability (core → packs → project overlays).
- [ ] Add **Edison rules** for CWAM and continuation guidance (single source of prose; surfaced by clients and `session next`).
- [ ] Extend **session schema** so per-session continuation settings can live in `session.meta.continuation` without violating `additionalProperties: false`.
- [ ] Update `session.template.json` to include a safe default for `meta.continuation` (or ensure defaults are optional and safe when omitted).
- [ ] Document guardrails in-code/config comments so implementers don’t accidentally duplicate Edison commands or add hardcoded behavior.

<!-- /EXTENSIBLE: Objectives -->

<!-- EXTENSIBLE: AcceptanceCriteria -->
## Acceptance Criteria

- [ ] Config loads successfully with the new domains present (no required hardcoded knobs; defaults are safe).
- [ ] Rules registry includes CWAM + continuation rules with clear contexts (so they can be fetched by `RulesEngine.get_rules_for_context` and/or CLI rule display).
- [ ] `src/edison/data/schemas/domain/session.schema.yaml` validates sessions that include `meta.continuation` (and still rejects unknown fields under `meta`).
- [ ] Existing sessions without `meta.continuation` remain valid (field optional).
- [ ] All changes are configuration-first (no hardcoded thresholds in code).

<!-- /EXTENSIBLE: AcceptanceCriteria -->

<!-- EXTENSIBLE: TechnicalDesign -->
## Technical Design

### A) Config domains (core defaults)

Add two new config files under `src/edison/data/config/`:

1) `continuation.yaml`
   - `continuation.enabled: bool`
   - `continuation.defaultMode: off|soft|hard` (recommended default: `soft`)
   - `continuation.budgets`: max iterations, cooldown, stop-on-blocked, etc.
   - `continuation.completionPolicy`: `parent_validated_children_done` (default) vs `all_tasks_validated`
   - `continuation.templates`: text templates for the injected prompt (short, deterministic, no bloat)
   - `continuation.platformOverrides`: allow overriding modes/budgets per platform (claude/pal/codex/opencode)

2) `context_window.yaml` (CWAM)
   - `context_window.enabled: bool`
   - `context_window.reminders.enabled: bool`
   - `context_window.reminders.thresholds`: configurable thresholds (if any; OpenCode plugin can use)
   - `context_window.truncation`: settings for tool output truncation (OpenCode only; other clients may only show guidance)

Important: these are defaults only; packs/projects must be able to override.

### B) Rules (single-source prose)

Add rules in `src/edison/data/rules/registry.yml`:

- `RULE.CONTEXT.CWAM_REASSURANCE`
  - category: context
  - contexts: include a dedicated context type (recommended: `context_window`)
  - guidance: a very short, non-verbose reassurance + behavior constraint (do not rush, continue methodically)

- `RULE.CONTINUATION.NO_IDLE_UNTIL_COMPLETE`
  - category: session
  - contexts: include a dedicated context type (recommended: `continuation`)
  - guidance: the behavioral rule for FC/RL, pointing at the loop driver (`edison session next <session-id>`)

Do not embed client-specific or OpenCode-specific details in the rule prose.

### C) Session schema extension

Extend `src/edison/data/schemas/domain/session.schema.yaml`:
- Under `meta.properties`, add a `continuation` property:
  - `type: object`
  - `additionalProperties: false`
  - `properties` include: `mode`, `maxIterations`, `cooldownSeconds`, `stopOnBlocked`, `enabled` (optional)
  - All properties optional (so existing sessions remain valid).

Update `src/edison/data/templates/session.template.json`:
- Either include a minimal `meta.continuation` default (preferred: `{ "mode": "soft" }`), or omit and rely on defaults elsewhere.

Design constraint:
- We store **desired settings** in the session, not runtime counters/iteration state. Clients can keep ephemeral counters.

<!-- /EXTENSIBLE: TechnicalDesign -->

<!-- EXTENSIBLE: FilesToModify -->
## Files to Create/Modify

```
# Create
src/edison/data/config/continuation.yaml
src/edison/data/config/context_window.yaml

# Modify
src/edison/data/rules/registry.yml
src/edison/data/schemas/domain/session.schema.yaml
src/edison/data/templates/session.template.json
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
- Existing orchestration primitive: `src/edison/core/session/next/compute.py`
- Existing hook-safe context refresher: `src/edison/core/session/context_payload.py`
- Rules engine: `src/edison/core/rules/engine.py`

<!-- /EXTENSIBLE: RelatedFiles -->

<!-- EXTENSIBLE: Notes -->
## Notes

- Guardrail: do **not** create new “status/context/runner” commands for this; the backbone is `session next` + rules + config.
- Inspiration-only: oh-my-opencode concepts (forced continuation, Ralph loop, CWAM) are to be re-derived in Edison-native form; do not copy code.

<!-- /EXTENSIBLE: Notes -->
