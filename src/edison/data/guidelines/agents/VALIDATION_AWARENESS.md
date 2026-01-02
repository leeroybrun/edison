# Validation Awareness (Agents)

Agents implement; validators validate. Treat validation as a first-class deliverable: evidence + clear reports are part of “done”.

## Validator Tiers (Waves)

- **Global**: always runs first (e.g., `global-*`). Blocking validators must approve.
- **Critical**: cross-cutting risk checks (e.g., security/performance). Blocking validators must approve.
- **Comprehensive**: additional, specialized validators that are pattern-triggered (and may be advisory if `blocking=false`). The active roster is listed in `AVAILABLE_VALIDATORS.md`.

## Source of Truth

- Roster + wave membership: merged `validation.validators` config (core → packs → user → project) and `edison qa validate <task-id> --dry-run`.
- Evidence requirements: `validation.evidence.requiredFiles` plus any preset-specific additions.

