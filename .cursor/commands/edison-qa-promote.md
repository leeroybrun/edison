# edison-qa-promote

Workflow: promote a task/QA record to `validated` after successful validation.

Only use when:
- Required validators are green
- Evidence is present for the round(s)
- There are no open blocking findings


## Usage

```bash
edison qa promote $1
```


## Arguments

- task_id (required): Task identifier




## When to use

- All validations passed and you want to finalize




## Related

- /edison-qa-audit
