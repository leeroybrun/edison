---
id: 038-pal-codex-prompts-cwam-continuation
title: "Prompts: Pal + Codex alignment for CWAM + continuation guidance"
owner: leeroy
created_at: '2025-12-31T10:12:20Z'
updated_at: '2025-12-31T10:12:20Z'
tags:
  - prompts
  - pal
  - codex
  - cwam
  - continuation
depends_on:
  - 033-continuation-config-rules-session-schema
---
# Prompts: Pal + Codex alignment for CWAM + continuation guidance

<!-- EXTENSIBLE: Summary -->
## Summary

Ensure “for all clients” guidance exists even where we cannot enforce idle loops:
- Pal prompt composition should include minimal CWAM + “don’t stop early” guidance.
- Codex-facing prompts (via composed agent prompts and/or core guideline injection) should include the same minimal guidance without bloating.

<!-- /EXTENSIBLE: Summary -->

<!-- EXTENSIBLE: ProblemStatement -->
## Problem Statement

Some clients are prompt-only:
- Pal is a prompt composition surface.
- Codex adapter mainly syncs prompts (no idle hooks).

We want consistent “don’t stop early” and “don’t rush due to context anxiety” behavior across these clients, but:
- prompts must remain short,
- prose must be single-source where possible (rules / shared includes),
- we must avoid the “kitchen sink” vibe.

<!-- /EXTENSIBLE: ProblemStatement -->

<!-- EXTENSIBLE: Objectives -->
## Objectives

- [ ] Pal: include a tiny CWAM + continuation block in `compose_pal_prompt` output, sourced from rules/context (not hardcoded text).
- [ ] Codex: ensure composed agent prompts (synced to `.codex/prompts`) include the same tiny guidance (prefer a shared include fragment, not copy/paste).
- [ ] Make it config-controlled so projects can tune/disable verbosity.

<!-- /EXTENSIBLE: Objectives -->

<!-- EXTENSIBLE: AcceptanceCriteria -->
## Acceptance Criteria

- [ ] Pal prompt output contains a “Context window / don’t rush” line and a “do not stop until Edison indicates completion” line when enabled.
- [ ] Codex prompts contain the same guidance with minimal additional tokens.
- [ ] Guidance text is authored once (rules or shared include), not duplicated across many files.

<!-- /EXTENSIBLE: AcceptanceCriteria -->

<!-- EXTENSIBLE: TechnicalDesign -->
## Technical Design

<!-- Optional: Include technical design details, code snippets, diagrams -->
### Pal

Modify `src/edison/core/adapters/platforms/pal/composer.py`:
- Pull rules using `RulesEngine.get_rules_for_context("context_window")` and `RulesEngine.get_rules_for_context("continuation")` (or whichever canonical context names are chosen in task `033-*`).
- Append a minimal section (2–4 lines max) to the Pal prompt, e.g.:
  - CWAM reassurance line
  - “Do not stop until `edison session next` indicates completion.”

Keep this section strictly config-controlled (enable/disable and max length).

### Codex

Codex integration is prompt-sync driven (`src/edison/core/adapters/platforms/codex.py`).

Implement one of:
- Add a shared include fragment in Edison’s composed agent prompt templates that contains CWAM + continuation guidance (preferred).
- Or extend a single central composed prompt section that all Codex prompts share.

Do not copy/paste the guidance into multiple agent files.

<!-- /EXTENSIBLE: TechnicalDesign -->

<!-- EXTENSIBLE: FilesToModify -->
## Files to Create/Modify

<!-- List files that will be changed -->
```
# Modify
src/edison/core/adapters/platforms/pal/composer.py
src/edison/data/agents/**  # whichever core prompt templates are the right single injection point
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

<!-- List related files for context -->
 - Plan: `.project/plans/2025-12-31-continuation-ralph-loop-cwam-opencode.md`
 - Rules engine: `src/edison/core/rules/engine.py`
 - Pal composer: `src/edison/core/adapters/platforms/pal/composer.py`

<!-- /EXTENSIBLE: RelatedFiles -->

<!-- EXTENSIBLE: Notes -->
## Notes

<!-- Additional notes, context, or considerations -->
- This task is guidance-only; enforcement is via OpenCode plugin and Claude hooks.

<!-- /EXTENSIBLE: Notes -->
