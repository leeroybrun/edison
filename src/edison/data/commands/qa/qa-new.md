---
id: qa-new
domain: qa
command: new
short_desc: Create QA brief for a task
cli: edison qa new <task_id>
args:
- name: task_id
  description: Task identifier
  required: true
when_to_use: '- The task is ready (or nearly ready) for validation

  - You want to start tracking validation rounds

  '
related_commands:
- qa-validate
- qa-round
---

Workflow: create (or ensure) the QA brief/record for a completed task.

Notes:
- QA briefs track rounds, evidence, and validator results.
- Create it when a task is moving toward validation.
