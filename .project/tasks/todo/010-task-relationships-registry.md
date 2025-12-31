---
id: 010-task-relationships-registry
title: "Refactor: unified task relationship registry + canonical on-disk format (incl. bundles)"
created_at: "2025-12-28T19:05:00Z"
updated_at: "2025-12-28T15:47:58Z"
tags:
  - edison-core
  - tasks
  - architecture
  - refactor
---
# Refactor: unified task relationship registry + canonical on-disk format (incl. bundles)

## Summary

Replace today’s fragmented task relationship fields (`parent_id`, `child_ids`, `depends_on`, `blocks_tasks`, `related`) with a single canonical relationship model + registry, and move the on-disk frontmatter to a unified `relationships:` list format.

This refactor also introduces a **new, explicitly separate** relationship type for validation grouping:
- `bundle_root` (directed): membership in a validation bundle rooted at another task (see `.project/plans/plan-2-validation-bundles.md`).

This refactor must preserve existing semantics:
- Hierarchy is **single-parent** (tree), enforced fail-closed.
- `depends_on` and `blocks` are symmetric inverses (if A depends_on B ⇒ B blocks A).
- `related` is symmetric and **non-blocking** (planning/grouping only).
- `bundle_root` is **directed** and **non-blocking** (validation grouping only; not planning/readiness).
- Claiming a task is blocked when its dependency prerequisites aren’t satisfied.
- `edison task plan` waves still work; within-wave grouping should continue to prefer related clusters.

## Wave / Parallelization

- **Wave:** 1 (foundation)
- **Safe to run in parallel with:** none (this defines the new API and on-disk format)
- **Do not run in parallel with:** any task changing `TaskRepository` serialization/parsing or `TaskIndex` graph semantics

## Problem Statement

Task relationships are currently represented and mutated in multiple ways:
- Parent/child is duplicated (`parent_id` on child + `child_ids` on parent), and updated by multiple call sites.
- Dependencies are stored as `depends_on`, but blockers are separately stored as `blocks_tasks` with no enforced inversion.
- `related` was added as yet another relationship axis.
- Readiness/claim planning consumes different fields in different modules, increasing drift risk.

This is now a correctness and maintenance risk as Edison grows.

## Objectives

- [ ] Introduce a **single canonical relationship abstraction** and registry.
- [ ] Define a canonical on-disk task frontmatter representation using a single `relationships:` list.
- [ ] Implement deterministic normalization and invariants in one place:
  - no self-edges
  - dedupe
  - stable ordering
  - symmetry/inverse enforcement for the relevant types
  - single-parent enforcement (fail-closed)
- [ ] Update core task load/save + indexing to use the canonical relationship model (without changing behavior yet).
- [ ] Keep the CLI default outputs **human-readable**; `--json` remains optional.

## Canonical Relationship Format (On-Disk)

Task frontmatter must converge to:

```yaml
relationships:
  - type: parent
    target: "001-foo"
  - type: child
    target: "002-bar"
  - type: depends_on
    target: "003-baz"
  - type: blocks
    target: "004-qux"
  - type: related
    target: "005-quux"
  - type: bundle_root
    target: "006-bundle-root-task"
```

Notes:
- Explicit `parent` and `child` edges are allowed, but the system must keep them consistent.
- Multiple parents are forbidden (single-parent tree).
- `bundle_root` is a single-target relationship: at most one `bundle_root` per task (fail-closed unless forced by a mutator CLI with an explicit override flag).

## Technical Design

### A) New relationship framework (generic + task bindings)

Create a focused package (avoid monoliths). Prefer a small **generic** core that can later be reused for QA, plus a task-domain binding:

- `edison/core/relationships/*` (generic primitives):
  - edge models, normalization utilities, and a registry/handler protocol
- `edison/core/task/relationships/*` (task-specific):
  - `RelationshipType` enum: `PARENT`, `CHILD`, `DEPENDS_ON`, `BLOCKS`, `RELATED`
  - task-specific handlers enforcing the invariants below

Concrete file layout suggestion (you may tweak, but keep it modular):
- `edison/core/relationships/models.py`
- `edison/core/relationships/registry.py`
- `edison/core/task/relationships/types.py`:
  - `RelationshipType` enum: `PARENT`, `CHILD`, `DEPENDS_ON`, `BLOCKS`, `RELATED`, `BUNDLE_ROOT`
- `edison/core/task/relationships/models.py`:
  - `RelationshipEdge(type, target)`
  - parsing/normalization helpers
- `edison/core/task/relationships/handlers/*`:
  - one handler per type (or per family, e.g. `parent_child`, `depends_blocks`, `related`)
  - each handler encodes:
    - directed/symmetric behavior
    - inverse mapping
    - how to validate/mutate
- `edison/core/task/relationships/registry.py`:
  - `RelationshipRegistry` with a unified API:
    - `add_relationship(type, a, b, ...)`
    - `remove_relationship(type, a, b, ...)`
    - `normalize(task)` / `normalize_pair(a,b)` etc
  - registry calls into handlers; all invariants enforced centrally.
- `edison/core/task/relationships/service.py`:
  - `TaskRelationshipService` that loads tasks via `TaskRepository`, calls registry to compute the required cross-task mutations, and saves both tasks safely.

### B) Task model changes

Update `src/edison/core/task/models.py`:
- Add a canonical `relationships: list[RelationshipEdge]` field to `Task`.
- `Task.to_dict()`/`from_dict()` should include the canonical relationships form.

### C) Persistence + indexing

Update:
- `src/edison/core/task/repository.py`
- `src/edison/core/task/index.py`

Rules:
- Read/write must treat `relationships` as the single canonical representation.
- **Do not** keep writing legacy fields (`parent_id`, `child_ids`, `depends_on`, `blocks_tasks`, `related`) once this task is complete.
- If you need transitional parsing for existing files, implement it **inside a single codec** (e.g., `TaskRelationshipCodec`) and keep it behind a short-lived compatibility layer that can be removed in the later cleanup task.

### D) Tests (TDD)

Add unit tests proving:
- normalization determinism (stable ordering, dedupe)
- symmetry/inverse enforcement:
  - adding `depends_on` creates inverse `blocks` on the target
  - adding `related` enforces symmetric edges
  - adding `parent`/`child` stays consistent and blocks multiple parents
- `bundle_root` invariants:
  - a task has at most one bundle_root edge
  - add/remove behaves deterministically and does not touch other relationship families
- parsing:
  - a task file with legacy fields can be decoded into canonical relationships (if compatibility layer exists)
  - canonical relationships serialize back correctly

## Acceptance Criteria

- [ ] Canonical relationship registry and service exist and are used by persistence/index code.
- [ ] Task frontmatter supports the canonical `relationships:` list and can be round-tripped deterministically.
- [ ] Single-parent is enforced fail-closed at the relationship layer.
- [ ] Inverse/symmetric invariants are enforced in exactly one place (no scattered “also update other side” logic).
- [ ] No new relationship logic is duplicated in call sites; all future mutations must go through `TaskRelationshipService`.
- [ ] TDD: tests cover relationship invariants and canonical serialization/parsing.

## Out of Scope (for this task)

- Refactoring all CLIs/workflows/consumers to use the new registry (done in follow-up tasks).
- Migrating the repo’s existing `.project/**` task files (done in a follow-up task).
