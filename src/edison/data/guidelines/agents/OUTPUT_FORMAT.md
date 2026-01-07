# Implementation Report Output Format (Core)

Agents MUST produce a **structured implementation report** for every implementation round.

Canonical format: **Markdown + YAML frontmatter** (LLM-readable body, machine-readable frontmatter).

## Where it lives

- Round directory: `{{fn:evidence_root}}/<task-id>/round-<N>/` (append-only; never overwrite old rounds)
- Report filename: **config-driven** (`validation.artifactPaths.implementationReportFile`, default `{{config.validation.artifactPaths.implementationReportFile}}`)
- Command evidence: stored separately under the fingerprinted snapshot store (`.project/qa/evidence-snapshots/...`) and may be shared across tasks/rounds when the repo fingerprint is unchanged.

Example path:
- `{{fn:evidence_root}}/<task-id>/round-1/{{config.validation.artifactPaths.implementationReportFile}}`

## Schema (single source of truth)

See the schema for the exact required fields:
- `edison read implementation-report.schema.yaml --type schemas/reports`

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
  redEvidence: "edison evidence status <task-id> --preset <preset>"
  greenEvidence: "edison evidence status <task-id> --preset <preset>"
  notes: ""
tracking:
  processId: 12345
  startedAt: "2025-12-02T10:30:45Z"
  completedAt: "2025-12-02T10:31:12Z" # Optional until the round is completed
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
- Round artifacts (validator reports, `{{config.validation.artifactPaths.bundleSummaryFile}}`, Context7 markers, screenshots) live in the round directory and must be referenced from the report and QA brief.
- Command evidence (build/test/lint outputs) must be captured via `edison evidence capture` and is referenced via `edison evidence status` (snapshot-based).
- Keep report content factual and actionable; no vague “done” statements without evidence pointers.
