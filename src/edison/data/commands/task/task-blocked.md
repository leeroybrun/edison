---
id: task-blocked
domain: task
command: blocked
short_desc: Explain why a todo task is blocked
cli: edison task blocked
args: []
when_to_use: '- You expected a task to show up in `task ready` but it doesn''t

  - You want an explanation for dependency blocking

  '
related_commands:
- task-ready
- task-status
---

Lists todo tasks that are blocked by unmet `depends_on` prerequisites,
and explains which dependency is blocking and its current state.
