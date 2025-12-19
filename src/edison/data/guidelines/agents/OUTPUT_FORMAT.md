# Implementation Report Output Format (Core)

Agents MUST produce a **structured implementation report** for every implementation round.

Canonical format: **Markdown + YAML frontmatter** (LLM-readable body, machine-readable frontmatter).

## Where it lives

- Evidence root: `{{fn:evidence_root}}/<task-id>/`
- Round directory: `round-<N>/` (append-only; never overwrite old rounds)
- Report filename: **config-driven** (`validation.artifactPaths.implementationReportFile`, default `implementation-report.md`)

Example path:
- `{{fn:evidence_root}}/<task-id>/round-1/implementation-report.md`

## Schema (single source of truth)

See the schema for the exact required fields:
- `{{fn:project_config_dir}}/_generated/schemas/reports/implementation-report.schema.yaml`

## Required machine fields (YAML frontmatter)

```yaml
---
taskId: "<task-id>"
round: 1
implementationApproach: "orchestrator-direct" # or delegated-single | delegated-mixed
primaryModel: "<model-id>"
completionStatus: "complete" # or partial | blocked
notesForValidator: "Key context, tradeoffs, and where to scrutinize"
followUpTasks:
  - title: "Add missing edge-case tests"
    blockingBeforeValidation: true
    claimNow: true
    category: "test"
delegations:
  - filePattern: "<path or glob>"
    model: "<model-id>"
    role: "<agent-role>"
    outcome: "success"
blockers:
  - description: "Waiting for <dependency>"
    severity: "high"
    owner: "user"
tddCompliance:
  followed: true
  redEvidence: "command-test.txt"
  greenEvidence: "command-test.txt"
  notes: ""
tracking:
  processId: 12345
  startedAt: "2025-12-02T10:30:45Z"
  completedAt: "2025-12-02T10:31:12Z"
---
```

## Human body (Markdown)

After the frontmatter, include a short Markdown body for humans/validators (recommended):
- Summary (what changed)
- Evidence reviewed/generated (commands + filenames)
- Risks / known gaps
- Follow-ups rationale (why blocking/non-blocking)

## Critical rules

- **`followUpTasks[]` is the canonical follow-up channel** for implementation-discovered work; `edison session next` reads it to propose splits and to enforce parent/child semantics.
- Evidence files (automation logs, Context7 markers, screenshots, exports) must live in the same round directory and be referenced from the report and the QA brief.
- Keep report content factual and actionable; no vague “done” statements without evidence pointers.
