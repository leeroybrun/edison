---
id: read
domain: rules
command: read
short_desc: Read a composed artifact (playbook)
cli: edison read <name> --type <type>
args:
- name: type
  description: Generated subfolder (e.g., constitutions, guidelines/shared, agents,
    start). Empty means root.
  required: false
- name: section
  description: Optional SECTION marker name to extract (e.g., RULE.GUARDS.FAIL_CLOSED).
  required: false
- name: name
  description: File name without extension (defaults to .md), e.g. ORCHESTRATOR, AVAILABLE_AGENTS
  required: true
when_to_use: '- The workflow tells you to read from `.edison/_generated/...`

  - You need the canonical, composed version (not a bundled template)

  '
related_commands:
- rules-current
---

Workflow: read the canonical, composed artifact from `.edison/_generated/`.

Notes:
- This is for reading developer-composed artifacts (agents, constitutions, guidelines, start prompts).
- Do NOT run `edison compose ...` from chat. If the file is missing, ask the developer to compose it.
- If you only need a specific chunk of a composed file, use `--section <SECTION_NAME>` to extract it
  from `<!-- section: ... -->` markers (same semantics as `{{include-section:...}}`).
