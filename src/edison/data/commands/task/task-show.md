---
id: task-show
domain: task
command: show
short_desc: Show raw task Markdown
cli: edison task show <task_id>
args:
- name: task_id
  description: Task identifier (e.g., 150-wave1-auth-gate)
  required: true
when_to_use: To quickly inspect the raw task document as stored on disk
related_commands:
- task-status
- qa-show
---

Prints the task Markdown file exactly as stored (including YAML frontmatter).
