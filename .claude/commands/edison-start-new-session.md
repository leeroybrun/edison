---
description: "Print START_NEW_SESSION prompt"
edison-generated: true
edison-id: "start-new-session"
edison-platform: "claude"



---

# edison-start-new-session

Prints the Edison START_NEW_SESSION prompt used to bootstrap a fresh session.
This is a prompt document meant for the LLM; it does not mutate task/session state.


```bash
edison compose all --start && cat .edison/_generated/start/START_NEW_SESSION.md
```



## When to use

- Starting a brand new Edison session
- You want the canonical start prompt text in-chat



## Related Commands

- /edison-session-next

- /edison-session-status
