---
id: qa-validate
domain: qa
command: validate
short_desc: Validate a specific task (playbook)
cli: edison qa validate <task_id> --execute
args:
- name: task_id
  description: Task identifier
  required: true
when_to_use: '- The task is `done` and ready for validation

  - You want Edison to run the validators (use `--execute`)

  '
related_commands:
- qa-round
- qa-promote
---

Workflow: run QA validation for a specific task (creates a validation round).
