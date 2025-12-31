---
id: 021-actor-identity-core
title: "Core: Actor identity resolver (role → constitution) for compaction recovery"
created_at: "2025-12-28T19:55:00Z"
updated_at: "2025-12-28T19:55:00Z"
tags:
  - edison-core
  - hooks
  - compaction
  - constitutions
  - ergonomics
depends_on:
  - 001-session-id-inference
  - 002-prompts-constitutions-compaction
---

# Core: Actor identity resolver (role → constitution) for compaction recovery

## Summary

Introduce a first-class “Actor Identity” resolver that can reliably answer:
- which Edison role is currently active (`orchestrator|agent|validator`)
- optional role id (e.g. specific agent/validator profile id)
- which constitution file should be re-read
- the exact `edison read …` command to do so

This must be centralized and reusable by hooks (`edison session context`) and by humans (`edison session whoami`).

## Problem Statement

After compaction, LLMs often read the wrong constitution (or none). Edison currently:
- prints all constitution paths in `edison session context`
- has a compaction reminder hook, but it hardcodes an incorrect `default_role` and wrong filename template

Edison needs a robust “who am I?” mechanism that **adds clarity** without duplicating constitution content.

## Objectives

- [ ] Define an internal `ActorIdentity` data model (kind/id/constitution/readCmd/source).
- [ ] Implement centralized actor identity resolution with precedence:
  1) environment variables injected at spawn time
  2) best-effort process-events fallback (optional for Phase 1; mandatory by Task 023)
  3) unknown/fallback
- [ ] Ensure the resolved constitution paths match actual generated names:
  - `.edison/_generated/constitutions/AGENTS.md`
  - `.edison/_generated/constitutions/ORCHESTRATOR.md`
  - `.edison/_generated/constitutions/VALIDATORS.md`
- [ ] Add tests for parsing/normalization and for “read command” correctness.

## Technical Design

### Environment variables (primary)

Standardize these env vars:
- `EDISON_ACTOR_KIND`: `orchestrator|agent|validator`
- `EDISON_ACTOR_ID`: optional (string)

Optional (if helpful for debugging):
- `EDISON_ACTOR_SOURCE`: reserved (do not rely on externally)

Actor identity resolution must be resilient:
- normalize case and allow legacy aliases (e.g. `agents` → `agent`, `validators` → `validator`)
- reject unknown kinds cleanly

### Constitution resolution

Derive constitution path from `project_root` and role:
- use `edison.core.utils.paths.project.get_project_config_dir(project_root, create=False)`
- use `cfg_dir / "_generated" / "constitutions" / "<ROLE>.md"`

Map:
- agent → `AGENTS.md`
- orchestrator → `ORCHESTRATOR.md`
- validator → `VALIDATORS.md`

### Read command

Derive the recommended command:
- agent → `edison read AGENTS --type constitutions`
- orchestrator → `edison read ORCHESTRATOR --type constitutions`
- validator → `edison read VALIDATORS --type constitutions`

If `actorId` exists and Edison has a *role-specific* doc to read in addition to constitutions, do **not** invent it here. Keep scope to constitutions unless such mapping already exists in Edison core config.

### Module layout

Add a new core module, for example:
- `src/edison/core/actor/identity.py`

Export:
- `resolve_actor_identity(project_root: Path, session_id: str|None) -> ActorIdentity`
- `format_actor_identity_markdown(...) -> str` (optional; prefer doing rendering in `session/context_payload.py`)

## Acceptance Criteria

- [ ] Running `edison session context --json` includes actor identity fields once Task 022 is completed.
- [ ] Actor resolution returns correct `constitutionPath` and `readCommand` for all supported kinds.
- [ ] Unknown/missing env vars result in `actorKind="unknown"` (no crash).
- [ ] Tests exist and pass for normalization and correct read commands.

## Files to Create/Modify

```
# Create
src/edison/core/actor/identity.py
src/edison/core/actor/__init__.py

# Modify (tests)
tests/... (add unit tests for actor identity resolution)
```

