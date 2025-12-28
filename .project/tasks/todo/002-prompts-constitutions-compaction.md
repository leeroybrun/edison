---
id: 002-prompts-constitutions-compaction
title: 'Chore: prompts constitutions compaction'
created_at: '2025-12-28T10:00:54Z'
updated_at: '2025-12-28T10:00:54Z'
tags:
  - edison-core
  - prompts
  - constitutions
  - hooks
depends_on:
  - 003-validation-presets
  - 004-stale-sessions-resumable
---
# Chore: prompts constitutions compaction

<!-- EXTENSIBLE: Summary -->
## Summary

Make Edison’s “happy path” durable across context compaction by moving session-long guidance into constitutions (via include-only files), keeping start prompts bootstrap-only, and enforcing post-compaction constitution re-read via hooks.

<!-- /EXTENSIBLE: Summary -->

<!-- EXTENSIBLE: Wave -->
## Wave / Parallelization

- **Wave:** 3 (prompts/docs/hooks)
- **Safe to run in parallel with:** none (this task touches many shared docs/prompts/hook templates)
- **Depends on:** `004-stale-sessions-resumable` (so stale/resume prompts can reference real commands) and `003-validation-presets` (so durable guidance for “quick preset” is accurate)

<!-- /EXTENSIBLE: Wave -->

<!-- EXTENSIBLE: ProblemStatement -->
## Problem Statement

Beta feedback highlights recurring orchestration failures that are not code bugs but “guidance visibility” failures:
- LLMs forget to read constitutions and drift after compaction.
- Start prompts help at session start, but compaction drops them; constitutions are what get re-read.
- Important rules are missing or unclear at the moment decisions happen (worktree/no-worktree, parallelism, grouped validation, “don’t pass session id unless resuming”).
- Some start prompts reference non-existent commands (must never ship).
- Documentation drift exists (docs contradict actual storage semantics).
- Validation-first guidance lacked nuance for docs-only work, causing orchestrators to get blocked until using `--force` instead of being guided into a light, policy-approved validation path.

We must fix this following `docs/PROMPT_DEVELOPMENT.md`:
- Single source of truth via include-only files under `guidelines/includes/`.
- No double-loading: if the same content is needed in both constitutions and start prompts, extract into a shared include and include the appropriate sections (bootstrap vs durable).

<!-- /EXTENSIBLE: ProblemStatement -->

<!-- EXTENSIBLE: Objectives -->
## Objectives

- [ ] Create a canonical include-only file for durable orchestration gates under `src/edison/data/guidelines/includes/` with role-specific sections.
- [ ] Ensure ORCHESTRATOR constitution includes the durable orchestration gate section (compaction-safe).
- [ ] Ensure all start prompts include only a small bootstrap section (and reuse shared include sections to avoid duplication).
- [ ] Implement/adjust compaction hooks so they explicitly require re-reading the constitution (directive, not informational).
- [ ] Ensure start prompts reference only real CLIs (either implement missing CLIs or update prompts to match reality).
- [ ] Fix documentation drift for task/QA file locations and state semantics.
- [ ] Make session-long “workflow stickiness” improvements durable: delegation/parallelism gates, tracking/validation reminders, worktree/no-worktree decision gate, and meta-worktree symlink realities (e.g. `specs/`) must be present in the ORCHESTRATOR constitution via includes (not only start prompts).
- [ ] Clarify Context7 expectations at the point of use (constitutions/guidelines): “post-training packages” are defined only by config, discoverable via `edison config show context7 --format yaml`, and are irrelevant for docs-only changes.
- [ ] Add explicit orchestration guidance for “docs-only / quick preset” so the validation-first rule remains principled without blocking progress unnecessarily:
  - validate using the configured quick preset path (single validator) and proceed
  - do not use `--force` as a routine escape hatch for docs-only work

<!-- /EXTENSIBLE: Objectives -->

<!-- EXTENSIBLE: AcceptanceCriteria -->
## Acceptance Criteria

- [ ] There is exactly one canonical include-only file for orchestration gates, and overlapping guidance is not duplicated elsewhere.
- [ ] ORCHESTRATOR constitution includes the durable orchestration gates, so re-reading it after compaction restores key rules.
- [ ] All start prompts under `src/edison/data/start/*.md` include a bootstrap include section and do not duplicate durable gate content.
- [ ] Compaction hook output explicitly instructs the user/LLM to re-read the appropriate constitution with the exact command.
- [ ] Start prompts do not reference missing CLIs.
- [ ] `docs/WORKFLOWS.md` is corrected so it matches actual session-scoped storage semantics (global vs session queues).
- [ ] `edison compose all` succeeds after changes (no broken includes/sections).

<!-- /EXTENSIBLE: AcceptanceCriteria -->

<!-- EXTENSIBLE: TechnicalDesign -->
## Technical Design

Constraints:
- Follow `docs/PROMPT_DEVELOPMENT.md` strictly (single truth, no double-loading, role-specific includes).
- Avoid adding new “monolithic” prompt docs; use includes with clear sections.

Implementation outline:
1) Create a new include-only file, e.g. `src/edison/data/guidelines/includes/ORCHESTRATION_GATES.md`, with sections such as:
   - `#orchestrator-session-long` (durable; included by ORCHESTRATOR constitution)
   - `#start-bootstrap` (minimal; included by start prompts)
   Ensure any overlap appears once in this include and is referenced by both sections if necessary.

2) Update ORCHESTRATOR constitution template (or a guideline that is embedded in it) to include `#orchestrator-session-long`.

3) Update all start prompts under `src/edison/data/start/` to include `#start-bootstrap` and keep them bootstrap-only.

4) Compaction hook:
   - Locate the platform compaction hook implementation/templates.
   - Make compaction output directive (not informational) and provide exact commands. Current implementation is `src/edison/data/templates/hooks/compaction-reminder.sh.template` driven by `src/edison/data/config/hooks.yaml` (`hooks.definitions.compaction-reminder.config.message_template`).
   - Update the template/config so it prints something unambiguous like:
     - “MANDATORY: Re-read your constitution NOW (post-compaction): `edison read AGENTS --type constitutions` (or ORCHESTRATOR / VALIDATORS depending on your role).”
   - Do not add double-loaded content: the hook should print a short directive, and the constitution remains the durable source of truth.

5) Docs drift fixes:
   - Update `docs/WORKFLOWS.md` (and any other affected docs) to describe session-scoped storage accurately.
   - Update `docs/WORKTREES.md` (if needed) and/or orchestrator guidelines to explicitly mention meta-managed symlinked paths (e.g. `specs/`) and how commits for those must occur on the meta worktree/branch (do not bury this in troubleshooting).

<!-- /EXTENSIBLE: TechnicalDesign -->

<!-- EXTENSIBLE: FilesToModify -->
## Files to Create/Modify

<!-- List files that will be changed -->
```
# Create
src/edison/data/guidelines/includes/ORCHESTRATION_GATES.md

# Modify
src/edison/data/start/START_AUTO_NEXT.md
src/edison/data/start/START_NEW_SESSION.md
src/edison/data/start/START_RESUME_SESSION.md
src/edison/data/start/START_VALIDATE_SESSION.md
src/edison/data/start/START_CLEANUP.md
src/edison/data/start/START_CONTINUE_STALE.md
docs/WORKFLOWS.md
docs/WORKTREES.md
src/edison/data/templates/hooks/* (if compaction hooks are templated here)
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

- [ ] `edison compose all` succeeds
- [ ] Start prompts render without broken includes
- [ ] Compaction hook output is directive and includes exact re-read command
- [ ] Docs no longer contradict storage semantics

<!-- /EXTENSIBLE: VerificationChecklist -->

<!-- EXTENSIBLE: SuccessCriteria -->
## Success Criteria

<!-- Define what success looks like -->

<!-- /EXTENSIBLE: SuccessCriteria -->

<!-- EXTENSIBLE: RelatedFiles -->
## Related Files

- Prompt development rules: `docs/PROMPT_DEVELOPMENT.md`
- Start prompts: `src/edison/data/start/*.md`
- Constitutions (generated): `.edison/_generated/constitutions/ORCHESTRATOR.md`
- Orchestrator workflow: `src/edison/data/guidelines/orchestrators/SESSION_WORKFLOW.md`
- Worktrees/meta: `docs/WORKTREES.md`

<!-- /EXTENSIBLE: RelatedFiles -->

<!-- EXTENSIBLE: Notes -->
## Notes

This task is intentionally “prompt-system refactoring”: correctness is measured by DRY composition and compaction resilience, not by feature changes.

<!-- /EXTENSIBLE: Notes -->
