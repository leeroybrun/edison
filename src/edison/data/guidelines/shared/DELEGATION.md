# Delegation (Core)


## Delegation Checklist (fail-closed)
- [ ] Load delegation config via ConfigManager overlays (`.edison/_generated/constitutions/ORCHESTRATORS.md` → pack overlays → `.edison/config/delegation.yml`) before deciding.
- [ ] Apply the deterministic priority chain to pick the best-matched sub-agent.
- [ ] Include config-driven guidance (preferred model, Zen role mapping, ownership) in every prompt you send.
- [ ] Use parallel sub-agents up to the configured concurrency cap; batch overflow.
- [ ] If no clear match emerges, halt and escalate—do not delegate ambiguously.

## Decision Priority Chain (deterministic)
1. User instruction (explicit requests override).
2. File pattern rules (`config.filePatternRules`).
3. Task type rules (`config.taskTypeRules`).
4. Sub-agent defaults (`config.subAgentDefaults`).
5. Tie-breakers (`orchestratorGuidance.tieBreakers`):
   - `order`: prefer matches from earlier rule types.
   - `modelPriority`: choose the highest-priority model listed.
   - `subAgentPriority`: deterministic ordering defined in the config (fallback: alphabetical key).
   - Final tie: stable alphabetical by rule key. The selected sub-agent executes without reassigning.

## Principles
- Delegate most work; orchestrators focus on planning, splitting, coordination, and validation oversight.
- Prefer parallelization for large/independent chunks; batch additional tasks if you hit the cap.
- Fail-closed: when in doubt or if configs conflict, stop and request clarification rather than guessing.
- Sub-agents MUST NOT re-delegate; delegation decisions stay with the orchestrator.

## Zen MCP delegation
- Use the Edison-provided `mcp__edison-zen__clink` tool to launch sub-agents/validators.
- Role mappings come from config overlays; prefer ConfigManager-resolved roles/models instead of hard-coding names.
- Include the resolved Zen role and model in prompts so the correct remote persona is activated.

## Prompt composition (new)
- Generate role-specific prompt bundles with `edison prompts compose --role <role> [--session <id>]`; this emits Zen/Codex/Cursor-ready templates using the same config overlays.
- Composition pipeline pulls delegation + session settings (owner, concurrency, guardrails) from YAML config; avoid manual edits to generated prompts.
- Attach the composed prompt when launching via Zen MCP so every sub-agent sees the same constraints and ownership markers.

## Enforcement
- Respect `neverImplementDirectly: true` (or equivalent) flags—those tasks must be delegated.
- Multi-role tasks marked `partial` should list multiple preferred models; choose a diverse set when delegating waves.
- Validate configs with guarded helpers (e.g., `edison delegation validate config|decide`) before sending work.

## Parallelization pattern
- When work is non-trivial or time-sensitive, split into child tasks per implementer and run in parallel within the concurrency cap.
- Keep children linked to the parent for validation bundles; launch validators separately to preserve independence.

## Reporting
- Every task requires an Implementation Report JSON. When delegation occurs, add entries under `delegations[]` capturing who/what was delegated, model/role used, and outcomes.
