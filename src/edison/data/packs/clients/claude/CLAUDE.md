# Claude Code (Edison)

This document provides a small, **project-agnostic** brief for using Edison with Claude Code / Claude Desktop.

## Entry point

- Read `AGENTS.md` at the repo root.
- Determine your role from the task assignment.
- Re-read your role constitution at the start of each new session and after any context compaction.

## Orchestrator workflow (if you are the ORCHESTRATOR)

- **Constitution (single source of truth)**: `.edison/_generated/constitutions/ORCHESTRATOR.md`
- **Drive work “on rails”**: run `edison session next <session-id>` before every action.
- **Rosters**:
  - `.edison/_generated/AVAILABLE_AGENTS.md`
  - `.edison/_generated/AVAILABLE_VALIDATORS.md`
- **Key workflows**:
  - `.edison/_generated/guidelines/orchestrators/SESSION_WORKFLOW.md`
  - `.edison/_generated/guidelines/shared/DELEGATION.md`
  - `.edison/_generated/guidelines/shared/VALIDATION.md`

## Implementer workflow (if you are an AGENT)

- **Constitution**: `.edison/_generated/constitutions/AGENTS.md`
- **Output format**: `.edison/_generated/guidelines/agents/OUTPUT_FORMAT.md`

## Validator workflow (if you are a VALIDATOR)

- **Constitution**: `.edison/_generated/constitutions/VALIDATORS.md`
- **Output format**: `.edison/_generated/guidelines/validators/OUTPUT_FORMAT.md`

## Guardrails

- **Never edit** `.edison/_generated/*` by hand.
- **Do not reference** legacy pre-Edison prompt/workflow paths.
- **Keep context lean**: prefer focused snippets and referenced artifact paths over full-file dumps.
