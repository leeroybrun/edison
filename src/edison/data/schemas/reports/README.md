# Report Schemas

Schemas for agent output formats and structured reports.

## Schemas

| Schema | Purpose | Validated In |
|--------|---------|--------------|
| `validator-report.schema.json` | Validator execution results | Tests |
| `delegation-report.schema.json` | Agent delegation summaries | Tests |

## Usage

Report schemas define the structure of output documents produced by agents:

- **validator-report**: Structured output from validator executions including tracking info, verdicts, and timestamps
- **delegation-report**: Summary of delegation decisions and outcomes

## Related Code

- `scripts/validators/validate` - Validator execution
- `.project/qa/validation-evidence/` - Validation output storage
- Agent delegation workflows
