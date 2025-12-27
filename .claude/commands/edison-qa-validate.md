---
description: "Validate a specific task (playbook)"

argument-hint: "task_id"


---

# edison-qa-validate

Workflow: run QA validation for a specific task (creates a validation round).


```bash
edison qa validate $1 --round 1
```


## Arguments

- **task_id** (required): Task identifier



## When to use

- The task is `done` and ready for validation
- You need a deterministic round number



## Related Commands

- /edison-qa-audit

- /edison-qa-promote
