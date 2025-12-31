---
id: task-ready
domain: task
command: ready
short_desc: Mark task ready for QA (wip→done)
cli: edison task ready <record_id>
args:
- name: record_id
  description: Task identifier to mark ready (omit to list ready tasks)
  required: false
when_to_use: '- Implementation is complete and ready to validate

  '
related_commands:
- qa-new
- qa-validate
---

Workflow: mark the task ready for validation (typically `wip` → `done`).

Use this only when:
- Tests are green
- The implementation is complete (no TODO/FIXME placeholders)
- Any required evidence generation has been run
