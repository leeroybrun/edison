---
id: qa-promote
domain: qa
command: promote
short_desc: Promote QA/task to validated
cli: edison qa promote <task_id>
args:
- name: task_id
  description: Task identifier
  required: true
when_to_use: '- All validations passed and you want to finalize

  '
related_commands:
- qa-round
- qa-audit
---

Workflow: promote a task/QA record to `validated` after successful validation.

Only use when:
- Required validators are green
- Evidence is present for the round(s)
- There are no open blocking findings
