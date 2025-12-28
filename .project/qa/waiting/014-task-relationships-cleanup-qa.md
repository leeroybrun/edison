---
id: 014-task-relationships-cleanup-qa
task_id: 014-task-relationships-cleanup
title: "QA for 014-task-relationships-cleanup: remove legacy relationship fields"
round: 1
created_at: "2025-12-28T19:05:40Z"
updated_at: "2025-12-28T19:05:40Z"
---
# QA for 014-task-relationships-cleanup: remove legacy relationship fields

## Validation Scope

- Verify legacy fields are removed fully (models, repository, index, consumers, CLIs).
- Verify canonical relationships remain deterministic and invariant-preserving.

## Acceptance Checks

- [ ] No legacy relationship keys exist in task frontmatter or code paths.
- [ ] Relationship invariants are still enforced by the registry/service.

