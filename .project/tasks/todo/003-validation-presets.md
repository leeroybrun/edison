---
id: 003-validation-presets
title: 'Chore: validation presets'
created_at: '2025-12-28T10:00:54Z'
updated_at: '2025-12-28T10:00:54Z'
tags:
  - edison-core
  - validation
  - presets
  - config
depends_on:
  - 001-session-id-inference
related:
  - 004-stale-sessions-resumable
---
# Chore: validation presets

<!-- EXTENSIBLE: Summary -->
## Summary

Introduce config-driven, pack-extensible validation presets (including a `quick` preset) without duplicating logic across call sites. Presets must drive validator selection and evidence requirements consistently and be wave-name-agnostic in docs.

<!-- /EXTENSIBLE: Summary -->

<!-- EXTENSIBLE: Wave -->
## Wave / Parallelization

- **Wave:** 2 (core policy)
- **Safe to run in parallel with:** `004-stale-sessions-resumable` (touches different modules)
- **Do not run in parallel with:** tasks modifying `src/edison/data/guidelines/shared/VALIDATION.md` or `docs/WORKFLOWS.md` (this task updates validation docs)

<!-- /EXTENSIBLE: Wave -->

<!-- EXTENSIBLE: ProblemStatement -->
## Problem Statement

Beta feedback showed validation/evidence overhead is too heavy for docs/config-only tasks:
- too many always-run validators
- required automation evidence files even when not meaningful
- unnecessary workflow friction for trivial changes

We need a flexible policy system that:
- allows projects/packs to define any number of presets
- selects presets deterministically (file-context inference; no easy bypass)
- applies preset decisions uniformly (rosters, evidence requirements, guards, session-next UX)
- keeps validation guidance wave-name-agnostic (do not hardcode wave names in docs)

<!-- /EXTENSIBLE: ProblemStatement -->

<!-- EXTENSIBLE: Objectives -->
## Objectives

- [ ] Add `validation.presets` config (merged core → packs → project) supporting arbitrary preset definitions.
- [ ] Implement a single core “validation policy resolver” to compute effective preset and requirements (no duplicated logic).
- [ ] Implement default `quick` preset:
  - validators: **only** `global-codex`
  - required evidence: **Option A** (implementation report only; no automation `command-*.txt` required)
- [ ] Ensure deterministic preset inference from changed files (FileContextService).
- [ ] Wire policy into validator roster building and evidence requirement checks (guards + session-next).
- [ ] Update validation docs/guidelines to be wave-name-agnostic and policy-driven.

<!-- /EXTENSIBLE: Objectives -->

<!-- EXTENSIBLE: AcceptanceCriteria -->
## Acceptance Criteria

- [ ] A project/pack can define new presets in config without code changes beyond the single policy resolver.
- [ ] There is exactly one canonical place where preset selection and requirements are computed (core policy module).
- [ ] For a docs-only task, preset inference selects `quick` (configurable by patterns), and:
  - `edison qa validate <task> --dry-run` shows only `global-codex` as blocking
  - task/qa guards do not require automation evidence files for promotion under `quick`
  - implementation report is still required for the round
- [ ] For a code-touching task, inference escalates above `quick` (cannot accidentally downgrade).
- [ ] Docs are wave-name-agnostic: guidance describes “waves as configured” and “blocking per validator metadata,” not special wave names.
- [ ] Missing evidence / missing report errors and blockers are actionable:
  - include the exact expected evidence directory (repo-relative when possible)
  - include the canonical fix command(s) (prefer `edison session track start --type implementation --task <id>` for missing implementation report; `edison qa validate <id> --execute` for missing validator reports)
- [ ] Unit tests cover preset inference and enforcement (escalation rules, required evidence behavior).

<!-- /EXTENSIBLE: AcceptanceCriteria -->

<!-- EXTENSIBLE: TechnicalDesign -->
## Technical Design

Hard constraints (DRY / no competing implementations):
- Preset selection + requirements must be computed in exactly one place (new policy module).
- Validator roster building remains centralized in `ValidatorRegistry.build_execution_roster()`; it calls the policy module and does not re-implement preset logic.
- Evidence/guard checks must consult the same policy module (no separate “preset checks” in guards vs session-next).
- Config merging must use existing Edison overlay logic (core → packs → user → project).
- Guidance must be wave-name-agnostic: do not introduce prose that assumes special wave names like “global/critical”.

Suggested data flow (single truth):
`FileContextService` → `ValidationPolicyResolver` → (a) roster filtering in `ValidatorRegistry` (b) required evidence patterns used by guards/session-next.

Preset inference:
- Deterministic mapping based on changed file paths (glob buckets configured in `validation.presetInference`).
- Safety: if any “code” bucket matches, inferred preset must be ≥ `standard`.

Default presets shipped by Edison core:
- `quick`: only `global-codex` required; required automation evidence = none; implementation report still required.
- `standard`: maps to current behavior.

Current Edison implementation touchpoints to keep aligned (for implementers):
- Required automation evidence is currently global and fail-closed via `QAConfig.get_required_evidence_files()` reading `src/edison/data/config/qa.yaml` (`validation.evidence.requiredFiles`). `missing_evidence_blockers()` uses that list unconditionally. For presets to work, “required evidence” must become policy-driven and may be empty for `quick` while remaining fail-closed for `standard`.
- QA guards currently call `missing_evidence_blockers()` and will hard-fail promotion when required evidence is missing (`src/edison/core/state/builtin/guards/qa.py:has_validator_reports`). This must be made preset-aware via the single policy resolver.
- Validators are configured in `src/edison/data/config/validators.yaml` under `validation.validators.*` and currently many are `always_run: true` (including security/performance). For `quick`, policy must be able to produce a roster containing only `global-codex` without relying on every validator’s `always_run` field.

<!-- /EXTENSIBLE: TechnicalDesign -->

<!-- EXTENSIBLE: FilesToModify -->
## Files to Create/Modify

<!-- List files that will be changed -->
```
# Create
src/edison/core/qa/policy/__init__.py
src/edison/core/qa/policy/models.py
src/edison/core/qa/policy/config.py
src/edison/core/qa/policy/inference.py
src/edison/core/qa/policy/resolver.py

# Modify (one canonical place for config; choose it and keep DRY)
src/edison/data/config/qa.yaml (or src/edison/data/config/validators.yaml)
src/edison/core/registries/validators.py
src/edison/core/qa/evidence/analysis.py
src/edison/core/state/builtin/guards/task.py
src/edison/core/state/builtin/guards/qa.py (if required evidence is enforced here)
src/edison/core/session/next/actions.py
src/edison/data/guidelines/shared/VALIDATION.md

# Tests
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
- [ ] Docs-only tasks infer `quick` and roster shows only `global-codex`
- [ ] Under `quick`, guards do not require `command-type-check.txt`, `command-lint.txt`, `command-test.txt`, `command-build.txt`
- [ ] Under `quick`, implementation report is still required
- [ ] Docs are wave-name-agnostic and accurate

<!-- /EXTENSIBLE: VerificationChecklist -->

<!-- EXTENSIBLE: SuccessCriteria -->
## Success Criteria

Validation friction for trivial work is dramatically reduced without opening bypass vectors:
- trivial/docs/config-only tasks run a single global validator and require only an implementation report
- code changes still trigger stronger validation automatically

<!-- /EXTENSIBLE: SuccessCriteria -->

<!-- EXTENSIBLE: RelatedFiles -->
## Related Files

- Validators config: `src/edison/data/config/validators.yaml`
- Evidence requirements config: `src/edison/data/config/qa.yaml`
- Canonical roster builder: `src/edison/core/registries/validators.py`
- File change detection: `src/edison/core/context/files.py`
- Evidence + missing evidence: `src/edison/core/qa/evidence/analysis.py`
- Validation guidance: `src/edison/data/guidelines/shared/VALIDATION.md`

<!-- /EXTENSIBLE: RelatedFiles -->

<!-- EXTENSIBLE: Notes -->
## Notes

This task must also update “fail-closed” assumptions around required automation evidence so that presets can legally require none (while still requiring an implementation report).

<!-- /EXTENSIBLE: Notes -->
