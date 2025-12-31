---
id: task-relate
domain: task
command: relate
short_desc: "Add/remove non-blocking related-task links (`related` frontmatter)"
cli: "edison task relate <task_a> <task_b> [--remove] [--json]"
args:
  - name: task_a
    description: "Task ID (A)."
    required: true
  - name: task_b
    description: "Task ID (B)."
    required: true
  - name: --remove
    description: "Remove relation instead of adding it."
    required: false
  - name: --json
    description: "Output JSON."
    required: false
when_to_use: |
  - Two tasks touch the same subsystem but are not strict prerequisites
  - You want the wave planner to keep tasks clustered (best-effort) without blocking
related_commands:
  - task-link
  - task-audit
  - task-waves
---

**Guardrails**
- Use `related` for “keep in mind” coupling, not for ordering. If ordering matters, use `depends_on`.
- Keep `related` lists small (signal > noise).

**Steps**
1. Decide relationship type:
   - Blocking prerequisite → add `depends_on` in frontmatter.
   - Soft coupling → use `edison task relate`.
2. Add relation: `edison task relate <A> <B>`
3. If you later decide it is blocking, remove `related` and replace with `depends_on` explicitly.

