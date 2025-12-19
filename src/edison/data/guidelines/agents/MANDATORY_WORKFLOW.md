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

#### Phase 1: Implement (TDD + Context7)

1. **Start tracking (MANDATORY)**: `edison session track start --task <task-id> --type implementation`
   - This prepares/locks the round evidence directory and establishes the canonical location for round artifacts.
2. Read requirements and locate existing patterns in the codebase.
3. If the change touches any Context7‑detected package (per merged config), refresh docs via Context7 and create the required `context7-<package>.txt` marker(s) in the evidence round directory.
4. Follow TDD: RED → GREEN → REFACTOR (tests first, then minimal implementation, then cleanup).
5. Run the project’s automation suite (type-check, lint, test, build or equivalent). Capture outputs as evidence files **using the filenames from merged config** (required: {{function:required_evidence_files("inline")}}).

#### Phase 2: Produce the Implementation Report (required)

Create or update the implementation report for the current round:
- **Path**: `{{fn:evidence_root}}/<task-id>/round-<N>/implementation-report.md` (filename is config-driven; default is `implementation-report.md`).
- **Schema (LLM reference)**: `{{fn:project_config_dir}}/_generated/schemas/reports/implementation-report.schema.yaml`
- Include any implementation‑discovered follow-ups in `followUpTasks[]` (used by `edison session next` to propose follow-up planning).

#### Phase 3: Handoff to orchestrator (do NOT self-validate)

Before handing off, **complete tracking (MANDATORY)**:

```bash
edison session track complete --task <task-id>
```

Return a crisp handoff to the orchestrator:
- What changed and why
- Commands you ran and where the evidence files live
- Where the implementation report lives
- Any blockers or follow-ups (especially those that must block validation)

### Agent CLI (what you may run)

Agents are generally **read-only** on task/session orchestration:

```bash
# Read-only: inspect task state/details
edison task status <task-id>

# Tracking (mandatory for implementation rounds)
edison session track start --task <task-id> --type implementation
edison session track complete --task <task-id>
```

> Orchestrator-only (do NOT run unless explicitly told): `edison task claim`, `edison task ready`, `edison qa promote`, `edison qa bundle`, `edison qa validate`.

## Evidence Required (minimum)

- Implementation report (`implementation-report.md`) exists for the latest round.
- Automation evidence files exist per project config (required: {{function:required_evidence_files("inline")}}).
- Context7 markers exist for any required packages (if applicable).

## Critical Rules

1. **Never orchestrate by default** – do not move tasks/QA or run promotion commands unless explicitly delegated.
2. **Never implement without tests** – TDD is mandatory.
3. **Always provide evidence** – no evidence = not ready for validation.
4. **Always check delegation scope** – if mis-assigned, return MISMATCH rather than doing the wrong work.

<!-- /section: workflow -->

## References

- Extended workflow: `{{fn:project_config_dir}}/_generated/guidelines/agents/AGENT_WORKFLOW.md`
- Output format: `{{fn:project_config_dir}}/_generated/guidelines/agents/OUTPUT_FORMAT.md`
- Session workflow: `{{fn:project_config_dir}}/_generated/guidelines/orchestrators/SESSION_WORKFLOW.md`

---

**Version**: 1.0 (Extracted from pre-Edison agents)
**Applies to**: ALL implementing agents (api-builder, component-builder, database-architect, feature-implementer, test-engineer)
