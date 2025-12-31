---
id: validate-now
domain: internal
command: validate
short_desc: Validate current work (playbook)
cli: edison qa validate <task_id> --execute
args:
- name: task_id
  description: Task identifier to validate
  required: true
when_to_use: '- You want feedback while still implementing

  - You want a pre-flight validation run before task-ready

  '
related_commands:
- session-next
- task-status
---

Workflow: run the configured validators on the current context and record evidence.

Use this to get fast feedback before marking a task as `done`, or as a
final check before promotion.
