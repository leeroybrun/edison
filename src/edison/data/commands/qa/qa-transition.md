---
id: qa-transition
domain: qa
command: transition
short_desc: Transition a QA brief between states
cli: edison qa transition <task_id> --to <state>
args:
- name: task_id
  description: Task identifier (or QA id ending with -qa/.qa)
  required: true
when_to_use: To explicitly transition a QA record state (alias of `qa promote`)
related_commands:
- qa-promote
- qa-validate
- task-transition
---

Workflow: use this to move QA through the validation lifecycle (e.g., `waiting → todo`, `todo → wip`, `wip → done`, `done → validated`).

