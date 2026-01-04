---
id: qa-validate
domain: qa
command: validate
short_desc: Validate a specific task or cluster (playbook)
cli: edison qa validate <task_id> --scope auto --execute
args:
- name: task_id
  description: Task identifier
  required: true
- name: preset
  description: Optional validation preset override (e.g., fast, standard, strict, deep)
  required: false
when_to_use: '- The task is `done` and ready for validation

  - You want Edison to run the validators (use `--execute`)

  - You need cluster validation (use `--scope auto|hierarchy|bundle`)

  - You want to override the validation preset (use `--preset <name>`)

  '
related_commands:
- qa-round
- qa-promote
---

Workflow: run QA validation for a specific task (creates a validation round).
