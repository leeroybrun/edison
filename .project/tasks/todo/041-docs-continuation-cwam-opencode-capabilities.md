---
id: 041-docs-continuation-cwam-opencode-capabilities
title: "Docs: Continuation (FC/RL), CWAM, and OpenCode integration + capability matrix"
owner: leeroy
created_at: '2025-12-31T10:12:24Z'
updated_at: '2025-12-31T10:12:24Z'
tags:
  - docs
  - continuation
  - cwam
  - opencode
depends_on:
  - 033-continuation-config-rules-session-schema
  - 034-session-next-completion-continuation-contract
  - 035-session-continuation-cli
  - 036-start-prompt-ralph-loop
  - 037-claude-hooks-stop-continuation-cwam
  - 038-pal-codex-prompts-cwam-continuation
  - 039-opencode-adapter-generate-plugin
  - 040-opencode-plugin-idle-enforcement-truncation
---
# Docs: Continuation (FC/RL), CWAM, and OpenCode integration + capability matrix

<!-- EXTENSIBLE: Summary -->
## Summary

Write minimal, non-overwhelming documentation for:
- Continuation system (FC + RL) and how to enable/disable/tune it
- CWAM (guidance + OpenCode truncation behavior)
- OpenCode support and setup (`edison opencode setup`, `.opencode/plugin/edison.ts`)
- A capability matrix that honestly explains what works in each client and why

<!-- /EXTENSIBLE: Summary -->

<!-- EXTENSIBLE: ProblemStatement -->
## Problem Statement

We explicitly want to avoid an “over-the-top / kitchen sink” impression.

These features touch multiple clients and can easily become confusing unless we:
- clearly define the Edison-native source of truth (session next + rules + config),
- explain per-client differences (what can be enforced vs guidance-only),
- keep docs short and navigable (one matrix + one page per feature).

<!-- /EXTENSIBLE: ProblemStatement -->

<!-- EXTENSIBLE: Objectives -->
## Objectives

- [ ] Add a “Client Capability Matrix” doc:
  - Codex CLI / Pal / Claude hooks / OpenCode plugin
  - what each can do (idle loop vs stop hook vs guidance-only)
- [ ] Add a “Continuation” doc:
  - what FC is, what RL is, how completion is computed (Edison-native, configurable policy)
  - how to enable RL per session (`edison session continuation set … --mode hard`)
  - how to disable or tune budgets
- [ ] Add a “CWAM” doc:
  - what it is, where it appears (session next/context/hooks/prompts)
  - what OpenCode truncation does and how to configure it
- [ ] Add an “OpenCode integration” doc:
  - what files are generated
  - how to run `edison opencode setup`
  - troubleshooting (edison not found in PATH; session id resolution)

<!-- /EXTENSIBLE: Objectives -->

<!-- EXTENSIBLE: AcceptanceCriteria -->
## Acceptance Criteria

- [ ] Docs exist and are linked from a central place (README or docs index) without expanding the README into a wall of text.
- [ ] Capability matrix is honest: RL hard loop is only enforceable in OpenCode; Claude is stop-hook only; Pal/Codex are guidance-only.
- [ ] Docs explicitly state “we implement concepts, not oh-my-opencode code” and do not reference copying their implementation.

<!-- /EXTENSIBLE: AcceptanceCriteria -->

<!-- EXTENSIBLE: TechnicalDesign -->
## Technical Design

Prefer a small set of docs files:
- `docs/features/continuation.md`
- `docs/features/context-window-anxiety-management.md`
- `docs/integrations/opencode.md`
- `docs/capabilities/clients.md`

Keep docs implementation-oriented:
- commands to run
- config keys to set
- common failure modes

Avoid narrative fluff and giant lists of features.

<!-- /EXTENSIBLE: TechnicalDesign -->

<!-- EXTENSIBLE: FilesToModify -->
## Files to Create/Modify

```
# Create
docs/capabilities/clients.md
docs/features/continuation.md
docs/features/context-window-anxiety-management.md
docs/integrations/opencode.md

# Modify
README.md  # add minimal links only (do not bloat)
docs/README.md  # if a docs index exists
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

<!-- /EXTENSIBLE: RelatedFiles -->

<!-- EXTENSIBLE: Notes -->
## Notes

<!-- Additional notes, context, or considerations -->

<!-- /EXTENSIBLE: Notes -->
