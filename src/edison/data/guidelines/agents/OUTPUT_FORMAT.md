# Implementation Report Output Format (Core)

Agents MUST produce a **machine-readable implementation report** for every implementation round. This is the primary structured input for:
- validators (to understand what was done, what’s risky, what’s incomplete)
- `edison session next` (to propose follow-ups and keep the session on rails)

## Where it lives

- Evidence root: `.project/qa/validation-evidence/<task-id>/`
- Round directory: `round-<N>/` (append-only; never overwrite old rounds)
- Report filename: **config-driven** (`validation.artifactPaths.implementationReportFile`, default `implementation-report.json`)

Example path:
- `.project/qa/validation-evidence/<task-id>/round-1/implementation-report.json`

## Schema (single source of truth)

See the schema for the exact required fields:
- `.edison/_generated/schemas/reports/implementation-report.schema.json`

## Minimal expected shape (illustrative)

```json
{
  "taskId": "<task-id>",
  "round": 1,
  "implementationApproach": "orchestrator-direct | delegated-single | delegated-mixed",
  "primaryModel": "<model-id>",
  "completionStatus": "complete | partial | blocked",
  "notesForValidator": "Key context, tradeoffs, and where to scrutinize",
  "followUpTasks": [
    {
      "title": "Add missing edge-case tests",
      "blockingBeforeValidation": true,
      "claimNow": true,
      "category": "test"
    }
  ],
  "delegations": [
    { "filePattern": "<path or glob>", "model": "<model-id>", "role": "<agent-role>", "outcome": "success" }
  ],
  "blockers": [
    { "description": "Waiting for <dependency>", "severity": "high", "owner": "user" }
  ],
  "tddCompliance": {
    "followed": true,
    "redEvidence": "command-test.txt",
    "greenEvidence": "command-test.txt",
    "notes": ""
  }
}
```

## Critical rules

- **`followUpTasks[]` is the canonical follow-up channel** for implementation-discovered work; `edison session next` reads it to propose splits and to enforce parent/child semantics.
- Evidence files (automation logs, Context7 markers, screenshots, exports) must live in the same round directory and be referenced from the report and the QA brief.
- Keep report content factual and actionable; no vague “done” statements without evidence pointers.
