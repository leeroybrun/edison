# Task Planning (Parallelizable Waves)

Use `edison task plan` to compute **parallelizable waves** of todo tasks from `depends_on` (Wave 1 = “start now”).

- Respect `orchestration.maxConcurrentAgents` (shown as “Max concurrent” and used for batch suggestions).
- For “why blocked”, run `edison task blocked <task-id>`.
- Use `--json` only if you need structured output for tools/scripts.
