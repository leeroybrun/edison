---
id: 007-session-auto-merge
title: 'Chore: session auto merge'
created_at: '2025-12-28T10:00:56Z'
updated_at: '2025-12-28T10:00:56Z'
tags:
  - edison-core
  - sessions
  - git
  - merge
depends_on:
  - 005-tampering-protection-module
  - 009-meta-worktree-commit-helper
---
# Chore: session auto merge

<!-- EXTENSIBLE: Summary -->
## Summary

Add a configurable, safe-by-default “session end auto-merge” pipeline that merges a session worktree branch back to the base branch, with optional AI-assisted conflict resolution and explicit human approval gates.

<!-- /EXTENSIBLE: Summary -->

<!-- EXTENSIBLE: Wave -->
## Wave / Parallelization

- **Wave:** 7 (high-risk git lifecycle; last)
- **Safe to run in parallel with:** none (touches session lifecycle, config, and safety-sensitive git behavior)
- **Depends on:** `005-tampering-protection-module` (verify/logging may be extended there) and `009-meta-worktree-commit-helper` (meta/shared-state awareness)

<!-- /EXTENSIBLE: Wave -->

<!-- EXTENSIBLE: ProblemStatement -->
## Problem Statement

Desired Edison behavior: when a session is complete, it should be able to merge the session worktree back into the main/base branch in a controlled way:
- never switching branches in the primary checkout
- preserving safety constraints
- handling conflicts with configurable policy (manual, AI-assisted, auto-safe-only)
- recording evidence and requiring human approval where appropriate

Auto-Claude implements a similar flow (AI-assisted merge conflict resolution). Edison should provide an equivalent but configurable mechanism aligned with Edison’s evidence + validation model.

<!-- /EXTENSIBLE: ProblemStatement -->

<!-- EXTENSIBLE: Objectives -->
## Objectives

<!-- List specific, measurable objectives with checkboxes -->
- [ ] Define configuration for merge strategy and conflict handling (merge-no-ff default recommended).
- [ ] Implement merge in an isolated worktree/workspace (never change primary checkout HEAD).
- [ ] Implement conflict detection + conflict resolution pipeline:
  - safe-only auto resolution for configured safe paths (e.g., lockfiles)
  - AI-assisted proposals for other conflicts (must require human approval before applying)
- [ ] Ensure post-merge automation can run and record evidence.
- [ ] Integrate with session close/complete lifecycle in a way that is safe and opt-in via config.
- [ ] Handle meta-worktree/shared-state reality: merging the session code branch must not pretend it “merged everything” if the meta branch contains unmerged commits (warn + guidance).

<!-- /EXTENSIBLE: Objectives -->

<!-- EXTENSIBLE: AcceptanceCriteria -->
## Acceptance Criteria

<!-- List specific criteria that must be met for task completion -->
- [ ] A project can enable/disable auto-merge via config.
- [ ] Default merge strategy is configurable; recommended default is merge commit (`merge --no-ff`).
- [ ] Merge pipeline never switches primary checkout branches.
- [ ] Conflicts are handled according to configured policy; non-safe conflicts require explicit human approval before being written.
- [ ] Evidence is written for merge actions (commands run, conflict resolution decisions).
- [ ] If the repository uses meta worktree shared state, the merge pipeline detects and warns when meta branch has commits/dirty state that also need handling (no silent omission).
- [ ] Tests cover “no conflict” merge path and basic conflict detection logic (AI resolver can be mocked at boundary).

<!-- /EXTENSIBLE: AcceptanceCriteria -->

<!-- EXTENSIBLE: TechnicalDesign -->
## Technical Design

Constraints:
- This is a high-risk feature. Keep it behind config flags and implement incrementally:
  1) merge preview/dry-run
  2) merge execution without conflicts
  3) conflict detection
  4) safe-path auto resolutions
  5) AI-assisted proposals + approval gate

Implementation outline:
1) Config (single source):
   - Add config under `session.merge` (location: `src/edison/data/config/session.yaml` or `git.yaml`; pick the canonical home and keep DRY):
     - `session.merge.enabled: false` (default off)
     - `session.merge.strategy: merge_no_ff | squash | rebase` (default merge_no_ff)
     - `session.merge.targetBranch: <ref>` (default from session base branch)
     - `session.merge.conflicts.mode: manual | ai_assist | ai_auto_safe_only` (default ai_assist)
     - `session.merge.conflicts.safeGlobs: [...]` (default lockfiles / generated artifacts)
     - `session.merge.postMerge.runAutomation: true|false` and how evidence is captured

2) Core pipeline (new package, small focused modules):
   - Add a small `src/edison/core/session/merge/` package for:
     - planning: resolve base/target refs without mutating primary checkout
     - execution: run merge in an isolated worktree directory (temporary)
     - conflict detection: identify conflicted files + conflict markers
     - safe auto-resolve: strategies for safeGlobs only (purely mechanical)
     - ai boundary (optional): generate proposed resolutions; applying still requires explicit human approval unless in safe-only mode

3) CLI:
   - Add `edison session merge` with:
     - `--dry-run` (prints plan + what would happen)
     - `--execute` (runs merge)
     - `--session <id>` optional (but should integrate with the global session-id inference policy from task 001)
   - CLI must refuse to run in the primary checkout unless it can guarantee no branch switching occurs (prefer operating in a temporary worktree under the worktrees root).

4) Integration:
   - Integrate into session end lifecycle behind config:
     - The safest integration point is `edison session complete` or a new explicit `edison session close --merge` flag (opt-in).
     - Never auto-merge by default just because a session is validated/closing.

5) Meta worktree awareness:
   - If worktrees.sharedState.mode is meta (default in this repo), then:
     - session worktrees contain symlinks to meta-managed paths (e.g. `specs/`, `.project/*`)
     - code-branch merge does not include those changes
   - The merge pipeline must detect and warn when meta worktree/branch has unmerged commits or dirty state and provide guidance (e.g., “commit/merge meta separately”).

<!-- /EXTENSIBLE: TechnicalDesign -->

<!-- EXTENSIBLE: FilesToModify -->
## Files to Create/Modify

<!-- List files that will be changed -->
```
# Create
src/edison/core/session/merge/... (new package, small focused modules)
src/edison/cli/session/merge.py (or grouped under session subcommands)

# Modify
src/edison/core/session/lifecycle/verify.py / complete flow (only when enabled; keep opt-in)
src/edison/data/config/session.yaml (or src/edison/data/config/git.yaml; choose canonical home and document)
docs/WORKTREES.md / docs/WORKFLOWS.md (document merge behavior and safety)
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
- [ ] `edison session merge --dry-run` prints a plan without mutating primary checkout
- [ ] `edison session merge --execute` succeeds on a no-conflict scenario and records evidence
- [ ] Conflict path prints proposed resolutions and requires explicit approval before applying (unless safe-only policy)
- [ ] When meta mode is enabled, merge warns if meta branch has pending commits/dirty state

<!-- /EXTENSIBLE: VerificationChecklist -->

<!-- EXTENSIBLE: SuccessCriteria -->
## Success Criteria

Session close-out can merge session branches back safely, with clear human approval gates, and without falsely claiming meta-managed shared-state changes were merged.

<!-- /EXTENSIBLE: SuccessCriteria -->

<!-- EXTENSIBLE: RelatedFiles -->
## Related Files

- Worktree/meta model: `docs/WORKTREES.md`
- Session verification/close-out: `src/edison/core/session/lifecycle/verify.py`, `src/edison/cli/session/complete.py`
- Session creation/worktree management: `src/edison/core/session/worktree/manager.py`
- Git constraints (primary checkout safety): `src/edison/data/guidelines/shared/GIT_WORKFLOW.md`

<!-- /EXTENSIBLE: RelatedFiles -->

<!-- EXTENSIBLE: Notes -->
## Notes

Implement in small slices and keep the default strictly opt-in. This feature is high-risk and should not run automatically without explicit project config enabling it.

<!-- /EXTENSIBLE: Notes -->
