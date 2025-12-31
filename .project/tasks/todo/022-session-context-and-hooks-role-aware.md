---
id: 022-session-context-and-hooks-role-aware
title: "Core: Make session context + compaction hook role-aware (no hardcoded role)"
created_at: "2025-12-28T19:55:00Z"
updated_at: "2025-12-28T19:55:00Z"
tags:
  - edison-core
  - hooks
  - compaction
  - session-context
depends_on:
  - 021-actor-identity-core
---

# Core: Make session context + compaction hook role-aware (no hardcoded role)

## Summary

Upgrade `edison session context` (the universal hook injection point) to include “Actor Identity” so that:
- SessionStart / UserPromptSubmit hooks always remind the LLM which constitution to read
- the PreCompact reminder is correct and minimal

Remove the brittle “default_role + message_template” mechanism that currently points to wrong filenames.

## Objectives

- [ ] Extend `SessionContextPayload` and renderers to include actor identity:
  - JSON keys: `actorKind`, `actorId`, `actorConstitution`, `actorReadCmd`, `actorResolution`
  - Markdown: include a clear “Actor” section with the exact `edison read …` command
- [ ] Add config support in `src/edison/data/config/session.yaml`:
  - allow `session.context.payload.fields` to include actor identity fields
  - allow `session.context.render.markdown.fields` to include an “actor” stanza
  - keep deterministic/stable ordering
- [ ] Fix `hooks.definitions.compaction-reminder` config and template:
  - remove `default_role` and the `{ROLE}` placeholder replacement approach
  - print a short directive that points to the context’s actor stanza
  - ensure no wrong filenames are referenced

## Technical Design

### Session context JSON payload changes

Modify:
- `src/edison/core/session/context_payload.py`

In `SessionContextPayload.to_dict()`:
- include actor identity only if project is Edison project
- ensure keys are included only when configured via `session.context.payload.fields` (consistent with existing behavior)

### Session context Markdown rendering changes

In `format_session_context_markdown()`:
- implement a new render field token, e.g. `actor`, that prints:
  - `- Actor: <kind> (<id>)` (id optional)
  - `- Re-read constitution: <exact command>`
  - optionally `- Constitution path: <relative path>` (configurable; keep compact by default)

Add the `actor` field to default core config:
- `src/edison/data/config/session.yaml`

### Hook changes

Modify:
- `src/edison/data/templates/hooks/compaction-reminder.sh.template`
- `src/edison/data/config/hooks.yaml`

Behavior:
- continue calling `edison session context` (already does)
- then print a single directive line like:
  - `⚠️ After compaction: re-read your constitution (see Actor in Edison Context above).`

Do **not** attempt to resolve role in the hook template itself; rely on session context.

## Acceptance Criteria

- [ ] `edison session context` (text mode) prints an Actor stanza by default in Edison projects.
- [ ] `edison session context --json` includes actor identity fields (when enabled in config).
- [ ] Compaction reminder hook does not reference nonexistent paths like `constitutions/agents.md`.
- [ ] Hooks remain fail-open and deterministic (no timestamps in context output).

## Files to Modify

```
src/edison/core/session/context_payload.py
src/edison/data/config/session.yaml
src/edison/data/templates/hooks/compaction-reminder.sh.template
src/edison/data/config/hooks.yaml
```

