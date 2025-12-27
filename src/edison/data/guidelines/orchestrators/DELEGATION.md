# Delegation Models (Orchestrators)

> Canonical path: `{{fn:project_config_dir}}/_generated/guidelines/orchestrators/DELEGATION.md` (read via `edison read DELEGATION --type guidelines/orchestrators`; composed via ConfigManager overlays; never hardcode roles/models—resolve from YAML).

<!-- section: rules -->
## Delegation Criteria

- Load the delegation roster first: run `edison read AVAILABLE_AGENTS` (fail-closed if missing).
- Source of truth lives in YAML overlays (core → packs → user → project), but orchestrators should rely on the generated roster + `edison session next` suggestions rather than hardcoding config paths in prompts.
- Delegate by default; orchestrators implement only when criteria say **Handle Directly**.
- Enforce the priority chain (user instruction → file pattern rules → task type rules → sub-agent defaults → tie-breakers). Stop if ambiguous.

### Tasks to Delegate
- Multi-skill work (backend + frontend + data) or anything exceeding a single role’s scope.
- Time-sensitive tasks benefiting from concurrency within the configured cap.
- Tasks requiring specialized roles (security, database, migrations, infra, UX) flagged in config.
- Large refactors or net-new features where independent slices can run in parallel.

### Tasks to Handle Directly
- Truly trivial edits faster to apply than to brief (docs typo, single-line rename) **and** unblocked by config flags like `neverImplementDirectly`.
- Hotfixes explicitly assigned to the orchestrator by user instruction or escalation owner.
- Delegation config unavailable/invalid and time does not allow re-resolution (log and fix config immediately afterward).

## Agent Selection Guidance

- Resolve candidates from the generated roster + rules output (no hardcoded names). Use:
  - `edison read AVAILABLE_AGENTS`
  - `edison session next <session-id>`
- Choose the **first deterministic match** from the priority chain; do not shop for a better model after selection.
- Keep independence: separate implementer vs validator roles/models; never assign both to one agent.
- Honor ownership signals (task owner, session owner, required model) carried in config overlays.

### Selection Signals
- File/path patterns → maps to specialization (e.g., `db/**` → database-architect role).
- Task labels/tags → use `taskTypeRules` to route (e.g., `performance`, `compliance`).
- Model preferences → pick highest-priority model listed under the chosen agent.
- Capacity → respect concurrency cap; batch overflow rather than over-assigning.

## Delegation Prompt Structure

- Compose prompts using your orchestration layer's prompt templating system to pull the YAML overlays you used for selection.
- Include session/task context, acceptance criteria, constraints (TDD, no mocks, no legacy/hardcodes), and expected deliverables (implementation report path, tests, commands run).
- Attach ownership + model details from config so Pal activates the correct persona.

### Prompt Template

1. **Role & Model**: `<resolved role> | <resolved model> | owner=<session_owner>`
2. **Task & Scope**: task id, brief summary, files/paths in scope, out-of-scope guardrails.
3. **Constraints**: TDD (red→green→refactor), no mocks, config-only values, no legacy fallbacks, DRY/SOLID/KISS/YAGNI.
4. **Deliverables**: code changes, tests, commands run + outputs, implementation report location, evidence paths.
5. **Coordination**: how to ask clarifications, when to pause, target handoff time.

## Verification Protocol

- Require an implementation report per delegation; reject incomplete reports.
- Re-run the listed commands (tests/lint/typecheck) locally; add missing automation if absent.
- Diff review: confirm requirements met, no hardcoded values, config wired to YAML, and no legacy paths remain.
- Validate integration: run minimal end-to-end path if feasible; ensure artifacts land in expected directories.
- Record verdict and evidence in the session Activity Log and QA bundle before promotion.

## When to Re-delegate vs Fix Yourself

- **Re-delegate** when the gap is substantial (missing features, incorrect approach, blocked expertise) or when throughput improves by reassigning within concurrency budget.
- **Fix yourself** when remaining issues are small, faster than briefing (e.g., rename, doc wording, single assertion) and do not conflict with independence rules.
- Never chain re-delegations: one bounce only; otherwise pause and re-plan the split.

## Parallel vs Sequential

- Use parallel delegation for independent slices with minimal coupling; cap at configured concurrency and batch remainder.
- Use sequential delegation when outputs are serially dependent (e.g., schema design → API scaffold → UI wiring) or when coordination risk is high.
- Keep validators separate and parallelizable; do not co-locate implementer and validator roles.
- Always log the chosen pattern (parallel/sequential/mixed) and rationale in the Activity Log for traceability.
<!-- /section: rules -->
