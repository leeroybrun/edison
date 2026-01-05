---
id: task-ready
domain: task
command: ready
short_desc: List tasks ready to be claimed
cli: edison task ready [--session <session-id>] [<task-id> [--skip-context7 --skip-context7-reason "<why>"]]
args:
- name: record_id
  description: (Deprecated) Task identifier to complete (use `edison task done <task>`). Omit to list.
  required: false
- name: --skip-context7
  description: (Deprecated completion path only) Bypass Context7 checks (requires --skip-context7-reason)
  required: false
- name: --skip-context7-reason
  description: (Deprecated completion path only) Justification for Context7 bypass
  required: false
when_to_use: '- You want to find the next claimable task (todo + deps satisfied)

  '
related_commands:
- qa-new
- qa-validate
- task-done
---

Workflow: list tasks that are ready to be claimed (derived from dependency readiness).

Use this only when:
- You want to pick your next task in the session

Note: `edison task ready <task-id>` is a deprecated alias for task completion.
Prefer `edison task done <task-id>`.
