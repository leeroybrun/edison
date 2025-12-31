---
id: task-new
domain: task
command: new
short_desc: Create a new task (playbook)
cli: 'edison task new --id <id> --slug <slug>

  '
args:
- name: id
  description: Numeric id (e.g., 100)
  required: true
- name: slug
  description: Short slug (e.g., implement-auth)
  required: true
when_to_use: '- You''re about to start a new unit of work

  - You want a canonical task record for Edison workflows

  '
related_commands:
- task-claim
- task-status
---

Workflow: create a new task with a stable ID and clear scope.

Recommended:
- Keep the task small enough to validate in one round.
- Put acceptance criteria into the task description.
