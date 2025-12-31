---
id: 024-session-whoami-cli-and-docs
title: "CLI/Docs: Add `edison session whoami` and document role recovery behavior"
created_at: "2025-12-28T19:55:00Z"
updated_at: "2025-12-28T19:55:00Z"
tags:
  - edison-core
  - cli
  - docs
  - hooks
  - compaction
depends_on:
  - 021-actor-identity-core
  - 022-session-context-and-hooks-role-aware
  - 023-env-and-process-events-fallback-for-role
---

# CLI/Docs: Add `edison session whoami` and document role recovery behavior

## Summary

Provide a simple, explicit CLI to print the currently resolved actor identity and the exact constitution read command, and document how role recovery works across hooks, env vars, and PID fallback.

This is an operator-friendly fallback when hooks are disabled or a platform does not support hooks.

## Objectives

- [ ] Add `edison session whoami` CLI that prints:
  - actor kind (`orchestrator|agent|validator|unknown`)
  - actor id (optional)
  - constitution path (single resolved file)
  - exact `edison read … --type constitutions` command
  - resolution source (env/process-events/fallback)
- [ ] Support `--json` output.
- [ ] Document the actor identity env vars and resolution order.
- [ ] Update hook template README to clarify that compaction recovery is primarily via `UserPromptSubmit` injection, with PreCompact as best-effort.

## Technical Design

### CLI shape

Create `src/edison/cli/session/whoami.py` and wire it into the CLI registry (where session subcommands are registered).

Implementation:
- Determine `project_root` via existing helpers (`get_repo_root`).
- Resolve session id via existing resolver (best-effort; do not require).
- Call the centralized resolver from `edison.core.actor.identity`.
- Print JSON or human output.

Human output (example):
- `Actor: orchestrator`
- `Constitution: .edison/_generated/constitutions/ORCHESTRATOR.md`
- `Read: edison read ORCHESTRATOR --type constitutions`
- `Resolved via: env`

### Docs updates

Update/add:
- `src/edison/data/templates/hooks/README.md` (role recovery explanation)
- A small durable guideline section (include-only if needed) describing:
  - how roles are identified
  - why hooks remain minimal and point back to constitutions
  - env var names and precedence

Do not duplicate constitution content; only describe the mechanism.

## Acceptance Criteria

- [ ] `edison session whoami` works in an Edison project even without an active session, returning `unknown` safely.
- [ ] `edison session whoami --json` produces stable keys.
- [ ] Docs clearly explain:
  - what env vars exist
  - what the fallback is
  - how to recover when hooks are disabled

## Files to Create/Modify

```
# Create
src/edison/cli/session/whoami.py

# Modify
src/edison/cli/session/__init__.py (or equivalent command registry)
src/edison/data/templates/hooks/README.md
src/edison/data/guidelines/... (only if a durable include is needed)
```

