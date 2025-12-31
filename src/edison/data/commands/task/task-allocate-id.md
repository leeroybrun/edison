---
id: task-allocate-id
domain: task
command: allocate-id
short_desc: "Allocate the next available task ID (stable + collision-free)"
cli: "edison task allocate-id [--parent <task_id>] [--prefix <slug>] [--json]"
args:
  - name: --parent
    description: "Parent task ID for child allocation (e.g., 150-wave1 or 201)."
    required: false
  - name: --prefix
    description: "Optional suffix/prefix to append to the allocated ID."
    required: false
  - name: --json
    description: "Output JSON."
    required: false
when_to_use: |
  - You want to create a new task and need a stable, unused ID
  - You are about to split work and want child IDs that won’t collide
related_commands:
  - task-new
  - task-split
---

**Guardrails**
- Prefer stable, human-readable IDs over ad-hoc names. IDs are coordination primitives (relationships, waves, audit).
- Do not hand-pick IDs when parallel work is happening; use this to avoid collisions.

**Steps**
1. Decide whether this is a **top-level** task or a **child** task.
2. Allocate:
   - Top-level: run `edison task allocate-id --prefix <slug>`
   - Child: run `edison task allocate-id --parent <parent_id> --prefix <slug>`
3. Use the returned ID as the canonical record ID when creating the task.

**Reference**
- If you suspect duplicates, run `edison task similar --query "<title>" --json` before creating the task.

