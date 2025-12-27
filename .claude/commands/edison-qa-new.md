---
description: "Create QA brief for a task"

argument-hint: "task_id"


---

# edison-qa-new

Workflow: create (or ensure) the QA brief/record for a completed task.

Notes:
- QA briefs track rounds, evidence, and validator results.
- Create it when a task is moving toward validation.


```bash
edison qa new $1
```


## Arguments

- **task_id** (required): Task identifier



## When to use

- The task is ready (or nearly ready) for validation
- You want to start tracking validation rounds



## Related Commands

- /edison-qa-validate

- /edison-qa-audit
