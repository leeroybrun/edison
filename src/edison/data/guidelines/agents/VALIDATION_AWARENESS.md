# Validation Awareness

<!-- MANDATORY: All agents MUST read this before implementation -->
<!-- Generated from pre-Edison agent content extraction -->

## Purpose

All agent work is validated by a multi-validator architecture before tasks can be promoted to `done`. Understanding this system helps you produce work that passes validation on the first try.

## How Validation Works

**Full Guide**: See `.edison/_generated/guidelines/shared/VALIDATION.md` for complete workflow details.

### Quick Summary

Your work is validated by the roster in `AVAILABLE_VALIDATORS.md`, organized into three tiers:

- **Tier 1: Global Validators** (always run, unanimous approval required)
  - Review end-to-end correctness, architecture, patterns
  - All must approve before proceeding to next tier

- **Tier 2: Critical Validators** (always run, blocking)
  - Security, performance, testing validation
  - ANY failure blocks promotion

- **Tier 3: Specialized Validators** (pattern-triggered)
  - Framework-specific best practices
  - Triggered by changed file patterns
  - Block if configured with `blocksOnFail=true`

**Validators run in waves**: Global → Critical → Specialized. See `AVAILABLE_VALIDATORS.md` for current roster and triggers.

### Your Role: Produce Excellent Work

**CRITICAL**: You do NOT run validation yourself. The orchestrator runs ALL applicable validators in batched parallel waves after you complete your work.

**Your incentive**: Produce excellent work to **pass all validators on first try**.

## Tips for First-Try Approval

### Security Best Practices
- Add authentication checks to protected resources
- Validate all input with schema validation
- Sanitize error messages (no internal details exposed)

### Performance Best Practices
- Limit fields in queries (select only needed data)
- Use pagination for large datasets
- Avoid N+1 queries and unnecessary computations

### Testing Best Practices
- Follow TDD: Write tests FIRST (red), implement (green), refactor
- Use real behavior, real code, real libs - NO MOCKS
- Ensure all tests pass before marking work complete

### Framework-Specific Best Practices
- Follow proper state management patterns
- Handle error/loading/empty states
- Use accessibility requirements (ARIA labels, semantic HTML)
- Refer to pack guidelines for specialized requirements

## CLI Commands

```bash
# Mark task ready for validation (agent)
edison task ready <task-id>
```

**NOTE**: Agents do NOT run validation - the orchestrator does.

## References

**Complete validation guide**: `.edison/_generated/guidelines/shared/VALIDATION.md`

**Additional resources**:
- Validator roster (dynamic): `{{PROJECT_EDISON_DIR}}/_generated/AVAILABLE_VALIDATORS.md`
- Validation output format: `.edison/_generated/guidelines/validators/OUTPUT_FORMAT.md`

---

**Version**: 1.0 (Extracted from pre-Edison agents)
**Applies to**: ALL implementing agents
**Key Insight**: Agents produce excellent work; orchestrator validates
