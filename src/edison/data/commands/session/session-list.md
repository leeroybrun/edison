---
id: session-list
domain: session
command: list
short_desc: List sessions across states
cli: edison session list
args:
- --status <state>
- --owner <owner>
when_to_use: When you need to discover sessions and where they live
related_commands:
- session-status
- session-show
- session-next
---

Lists sessions across all states. Use `--status` to filter (accepts semantic state or directory alias like `wip`).

