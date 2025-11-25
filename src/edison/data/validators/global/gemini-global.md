# Gemini Global Validation – Comprehensive

This validator performs a comprehensive, model-agnostic quality review covering:
- Requirements alignment
- Correctness and safety
- Test sufficiency and determinism
- Robust error handling and recovery
- Documentation and maintainability

Instructions to operator:
- Treat this as the Gemini counterpart to other global validators.
- Use the same output format and sections as `_report-template.md`.
- See `.edison/core/validators/VALIDATOR_WORKFLOW.md` for process.

## Edison validation guards (current)
- Validate only against bundles emitted by `edison validators bundle <root-task>`; block/return `BLOCKED` if the manifest or parent `bundle-approved.json` is missing.
- Load roster, triggers, and blocking flags via ConfigManager overlays (`.edison/core/config/validators.yaml` → pack overlays → `.agents/config/validators.yml`) instead of JSON.
- `edison qa promote` now enforces state machine rules plus bundle presence; ensure your Markdown + JSON report lives in the round evidence directory referenced by the bundle.
- Honor Context7 requirements: auto-detected post-training packages must have markers (HMAC when enabled) before issuing approval.
