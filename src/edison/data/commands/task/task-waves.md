---
id: task-waves
domain: task
command: waves
short_desc: "Compute topological waves of parallelizable todo tasks (depends_on)"
cli: "edison task waves [--cap <n>] [--json] [--session <session_id>]"
args:
  - name: --session
    description: "Optional session scope for planning (filters to tasks with matching session_id)."
    required: false
  - name: --cap
    description: "Optional max parallel cap override (defaults to orchestration.maxConcurrentAgents when available)."
    required: false
  - name: --json
    description: "Output JSON."
    required: false
when_to_use: |
  - You want to schedule work into safe parallel batches
  - You want to validate that `depends_on` encodes the intended sequencing
related_commands:
  - task-audit
  - task-blocked
  - task-backlog-coherence
---

**Guardrails**
- Waves are computed from `depends_on`, not from task prose. If prose disagrees with waves, fix the task metadata.
- Default behavior plans the **global backlog**. Use `--session <id>` for session-scoped planning.

**Steps**
1. Run `edison task waves --json`.
2. Review:
   - Wave sizes (parallelism)
   - Blocked tasks (external missing/unsatisfied dependencies)
3. Cross-check with `edison task audit --json --tasks-root .project/tasks`:
   - If two tasks in the same wave touch the same files/modules, re-scope or add sequencing.
4. If you have a cap, use `--cap <n>` (or read `maxConcurrentAgents` in the JSON output) to create safe batches.

**Reference**
- If a task you expect to be schedulable is missing, run `edison task blocked`.

