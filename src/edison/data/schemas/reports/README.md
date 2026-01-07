# Report Schemas

Schemas for agent output formats and structured reports.

## Schemas

| Schema | Purpose | Validated In |
|--------|---------|--------------|
| `implementation-report.schema.yaml` | Implementation round report (agents/orchestrator) | Runtime (when schema validation is enabled) |
| `validator-report.schema.yaml` | Validator execution results | Tests |
| `delegation-report.schema.yaml` | Agent delegation summaries | Tests |

## Usage

Report schemas define the structure of output documents produced by agents:

- **implementation-report**: Structured output from implementation rounds including follow-ups and validator-facing notes
- **validator-report**: Structured output from validator executions including tracking info, verdicts, and timestamps
- **delegation-report**: Summary of delegation decisions and outcomes

### Canonical File Format

Reports are written as **Markdown with YAML frontmatter**:
- YAML frontmatter = machine-readable payload validated against these JSON schemas
- Markdown body = optional human/LLM-readable explanation and evidence pointers

## Related Code

- `edison qa validate` - Validator execution
- `{{fn:evidence_root}}/` - Round artefacts (reports/markers/summaries)
- `.project/qa/evidence-snapshots/` - Command evidence snapshots (build/test/lint outputs)
- Agent delegation workflows
