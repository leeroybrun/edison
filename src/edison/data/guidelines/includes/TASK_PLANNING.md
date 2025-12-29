# Task Waves (Parallelizable Waves) - Include-Only File
<!-- WARNING: This file is for {{include-section:}} only. DO NOT read directly. -->

<!-- section: orchestrator-step-snippet -->
## orchestrator-step-snippet

Compute parallelizable “waves” from `depends_on`:

```bash
edison task waves
```

- Prefer **Wave 1** tasks for “start now”.
- Respect the configured cap (`orchestration.maxConcurrentAgents`). If Wave 1 exceeds the cap, use the printed batch suggestions (or `--json` for structured batches).
- Use `edison task relate <task-a> <task-b>` to link non-blocking “related” tasks (this influences within-wave grouping).
- If a desired todo task isn’t in Wave 1, inspect why:
  ```bash
  edison task blocked <task-id>
  ```
<!-- /section: orchestrator-step-snippet -->

<!-- section: orchestrator-cli-snippet -->
## orchestrator-cli-snippet

### Task Waves (Parallelizable Waves)

```bash
edison task waves [--json] [--cap <n>]
```

**Purpose**: Compute topological “waves” of **todo** tasks based on `depends_on`, so you can safely delegate independent work in parallel without reading every task file.

**How to use**:
- Prefer **Wave 1** tasks for “start now”.
- Respect the configured cap (`orchestration.maxConcurrentAgents`). Use `--json` only when you need structured batches for tools/scripts.
- Use `edison task blocked` for detailed “why blocked” explanations on a specific task.
<!-- /section: orchestrator-cli-snippet -->

<!-- section: orchestrator-constitution-snippet -->
## orchestrator-constitution-snippet

Use `edison task waves` to compute parallelizable waves of todo tasks from `depends_on` (Wave 1 = “start now”), and respect `orchestration.maxConcurrentAgents`. Use `edison task blocked <task-id>` for “why blocked” explanations.
<!-- /section: orchestrator-constitution-snippet -->
