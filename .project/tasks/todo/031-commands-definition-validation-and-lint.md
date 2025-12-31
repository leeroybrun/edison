---
id: "031-commands-definition-validation-and-lint"
title: "Commands system reliability: validate/lint command definitions (OpenSpec-style deterministic validator)"
type: feature
owner:
session_id:
parent_id:
child_ids:
depends_on:
  - "26.9-wave4-slash-commands-and-start-plan-mode"
blocks_tasks:
related:
  - "26.10-wave4-docs-guidelines-and-migrations"
claimed_at:
last_active:
continuation_id:
created_at: "2025-12-31T00:00:00Z"
updated_at: "2025-12-31T00:00:00Z"
tags:
  - commands
  - validation
  - cli
  - docs
priority: medium
estimated_hours:
model:
---

# Commands system reliability: validate/lint command definitions (OpenSpec-style deterministic validator)

## Summary

Now that Edison commands are defined as layered markdown files under `src/edison/data/commands/**`, we need deterministic tooling to keep them coherent and reliable:
- validate frontmatter schema and required fields
- detect duplicate IDs and domain/command collisions
- enforce minimum workflow guardrails for “high-risk” commands (Ask gate, read-only defaults)
- provide stable JSON output for automation/CI

This mirrors OpenSpec’s philosophy: a deterministic validator with structured output and non-zero exit codes on invalid input.

## Required Reading

- Command system implementation: `src/edison/core/adapters/components/commands.py`
- Platform config: `src/edison/data/config/commands.yaml`
- OpenSpec validate command UX reference: `/tmp/edison-vendor-commands/OpenSpec/src/commands/validate.ts`

## Objectives

- [ ] Add a deterministic CLI: `edison commands validate [--json] [--strict]` (exact naming may vary).
- [ ] Validation must check:
  - required frontmatter keys exist (`id`, `domain`, `command`, `short_desc`, etc.)
  - unique `id` across layers after composition (or explicit override rules)
  - no two commands generate the same output stem (`<prefix><id>.md`) for a platform
  - optional “lint” checks for high-value command families:
    - contains an explicit “Ask”/approval gate section
    - includes guardrails for read-only analysis when appropriate
    - includes a strict output contract when the command claims deterministic results
- [ ] Output contract:
  - JSON: `{ ok, errors: [...], warnings: [...], summary: {...}, version }`
  - Text: clear “valid/invalid” + actionable next steps
- [ ] Exit codes:
  - non-zero on invalid (errors), zero if ok

## Acceptance Criteria

- [ ] Running validation in CI can fail-fast when a command definition is broken.
- [ ] Output is deterministic and stable across runs.
- [ ] Validator UX includes “next steps” hints (OpenSpec style).

## Files to Create/Modify

```
# Add (suggested)
src/edison/cli/commands/validate.py
src/edison/core/commands/validate.py
src/edison/data/schemas/domain/command.schema.yaml
```
