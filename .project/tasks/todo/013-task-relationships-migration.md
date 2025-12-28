---
id: 013-task-relationships-migration
title: "Chore: migrate repo + edison-ui to canonical task relationships format"
created_at: "2025-12-28T19:05:30Z"
updated_at: "2025-12-28T19:05:30Z"
tags:
  - edison-core
  - tasks
  - migration
  - templates
  - docs
depends_on:
  - 011-task-relationships-mutators
  - 012-task-relationships-consumers
---
# Chore: migrate repo + edison-ui to canonical task relationships format

## Summary

After the new canonical relationship system is in place, migrate the on-disk task files in this repo (and `../edison-ui`) to the canonical `relationships:` format and update templates/docs accordingly.

Because Edison is not deployed externally yet, we can do a straightforward migration without needing a permanent CLI. A one-off script (kept under `scripts/migrations/`) is acceptable.

## Wave / Parallelization

- **Wave:** 3 (migration + docs/templates)
- **Safe to run in parallel with:** none (touches many files and both repos)

## Migration Scope

### A) Edison repo

Migrate task frontmatter under:
- `.project/tasks/**`
- `.project/sessions/**/tasks/**` (if any exist)

Convert legacy fields into canonical relationships edges:
- `parent_id` + `child_ids` → `parent`/`child` edges (symmetric)
- `depends_on` + `blocks_tasks` → `depends_on`/`blocks` edges (inverse)
- `related` → `related` edges (symmetric)

Remove legacy keys after conversion.

### B) Edison templates and docs

Update templates to emit canonical relationships:
- `src/edison/data/templates/documents/TASK.md` (remove legacy relationship fields)

Update docs/guidelines:
- Any mention of `depends_on`, `child_ids`, etc as first-class frontmatter should be updated to “relationships-based”.

### C) edison-ui

Update `../edison-ui` (or whatever current path is configured) so it reads and displays canonical `relationships` (and no longer depends on legacy keys).

## Deliverables

- [ ] One-off migration script (Python) that:
  - walks the repo, parses YAML frontmatter, rewrites relationship format deterministically
  - is safe to re-run (idempotent)
  - can also target `../edison-ui` fixtures/data if needed
- [ ] Updated task template to canonical relationship format
- [ ] Updated docs that explain relationships + how to use `edison task link`/`relate`/`plan` under the new model

## Acceptance Criteria

- [ ] After migration, Edison can still list/claim/plan tasks and build the task graph correctly.
- [ ] `edison task plan` still computes waves and groups related tasks.
- [ ] `../edison-ui` renders task relationships correctly from canonical `relationships`.

