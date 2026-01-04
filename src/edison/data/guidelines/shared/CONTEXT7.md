# Context7 (Condensed, Mandatory)

## Extended Guide

For agent-specific workflow integration (tracking, evidence directories, and config inspection), see:
- `guidelines/agents/MANDATORY_WORKFLOW.md`
- `guidelines/agents/EDISON_CLI.md`

## When to use
- For packages detected by your project's Context7 triggers/content rules
- Check your project's `context7` config for the complete list and triggers

## Workflow (two steps)
{{include-section:guidelines/includes/CONTEXT7.md#agent}}

## Rules
- Always query Context7 BEFORE coding with Context7‑detected packages.
- Implement using current docs; do not rely on training‑time memory.

## Red flags (query immediately if you see)
- Styling not applying because of syntax/version mismatches
- Framework/runtime errors after routing/data API changes
- Type errors from validation/database packages after API shifts
- Deprecation warnings

<!-- section: RULE.CONTEXT7.EVIDENCE_REQUIRED.SHORT -->
**Context7 evidence:** Create `context7-<package>.txt` markers for every Context7‑detected package; guards block `{{fn:semantic_state("task","wip")}}→{{fn:semantic_state("task","done")}}` if missing.
<!-- /section: RULE.CONTEXT7.EVIDENCE_REQUIRED.SHORT -->

<!-- section: RULE.CONTEXT7.EVIDENCE_REQUIRED -->
## Evidence markers (required when used)
- When a task uses any Context7-detected package (driven by `context7.triggers` and optional `context7.contentDetection`), include a marker file per package in the current round evidence directory, e.g.:
  - `{{fn:evidence_root}}/<task-id>/round-<N>/context7-<package>.txt`
  - Briefly list topics queried and the doc version/date.
- To inspect the merged Context7 configuration: `edison config show context7 --format yaml`
- Guards treat missing markers as a blocker for `{{fn:semantic_state("task","wip")}} → {{fn:semantic_state("task","done")}}` on tasks that touch these packages.
- Notes in task files (e.g., "Context7 (<library>)") are NOT accepted as evidence.
- When HMAC stamping is enabled in config, include the stamped digest inside each marker.
<!-- /section: RULE.CONTEXT7.EVIDENCE_REQUIRED -->

## Auto-detection & enforcement
- `edison task done` auto-detects Context7‑detected packages from the git diff and blocks completion if matching markers are absent.
- State machine guards reuse the detection results; you cannot bypass Context7 by skipping the done step.
- Use `--session <id>` so detection runs against the correct session worktree.
