---
id: task-claim
domain: task
command: claim
short_desc: Claim and move task to wip
cli: edison task claim <record_id>
args:
- name: record_id
  description: Task or QA identifier (e.g., 150-wave1-auth-gate)
  required: true
when_to_use: '- You are ready to start implementation on a specific task

  - You want Edison to lock/track ownership to prevent parallel edits

  '
related_commands:
- task-status
- session-next
---

Workflow: move a task from `todo` → `wip` and associate it with the active session.

After claiming:
- Follow your agent constitution + mandatory workflow (TDD, no mocks, config-first).
- Work only inside the session worktree (no git checkout/switch in primary).
