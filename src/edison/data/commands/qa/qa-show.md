---
id: qa-show
domain: qa
command: show
short_desc: Show raw QA Markdown
cli: edison qa show <qa_id>
args:
- name: qa_id
  description: QA identifier (e.g., 150-wave1-auth-gate-qa)
  required: true
when_to_use: To quickly inspect the raw QA brief as stored on disk
related_commands:
- qa-new
- qa-round
- task-show
---

Prints the QA Markdown file exactly as stored (including YAML frontmatter).
