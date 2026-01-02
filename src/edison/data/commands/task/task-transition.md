---
id: task-transition
domain: task
command: transition
short_desc: Transition a task between states
cli: edison task transition <task_id> --to <state>
args:
- name: task_id
  description: Task identifier (e.g., 150-wave1-auth-gate)
  required: true
when_to_use: To explicitly transition a task state (clearer mental model than "status")
related_commands:
- task-status
- qa-promote
---

Workflow: transitions are state-machine guarded by default. Use `--dry-run` to preview and `--force` only when you must bypass guards.

