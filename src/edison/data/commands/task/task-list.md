---
id: task-list
domain: task
command: list
short_desc: "List tasks (and QA) with optional status/session filters"
cli: "edison task list [--type task|qa] [--status <state>] [--session <session_id>] [--json]"
args:
  - name: --type
    description: "Record type to list (`task` or `qa`)."
    required: false
  - name: --status
    description: "Filter by state (validated against WorkflowConfig)."
    required: false
  - name: --session
    description: "Filter by session id."
    required: false
  - name: --json
    description: "Output JSON."
    required: false
when_to_use: |
  - You need a quick inventory of tasks/QA in a given state
  - You want to confirm what exists before creating a new task
related_commands:
  - task-status
  - qa-new
---

**Guardrails**
- Don’t create new tasks until you’ve confirmed there isn’t already a task covering the same scope.

**Steps**
1. List todo tasks: `edison task list --status todo`
2. If you’re working in a session, filter: `edison task list --status wip --session <session_id>`
3. If you need QA inventory: `edison task list --type qa --status todo`

