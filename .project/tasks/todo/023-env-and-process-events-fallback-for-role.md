---
id: 023-env-and-process-events-fallback-for-role
title: "Core: Inject actor env vars at spawn + PID/process-events fallback for role recovery"
created_at: "2025-12-28T19:55:00Z"
updated_at: "2025-12-28T19:55:00Z"
tags:
  - edison-core
  - orchestrator
  - hooks
  - tracking
  - compaction
depends_on:
  - 021-actor-identity-core
  - 022-session-context-and-hooks-role-aware
---

# Core: Inject actor env vars at spawn + PID/process-events fallback for role recovery

## Summary

Make role recovery robust even when:
- the orchestrator is launched by Edison (env injection should “just work”)
- env vars are missing (fallback to process-events.jsonl using topmost PID)

## Objectives

- [ ] Inject `EDISON_ACTOR_KIND=orchestrator` into the spawned orchestrator environment.
- [ ] Inject `AGENTS_SESSION=<session_id>` into the spawned orchestrator environment when available.
- [ ] Implement a best-effort process-events fallback in the actor identity resolver:
  - determine topmost pid via `edison.core.utils.process.inspector.find_topmost_process`
  - scan configured process-events jsonl for a matching orchestrator record
  - infer `actorKind=orchestrator` when matched
- [ ] Add tests for precedence:
  - env vars override process-events fallback
  - fallback works when env vars missing
  - fallback fails open when log missing/too large/unreadable

## Technical Design

### Spawn env injection

Modify:
- `src/edison/core/orchestrator/launcher.py`

In `OrchestratorLauncher.launch()`:
- after `env = os.environ.copy()` and `env.update(profile_env)`, set:
  - `env["EDISON_ACTOR_KIND"] = "orchestrator"`
  - (optional) `env["EDISON_ACTOR_ID"] = <profile_name>` if it helps debugging (but do not rely on it elsewhere)
  - if tokens include `session_id`, set `env["AGENTS_SESSION"] = tokens["session_id"]`

This should be safe even if `AGENTS_SESSION` is already set (overwrite only when tokens has session id).

### Process-events fallback

Modify/add in:
- `src/edison/core/actor/identity.py`
- reuse `src/edison/core/tracking/process_events.py` utilities only if it can be made efficient for hooks

Implement a tail-scan helper that:
- reads the jsonl file from the end (bounded), or reads the last N lines
- parses json objects and returns the first matching orchestrator record

Matching logic:
- `kind == "orchestrator"`
- `processId == <topmost pid>`
- optional: `sessionId == resolved session id` if known

### Why this is safe

- process logging is already enabled by default in `orchestration.yaml`
- the fallback is best-effort and must never crash hooks

## Acceptance Criteria

- [ ] Launching a session via Edison autostart results in orchestrator subprocess inheriting `EDISON_ACTOR_KIND=orchestrator` and `AGENTS_SESSION`.
- [ ] `edison session context` correctly reports actor kind as orchestrator inside the orchestrator process even after compaction (via hook injection).
- [ ] If env vars are absent, actor identity still resolves orchestrator role via process-events when available.
- [ ] Unit tests exist and pass for resolution precedence and fail-open behavior.

## Files to Modify

```
src/edison/core/orchestrator/launcher.py
src/edison/core/actor/identity.py
tests/... (actor identity resolver tests incl. process-events fallback)
```

