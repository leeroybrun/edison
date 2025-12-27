---
description: "Run memory pipelines"


---

# edison-memory-run

Runs configured memory pipelines for an event (e.g. session-end).
This is typically used to persist structured session insights and/or index episodic memory.


```bash
edison memory run --event session-end --session <session-id>
```



## When to use

- You want to persist structured session insights
- You want to trigger provider indexing (episodic sync/index)



## Related Commands

- /edison-memory-search

- /edison-session-next
