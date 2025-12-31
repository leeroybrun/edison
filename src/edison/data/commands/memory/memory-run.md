---
id: memory-run
domain: memory
command: run
short_desc: Run memory pipelines
cli: edison memory run --event session-end --session <session-id>
args: []
when_to_use: '- You want to persist structured session insights

  - You want to trigger provider indexing (episodic sync/index)

  '
related_commands:
- memory-search
- session-next
---

Runs configured memory pipelines for an event (e.g. session-end).
This is typically used to persist structured session insights and/or index episodic memory.
