# Validator Troubleshooting Guide

Authoritative, configuration-driven checklist for diagnosing and fixing validator issues. All behavior is YAML-controlled—never hardcode validator IDs, triggers, or limits in code or docs.

## Validation Architecture Overview

The validation system uses a centralized `ValidationExecutor` with:
- **CLIEngine**: Direct CLI execution (codex, claude, gemini, auggie, coderabbit)
- **ZenMCPEngine**: Delegation fallback when CLI unavailable
- **Wave-based execution**: Validators grouped into waves with parallel execution
- **Automatic fallback**: CLI → delegation when tools not installed

## Common validator errors and solutions

- **CLI tool not available**: Install the required CLI tool or configure `fallback_engine: zen-mcp` in YAML to delegate automatically.
- **Missing bundle or stale manifest**: `edison qa bundle <task-id> [--session <session-id>]` to regenerate; attach the fresh bundle to the QA brief before re-running validators.
- **Validator roster mismatch**: Re-open `{{PROJECT_EDISON_DIR}}/_generated/AVAILABLE_VALIDATORS.md` and `_generated/validators/*.md` to confirm the current roster. Rebuild overlays if the roster looks outdated.
- **Report missing or incomplete**: Inspect `.project/qa/validation-evidence/<task-id>/round-<N>/` for absent `validator-<id>-report.json`; re-run with `--validators <id>` to regenerate the specific report.
- **Trigger not firing**: Check `validation.validators.<id>.triggers` in YAML. Ensure the changed files match a trigger pattern.
- **Context7 or model error**: Validate that the required `context7_packages` in YAML are available; rerun with the same round and capture stderr logs for evidence.
- **Delegation required but not executed**: When CLI is unavailable, check `.project/qa/validation-evidence/<task-id>/round-<N>/delegation-<validator>.md` for orchestrator instructions.

## How to debug validator failures

1. **Check engine availability**: Run `edison qa validate <task-id> --dry-run` to see which validators can execute directly (✓) vs need delegation (→).

2. **Confirm config sources**: Reload `{{PROJECT_EDISON_DIR}}/_generated/AVAILABLE_VALIDATORS.md` and the active YAML overlays to ensure the roster and triggers you expect are in use.

3. **Inspect evidence**: Review evidence files under `.project/qa/validation-evidence/<task-id>/round-<N>/`:
   - `command-<validator>.txt` - CLI output from direct execution
   - `delegation-<validator>.md` - Instructions for delegated validators
   - `validator-<id>-report.json` - Structured validation result

4. **Check logs and traces**: Rerun the failing validator with `edison qa run <validator-id> <task-id>` and capture stdout/stderr.

5. **Validate YAML values**: Ensure `validation.engines`, `validation.validators`, and `validation.waves` are properly configured.

## How to run validators manually

### Show Roster (No Execution)
```bash
edison qa validate <task-id>
```

### Execute All Validators
```bash
edison qa validate <task-id> --execute
```

### Execute Specific Wave
```bash
edison qa validate <task-id> --execute --wave critical
```

### Execute Specific Validators
```bash
edison qa validate <task-id> --execute --validators global-codex security
```

### Run Single Validator
```bash
edison qa run <validator-id> <task-id>
```

### Dry Run (Show Execution Plan)
```bash
edison qa validate <task-id> --dry-run
```

### Where Results Land
- Evidence: `.project/qa/validation-evidence/<task-id>/round-<N>/`
- CLI output: `command-<validator>.txt`
- Delegation: `delegation-<validator>.md`
- Reports: `validator-<id>-report.json`

## How to check validator configuration

### Configuration Files
- Base config: `src/edison/data/config/validators.yaml`
- Project overlays: `.edison/config/validators.yaml`

### Configuration Structure
```yaml
validation:
  engines:
    codex-cli:
      type: cli
      command: codex
      response_parser: codex
    zen-mcp:
      type: delegated

  validators:
    global-codex:
      name: "Global Validator (Codex)"
      engine: codex-cli
      fallback_engine: zen-mcp
      wave: critical
      blocking: true
      always_run: true

  waves:
    - name: critical
      execution: parallel
      continue_on_fail: false
```

### Generated Views
- `{{PROJECT_EDISON_DIR}}/_generated/AVAILABLE_VALIDATORS.md` - Human-readable roster
- `{{PROJECT_EDISON_DIR}}/_generated/validators/*.md` - Composed validator prompts

## How to add custom validators

1. **Define engine** (if new CLI tool):
   ```yaml
   validation:
     engines:
       my-cli:
         type: cli
         command: my-tool
         response_parser: plain_text
   ```

2. **Define validator**:
   ```yaml
   validation:
     validators:
       my-validator:
         name: "My Custom Validator"
         engine: my-cli
         fallback_engine: zen-mcp
         prompt: "validators/my-validator.md"
         wave: comprehensive
         blocking: false
         triggers: ["**/*.ts", "**/*.tsx"]
   ```

3. **Add to wave**:
   ```yaml
   validation:
     waves:
       - name: comprehensive
         validators: [..., my-validator]
   ```

4. **Create prompt file**: Add `.edison/validators/my-validator.md` with validation criteria.

5. **Regenerate**: Run `edison compose all` to update generated files.

6. **Test**: `edison qa run my-validator <task-id>` to verify.

## Understanding Execution Modes

### Direct Execution (CLI Available)
```
edison qa validate T-001 --execute

Wave: critical
  ✓ global-codex: approve (2.3s)     ← CLIEngine
  ✓ security: approve (1.1s)          ← CLIEngine
```

### Mixed Execution (CLI + Delegation)
```
Wave: critical
  ✓ global-codex: approve (2.3s)     ← CLIEngine
  → global-gemini: pending           ← ZenMCPEngine (delegation)

═══ ORCHESTRATOR ACTION REQUIRED ═══
Delegation instructions saved to evidence folder.
```

### Pure Delegation (No CLIs Available)
```
Wave: critical
  → global-codex: pending            ← ZenMCPEngine
  → global-claude: pending           ← ZenMCPEngine

All validators require delegation.
```

## FAQ

- **Why did a validator not run?** Check `triggers` patterns in YAML; use `--dry-run` to see the execution plan.

- **Can I skip a blocking validator?** No. Blocking validators are defined in YAML with `blocking: true`. Change the config to modify.

- **How do I see which validators can execute directly?** Run `edison qa validate <task-id> --dry-run` - validators marked ✓ have CLI available, → need delegation.

- **Where are validator decisions stored?** In `.project/qa/validation-evidence/<task-id>/round-<N>/` as JSON and text files.

- **What happens when CLI is not installed?** The `fallback_engine` (typically `zen-mcp`) generates delegation instructions for the orchestrator.

- **How do I handle delegated validators?** Read the instructions in `delegation-<validator>.md`, execute manually with the specified zenRole, and save results to `validator-<id>-report.json`.

- **Why does validation show "ORCHESTRATOR ACTION REQUIRED"?** Some validators couldn't execute directly. Follow the displayed instructions to complete validation.
