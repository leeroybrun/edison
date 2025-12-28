---
id: 010-task-relationships-registry-qa
task_id: 010-task-relationships-registry
title: "QA for 010-task-relationships-registry: unified task relationship registry + canonical on-disk format"
round: 1
created_at: "2025-12-28T19:05:00Z"
updated_at: "2025-12-28T19:05:00Z"
---
# QA for 010-task-relationships-registry: unified task relationship registry + canonical on-disk format

## Validation Scope

- Verify relationship invariants are enforced (single-parent, symmetry, inverse mapping).
- Verify canonical serialization/parsing is deterministic and covered by tests.
- Verify no duplicated “relationship mutation” logic exists outside the registry/service.

## Acceptance Checks

- [ ] Unit tests cover symmetry/inverse/single-parent cases.
- [ ] `TaskRepository` writes canonical `relationships` (no legacy writes).
- [ ] `TaskIndex`/`TaskGraph` can build graph state from canonical relationships.

