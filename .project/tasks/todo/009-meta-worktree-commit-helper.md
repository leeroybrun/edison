---
id: 009-meta-worktree-commit-helper
title: 'Chore: meta worktree commit helper'
created_at: '2025-12-28T11:30:30Z'
updated_at: '2025-12-28T11:30:30Z'
tags:
  - edison-core
  - git
  - worktrees
  - meta
  - cli-ux
depends_on:
  - 002-prompts-constitutions-compaction
---
# Chore: meta worktree commit helper

<!-- EXTENSIBLE: Summary -->
## Summary

Add a small helper command to reduce confusion when repositories use meta-worktree shared state (e.g. `specs/` symlinked to the meta branch). The helper should make it obvious when changes must be committed on the meta branch and provide a safe, guided workflow to do so.

<!-- /EXTENSIBLE: Summary -->

<!-- EXTENSIBLE: Wave -->
## Wave / Parallelization

- **Wave:** 6 (meta UX)
- **Safe to run in parallel with:** none recommended (often touches docs that also change elsewhere)
- **Depends on:** `002-prompts-constitutions-compaction` (so docs/prompt guidance about meta/shared state is consistent)

<!-- /EXTENSIBLE: Wave -->

<!-- EXTENSIBLE: ProblemStatement -->
## Problem Statement

In meta shared-state mode (`worktrees.sharedState.mode: meta`), many repo-root paths are symlinked into the primary/session worktrees but are actually owned by the meta worktree/branch (default `edison-meta`). Beta testers reported confusion because:
- they committed code changes in the session/code branch
- then discovered `specs/` (and potentially other shared paths) required a separate commit in the meta worktree

Today this is documented, but still easy to miss in the moment. We want a CLI helper that:
- detects meta mode and the meta worktree path/branch
- shows whether the meta worktree is dirty and which shared paths changed
- provides guided commands to commit meta changes safely

This is defense-in-depth for usability; it does not replace documentation.

<!-- /EXTENSIBLE: ProblemStatement -->

<!-- EXTENSIBLE: Objectives -->
## Objectives

- [ ] Add a CLI helper to inspect meta shared-state status, including dirty state and changed paths under `worktrees.sharedState.sharedPaths`.
- [ ] Add an optional guided “commit meta” action that runs `git commit` in the meta worktree (subject to existing commit guard).
- [ ] Ensure the helper is safe-by-default: it must not switch branches in the primary checkout and must not run destructive git commands unless explicitly requested.

<!-- /EXTENSIBLE: Objectives -->

<!-- EXTENSIBLE: AcceptanceCriteria -->
## Acceptance Criteria

- [ ] A new command exists (exact naming up to implementation, but must be documented), e.g.:
  - `edison git meta status`
  - `edison git meta commit -m "..."` (explicit message required)
- [ ] `edison git meta status` prints:
  - whether `worktrees.sharedState.mode` is `meta`
  - the resolved meta worktree path (from config `worktrees.sharedState.metaPathTemplate`)
  - the meta branch name (from config `worktrees.sharedState.metaBranch`)
  - whether the meta worktree has uncommitted changes
  - a list of changed files limited to configured shared paths (best effort)
- [ ] If the meta worktree is missing, command output includes the fix command: `edison git worktree-meta-init`.
- [ ] `edison git meta commit -m ...` runs `git commit` inside the meta worktree directory only (no branch switches in primary).
- [ ] Unit tests cover:
  - meta mode detection from config
  - meta path resolution
  - output behavior when meta worktree is missing

<!-- /EXTENSIBLE: AcceptanceCriteria -->

<!-- EXTENSIBLE: TechnicalDesign -->
## Technical Design

Constraints:
- Reuse existing worktree configuration and path resolution (`src/edison/data/config/worktrees.yaml`).
- Do not create competing worktree logic. Use existing core helpers for worktree/meta path discovery if present; otherwise add a small focused helper module.
- Keep “commit” strictly opt-in and explicit.

Implementation outline:
1) Config access:
   - Read `worktrees.sharedState.mode`, `metaBranch`, `metaPathTemplate`, and `sharedPaths` using the existing config system.
   - Resolve the meta worktree path the same way `edison git worktree-meta-init` does (prefer reusing its helpers).

2) Status:
   - Determine if meta worktree exists and is a git repo.
   - Determine dirty state via `git status --porcelain` executed in the meta worktree directory.
   - Optionally filter displayed paths to configured `sharedPaths` (so users see only relevant changes).

3) Commit:
   - Require `-m/--message` and run `git commit` in the meta worktree directory.
   - Do not implement “commit in both code + meta” here (that may be a future follow-up); focus on making meta commits obvious and easy.

<!-- /EXTENSIBLE: TechnicalDesign -->

<!-- EXTENSIBLE: FilesToModify -->
## Files to Create/Modify

```
# Create (suggested)
src/edison/cli/git/meta.py (or git subcommand group)
src/edison/core/git/meta.py (small helper for resolving meta path, if needed)

# Modify (only if needed to reuse canonical helpers)
src/edison/cli/git/worktree_meta_init.py
docs/WORKTREES.md (only if documenting the new helper)

# Tests
tests/**/*
```

<!-- /EXTENSIBLE: FilesToModify -->

<!-- EXTENSIBLE: TDDEvidence -->
## TDD Evidence

### RED Phase
- Test file:
- Output:

### GREEN Phase
- Output:

### REFACTOR Phase
- Notes:

<!-- /EXTENSIBLE: TDDEvidence -->

<!-- EXTENSIBLE: VerificationChecklist -->
## Verification Checklist

- [ ] `pytest -q` passes
- [ ] In a repo with meta mode enabled, `edison git meta status` shows meta path/branch and dirty state
- [ ] If meta worktree is missing, output suggests `edison git worktree-meta-init`
- [ ] `edison git meta commit -m "..."` attempts a commit inside meta worktree

<!-- /EXTENSIBLE: VerificationChecklist -->

<!-- EXTENSIBLE: SuccessCriteria -->
## Success Criteria

Users/LLMs stop being surprised by “specs/ is symlinked”: the CLI makes meta changes visible and provides an obvious, safe way to commit them.

<!-- /EXTENSIBLE: SuccessCriteria -->

<!-- EXTENSIBLE: RelatedFiles -->
## Related Files

- Meta/shared-state config: `src/edison/data/config/worktrees.yaml`
- Meta worktree init: `src/edison/cli/git/worktree_meta_init.py`
- Worktrees docs: `docs/WORKTREES.md`

<!-- /EXTENSIBLE: RelatedFiles -->

<!-- EXTENSIBLE: Notes -->
## Notes

This is primarily a UX task. It should not attempt to automatically merge meta into code branches; it should just expose state and guide the user.

<!-- /EXTENSIBLE: Notes -->
