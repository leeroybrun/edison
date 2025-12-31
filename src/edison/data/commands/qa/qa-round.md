---
id: qa-round
domain: qa
command: round
short_desc: Inspect QA rounds for a task
cli: edison qa round <task_id> --list
args:
- name: task_id
  description: Task identifier
  required: true
when_to_use: '- You want to see which round is current

  - You want to check whether QA is pending/blocked/approved

  '
related_commands:
- qa-validate
- task-status
---

Workflow: inspect the QA round history for a task (current round, list of rounds).
