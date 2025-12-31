---
id: memory-save
domain: memory
command: save
short_desc: Save a memory summary
cli: edison memory save <summary>
args: []
when_to_use: '- You want to record a brief decision or gotcha

  '
related_commands:
- memory-search
- session-context
---

Saves a session summary string to configured memory providers (optional).
Use this for ad-hoc notes; for structured session summaries use `memory run`.
