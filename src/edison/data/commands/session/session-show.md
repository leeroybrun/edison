---
id: session-show
domain: session
command: show
short_desc: Show raw session JSON
cli: edison session show <session_id>
args:
- name: session_id
  description: Session identifier (e.g., sess-001)
  required: true
when_to_use: To inspect the persisted session record (including git/worktree metadata)
related_commands:
- session-status
- session-verify
---

Prints the session JSON record exactly as stored on disk.
