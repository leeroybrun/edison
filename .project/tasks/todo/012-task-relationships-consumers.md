---
id: 012-task-relationships-consumers
title: "Refactor: update readiness/planning/session-next to use canonical relationships"
created_at: "2025-12-28T19:05:20Z"
updated_at: "2025-12-28T15:47:58Z"
tags:
  - edison-core
  - tasks
  - planning
  - session-next
  - refactor
depends_on:
  - 010-task-relationships-registry
related:
  - 011-task-relationships-mutators
  - 027-qa-bundle-scopes-and-guards
---
# Refactor: update readiness/planning/session-next to use canonical relationships

## Summary

Update all Edison logic that **reads** task relationships (readiness, claim gating, planning waves, session-next context) to use the canonical relationships graph, not legacy fields.

## Wave / Parallelization

- **Wave:** 2 (refactor consumers)
- **Safe to run in parallel with:** `011-task-relationships-mutators` (different modules; coordinate only if registry API needs changes)
- **Do not run in parallel with:** `010-task-relationships-registry` (must be stable first)

## In Scope Consumers

- `TaskReadinessEvaluator` (dependency satisfaction)
- `dependencies_satisfied` state-machine condition (claim enforcement)
- `TaskPlanner` (wave planning + within-wave related grouping)
- `session next` “related tasks in session” computation/output
- Any other direct reads of `parent_id`, `child_ids`, `depends_on`, `blocks_tasks`, `related`

## Out of Scope (explicit)

- Bundle scope semantics for QA bundling/validation (`--scope bundle|hierarchy|auto`) and bundle-root clusters are implemented in `027-qa-bundle-scopes-and-guards`.

## Required Behavior (must remain true)

- Readiness semantics stay the same: a todo task is ready when all prerequisites are in configured satisfied states (`tasks.readiness.dependencySatisfiedStates`).
- Claim semantics stay fail-closed: claiming is blocked if prerequisites are not satisfied.
- `edison task plan` still returns topological waves based on dependency prerequisites.
- Within-wave ordering continues to prefer related clusters (non-blocking).

## Acceptance Criteria

- [ ] No consumer reads legacy relationship fields directly; all relationship reads go through one graph/query surface.
- [ ] `edison task ready`, `edison task blocked`, claim gating, and `edison task plan` behave as before.
- [ ] Tests cover readiness, blocked reporting, planning waves, and related grouping.
