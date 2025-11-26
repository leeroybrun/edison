# Validator Troubleshooting Guide

Authoritative, configuration-driven checklist for diagnosing and fixing validator issues. All behavior is YAML-controlled—never hardcode validator IDs, triggers, or limits in code or docs.

## Common validator errors and solutions
- **Missing bundle or stale manifest**: `edison validators bundle <task-id> [--session <session-id>]` to regenerate; attach the fresh bundle to the QA brief before re-running validators.
- **Validator roster mismatch**: Re-open `{{PROJECT_EDISON_DIR}}/_generated/AVAILABLE_VALIDATORS.md` and `_generated/validators/*.md` to confirm the current roster. Rebuild overlays if the roster looks outdated.
- **Report missing or incomplete**: Inspect `.project/qa/validation-evidence/<task-id>/round-<N>/` for absent `<validator>.json`; re-run with `--validators <id>` to regenerate the specific report without overwriting the round directory.
- **Trigger not firing**: Check `validation.roster.*[].triggers` in YAML overlays (`src/edison/data/config/validators.yaml` + `.edison/config/*.yml`). Ensure the changed files match a trigger pattern; adjust YAML instead of hardcoding.
- **Context7 or model error**: Validate that the required `context7Packages` in YAML are available; rerun with the same round and capture stderr logs for evidence.
- **Max rounds exceeded**: `validation.maxRounds` is defined in YAML overlays. If the next run would exceed it, halt, mark QA as blocked, and escalate per the runbook instead of bumping a hardcoded number.

## How to debug validator failures
1. **Confirm config sources**: Reload `{{PROJECT_EDISON_DIR}}/_generated/AVAILABLE_VALIDATORS.md` and the active YAML overlays (`{{PROJECT_EDISON_DIR}}/config/*.yml`) to ensure the roster and triggers you expect are the ones in use.
2. **Rebuild the bundle**: `edison validators bundle <task-id> [--session <session-id>]` and verify the bundle snippet included in the QA brief matches the current code state.
3. **Inspect evidence**: Review `bundle-approved.json` plus individual validator reports under `.project/qa/validation-evidence/<task-id>/round-<N>/`. Missing files are treated as failures.
4. **Check logs and traces**: Rerun the failing validator with `--validators <id> --round <N>` and capture stdout/stderr logs; attach them to the QA brief for traceability.
5. **Validate YAML values**: Ensure `validation.dimensions` sum to 100, `validation.maxRounds` exists, and all `zenRole` references resolve through overlays; fix YAML and regenerate manifests if anything is inconsistent.

## How to run validators manually
- **Prepare bundle**: `edison validators bundle <task-id> [--session <session-id>]` (must be fresh before every manual run).
- **Run all required validators**: `edison validators validate <task-id> [--session <session-id>] [--round <N>]` (round auto-increments when omitted). The command derives the validator list from YAML + the bundle; do not pass hardcoded IDs.
- **Re-run a subset**: `edison validators validate <task-id> --validators <id> --round <N>` to reproduce a specific failure without touching other reports. Use only after a full run produced evidence.
- **Where results land**: `.project/qa/validation-evidence/<task-id>/round-<N>/` contains per-validator JSON plus `bundle-approved.json` (canonical decision artifact).

## How to check validator configuration
- Open `src/edison/data/config/validators.yaml` for the base roster, triggers, and defaults.
- Overlay precedence (fail-closed, no fallbacks):
  1) Base config above
  2) Optional org overlays: `.edison/core/config/*.yml`
  3) Project overlays: `.edison/config/*.yml` (final authority)
- Generated views: `{{PROJECT_EDISON_DIR}}/_generated/AVAILABLE_VALIDATORS.md` and `_generated/validators/*.md` mirror the effective config; regenerate via the bundle command when overlays change.
- Verify `validation.maxRounds`, `blocking_validators`, trigger patterns, and `zenRole` mappings only through YAML; if values look wrong, fix overlays and rebuild instead of patching code.

## How to add custom validators
1. **Define YAML entry**: Add a new validator under the appropriate roster section in `.edison/config/validators.yml` (or another project overlay). Specify `id`, `specFile`, `zenRole`, `triggers`, `model`, `interface`, and whether it `blocksOnFail`—all in YAML, not code.
2. **Provide spec content**: Create the validator spec document under `.edison/config/validators/<path>.md` or another configured location referenced by `specFile`.
3. **Register triggers**: Ensure `triggers` match the files the validator should watch; prefer precise globs to avoid accidental runs.
4. **Regenerate manifests**: Run `edison validators bundle <task-id>` to rebuild `_generated/validators/` and `AVAILABLE_VALIDATORS.md`, then commit the generated artifacts if your workflow requires.
5. **Run and verify**: Execute `edison validators validate <task-id> --validators <new-id>` for a focused check, confirm the report appears in the round directory, and document the new validator in the QA brief.

## FAQ
- **Why did a validator not run?** Check trigger patterns in YAML overlays and confirm the changed files match; rebuild the bundle after any YAML change.
- **Can I skip a blocking validator?** No. The set of blocking validators comes from `validation.blocking_validators` in YAML; changing it requires an overlay update and regenerated manifests.
- **How do I see the exact roster the CLI will use?** Open `{{PROJECT_EDISON_DIR}}/_generated/AVAILABLE_VALIDATORS.md` after running `edison validators bundle <task-id>`.
- **Where are validator decisions stored?** In `.project/qa/validation-evidence/<task-id>/round-<N>/bundle-approved.json` and per-validator JSON files.
