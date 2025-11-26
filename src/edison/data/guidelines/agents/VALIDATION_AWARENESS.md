# Validation Awareness

<!-- MANDATORY: All agents MUST read this before implementation -->
<!-- Generated from pre-Edison agent content extraction -->

## Purpose

All agent work is validated by a multi-validator architecture before tasks can be promoted to `done`. Agents must understand this system to produce work that passes validation on the first try. This document explains the 9-validator architecture and your role within it.

## Requirements

### The Multi-Validator Architecture

Your work will be validated by **9 independent validators** organized in three tiers:

#### Tier 1: Global Validators (ALWAYS run, BOTH must approve)

| Validator | Model | Purpose |
|-----------|-------|---------|
| **Codex Global** | Codex | Code quality, patterns, consistency |
| **Claude Global** | Claude | Architecture, design, maintainability |

**Both global validators MUST approve** for a task to pass validation.

#### Tier 2: Critical Validators (ALWAYS run, blocking)

| Validator | Model | Purpose | Blocks |
|-----------|-------|---------|--------|
| **Security** | Codex | Auth, input validation, secrets, injection attacks | Yes |
| **Performance** | Codex | Query optimization, caching, memory leaks | Yes |

**Critical validators can BLOCK task promotion** even if globals approve.

#### Tier 3: Specialized Validators (triggered by file patterns)

Specialized validators are triggered by file patterns defined in active packs. These validators ensure framework-specific best practices are followed.

**Specialized validators run based on changed files**. Active packs contribute specialized validators for their frameworks. Check `.edison/config/validators.yml` for current triggers and validator configuration.

### Your Role: Produce Excellent Work

**CRITICAL**: You do NOT run validation yourself. The orchestrator runs ALL applicable validators in batched parallel waves after you complete your work.

**Your incentive**: Produce excellent work to **pass all validators on first try**.

#### What Validators Check

**Codex Global**:
- Code follows established patterns
- Consistent naming conventions
- No code smells or anti-patterns
- Language-specific best practices

**Claude Global**:
- Architecture makes sense
- Code is maintainable
- Design decisions are sound
- No over-engineering or under-engineering

**Security Validator** (CRITICAL):
- Authentication checks on all protected resources
- Input validation with appropriate schema validation tools
- No injection vulnerabilities
- No cross-site scripting (XSS) vulnerabilities
- Sensitive data not exposed in responses
- Error messages don't leak internal details

**Performance Validator**:
- No N+1 queries
- Proper indexing used
- Pagination for large datasets
- Efficient resource utilization
- Proper caching strategies

**Testing Validator**:
- TDD compliance (tests written first)
- Adequate test coverage (>=80%)
- No skipped tests
- Fast tests (<100ms unit, <1s integration)
- Real behavior tested (minimal mocking)

**Specialized Validators** (triggered by file patterns):
- Framework-specific best practices followed
- Proper conventions and patterns used
- Accessibility standards met (where applicable)
- Comprehensive error handling
- Configuration follows conventions

### Validation Workflow

```
Agent completes work
        ↓
Agent marks task ready (edison tasks ready <task-id>)
        ↓
Orchestrator runs validators (batched parallel waves)
        ↓
    ┌───────────────────┐
    │ All validators    │ → Task promoted to done
    │ PASS              │
    └───────────────────┘
            OR
    ┌───────────────────┐
    │ Any validator     │ → Task blocked, issues returned
    │ FAILS             │   Agent must address and re-submit
    └───────────────────┘
```

### Validator Output Format

Validators produce structured reports:

```json
{
  "validator": "security",
  "status": "FAIL",
  "blocking": true,
  "findings": [
    {
      "severity": "CRITICAL",
      "file": "src/api/resource/handler.ts",
      "line": 23,
      "issue": "Missing authentication check",
      "fix": "Add authentication verification before processing request"
    }
  ],
  "summary": "1 critical issue found"
}
```

### How to Pass Validation

**Security Validator**:
```
PSEUDOCODE:
1. Add authentication checks to protected resources
   user = authenticate(request)

2. Validate all input with schema validation
   validated_data = validate_schema(input_data)

3. Sanitize error messages (no internal details)
   return error_response(
     message: "Invalid request",  // Generic message
     status: 400
   )
```

**Performance Validator**:
```
PSEUDOCODE:
1. Limit fields in queries (select only needed data)
   data = query_database({
     fields: [id, name, status]
   })

2. Use pagination for large datasets
   data = query_database({
     limit: page_size,
     offset: (page - 1) * page_size
   })
```

**Testing Validator**:
```
PSEUDOCODE:
1. Write tests FIRST (TDD workflow)
2. Run tests, verify they FAIL (red)
3. Implement feature
4. Run tests, verify they PASS (green)
5. Refactor if needed
```

**Specialized Validators**:
```
PSEUDOCODE:
Framework-specific validators check:
1. Proper state management patterns
2. Error/loading/empty state handling
3. Accessibility requirements (ARIA labels, semantic HTML)
4. Framework-specific best practices
5. Proper resource lifecycle management

Refer to pack guidelines for specific requirements.
```

## Evidence Required

For validation to pass, provide:

1. **Implementation Report JSON** - Per round, documenting changes
2. **Test Results** - All tests passing
3. **Build Verification** - Type-check, lint, build passing
4. **Coverage Report** - >=80% on critical paths
5. **TDD Evidence** - Git history showing tests before code

Evidence stored in: `.project/qa/validation-evidence/<task-id>/round-N/`

## CLI Commands

```bash
# Mark task ready for validation (agent)
edison tasks ready <task-id>

# Check validation status (orchestrator)
edison validators status <task-id>

# View validator reports (after validation)
cat .project/qa/validation-evidence/<task-id>/round-N/bundle-*.json
```

**NOTE**: Agents do NOT run `edison validators validate` - the orchestrator does.

## References

- Extended validation guide: `.edison/core/guides/extended/VALIDATION_GUIDE.md`
- Validator configuration: `.edison/validators/config.json`
- Validation output format: `.edison/validators/OUTPUT_FORMAT.md`

---

**Version**: 1.0 (Extracted from pre-Edison agents)
**Applies to**: ALL implementing agents
**Key Insight**: Agents produce excellent work; orchestrator validates
