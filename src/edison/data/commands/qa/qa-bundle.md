---
id: qa-bundle
domain: qa
command: bundle
short_desc: Inspect validation cluster scope and evidence layout (playbook)
cli: edison qa bundle <task_id> --scope auto
args:
- name: task_id
  description: Task identifier (root or bundle member)
  required: true
when_to_use: |
  - Before running validators, to confirm which tasks are in scope
  - To see the resolved bundle root and evidence directories
related_commands:
- qa-validate
- qa-promote
---

Workflow: compute the validation cluster manifest for `--scope auto|hierarchy|bundle`.
