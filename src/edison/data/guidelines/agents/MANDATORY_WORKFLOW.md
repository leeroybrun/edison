# Mandatory Workflow

<!-- MANDATORY: All agents MUST read this before implementation -->
<!-- Generated from pre-Edison agent content extraction -->

## Purpose

This document defines the mandatory workflow that ALL implementing agents must follow. Failure to follow this workflow will result in guard failures and blocked task promotion. The workflow ensures consistent task claiming, implementation, and completion across all sub-agents.

## Requirements

<!-- section: workflow -->
### Workflow Overview (Agents / Implementers)

**Key Principle (role boundary):** Agents implement code and produce evidence. **Orchestrators** manage sessions and state transitions (`task claim`, `task ready`, QA moves, bundling). Agents MUST NOT perform orchestration actions unless the orchestrator explicitly delegates that responsibility.

### The Implement‑and‑Handoff Cycle (what you do)

#### Phase 0: Intake (from orchestrator)

You should receive from the orchestrator:
- Task ID + acceptance criteria
- Scope boundaries (in/out)
- File paths to touch (or at least directory hints)
- Any required packs/project guidelines to follow
- Where to put evidence (task evidence directory + round)

If the task is missing acceptance criteria or scope boundaries, stop and ask for them.

#### Phase 1: Implement (TDD + Context7 + Evidence)

1. **Start tracking (MANDATORY)**:

{{include-section:guidelines/includes/TRACKING.md#agent-tracking}}

   - This establishes the canonical tracking metadata for the current round.

2. **Initialize evidence round (MANDATORY)**:
   ```bash
   edison qa round prepare <task-id>
   ```
   - Creates/updates the active round directory structure for capturing reports
   - Do this BEFORE starting implementation

3. Read requirements and locate existing patterns in the codebase.

4. If the change touches any Context7‑detected package (per merged config), refresh docs via Context7 and create the required `context7-<package>.txt` marker(s) in the evidence round directory.

5. Follow TDD: RED → GREEN → REFACTOR (tests first, then minimal implementation, then cleanup). This applies to executable behavior changes; content-only Markdown/YAML/template edits do not require new tests, but must not be used to bypass TDD when code changes.

6. **Run and capture evidence as you work (MANDATORY)**:
   - After each GREEN phase, run `edison evidence capture <task-id>` (captures preset-required evidence; config-driven)
   - **FIX any failures before proceeding** - evidence must show passing commands
   - For targeted reruns: `edison evidence capture <task-id> --only <name>` (alias: `--command <name>`)
   - Check status: `edison evidence status <task-id>`
   - If tests fail: capture once to get the full failure list, then iterate via tightly-scoped reruns (only failing tests / focused commands) to avoid re-running the full suite after every change. When focused reruns are green, re-run `edison evidence capture` to refresh the reusable snapshot.

**Critical**: Evidence is NOT just for recording—it proves you ran commands and fixed issues. If you capture a failing run, fix and re-capture until `exitCode: 0` before handoff.

#### Phase 2: Produce the Implementation Report (required)

Create or update the implementation report for the current round:
- **Path**: `{{fn:evidence_root}}/<task-id>/round-<N>/{{config.validation.artifactPaths.implementationReportFile}}` (filename is config-driven; default is `{{config.validation.artifactPaths.implementationReportFile}}`).
- **Schema (LLM reference)**: `edison read implementation-report.schema.yaml --type schemas/reports`
- Include any implementation‑discovered follow-ups in `followUpTasks[]` (used by `edison session next` to propose follow-up planning).

#### Phase 3: Handoff to orchestrator (do NOT self-validate)

Before handing off, **complete tracking (MANDATORY)**:

```bash
edison session track complete --task <task-id>
```

Return a crisp handoff to the orchestrator:
- What changed and why
- Commands you ran and the snapshot path from `edison evidence status <task-id>`
- Where the implementation report lives
- Any blockers or follow-ups (especially those that must block validation)

### Agent CLI (what you may run)

Agents are generally **read-only** on task/session orchestration:

```bash
# Read-only: inspect task state/details
edison task status <task-id>
```

> Orchestrator-only (do NOT run unless explicitly told): `edison task claim`, `edison task done` (and legacy `edison task ready <task>`), `edison qa promote`, `edison qa bundle`, `edison qa validate`.

## Evidence Required

Before handoff: `edison evidence status <task-id>`

All command evidence must show `exitCode: 0`. Run commands, fix failures, then capture.

## Critical Rules

1. **Never orchestrate by default** – do not move tasks/QA or run promotion commands unless explicitly delegated.
2. **Never implement executable behavior without tests** – TDD is mandatory. Content-only Markdown/YAML/template edits do not require new tests, but must not be used to bypass TDD when code changes.
3. **Always provide evidence** – no evidence = not ready for validation.
4. **Always check delegation scope** – if mis-assigned, return MISMATCH rather than doing the wrong work.

<!-- /section: workflow -->

## References

- Extended workflow: `edison read AGENT_WORKFLOW --type guidelines/agents`
- Output format: `edison read OUTPUT_FORMAT --type guidelines/agents`
- Session workflow: `edison read SESSION_WORKFLOW --type guidelines/orchestrators`

---

**Version**: 1.0 (Extracted from pre-Edison agents)
**Applies to**: ALL implementing agents (api-builder, component-builder, database-architect, feature-implementer, test-engineer)
