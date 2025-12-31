---
id: session-next
domain: session
command: next
short_desc: Show next session steps
cli: edison session next <session_id>
args:
- name: session_id
  description: Session identifier (e.g., sess-001). If unknown, run `edison session
    status` first.
  required: true
when_to_use: '- You just finished a step and want the next step

  - You''re resuming work after a break

  - You suspect you''re blocked by a guard/state mismatch

  '
related_commands:
- session-status
- task-status
---

Workflow: compute next steps for the current session.

Use this whenever you are unsure what Edison expects next. It reads
session/task/QA state and returns the recommended next actions.
