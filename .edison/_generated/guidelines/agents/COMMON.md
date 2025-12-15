# Agent Common Guidelines (MANDATORY)

Read this alongside your role constitution: `.edison/_generated/constitutions/AGENTS.md`.

## Canonical Guideline Roster
Use this roster instead of repeating the table in each agent file:

| # | Guideline | Path | Purpose |
|---|-----------|------|---------|
| 1 | **Workflow** | `.edison/_generated/guidelines/agents/MANDATORY_WORKFLOW.md` | Implement → evidence/report → handoff (no orchestration) |
| 2 | **TDD (embedded)** | `.edison/_generated/constitutions/AGENTS.md` | TDD principles + execution requirements |
| 3 | **Validation** | `.edison/_generated/guidelines/shared/VALIDATION.md` | Multi-validator architecture; roster in `AVAILABLE_VALIDATORS.md` |
| 4 | **Delegation** | `.edison/_generated/guidelines/agents/DELEGATION_AWARENESS.md` | Config-driven, no re-delegation |
| 5 | **Context7** | `.edison/_generated/guidelines/shared/CONTEXT7.md` | Post-training package docs |
| 6 | **Rules** | `.edison/_generated/guidelines/agents/IMPORTANT_RULES.md` | Production-critical standards |

## Edison CLI & Validation Tools

### Edison CLI
- `edison task status <task-id>` - Read-only: check task details/state
- `edison session track start --task <task-id> --type implementation` - Mandatory: start an implementation round (evidence directory + tracking)
- `edison session track complete --task <task-id>` - Mandatory: complete the round (stamps/validates required artifacts)
- `edison config show <domain> --format yaml` - Inspect merged config (read-only)

> Orchestrator-only (do not run unless explicitly told): `edison task claim`, `edison task ready`, `edison qa new`, `edison qa promote`, `edison qa bundle`, `edison qa validate`, `edison session next`, `edison git worktree-*`, `edison compose all`.

### Context7 Tools
- Context7 package detection (automatic in `edison task ready`)
- HMAC evidence stamping (when enabled in config)

### Validation Tools
- Validator execution (automatic in QA workflow)
- Bundle generation (automatic in `edison qa bundle`)

## Pack-Specific Guidelines Anchor
Pack overlays inject additional rules here when present.