---
id: task-status
domain: task
command: status
short_desc: Show current task state
cli: edison task status <record_id>
args:
- name: record_id
  description: Task or QA identifier (e.g., 150-wave1-auth-gate)
  required: true
when_to_use: To check current task progress and state
related_commands:
- task-claim
- session-status
---

Workflow: inspect a task's current state, owner, session linkage, and recent activity.
