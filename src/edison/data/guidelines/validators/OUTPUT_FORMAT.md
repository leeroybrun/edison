# Validator Output Format

Validators MUST produce a **structured validator report** for every validation run/round. This is the canonical structured input for:
- QA promotion guards (bundle approval)
- `edison qa validate` aggregation
- auditability and re-validation rounds

Canonical format: **Markdown + YAML frontmatter** (LLM-readable body, machine-readable frontmatter).

---

## Report File (REQUIRED): Markdown + YAML frontmatter

**Schema (single source of truth)**:
- `edison read validator-report.schema.yaml --type schemas/reports`

**Location (per round)**:
- `{{fn:evidence_root}}/<task-id>/round-<N>/validator-<validatorId>-report.md`

**Minimal expected frontmatter (illustrative)**:
```yaml
---
taskId: "TASK-123"
round: 1
validatorId: "security"
model: "codex"
verdict: "approve" # approve | reject | blocked | pending
summary: "All checks pass; no blocking issues found."
findings: []
tracking:
  processId: 12345
  startedAt: "2025-11-24T12:00:00Z"
  completedAt: "2025-11-24T12:10:00Z" # Optional until the run is completed
---
```

**Critical rules**
- The `model` field is mandatory and MUST match the validator’s configured engine/model binding (see `validation.validators` in merged config).
- The `tracking.processId` + `tracking.startedAt` fields are mandatory; `tracking.completedAt` is optional until completion. Start/complete tracking via the configured Edison tracking commands; do not fabricate timestamps.
- On rejection, append a new round directory (`round-<N+1>/`) and a new “Round N” section in the QA brief; never overwrite previous round reports.

---

## Markdown Body (RECOMMENDED)

After the frontmatter, include a short Markdown body for humans. For example:

```markdown
# {Validator Name} Validation Report

**Task**: [Task ID and Description]
**Status**: ✅ APPROVED | ⚠️ APPROVED WITH WARNINGS | ❌ REJECTED
**Timestamp**: [ISO 8601 timestamp]

---

## Summary
[2-3 sentence summary of overall findings]

---

## Evidence
| Check | Command | Status |
|-------|---------|--------|
| Command Evidence | <configured CI command> | ✅ PASS / ❌ FAIL / N/A |
| Context7 Markers | context7-*.txt | ✅ PRESENT / ❌ MISSING / N/A |

Reference the round evidence files (command-*.txt, context7-*.txt, validator-*-report.md, etc).

---

## Validation Results

### 1. {Check Name}: ✅ PASS | ⚠️ WARNING | ❌ FAIL
[Findings with file:line references]

### 2. {Check Name}: ✅ PASS | ⚠️ WARNING | ❌ FAIL
[Findings]

---

## Critical Issues (Blockers)
[List blocking issues that MUST be fixed]

---

## Warnings (Should Fix)
[List non-blocking issues]

---

## Final Decision
**Status**: ✅ APPROVED | ⚠️ APPROVED WITH WARNINGS | ❌ REJECTED
**Reasoning**: [1-2 sentence explanation]
```

---

## Section Requirements

### 1. Header
- **Task**: `**Task**: [task-id] - Brief description`
- **Status**: One of three values (see Status Definitions)
- **Timestamp**: ISO 8601 with timezone (e.g., `2025-12-02T10:30:45+00:00`)

### 2. Summary
- 2-3 sentences maximum
- Focus on overall quality and key findings

### 3. Evidence
Markdown table with validation tool results:
- **Check**: Human-readable name
- **Command**: Exact command executed
- **Status**: ✅ PASS, ❌ FAIL, or N/A

Reference evidence files: {{fn:required_evidence_files("inline")}}.

### 4. Validation Results
Numbered checks with status indicators (✅ PASS | ⚠️ WARNING | ❌ FAIL)

**Requirements**: Include file:line references, clear descriptions, actionable recommendations

**Example**:
```markdown
### 1. Type Safety: ❌ FAIL
- `path/to/file.ext:42` - Missing return type annotation
```

### 5. Critical Issues & Warnings
- **Critical Issues**: Blocking issues (security, test failures, TDD violations)
- **Warnings**: Non-blocking improvements (docs, style)

Format: `- **Category**: Description at file:line`

### 6. Final Decision
Two-line format: Status + Reasoning (1-2 sentences)

---

## Status Definitions

**✅ APPROVED**:
- All checks PASS, no critical issues, no security vulnerabilities

**⚠️ APPROVED WITH WARNINGS**:
- Core functionality validated, minor warnings only, no critical issues

**❌ REJECTED**:
- Any critical issue: security vulnerabilities, TDD violations, test/type-check failures, breaking changes, incomplete implementation

---

## Validator-Specific Extensions

Validators may add domain-specific sections:

- **Stack-specific**: Language/runtime conventions, framework patterns, async/concurrency rules (when applicable)
- **Edison**: CLI command patterns, configuration patterns, entity patterns, platform output compliance
- **Global**: Checklist, Context7 refresh notes, git diff analysis
