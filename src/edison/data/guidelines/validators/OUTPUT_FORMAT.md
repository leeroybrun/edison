# Validator Output Format

**Single Source of Truth**: All validators MUST use this standardized Markdown format.

---

## Universal Report Template

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
| Type Check | <type-check-command> | ✅ PASS / ❌ FAIL |
| Lint | <lint-command> | ✅ PASS / ❌ FAIL |
| Tests | <test-command> | ✅ PASS / ❌ FAIL |
| Build | <build-command> | ✅ PASS / ❌ FAIL / N/A |

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

Reference evidence files: command-test.txt, command-lint.txt, etc.

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
