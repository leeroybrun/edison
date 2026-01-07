# Evidence Commands

```bash
edison qa round <task-id> --new                   # Before implementing (creates round-N/)
edison evidence capture <task-id>                 # Capture required evidence (config-driven)
edison evidence status <task-id>                  # Check completeness
```

**Workflow:** Run command → Fix failures → Capture when `exitCode: 0`.
