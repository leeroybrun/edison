---
id: 011-task-relationships-mutators-qa
task_id: 011-task-relationships-mutators
title: "QA for 011-task-relationships-mutators: route relationship mutations through registry"
round: 1
created_at: "2025-12-28T19:05:10Z"
updated_at: "2025-12-28T19:05:10Z"
---
# QA for 011-task-relationships-mutators: route relationship mutations through registry

## Validation Scope

- Verify all relationship mutations are centralized (no scattered updates).
- Verify symmetric/inverse invariants are correct for:
  - parent/child
  - depends_on/blocks
  - related

## Acceptance Checks

- [ ] Mutator CLIs covered by unit tests.
- [ ] No relationship drift possible from partial updates (one-sided links).

