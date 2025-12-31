---
id: qa-audit
domain: qa
command: audit
short_desc: Audit prompt/guideline hygiene (duplication, purity)
cli: edison qa audit --check-duplication --check-purity
args: []
when_to_use: '- You suspect duplicated/conflicting guidance across the composed stack

  - You want to enforce prompt best practices (single source of truth)

  '
related_commands:
- rules-current
---

Workflow: audit Edison prompt/guideline content for quality issues:
- duplication across guidelines
- purity violations (project terms leaking into core/packs)
