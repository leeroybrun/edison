# Validator Workflow (Condensed, Mandatory)

Purpose: Single, fail‑closed runbook for validators (any model issuing verdicts). Implementers use `.agents/implementation/IMPLEMENTER_WORKFLOW.md`.

## Mandatory Preload (do not skip)
- `.agents/manifest.json` → load every `mandatory` entry
- `.agents/guidelines/VALIDATION.md` (anchors RULE.VALIDATION.*)
- `.edison/core/validators/OUTPUT_FORMAT.md` (human + JSON report schema)
- Validator config via ConfigManager overlays (`.edison/core/config/validators.yaml` → pack overlays → `.agents/config/validators.yml`) for roster, triggers, blocking rules, and evidence paths.

## 🔴 TRACKING (MANDATORY FIRST & LAST ACTIONS)

**FIRST ACTION - Before ANY validation:**
```bash
scripts/track start --task <task-id> --type validation --validator <validator-id> --model <model>
```

**LAST ACTION - After validation complete:**
```bash
scripts/track complete --task <task-id> --type validation --validator <validator-id>
```

**Why mandatory:** QA promotion guards check validator tracking stamps. Missing stamps = blocked QA promotion to `done`.

**Auto-stamped fields:** PID, timestamp, hostname, validator ID, and model are recorded at `start`. On `complete`, `tracking.completedAt` is stamped. The JSON schema requires `tracking.processId`, `tracking.startedAt`, and `tracking.completedAt`.

---

## 8‑Step Runbook (fail‑closed)
1) Scope: Open QA brief for `<task-id>`; ensure bundle manifest is present (via `edison validators bundle`).
2) Launch: Promote QA `todo → wip` using `edison qa promote --task <id> --to wip`.
3) Waves: Run validators in waves (global → critical → specialized) up to concurrency cap.
4) Model binding: Call the exact model per config; your JSON report MUST record the same `model`.
5) Deliverables: Produce human Markdown and JSON report per validator (schema‑valid) in the latest `round-*` directory.
6) Findings: Summarize verdicts in the QA brief; suggest follow‑ups as needed.
7) Decision:
   - If ANY blocking validator fails or is missing → add a Round entry `REJECTED` and return QA to `waiting`.
   - If ALL blocking validators approve → set `Bundle Approved: true` and promote QA to `done`.
8) Archive: Optionally promote QA `done → validated` (guard enforces bundle + bundle-approved).

## Blocking Criteria
- Every configured blocking validator has executed and approved.
- Every blocking JSON report is schema‑valid and the `model` matches config (strict binding).

## Quick commands
```bash
edison validators bundle <task-id>
edison qa promote --task <task-id> --to wip
edison qa promote --task <task-id> --to validated  # after bundle-approved.json exists
# Bundle summary filename is configurable via ConfigManager (`validators.bundle.bundleSummaryFile`, default: `bundle-approved.json`).
```

## Edison validation guards (current)
- Validate only against bundles emitted by `edison validators bundle <root-task>`; block/return `BLOCKED` if the manifest or parent `bundle-approved.json` is missing.
- Load roster, triggers, and blocking flags via ConfigManager overlays (`.edison/core/config/validators.yaml` → pack overlays → `.agents/config/validators.yml`) instead of JSON.
- `edison qa promote` now enforces state machine rules plus bundle presence; ensure your Markdown + JSON report lives in the round evidence directory referenced by the bundle.
- Honor Context7 requirements: auto-detected post-training packages must have markers (HMAC when enabled) before issuing approval.
