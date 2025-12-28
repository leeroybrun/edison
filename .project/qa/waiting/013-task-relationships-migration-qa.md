---
id: 013-task-relationships-migration-qa
task_id: 013-task-relationships-migration
title: "QA for 013-task-relationships-migration: migrate to canonical relationships format"
round: 1
created_at: "2025-12-28T19:05:30Z"
updated_at: "2025-12-28T19:05:30Z"
---
# QA for 013-task-relationships-migration: migrate to canonical relationships format

## Validation Scope

- Verify migration is correct and idempotent.
- Verify no legacy relationship fields remain in migrated task files.
- Verify templates/docs align with new storage semantics.

## Acceptance Checks

- [ ] `edison task plan`, `edison task blocked`, and `edison task ready` still work after migration.
- [ ] UI repo consumes new format.

