---
id: list
domain: rules
command: list
short_desc: List composed artifacts (playbook)
cli: edison list --type <type> --format detail
args:
- name: type
  description: Generated subfolder (e.g., start, constitutions, guidelines/shared,
    agents). Empty means root.
  required: false
when_to_use: '- You need to discover which composed files are available

  - You need to pick an appropriate start prompt / guideline / constitution

  '
related_commands:
- read
---

Workflow: list the canonical, composed artifacts under `.edison/_generated/`.

Use `--type start` to discover available `START_*.md` prompts.
