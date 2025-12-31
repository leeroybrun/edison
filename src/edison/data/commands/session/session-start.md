---
id: session-start
domain: session
command: start
short_desc: 'Start/resume: pick a START_* prompt (playbook)'
cli: 'edison list --type start --format detail

  edison read --type start START_<PROMPT_ID>

  '
args:
- name: PROMPT_ID
  description: Prompt ID suffix (e.g., NEW_SESSION, RESUME_SESSION, AUTO_NEXT)
  required: true
when_to_use: '- The user says “start a new session”, “resume”, “what next?”, “validate”,
  or “cleanup”

  - You need the canonical bootstrap instructions before acting

  '
related_commands:
- session-status
- session-context
- session-next
---

Workflow: choose the correct START_* prompt based on what the user wants,
then print the selected prompt text in-chat.

Important:
- Do NOT run `edison compose ...` from chat. Composition is a developer responsibility.
- Prefer a minimal catalog: treat START_* as composable/extensible and discover them dynamically.
