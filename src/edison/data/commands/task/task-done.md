---
id: task-done
domain: task
command: done
short_desc: Complete a task (wip→done) with evidence/TDD guards
cli: edison task done <task-id> [--session <session-id>] [--skip-context7 --skip-context7-reason "<why>"]
args:
- name: task-id
  description: Task identifier to complete (supports unique prefix shorthand like "12007")
  required: true
- name: --session
  description: Session completing the task (required)
  required: true
- name: --skip-context7
  description: Bypass Context7 checks (verified false positives only; requires --skip-context7-reason)
  required: false
- name: --skip-context7-reason
  description: Justification for Context7 bypass (required when --skip-context7 is set)
  required: false
when_to_use: "- Implementation is complete and ready to validate\n"
related_commands:
- task-ready
- evidence-init
- evidence-capture
- evidence-status
- qa-new
- qa-promote
- qa-validate
---

Workflow: complete a task (typically `wip` → `done`) while enforcing:
- Implementation report presence
- Required evidence presence
- Context7 markers (when detected)
- TDD readiness gates

Use this only when:
- Tests are green
- Evidence has been captured (see `edison evidence status <task-id>`)
- The task is claimed by your session (`--session`)
