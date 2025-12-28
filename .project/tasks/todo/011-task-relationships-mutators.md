---
id: 011-task-relationships-mutators
title: "Refactor: route all task relationship mutations through registry/service"
created_at: "2025-12-28T19:05:10Z"
updated_at: "2025-12-28T19:05:10Z"
tags:
  - edison-core
  - tasks
  - cli
  - refactor
depends_on:
  - 010-task-relationships-registry
---
# Refactor: route all task relationship mutations through registry/service

## Summary

Update all Edison code paths that **create/modify** task relationships to call the unified relationship service/registry instead of directly editing relationship fields.

This task must preserve existing UX and semantics, while ensuring invariants are centrally enforced.

## Wave / Parallelization

- **Wave:** 2 (refactor call sites)
- **Safe to run in parallel with:** `012-task-relationships-consumers` (different modules; coordinate only if relationship registry API needs changes)
- **Do not run in parallel with:** `010-task-relationships-registry` (must be stable first)

## In Scope Call Sites

Update these to use `TaskRelationshipService` / registry APIs:
- `edison task link ...` (parent/child)
- `edison task split ...` (creates subtasks; parent/child)
- `edison task new --parent ...` (parent/child)
- `edison task relate ...` (related)
- `TaskQAWorkflow.create_task(... parent_id=...)` (parent/child)

Notes:
- “Add relationship” should be a single call (e.g. `add_relationship("parent", parent, child)`), with the registry enforcing symmetry.
- No call site should need to manually “also update the other side”.

## Design Constraints

- DRY/SOLID: relationship invariants enforced in one place only.
- Preserve current guard behavior (e.g. cycle checks at completion, dependency checks at claim).
- CLI default output remains non-JSON; `--json` remains optional.

## Acceptance Criteria

- [ ] No production code directly mutates relationship lists/fields outside `TaskRelationshipService`.
- [ ] `edison task link`/`split`/`relate` behave the same from a user POV (except they now operate on canonical relationships).
- [ ] Adding/removing a relationship enforces the correct symmetric/inverse edges.
- [ ] Tests exist for each mutator command demonstrating it persists relationships correctly.

