---
id: 005-tampering-protection-module
title: 'Chore: tampering protection module'
created_at: '2025-12-28T10:00:55Z'
updated_at: '2025-12-28T10:00:55Z'
tags:
  - edison-core
  - tampering
  - adapters
  - settings
depends_on:
  - 006-task-group-helper
  - 008-cli-ergonomics-paths-aliases
related:
  - 007-session-auto-merge
---
# Chore: tampering protection module

<!-- EXTENSIBLE: Summary -->
## Summary

Add an optional “tampering protection” module that (1) enables platform-specific LLM settings to deny edits/writes to a protected Edison directory and (2) adds tamper-evident append-only logs + verification checks for unlogged state/evidence changes.

<!-- /EXTENSIBLE: Summary -->

<!-- EXTENSIBLE: Wave -->
## Wave / Parallelization

- **Wave:** 5 (defense-in-depth)
- **Safe to run in parallel with:** none recommended (touches shared infra: adapters, entity transition, evidence service, session verify)
- **Do not run in parallel with:** `007-session-auto-merge` (both may need to modify `src/edison/core/session/lifecycle/verify.py`)

<!-- /EXTENSIBLE: Wave -->

<!-- EXTENSIBLE: ProblemStatement -->
## Problem Statement

We want defense-in-depth against workflow tampering and accidental bypass:
- When enabled, LLM tool settings should prevent direct edits/writes to a protected folder used for Edison-managed “authority” artifacts (tampering evidence, decisions, stamps).
- Even with settings-based restrictions, we also want tamper-evident detection (append-only logs + `session verify` checks) to catch out-of-band modifications.

This must be implemented in a unified way:
- A project config file toggles the feature (`.edison/config/tampering.yaml`).
- Adapters/settings composition is the single source of truth for platform settings generation.
- Platform-specific settings output is implemented in platform adapters, with shared logic in a generalized/base adapter layer.

<!-- /EXTENSIBLE: ProblemStatement -->

<!-- EXTENSIBLE: Objectives -->
## Objectives

<!-- List specific, measurable objectives with checkboxes -->
- [ ] Add project config `.edison/config/tampering.yaml` with `tampering.enabled` and related settings (protected dir, etc.).
- [ ] Add CLI `edison tampering enable|disable|status`:
  - `enable` flips config and triggers settings composition.
  - It must not hand-write platform settings directly; composition pipeline remains canonical.
- [ ] Extend adapters/settings generation:
  - Generalized/base adapter logic determines protected paths and generic “deny rules”.
  - Platform adapters (Claude, etc.) implement concrete settings schemas.
- [ ] Add tamper-evident logging for key Edison events (state transitions + evidence writes) using existing append-only JSONL infrastructure (do not introduce a parallel logging system).
- [ ] Update `edison session verify` to detect “unlogged changes” to protected/stateful artifacts (tamper-evident), rather than relying on ineffective “directory vs state” checks.

<!-- /EXTENSIBLE: Objectives -->

<!-- EXTENSIBLE: AcceptanceCriteria -->
## Acceptance Criteria

<!-- List specific criteria that must be met for task completion -->
- [ ] `tampering.enabled` exists as a merged config value (core default false; project can enable).
- [ ] `edison tampering enable` updates `.edison/config/tampering.yaml` and re-composes settings via adapters.
- [ ] When enabled, composed platform settings deny write/edit access to the configured protected directory.
- [ ] The protected directory path/name is defined once (base/generalized adapter layer), and platform adapters consume it (no duplicated per-platform hardcoding).
- [ ] A single append-only log stream records state transitions and evidence write events (use existing `edison.core.audit.jsonl` / `edison.core.audit.logger` primitives or extend them; do not create a separate ad-hoc file format).
- [ ] `edison session verify` flags “unlogged state/evidence changes” (tamper-evident) with actionable output.
- [ ] Tests cover config toggling, adapter output changes, and verify detection logic.

<!-- /EXTENSIBLE: AcceptanceCriteria -->

<!-- EXTENSIBLE: TechnicalDesign -->
## Technical Design

Constraints:
- Do not implement tampering rules ad-hoc in CLIs. CLIs flip config + invoke the existing composition pipeline.
- Keep base adapter logic generalized; platform adapters only implement serialization/details.
- Append-only logs must be single-source and robust (atomic append, clear schema).

Implementation outline:
1) Config:
   - Create `.edison/config/tampering.yaml` with keys like:
     - `tampering.enabled: false` (core default false; project enables)
     - `tampering.protectedDir: "{PROJECT_MANAGEMENT_DIR}/_protected"` (single canonical default)
     - `tampering.platforms: ["claude", "cursor", "codex", ...]` (optional allowlist; default all supported)
     - `tampering.mode: "deny-write"` (optional future-proofing; default deny Edit/Write and destructive Bash for that folder where supported)

2) CLI:
   - Add a new `edison tampering` domain with `enable/disable/status` commands.
   - `enable` should:
     - write config
     - call the existing settings composition pipeline (e.g. `edison compose settings`)
     - ensure protected folder exists (optional)
   - `disable` should revert only the project toggle (no destructive deletion of the folder by default).

3) Adapter integration:
   - Add a shared, platform-agnostic helper in adapter components (preferred) that exposes:
     - protected path(s) resolved from merged config (exactly one canonical resolver)
     - an abstract representation of “deny rules” (e.g. `{denyPaths: [Path], denyPermissions: [...]}`) that platform-specific composers can render.
   - Integrate by extending existing settings composition where it already exists (e.g. Claude’s `SettingsComposer`):
     - do not hardcode the protected directory name in multiple platform adapters
     - platform adapters should only translate the abstract deny rules into each platform’s schema (Claude settings.json permissions.deny, etc.)

4) Tamper-evident logs + verify:
   - Reuse existing append-only JSONL infrastructure:
     - audit logging: `edison.core.audit.logger.audit_event()` / `edison.core.audit.jsonl.append_jsonl()`
     - process tracking events: `edison.core.tracking.process_events.append_process_event()` (do not duplicate; extend if appropriate)
   - Record events at single canonical hooks:
     - entity transitions: instrument the canonical transition path in `src/edison/core/entity/repository.py:BaseRepository.transition()` (single source)
     - evidence writes: instrument in `src/edison/core/qa/evidence/service.py` write methods (single source)
   - Update `src/edison/core/session/lifecycle/verify.py` to flag:
     - any stateful entity file changes (task/qa/session json/md) that are not paired with a corresponding logged transition event
     - any evidence report modifications not paired with a logged evidence-write event
   - Keep this “tamper-evident” (detect + report) not “tamper-proof”.

<!-- /EXTENSIBLE: TechnicalDesign -->

<!-- EXTENSIBLE: FilesToModify -->
## Files to Create/Modify

<!-- List files that will be changed -->
```
# Create
.edison/config/tampering.yaml
src/edison/cli/tampering/__init__.py
src/edison/cli/tampering/enable.py
src/edison/cli/tampering/disable.py
src/edison/cli/tampering/status.py
src/edison/core/tampering/... (small focused modules)

# Modify
src/edison/core/adapters/platforms/* (platform-specific settings generation)
src/edison/core/adapters/components/settings.py (Claude) + other platform settings composers as needed (avoid monolith; keep per-platform concerns localized)
src/edison/core/session/lifecycle/verify.py
src/edison/core/entity/repository.py (single transition hook point)
src/edison/core/qa/evidence/service.py (single evidence write hook point)
tests/**/*
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

- [ ] `pytest -q` passes
- [ ] `edison tampering enable` creates/updates `.edison/config/tampering.yaml` and changes composed settings output for at least Claude (`.claude/settings.json`)
- [ ] With tampering enabled, platform settings include deny rules for the protected folder
- [ ] A transition performed via CLI results in a logged audit event (single JSONL stream)
- [ ] Manually editing a protected/stateful artifact without the CLI triggers a warning/error in `edison session verify --phase closing`

<!-- /EXTENSIBLE: VerificationChecklist -->

<!-- EXTENSIBLE: SuccessCriteria -->
## Success Criteria

When enabled, Edison makes it meaningfully harder for an LLM to “paper over” missing evidence or state transitions:
- LLM tool settings deny editing/writing the protected folder
- Edison can detect and report unlogged state/evidence mutations in session verification

<!-- /EXTENSIBLE: SuccessCriteria -->

<!-- EXTENSIBLE: RelatedFiles -->
## Related Files

- Settings composer (Claude): `src/edison/core/adapters/components/settings.py`
- Claude core settings config: `src/edison/data/config/settings.yaml`
- Hooks/audit baseline: `src/edison/data/templates/hooks/compaction-reminder.sh.template`, `src/edison/cli/audit/event.py`
- Canonical entity transition point: `src/edison/core/entity/repository.py`
- Evidence single source: `src/edison/core/qa/evidence/service.py`
- Session verify: `src/edison/core/session/lifecycle/verify.py`

<!-- /EXTENSIBLE: RelatedFiles -->

<!-- EXTENSIBLE: Notes -->
## Notes

This module is optional but high-leverage. The “enable” command should be reversible (`disable`) and should never directly hand-edit platform settings files outside the composition system.

<!-- /EXTENSIBLE: Notes -->
