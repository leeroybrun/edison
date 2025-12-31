---
id: 027-qa-bundle-scopes-and-guards
title: "Refactor: QA bundle scopes + decouple validation bundles from hierarchy"
created_at: "2025-12-28T15:47:58Z"
updated_at: "2025-12-28T15:47:58Z"
tags:
  - edison-core
  - qa
  - validation
  - tasks
  - relationships
  - architecture
depends_on:
  - 010-task-relationships-registry
related:
  - 011-task-relationships-mutators
  - 012-task-relationships-consumers
---
# Refactor: QA bundle scopes + decouple validation bundles from hierarchy

## Summary

Introduce an explicit, non-hierarchical way to group tasks for validation by adding **bundle scopes** to QA bundling/validation and making “validation bundles” a first-class concept **separate from parent/child**.

This task implements the end-to-end behavior promised by `.project/plans/plan-2-validation-bundles.md`:
- `bundle_root` relationships define bundle membership
- `edison qa bundle` and `edison qa validate` support `--scope bundle|hierarchy|auto`
- QA/task promotion guards, session verification, and rules checkers are coherent and fail-closed for bundle members

## Wave / Parallelization

- **Wave:** 2 (core workflow refactor)
- **Safe to run in parallel with:** `011-task-relationships-mutators` (as long as the canonical relationship API from `010` is stable)
- **Do not run in parallel with:** `012-task-relationships-consumers` or any other task modifying QA workflow guards/conditions without coordination (to avoid drift)

## Problem Statement

Today Edison’s “bundle validation” behavior is effectively “task hierarchy validation”:
- `edison qa bundle <root>` builds the cluster by walking parent/child descendants.
- Users create “fake parent tasks” to validate a group of peer tasks together.
- Docs claim children can be promoted based on a parent bundle summary, but code paths and guards are inconsistent (some checks are per-task evidence only).

We need to make bundles explicit and decoupled:
- Parent/child = decomposition/follow-up hierarchy
- Bundle = “validate these tasks together”, even if they are peers

## Definitions (Self-contained)

### Bundle scope
Bundle scope controls how a “cluster” is computed for `qa bundle` / `qa validate`:
- `hierarchy`: cluster = root task + all descendants via parent/child
- `bundle`: cluster = root task + all tasks whose `bundle_root == root`
- `auto`: prefer `bundle` when root has any bundle members; else `hierarchy` if root has children; else `single`

### Bundle root
The bundle root is the task that:
- Anchors the cluster selection
- Owns the “bundle summary” evidence artifact for the round (and is the default locus for validator report files)

Bundle root is **not** a “parent task” in the hierarchy sense.

## Objectives

- [ ] Add a centralized “bundle scope resolver + cluster builder” used by all QA bundle/validate call sites.
- [ ] Extend `edison qa bundle` with `--scope` and make it compute clusters using `bundle_root` when requested.
- [ ] Extend `edison qa validate` with `--scope`:
  - in `bundle` scope: compute the **union of required validators across all bundle tasks** and execute them once
  - write an approved/rejected bundle summary that is coherent for bundle members
- [ ] Make QA promotion guards/conditions coherent for bundle members:
  - do not require per-member validator report files when validated as a bundle
  - still fail-closed when evidence/approval is missing or stale
- [ ] Update `session verify` and rules checkers so bundle members are treated correctly (no false failures when validation was performed at bundle root).
- [ ] Add tests (TDD, no mocks) proving bundle scope behavior and guard coherence.

## Acceptance Criteria

### CLI: `edison qa bundle`
- [ ] `edison qa bundle <task> --scope hierarchy` produces the same manifest as today (cluster by parent/child).
- [ ] `edison qa bundle <task> --scope bundle`:
  - resolves the bundle root deterministically:
    - if `<task>` has `bundle_root`, treat `<root> = <task>.bundle_root`
    - else treat `<root> = <task>`
  - includes every task with `bundle_root == <root>` plus `<root>` itself
- [ ] `edison qa bundle <task> --scope auto` selects scope deterministically (as defined above) and reports which scope was chosen.
- [ ] `--json` output includes `scope` and `rootTask` fields.

### CLI: `edison qa validate`
- [ ] `edison qa validate <task> --scope hierarchy --execute` continues to work (existing behavior).
- [ ] `edison qa validate <root> --scope bundle --execute`:
  - computes the union of required validators across all tasks in the bundle cluster
  - executes validators once (root task evidence directory)
  - writes a bundle summary with:
    - `rootTask`, `scope`, `round`, `approved` (overall), `tasks[]`, `validators[]`, `missing[]`
- [ ] When `approved=true`, every task in `tasks[]` can be promoted to `qa/validated` and `tasks/validated` without requiring per-task validator report files.
- [ ] When `approved=false`, promotion fails closed with actionable error messages including missing/failing validators.

### Guards / Conditions / Verification
- [ ] `qa done -> validated` guard logic works for:
  - single-task validation (no bundle)
  - hierarchy bundles
  - bundle_root bundles
- [ ] `session verify --phase closing` does not incorrectly fail bundle members that were validated as part of a bundle.
- [ ] Rule checker `validator-approval` remains correct for bundle members (either by reading member-local bundle summary or by correctly resolving root evidence).

### Tests
- [ ] Tests cover:
  - cluster building for each scope
  - union-validator selection for bundle scope
  - guard acceptance/rejection for bundle members
  - `qa bundle --json` and `qa validate --json` payload contracts

## Technical Design

### A) Centralize scope + cluster building

Create a small, focused service (names are suggestions; keep modules small and cohesive):
- `src/edison/core/qa/bundler/scopes.py`
  - `BundleScope` enum: `AUTO`, `HIERARCHY`, `BUNDLE`
  - parse/normalize from CLI/config
- `src/edison/core/qa/bundler/cluster.py`
  - `build_cluster(root_task: str, scope: BundleScope, *, session_id: str | None, project_root: Path) -> list[str]`
  - uses canonical `TaskIndex`/relationship graph queries
  - **bundle scope membership query**: tasks where relationship `bundle_root` targets the root
  - **hierarchy scope query**: descendants by parent/child
  - returns stable ordering (deterministic)

`src/edison/core/qa/bundler/manifest.py` should become a thin wrapper:
- `build_validation_manifest(root_task, scope=..., ...)` calls `build_cluster(...)` then renders the manifest payload.

### B) QA config (configuration-first)

Add configuration for default scope:
- `validation.bundles.defaultScope: auto|hierarchy|bundle`

CLI default `--scope` uses config if flag omitted.

### C) `edison qa bundle` changes

Update `src/edison/cli/qa/bundle.py`:
- Add `--scope` flag
- Include `scope` in text output and JSON output
- Write a *draft* bundle summary record that includes `scope`

### D) `edison qa validate` changes (bundle-aware execution + summary)

Update `src/edison/cli/qa/validate.py` bundle logic:

1) Cluster: compute `cluster_task_ids = build_cluster(root, scope, ...)`
2) Union roster:
   - For each `task_id` in cluster:
     - compute the task’s required validators via `ValidatorRegistry.build_execution_roster(task_id=task_id, ...)`
   - union all blocking validators + always-required validators across tasks
   - execute with `validators_filter=<union-ids>` on the root task using `ValidationExecutor`
3) Summary computation:
   - Derive `approved` by checking that every validator in the **union blocking set** has an approved report in the root evidence round
   - `missing[]` should list any missing/non-approved blocking validators (union-level)
4) Bundle summary file:
   - Must include `rootTask`, `scope`, `round`, `approved`, `tasks[]` (all cluster tasks), and `validators[]` verdicts for diagnostics.

Important: the current `_compute_bundle_summary` implementation reads validator reports in each task’s evidence dir, which does not work for “validate once for bundle”. This task must refactor the summary computation to use the root’s evidence + union roster.

### E) Guards/conditions must be bundle-aware

Update the QA promotion guard logic so bundle members can be promoted without local validator report files:

- `src/edison/core/state/builtin/guards/qa.py`:
  - `has_bundle_approval`: for a bundle member, check approval from the bundle summary written for that member (or resolve the root summary deterministically)
  - `has_all_waves_passed` and `has_validator_reports`: accept “bundle summary has validators[] and missing[] is empty” as evidence that validator waves ran and passed (fail-closed if data absent)
  - `can_validate_qa`: must succeed for bundle members when bundle summary indicates approval and missing is empty, even if the member has no local validator report files

Also audit any other workflows that assume “validator reports must exist under this task’s evidence dir” and adjust to bundle semantics.

### F) Session lifecycle + rules engine coherence

Update:
- `src/edison/core/session/lifecycle/verify.py` so bundle members don’t fail closing checks when validated via bundle root (depending on whether summaries are mirrored)
- `src/edison/core/rules/checkers.py` (`validator-approval`) so it remains correct for bundle members

Recommended approach (pick one and implement consistently):
1) **Mirror the bundle summary** into each member’s evidence round directory (so existing per-task checks keep working), OR
2) Keep a single root summary and make checkers/verify resolve the root.

The plan (`.project/plans/plan-2-validation-bundles.md`) allows either, but the implementation must choose one and make all checks consistent.

## Files to Create/Modify (Guidance)

```
# Core
src/edison/core/qa/bundler/cluster.py
src/edison/core/qa/bundler/scopes.py
src/edison/core/qa/bundler/manifest.py

# CLI
src/edison/cli/qa/bundle.py
src/edison/cli/qa/validate.py

# Guards / conditions / verification
src/edison/core/state/builtin/guards/qa.py
src/edison/core/state/builtin/conditions/qa.py
src/edison/core/session/lifecycle/verify.py
src/edison/core/rules/checkers.py

# Docs (update wording + examples for new scopes)
src/edison/data/guidelines/shared/VALIDATION.md
src/edison/data/guidelines/validators/VALIDATOR_COMMON.md
src/edison/data/guidelines/validators/EDISON_CLI.md

# Tests
tests/**/*
```

## Notes / References (for implementers)

- Bundle manifest builder: `src/edison/core/qa/bundler/manifest.py`
- QA bundle CLI: `src/edison/cli/qa/bundle.py`
- QA validate CLI: `src/edison/cli/qa/validate.py`
- Validation executor: `src/edison/core/qa/engines/executor.py`
- Guards: `src/edison/core/state/builtin/guards/qa.py`
- Session verify: `src/edison/core/session/lifecycle/verify.py`
- Validation guidelines (update for new bundle scope): `src/edison/data/guidelines/shared/VALIDATION.md`
- Plan: `.project/plans/plan-2-validation-bundles.md`
