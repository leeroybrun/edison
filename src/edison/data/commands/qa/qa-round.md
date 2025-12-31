---
id: qa-round
domain: qa
command: round
short_desc: Inspect or update QA rounds for a task
cli: edison qa round <task_id> --list
args:
- name: task_id
  description: Task identifier
  required: true
when_to_use: '- You want to see which round is current (`--current`)

  - You want to list the round history (`--list`)

  - You want to create a new evidence round directory (`--new`)

  - You want to record the round outcome (`--status approve|reject|blocked|pending`)

  '
related_commands:
- qa-validate
- task-status
---

Workflow: inspect or update QA round history for a task (current round, list of rounds, record outcomes).
