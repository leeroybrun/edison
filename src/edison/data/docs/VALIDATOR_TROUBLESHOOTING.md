# Validator Troubleshooting

This guide helps you debug validator failures, run validators manually, and check validator configuration.

## Common validator errors

Below are common validator errors and a suggested solution for each:
- Missing evidence files → solution: run the evidence init flow and re-run validation.
- Schema/config validation errors → solution: inspect the YAML for the failing section and fix invalid fields.
- CLI/tooling failures (typecheck/lint/test) → solution: run the command locally and fix the root cause (don’t just silence the validator).

## Debug validator failures

To debug validator failures:
1. Re-run the validator with verbose output when available.
2. Inspect logs and traces produced by the validator runner.
3. Confirm the validator is reading the expected config layer (core → packs → project).

## Run validators manually

You can run validators manually (outside automation) with concrete commands like:

```
edison qa validate
edison qa validate --preset standard
edison config show validation --format yaml
```

If a validator calls external tooling, run that command directly too (for example `uv run pytest`, `ruff`, or `mypy` depending on your project).

## Check validator configuration

To check validator configuration, verify the YAML sources under `.edison/config/` and then confirm the merged view:
- check validator configuration via `edison config show validation --format yaml`
- validate configuration by running `edison qa validate` and reviewing any schema errors

## Add custom validators

To add custom validators:
- register the validator in the appropriate registry/config
- configure it via YAML so it can be enabled/disabled per preset
- ensure it can be executed by the orchestrator/runner (inputs/outputs are deterministic)

## FAQ

**Q: Why did my validator fail even though my code “works”?**
A: Validators enforce reproducible quality gates; review the failing rule and its suggested fix.

**Q: Where do I see more details?**
A: Check logs and traces from the validator runner and re-run the failing command locally.

