# Context7 (Condensed, Mandatory)

## Extended Guide

For agent-specific patterns, detailed examples, and deep-dive workflows, see:
`.edison/_generated/guidelines/agents/CONTEXT7_REQUIREMENT.md`

## When to use
- For post‑training packages configured in your project
- Check your project's config for the complete list and supported versions

## Workflow (two steps)
{{include-section:guidelines/includes/CONTEXT7.md#agent}}

## Rules
- Always query Context7 BEFORE coding with post‑training packages.
- Implement using current docs; do not rely on training‑time memory.

## Red flags (query immediately if you see)
- Styling not applying because of syntax/version mismatches
- Framework/runtime errors after routing/data API changes
- Type errors from validation/database packages after API shifts
- Deprecation warnings

Read full: `.edison/_generated/guidelines/shared/CONTEXT7.md`.

<!-- section: RULE.CONTEXT7.EVIDENCE_REQUIRED.SHORT -->
**Context7 evidence:** Create `context7-<package>.txt` markers when using postTrainingPackages; guards block `wip→done` if missing.
<!-- /section: RULE.CONTEXT7.EVIDENCE_REQUIRED.SHORT -->

<!-- section: RULE.CONTEXT7.EVIDENCE_REQUIRED -->
## Evidence markers (required when used)
- When a task uses any package listed in `postTrainingPackages` (see ConfigManager overlays: `.edison/_generated/AVAILABLE_VALIDATORS.md` → pack overlays → `.edison/_generated/AVAILABLE_VALIDATORS.md`), include a marker file per package in the current round evidence directory, e.g.:
  - `.project/qa/validation-evidence/<task-id>/round-<N>/context7-<package>.txt`
  - Briefly list topics queried and the doc version/date.
- Guards treat missing markers as a blocker for `wip → done` on tasks that touch these packages.
- Notes in task files (e.g., "Context7 (<library>)") are NOT accepted as evidence.
- When HMAC stamping is enabled in config, include the stamped digest inside each marker.
<!-- /section: RULE.CONTEXT7.EVIDENCE_REQUIRED -->

## Auto-detection & enforcement
- `edison task ready` auto-detects post-training packages from the git diff and blocks readiness if matching markers are absent.
- State machine guards reuse the detection results; you cannot bypass Context7 by skipping the ready step.
- Use `--session <id>` so detection runs against the correct session worktree.
