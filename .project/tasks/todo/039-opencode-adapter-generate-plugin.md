---
id: 039-opencode-adapter-generate-plugin
title: "OpenCode: Add Edison adapter + `edison opencode setup` + generate `.opencode/plugin/edison.ts`"
owner: leeroy
created_at: '2025-12-31T10:12:21Z'
updated_at: '2025-12-31T10:12:21Z'
tags:
  - opencode
  - adapters
  - composition
  - setup
depends_on:
  - 033-continuation-config-rules-session-schema
  - 034-session-next-completion-continuation-contract
  - 016-composition-external-mounts
---
# OpenCode: Add Edison adapter + `edison opencode setup` + generate `.opencode/plugin/edison.ts`

<!-- EXTENSIBLE: Summary -->
## Summary

Add first-class OpenCode support to Edison by generating project-local OpenCode plugin artifacts.

Key deliverable: `.opencode/plugin/edison.ts` generated from an Edison template, which uses OpenCode’s official plugin API and calls Edison CLI to get continuation/completion state.

<!-- /EXTENSIBLE: Summary -->

<!-- EXTENSIBLE: ProblemStatement -->
## Problem Statement

We want Edison continuation (FC/RL) and CWAM to work “for all clients”, but only OpenCode provides:
- true idle events (`session.idle`) and
- an official plugin injection API.

To keep Edison coherent:
- Edison core computes completion/continuation (`session next`).
- OpenCode plugin is a thin adapter that queries Edison and injects the returned prompt.

We need a clean Edison “platform adapter” and setup command so projects can opt-in without manual file juggling.

<!-- /EXTENSIBLE: ProblemStatement -->

<!-- EXTENSIBLE: Objectives -->
## Objectives

- [ ] Add a new platform adapter (`OpencodeAdapter`) to Edison’s adapter system.
- [ ] Add `composition.adapters.opencode` in `src/edison/data/config/composition.yaml`.
- [ ] Add a new `edison opencode setup` command that:
  - ensures `.opencode/plugin/edison.ts` exists (via adapter sync / template render),
  - is configurable (e.g., `--apply/--no-apply`, `--force`),
  - does not require modifying global OpenCode user config by default (project-local plugin is sufficient).
- [ ] Add the template source for the OpenCode plugin file under Edison’s `data/templates/` (template-only; no npm package required).

<!-- /EXTENSIBLE: Objectives -->

<!-- EXTENSIBLE: AcceptanceCriteria -->
## Acceptance Criteria

- [ ] `edison compose all --opencode` (or the equivalent adapter sync) generates `.opencode/plugin/edison.ts` in the repo.
- [ ] `edison opencode setup` creates the `.opencode` directory and plugin file (idempotent).
- [ ] The generated plugin file uses only OpenCode official APIs (no transcript regex, no internal message-store mutation).
- [ ] The adapter is thin and config-driven; it does not contain Edison core logic (completion stays in `session next`).

<!-- /EXTENSIBLE: AcceptanceCriteria -->

<!-- EXTENSIBLE: TechnicalDesign -->
## Technical Design

### A) Template-based plugin generation

Create a template file (path recommendation):
- `src/edison/data/templates/opencode/plugin/edison.ts.template`

The adapter renders it to:
- `.opencode/plugin/edison.ts`

This matches OpenCode’s plugin discovery (project-local plugin directory).

### B) Adapter

Implement `OpencodeAdapter` similar to other platform adapters:
- location recommendation: `src/edison/core/adapters/platforms/opencode.py` (or a subpackage if preferred)
- responsibilities:
  - create/sync `.opencode/plugin/`
  - render the plugin template with project config (continuation/cwam knobs)
  - (optional) generate `.opencode/README.md` with minimal setup instructions

### C) `edison opencode setup`

Add a new CLI domain `opencode`:
- `edison opencode setup`

Setup should:
- validate you are in an Edison project
- run adapter sync (or call into the adapter directly)
- be safe-by-default and idempotent

Do not install global OpenCode config or modify `~/.config/opencode` by default; project-local plugin is sufficient for initial integration.

<!-- /EXTENSIBLE: TechnicalDesign -->

<!-- EXTENSIBLE: FilesToModify -->
## Files to Create/Modify

```
# Create
src/edison/core/adapters/platforms/opencode.py
src/edison/cli/opencode/__init__.py
src/edison/cli/opencode/setup.py
src/edison/data/templates/opencode/plugin/edison.ts.template

# Modify
src/edison/data/config/composition.yaml
src/edison/core/adapters/platforms/__init__.py
src/edison/core/adapters/__init__.py
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
- Platform adapter base: `src/edison/core/adapters/base.py`
- Composition config: `src/edison/data/config/composition.yaml`
- OpenCode plugin API docs (high-level): OpenCode loads `.opencode/plugin/*.{ts,js}` (project-local)

<!-- /EXTENSIBLE: RelatedFiles -->

<!-- EXTENSIBLE: Notes -->
## Notes

- This task generates the plugin file; the plugin’s behavioral implementation (idle enforcement + truncation) is handled in task `040-*`.
- Keep OpenCode integration minimal initially (plugin + setup). Avoid adding a bunch of OpenCode “modes/tools/commands” until we have real demand.
- Ordering note: this task also modifies `src/edison/data/config/composition.yaml`; it depends on `016-composition-external-mounts` to avoid concurrent edits to that config surface.

<!-- /EXTENSIBLE: Notes -->
