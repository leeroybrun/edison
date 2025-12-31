---
id: 036-start-prompt-ralph-loop
title: "Prompts: Add optional `START_RALPH_LOOP` start prompt (RL enablement)"
owner: leeroy
created_at: '2025-12-31T10:12:18Z'
updated_at: '2025-12-31T10:12:18Z'
tags:
  - prompts
  - start
  - continuation
depends_on:
  - 035-session-continuation-cli
---
# Prompts: Add optional `START_RALPH_LOOP` start prompt (RL enablement)

<!-- EXTENSIBLE: Summary -->
## Summary

Add a new optional start prompt that explains the Ralph Loop mode and shows exactly how to enable it for a session using Edison-native controls.

<!-- /EXTENSIBLE: Summary -->

<!-- EXTENSIBLE: ProblemStatement -->
## Problem Statement

Ralph Loop (hard continuation) is intentionally opt-in. We need a clean, discoverable “start prompt” that:
- does not bloat default start flows,
- can be requested explicitly via `edison session create --prompt START_RALPH_LOOP`,
- teaches the Edison-native way (no transcript `<promise>` markers, no ad-hoc loops): enable mode in Edison, then follow `session next`.

<!-- /EXTENSIBLE: ProblemStatement -->

<!-- EXTENSIBLE: Objectives -->
## Objectives

- [ ] Add `src/edison/data/start/START_RALPH_LOOP.md` with short, precise guidance.
- [ ] Ensure it references existing Edison primitives:
  - constitution re-read command
  - loop driver (`edison session next <session-id>`)
  - RL enablement command (`edison session continuation set <sid> --mode hard ...`)
- [ ] Ensure the prompt is model-agnostic and does not mention client-specific implementation details (OpenCode toasts, etc.).

<!-- /EXTENSIBLE: Objectives -->

<!-- EXTENSIBLE: AcceptanceCriteria -->
## Acceptance Criteria

- [ ] `edison list --type start` (or the equivalent Edison list command) shows `START_RALPH_LOOP` after composition.
- [ ] `edison session create --prompt START_RALPH_LOOP` prints the new prompt correctly.
- [ ] The prompt is short (no “kitchen sink” feel) and fully Edison-native.

<!-- /EXTENSIBLE: AcceptanceCriteria -->

<!-- EXTENSIBLE: TechnicalDesign -->
## Technical Design

The start prompt should include:
- A one-paragraph explanation of RL (hard continuation) and when to use it.
- A minimal “how to enable” snippet:
  - identify session id
  - run `edison session continuation set <sid> --mode hard`
- A reminder that “done” means Edison completion criteria (as surfaced by `session next`), not a `<promise>` marker.

<!-- /EXTENSIBLE: TechnicalDesign -->

<!-- EXTENSIBLE: FilesToModify -->
## Files to Create/Modify

```
# Create
src/edison/data/start/START_RALPH_LOOP.md

# Modify
src/edison/data/config/composition.yaml  # only if start prompts require registry changes (likely not)
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

- [ ] Tests pass locally
- [ ] Linting passes
- [ ] Type checking passes
- [ ] Documentation updated
- [ ] TDD evidence captured

<!-- /EXTENSIBLE: VerificationChecklist -->

<!-- EXTENSIBLE: SuccessCriteria -->
## Success Criteria

<!-- Define what success looks like -->

<!-- /EXTENSIBLE: SuccessCriteria -->

<!-- EXTENSIBLE: RelatedFiles -->
## Related Files

- Plan: `.project/plans/2025-12-31-continuation-ralph-loop-cwam-opencode.md`
- Existing start prompt example: `src/edison/data/start/START_AUTO_NEXT.md`

<!-- /EXTENSIBLE: RelatedFiles -->

<!-- EXTENSIBLE: Notes -->
## Notes

- Keep this prompt optional; do not alter default start prompts to include RL.

<!-- /EXTENSIBLE: Notes -->
