# Agent Common Guidelines (MANDATORY)

Read this alongside your role constitution: run `edison read AGENTS --type constitutions`.

## Canonical Guideline Roster
Use this roster instead of repeating the table in each agent file:

| # | Guideline | Read | Purpose |
|---|-----------|------|---------|
| 1 | **Workflow** | `edison read MANDATORY_WORKFLOW --type guidelines/agents` | Implement → evidence/report → handoff (no orchestration) |
| 2 | **TDD (embedded)** | `edison read AGENTS --type constitutions` | TDD principles + execution requirements |
| 3 | **Validation** | `edison read VALIDATION --type guidelines/shared` | Multi-validator architecture; roster in `AVAILABLE_VALIDATORS.md` (`edison read AVAILABLE_VALIDATORS`) |
| 4 | **Delegation** | `edison read DELEGATION_AWARENESS --type guidelines/agents` | Config-driven, no re-delegation |
| 5 | **Context7** | `edison read CONTEXT7 --type guidelines/shared` | Post-training package docs |
| 6 | **Rules** | `edison read IMPORTANT_RULES --type guidelines/agents` | Production-critical standards |

## Edison CLI & Validation Tools

### Edison CLI
- `edison task status <task-id>` - Read-only: check task details/state
- Tracking (mandatory): run `edison read MANDATORY_WORKFLOW --type guidelines/agents` (includes the canonical tracking commands).
- `edison config show <domain> --format yaml` - Inspect merged config (read-only)

> Orchestrator-only (do not run unless explicitly told): `edison task claim`, `edison task done` (and legacy `edison task ready <task>`), `edison qa new`, `edison qa promote`, `edison qa bundle`, `edison qa validate`, `edison session next`, `edison git worktree-*`, `edison compose all`.

{{include-section:guidelines/includes/GIT_WORKTREE_SAFETY.md#agent-git-safety}}

{{include-section:guidelines/includes/GIT_WORKTREE_SAFETY.md#worktree-confinement}}

### Context7 Tools
- Context7 package detection (automatic in `edison task done`)
- HMAC evidence stamping (when enabled in config)

### Validation Tools
- Validator execution (automatic in QA workflow)
- Bundle generation (automatic in `edison qa bundle`)

<!-- section: tools -->
<!-- /section: tools -->

## Pack-Specific Guidelines Anchor
Pack overlays inject additional rules here when present.

<!-- section: guidelines -->
<!-- /section: guidelines -->
