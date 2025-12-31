---
id: task-similar
domain: task
command: similar
short_desc: "Find likely duplicate/similar tasks (deterministic similarity index)"
cli: |
  edison task similar --query "<title or description>" [--threshold <f>] [--top <n>] [--json]
  edison task similar --task <task_id> [--threshold <f>] [--top <n>] [--json]
args:
  - name: --query
    description: "Free-text query (usually a title) to match against existing tasks."
    required: false
  - name: --task
    description: "Find similar tasks to an existing task id."
    required: false
  - name: --top
    description: "Maximum matches to return (default from config)."
    required: false
  - name: --threshold
    description: "Minimum similarity score (default from config)."
    required: false
  - name: --only-todo
    description: "Only consider tasks in todo state."
    required: false
  - name: --states
    description: "Comma-separated list of task states to search (overrides --only-todo)."
    required: false
  - name: --json
    description: "Output JSON."
    required: false
when_to_use: |
  - Before creating a new task (dedupe-first)
  - When consolidating a backlog and trying to remove overlap
related_commands:
  - task-audit
  - task-new
---

**Guardrails**
- Treat similarity matches as hypotheses. Confirm by reading the candidate tasks before merging/scoping changes.
- Prefer merging tasks when they share the same “canonical owner module/API”, and split when they bundle unrelated concerns.

**Steps**
1. If you’re about to create a task, run: `edison task similar --query "<proposed title>" --json`.
2. If you’re consolidating, run: `edison task similar --task <task_id> --json`.
3. For top matches:
   - Decide **merge**, **re-scope**, or **keep separate**.
   - If keeping separate, add explicit relationships (`depends_on` / `related`) to reduce drift.

**Reference**
- For a deterministic, backlog-root-only scan, run `edison task audit --json --tasks-root .project/tasks`.

