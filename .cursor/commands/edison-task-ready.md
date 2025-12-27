# edison-task-ready

Workflow: mark the task ready for validation (typically `wip` → `done`).

Use this only when:
- Tests are green
- The implementation is complete (no TODO/FIXME placeholders)
- Any required evidence generation has been run


## Usage

```bash
edison task ready $1
```


## Arguments

- task_id (required): Task identifier




## When to use

- Implementation is complete and ready to validate




## Related

- /edison-qa-new

- /edison-validate-now
