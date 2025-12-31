---
id: session-context
domain: session
command: context
short_desc: Print hook-safe session context
cli: edison session context
args: []
when_to_use: '- After context compaction

  - When you want a quick refresh without full orchestration output

  '
related_commands:
- session-next
- session-status
---

Prints a small, deterministic context refresher intended for:
- Claude Code hooks (SessionStart/PreCompact/UserPromptSubmit)
- Quick in-chat refresh without running full `session next`
