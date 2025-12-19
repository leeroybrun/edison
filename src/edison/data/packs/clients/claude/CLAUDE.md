# Claude Code (Edison)

This document provides a small, **project-agnostic** brief for using Edison with Claude Code / Claude Desktop.

## Entry point

- Read `AGENTS.md` at the repo root.
- Determine your role from the task assignment.
- Re-read your role constitution at the start of each new session and after any context compaction.

## Orchestrator workflow (if you are the ORCHESTRATOR)

- **Constitution (single source of truth)**: `{{PROJECT_EDISON_DIR}}/_generated/constitutions/ORCHESTRATOR.md`
- **Drive work “on rails”**: run `edison session next <session-id>` before every action.
- **Rosters**:
  - `{{PROJECT_EDISON_DIR}}/_generated/AVAILABLE_AGENTS.md`
  - `{{PROJECT_EDISON_DIR}}/_generated/AVAILABLE_VALIDATORS.md`
- **Key workflows**:
  - `{{PROJECT_EDISON_DIR}}/_generated/guidelines/orchestrators/SESSION_WORKFLOW.md`
  - `{{PROJECT_EDISON_DIR}}/_generated/guidelines/shared/DELEGATION.md`
  - `{{PROJECT_EDISON_DIR}}/_generated/guidelines/shared/VALIDATION.md`

## Implementer workflow (if you are an AGENT)

- **Constitution**: `{{PROJECT_EDISON_DIR}}/_generated/constitutions/AGENTS.md`
- **Output format**: `{{PROJECT_EDISON_DIR}}/_generated/guidelines/agents/OUTPUT_FORMAT.md`

## Validator workflow (if you are a VALIDATOR)

- **Constitution**: `{{PROJECT_EDISON_DIR}}/_generated/constitutions/VALIDATORS.md`
- **Output format**: `{{PROJECT_EDISON_DIR}}/_generated/guidelines/validators/OUTPUT_FORMAT.md`

## Guardrails

- **Never edit** `{{PROJECT_EDISON_DIR}}/_generated/*` by hand.
- **Do not reference** legacy pre-Edison prompt/workflow paths.
- **Keep context lean**: prefer focused snippets and referenced artifact paths over full-file dumps.
