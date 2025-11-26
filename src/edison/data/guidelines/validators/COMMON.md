# Validator Common Guidelines (MANDATORY)

Read this alongside your role file and the shared common instructions in `.edison/core/guidelines/shared/COMMON.md`.

## Context7 Knowledge Refresh
- Follow `.edison/core/guidelines/shared/COMMON.md#context7-knowledge-refresh-mandatory` before validating any task that touches post-training packages.
- Use the pack-provided `{{SECTION:TechStack}}` hints to target the correct libraries and topics.

## Edison validation guards (current)
- Validate only against bundles emitted by `edison validators bundle <root-task>`; return `BLOCKED` if the manifest or parent `bundle-approved.json` is missing.
- Load roster, triggers, and blocking flags via ConfigManager overlays (`.edison/core/config/validators.yaml` → pack overlays → `.edison/config/validators.yml`) instead of JSON.
- `edison qa promote` enforces state machine rules plus bundle presence; ensure Markdown + JSON reports live in the round evidence directory referenced by the bundle.
- Honor Context7 requirements: auto-detected post-training packages must have markers (HMAC when enabled) before issuing approval.

## Maintainability Baseline
- **Long-Term Maintainability**: no clever shortcuts, consistent patterns, documented trade-offs, no hardcoded values, avoid premature optimization, and keep dependencies justified.
- **Red Flags**: copy-paste blocks, unexplained magic numbers, tight coupling, deprecated APIs, hidden `@ts-ignore`/`any`, TODOs without tickets, or focused/ skipped tests.
