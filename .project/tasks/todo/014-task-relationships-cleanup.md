---
id: 014-task-relationships-cleanup
title: "Cleanup: remove legacy relationship fields + compat code"
created_at: "2025-12-28T19:05:40Z"
updated_at: "2025-12-28T15:47:58Z"
tags:
  - edison-core
  - tasks
  - cleanup
  - refactor
depends_on:
  - 013-task-relationships-migration
---
# Cleanup: remove legacy relationship fields + compat code

## Summary

Once the repo is migrated to canonical task relationships, remove the remaining legacy relationship fields and any compatibility parsing code. Ensure the system is fully coherent around the canonical `relationships:` format and the registry/service APIs.

## Wave / Parallelization

- **Wave:** 4 (cleanup)
- **Safe to run in parallel with:** none (touches core models/parsers)

## Objectives

- [ ] Remove legacy relationship fields from `Task` and `TaskSummary`:
  - `parent_id`, `child_ids`, `depends_on`, `blocks_tasks`, `related`
- [ ] Remove legacy parsing/writing code paths and ensure only canonical relationships are supported.
- [ ] Update any remaining docs/templates/schemas to match.

## Acceptance Criteria

- [ ] No legacy relationship keys are written or read anywhere in Edison core.
- [ ] All tests that touch task graph/readiness/planning/mutations pass and use canonical relationships.
- [ ] `edison task plan`, `edison task link`, and `edison task relate` all operate via canonical relationships.
- [ ] Validation-bundle membership (`bundle_root`) is supported via canonical relationships only (no ad-hoc extra frontmatter keys).
