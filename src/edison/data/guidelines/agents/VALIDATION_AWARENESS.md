# Validation Awareness

<!-- MANDATORY: All agents MUST read this before implementation -->
<!-- Generated from pre-Edison agent content extraction -->

## Purpose

All agent work is validated by a multi-validator architecture before tasks can be promoted to `done`. Agents must understand this system to produce work that passes validation on the first try. This document explains the tiered validator architecture and how to use the dynamic roster in `AVAILABLE_VALIDATORS.md`.

## Requirements

### The Multi-Validator Architecture

Your work is validated by the roster in `AVAILABLE_VALIDATORS.md`, organized into three tiers:

#### Tier 1: Global Validators (always run; all must approve)
- Current global validators and models are listed in `AVAILABLE_VALIDATORS.md`.
- Global validators review end-to-end correctness and must unanimously approve.

#### Tier 2: Critical Validators (always run; blocking)
- The critical validator roster lives in `AVAILABLE_VALIDATORS.md`.
- Any critical validator rejection blocks promotion, even if globals approve.

#### Tier 3: Specialized Validators (pattern-triggered)
- Triggered by file patterns defined in `.edison/_generated/AVAILABLE_VALIDATORS.md`.
- Active specialized validators and their triggers are documented in `AVAILABLE_VALIDATORS.md`.
- These validators can block if `blocksOnFail=true` in config.

**Specialized validators run based on changed files**. Active packs contribute specialized validators for their frameworks. Check `.edison/_generated/AVAILABLE_VALIDATORS.md` for current triggers and validator configuration.

### Your Role: Produce Excellent Work

**CRITICAL**: You do NOT run validation yourself. The orchestrator runs ALL applicable validators in batched parallel waves after you complete your work.

**Your incentive**: Produce excellent work to **pass all validators on first try**.

#### What Validators Check

**Global Validators** (Tier 1):
- Code follows established patterns and naming conventions
- Architecture makes sense and is maintainable
- Design decisions are sound
- No code smells or anti-patterns

**Critical Validators** (Tier 2):
- **Security**: Authentication, input validation, injection prevention, sensitive data handling.
- **Performance**: Query optimization, indexing, pagination, resource utilization.
- **Testing**: TDD compliance, coverage, test quality, no skipped tests.

**Specialized Validators** (Tier 3):
- Framework-specific best practices
- Accessibility standards
- Configuration conventions
- Domain-specific rules

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

**Security Validation**:
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

**Performance Validation**:
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

**Testing Validation**:
```
PSEUDOCODE:
1. Write tests FIRST (TDD workflow)
2. Run tests, verify they FAIL (red)
3. Implement feature
4. Run tests, verify they PASS (green)
5. Refactor if needed
```

**Specialized Validation**:
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

- Validator roster (dynamic): `{{PROJECT_EDISON_DIR}}/_generated/AVAILABLE_VALIDATORS.md`
- Extended validation guide: `.edison/_generated/guidelines/shared/VALIDATION.md`
- Validator configuration: `.edison/_generated/AVAILABLE_VALIDATORS.md`
- Validation output format: `.edison/_generated/guidelines/validators/OUTPUT_FORMAT.md`

---

**Version**: 1.0 (Extracted from pre-Edison agents)
**Applies to**: ALL implementing agents
**Key Insight**: Agents produce excellent work; orchestrator validates
