---
id: 001-session-id-inference
title: 'Chore: session id inference'
created_at: '2025-12-28T10:00:53Z'
updated_at: '2025-12-28T10:00:53Z'
tags:
  - edison-core
  - cli-ux
  - sessions
  - psutil
---
# Chore: session id inference

<!-- EXTENSIBLE: Summary -->
## Summary

Session ID detection/inference must “just work” across *all* Edison commands without requiring LLMs to pass `--session`, except when explicitly resuming a different session.

<!-- /EXTENSIBLE: Summary -->

<!-- EXTENSIBLE: Wave -->
## Wave / Parallelization

- **Wave:** 1 (foundation)
- **Safe to run in parallel with:** none (recommended to run first; many other tasks assume session inference works)
- **Do not run in parallel with:** any task modifying `src/edison/core/session/core/id.py` or `src/edison/core/utils/process/inspector.py`

<!-- /EXTENSIBLE: Wave -->

<!-- EXTENSIBLE: ProblemStatement -->
## Problem Statement

In beta sessions, LLMs repeatedly hit errors like:
- `No session could be resolved. Set AGENTS_SESSION ...`
- CLIs requiring an explicit session id even though Edison intends to infer it.

Observed root causes in Edison core:
1) Process-tree session inference is unreliable when `psutil` is absent (falls back to `python` + current PID, which changes across tool invocations).
2) Some CLIs require positional `session_id` and don’t attempt canonical auto-resolution.
3) `.session-id` is intended as *worktree-only*, but the canonical resolver currently reads it even in the primary checkout (must be gated).
4) CLI help/output does not strongly teach the intended rule: **do not pass `--session` unless resuming a different/older session**.

<!-- /EXTENSIBLE: ProblemStatement -->

<!-- EXTENSIBLE: Objectives -->
## Objectives

- [ ] Make `psutil` a required dependency so process-tree inference is reliable across platforms.
- [ ] Ensure the canonical resolver (`src/edison/core/session/core/id.py`) follows the intended priority: explicit → `AGENTS_SESSION` → worktree `.session-id` → process-derived → owner-based best-effort.
- [ ] Ensure `.session-id` is consulted **only** inside linked git worktrees (never in primary checkout).
- [ ] Ensure *every* CLI that needs a session auto-resolves it by default (no required positional session id unless the command is inherently multi-session).
- [ ] Ensure CLI help/output consistently teaches: “omit `--session` unless resuming.”
- [ ] Make process-derived lookup robust when multiple sessions exist for the same `{process}-pid-{pid}` prefix (because session IDs may include `-seq-N` suffixes for uniqueness).

<!-- /EXTENSIBLE: Objectives -->

<!-- EXTENSIBLE: AcceptanceCriteria -->
## Acceptance Criteria

- [ ] `psutil` is declared as a required dependency in `pyproject.toml` and process inference no longer silently degrades to unstable `python-pid-<current>` behavior.
- [ ] `.session-id` is only read/written/used inside linked worktrees; primary checkout never consults it for session resolution.
- [ ] After `edison session create` (with no `--session-id`), **all session-scoped commands** work without `--session` when run from the same controlling process context (orchestrator/LLM), including at minimum:
  - `edison session status` (no args)
  - `edison session next` (no args)
  - `edison task claim <task-id>` (with `--session` omitted)
  - `edison task ready <task-id>` (with `--session` omitted)
  - `edison qa bundle <task-id>` (with `--session` omitted)
  - `edison qa validate <task-id> --dry-run` (with `--session` omitted)
  - `edison qa promote <task-id> --status <...>` (with `--session` omitted, where applicable)
- [ ] When no session can be resolved, the error message is actionable and explicitly instructs:
  - “Most users should NOT pass `--session`.”
  - “To resume a previous session, pass `--session <id>`.”
  - How to discover existing sessions (e.g., `edison session status <id>` / session listing if available).
- [ ] If multiple sessions exist for the same inferred process prefix (e.g., `claude-pid-12345` and `claude-pid-12345-seq-1`), auto-resolution chooses the most appropriate existing session deterministically (prefer semantic active state; fall back to most-recently-updated).
- [ ] Add/adjust unit tests so session detection is deterministic and not dependent on the developer’s real process tree.

<!-- /EXTENSIBLE: AcceptanceCriteria -->

<!-- EXTENSIBLE: TechnicalDesign -->
## Technical Design

Constraints:
- Do not introduce competing session resolution logic. `edison.core.session.core.id.detect_session_id/require_session_id` remains the single source of truth.
- Prefer small focused modules; avoid monolithic “session utils” files.

Implementation outline:
1) Dependency:
   - Add `psutil` to `pyproject.toml` dependencies (required, not optional).

2) Canonical resolver updates:
   - Update `src/edison/core/session/core/id.py`:
     - Gate `<project-management-dir>/.session-id` resolution behind `edison.core.utils.git.worktree.is_worktree()`.
     - Keep the priority order unchanged otherwise.
     - Improve “process-derived lookup” to handle session-id suffixes:
       - derive the process prefix `"{process}-pid-{pid}"`
       - find candidate sessions whose id is exactly the prefix or starts with `"{prefix}-seq-"`
       - prefer candidates in semantic active state (from `WorkflowConfig`), else sort by last updated and pick the newest
       - this must remain within the canonical resolver (no separate second resolver elsewhere)

3) Process-tree inspector:
   - Update `src/edison/core/utils/process/inspector.py`:
     - Make psutil mandatory and remove the unstable `("python", os.getpid())` fallback for normal operation (keep any fallback only as last-ditch defense).
     - Fix the selection algorithm so `{process}-pid-{pid}` is stable across repeated CLI invocations inside IDE wrappers:
       - If a known LLM wrapper process exists in the parent chain (e.g. `claude`, `codex`, `cursor`, `gemini`, etc.), prefer the **highest such LLM** and use its PID (stable for the session).
       - Otherwise, prefer the highest Edison orchestrator/CLI process in the chain (where Edison is the true “topmost process”, e.g. launched by `edison orchestrator launch`).
       - Only fall back to the current process when neither can be detected.
     - Keep “python → edison” normalization using `_is_edison_script(cmdline)` so Edison scripts are classified as `edison` even when the OS process name is `python`.

4) CLI surfaces:
   - Audit CLIs that currently require explicit session id and align them to canonical auto-resolution (notably `src/edison/cli/session/next.py`).
   - Update CLI help and success output (especially `src/edison/cli/session/create.py`) to reinforce: “omit `--session` unless resuming.”
    - Ensure the canonical “session id required” error message in `require_session_id()` is coherent with the intended UX:
      - “Most users should NOT pass `--session`.”
      - “To resume a previous session explicitly, pass `--session <id>`.”
      - Mention `.session-id` as worktree-only and `AGENTS_SESSION` as the primary checkout escape hatch.

<!-- /EXTENSIBLE: TechnicalDesign -->

<!-- EXTENSIBLE: FilesToModify -->
## Files to Create/Modify

<!-- List files that will be changed -->
```
# Modify
pyproject.toml
src/edison/core/utils/process/inspector.py
src/edison/core/session/core/id.py
src/edison/cli/session/next.py
src/edison/cli/session/create.py

# Tests (add/update as appropriate)
tests/**/*
```

<!-- /EXTENSIBLE: FilesToModify -->

<!-- EXTENSIBLE: TDDEvidence -->
## TDD Evidence

### RED Phase
<!-- Link to failing test output -->
- Test file: 
- Output: 

### GREEN Phase
<!-- Link to passing test output -->
- Output: 

### REFACTOR Phase
<!-- Notes on refactoring performed -->
- Notes: 

<!-- /EXTENSIBLE: TDDEvidence -->

<!-- EXTENSIBLE: VerificationChecklist -->
## Verification Checklist

- [ ] `pytest -q` passes
- [ ] `edison session create` (no args) works and prints a clear message about inferred session id
- [ ] The acceptance-criteria commands above resolve without `--session`
- [ ] Resolver never consults `.session-id` in primary checkout (only linked worktrees)

<!-- /EXTENSIBLE: VerificationChecklist -->

<!-- EXTENSIBLE: SuccessCriteria -->
## Success Criteria

LLMs stop “cargo-culting” `--session` everywhere:
- process-derived sessions are stable under IDE wrappers (Claude/Codex/etc.)
- session-scoped CLIs work without explicit session id in the normal happy path
- help text and errors teach the intended default

<!-- /EXTENSIBLE: SuccessCriteria -->

<!-- EXTENSIBLE: RelatedFiles -->
## Related Files

- Canonical resolver: `src/edison/core/session/core/id.py`
- Process inspector: `src/edison/core/utils/process/inspector.py`
- Session naming: `src/edison/core/session/core/naming.py`
- Worktree session-id persistence: `src/edison/core/session/worktree/manager.py` (`_ensure_worktree_session_id_file`)
- Worktree detection: `src/edison/core/utils/git/worktree.py`
- CLI helper wrapper: `src/edison/cli/_utils.py` (`resolve_session_id` wrapper)

<!-- /EXTENSIBLE: RelatedFiles -->

<!-- EXTENSIBLE: Notes -->
## Notes

This task is foundational: if session inference is unreliable, LLMs will keep over-specifying `--session` and the workflow will drift.

<!-- /EXTENSIBLE: Notes -->
