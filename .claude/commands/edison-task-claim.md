---
description: "Claim and move task to wip"

argument-hint: "task_id"


---

# edison-task-claim

Workflow: move a task from `todo` → `wip` and associate it with the active session.

After claiming:
- Follow your agent constitution + mandatory workflow (TDD, no mocks, config-first).
- Work only inside the session worktree (no git checkout/switch in primary).


```bash
edison task claim $1
```


## Arguments

- **task_id** (required): Task identifier (e.g., TASK-123, 150-implement-feature)



## When to use

- You are ready to start implementation on a specific task
- You want Edison to lock/track ownership to prevent parallel edits



## Related Commands

- /edison-task-status

- /edison-session-next
