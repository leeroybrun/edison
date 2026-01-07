# Evidence Commands

```bash
edison qa round prepare <task-id>                 # Before implementing (prepares round-N/)
edison evidence capture <task-id>                 # Capture required evidence (config-driven)
edison evidence status <task-id>                  # Check completeness
```

**Workflow:** Run command → Fix failures → Capture when `exitCode: 0`.
