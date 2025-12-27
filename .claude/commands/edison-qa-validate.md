---
description: "Validate a specific task (playbook)"
edison-generated: true
edison-id: "qa-validate"
edison-platform: "claude"


argument-hint: "task_id"


---

# edison-qa-validate

Workflow: run QA validation for a specific task (creates a validation round).


```bash
edison qa validate <task_id> --execute
```


## Arguments

- **task_id** (required): Task identifier



## When to use

- The task is `done` and ready for validation
- You want Edison to run the validators (use `--execute`)



## Related Commands

- /edison-qa-round

- /edison-qa-promote
