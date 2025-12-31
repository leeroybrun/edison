---
id: task-split
domain: task
command: split
short_desc: "Split a task into child subtasks (creates task + QA; links parent/child)"
cli: "edison task split <task_id> [--count <n>] [--prefix <label>] [--dry-run] [--force] [--json]"
args:
  - name: task_id
    description: "Task ID to split."
    required: true
  - name: --count
    description: "Number of subtasks to create (default: 2)."
    required: false
  - name: --prefix
    description: "Label appended after '<parent>.<n>-'."
    required: false
  - name: --dry-run
    description: "Preview split without creating tasks."
    required: false
  - name: --force
    description: "Skip pre-create duplicate checks (if configured)."
    required: false
  - name: --json
    description: "Output JSON."
    required: false
when_to_use: |
  - A task is too large to validate in one round
  - You need parallelizable subtasks with explicit ownership boundaries
related_commands:
  - task-link
  - task-audit
  - qa-new
---

**Guardrails**
- Split only when you can define clean boundaries (files/modules owned by each subtask).
- Prefer `--dry-run` first to confirm naming and count.
- After splitting, update the parent task to focus on integration/wiring + acceptance criteria across children.

**Steps**
1. Decide the split boundaries (by file/module ownership and acceptance criteria).
2. Preview: `edison task split <task_id> --count <n> --prefix <label> --dry-run`.
3. Create: rerun without `--dry-run`.
4. Re-run `edison task audit --json --tasks-root .project/tasks` to confirm no new overlaps/drift.

