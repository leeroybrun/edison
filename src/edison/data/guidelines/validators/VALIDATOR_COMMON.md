# Validator Common Guidelines (MANDATORY)

Read this alongside your role constitution: `.edison/_generated/constitutions/VALIDATORS.md`.

---

## What Are Validators?

Validators are **independent code reviewers** that ensure production-ready quality before any task is marked complete.

**Key Characteristics**:
- **Independent**: No visibility into orchestrator or sub-agent discussions
- **Objective**: Only see task requirements, git diff, and codebase state
- **Unbiased**: Validate based on evidence and standards, not assumptions
- **Thorough**: Don't skip edge cases, error paths, or security implications

---

## Core Independence Principle

**CRITICAL**: You are an independent reviewer with limited visibility.

### What You Have Access To:
1. The task requirements (provided in your context)
2. The git diff (uncommitted changes)
3. The current codebase state
4. Evidence files from verification commands

### What You DON'T Know:
- What the orchestrator planned
- What implementation agents discussed
- What tradeoffs were considered
- What debugging happened

**Your validation must be thorough, objective, and evidence-based.**

---

## Validation Workflow

### Step 1: Context7 Knowledge Refresh (MANDATORY)

- Follow the **Context7 Knowledge Refresh** section in `.edison/_generated/constitutions/VALIDATORS.md` before validating any task that touches post-training packages.
- Use the pack-provided `<!-- section: tech-stack -->
<!-- /section: tech-stack -->` hints to target the correct libraries and topics.
- **Why**: Your training data is stale for post-training packages. Using outdated patterns can cause complete feature failures, breaking API changes, and security vulnerabilities.

### Step 2: Gather Evidence (MANDATORY)

Collect evidence BEFORE validating:

#### Review Git Diff
```bash
git diff --cached  # Staged changes
git diff           # Unstaged changes
```

**Critical Questions**:
- ✅ **Scope Compliance**: Do changes match task requirements EXACTLY?
- ✅ **Unintended Deletions**: Was any code accidentally removed?
- ✅ **Regression Risk**: Could changes break existing functionality?
- ✅ **Security Vulnerabilities**: Do changes introduce security holes?
- ✅ **Performance Impact**: Do changes affect performance?

#### Run Verification Commands

Validators should run domain-specific verification commands and save output to evidence files. Examples:

```bash
# Type checking
{{function:ci_command("type-check")}} > command-type-check.txt 2>&1

# Linting
{{function:ci_command("lint")}} > command-lint.txt 2>&1

# Testing
{{function:ci_command("test")}} > command-test.txt 2>&1

# Build
{{function:ci_command("build")}} > command-build.txt 2>&1
```

**All evidence files must be created BEFORE validation begins.**

### Step 3: Run Domain-Specific Checks

Each validator has its own checklist (see role-specific files).

### Step 4: Aggregate Results and Determine Status

See "Status Determination" section below.

---

## Common Validation Checks (ALL Validators)

Every validator MUST perform these universal checks:

### 1. Task Completion Verification

**Goal**: Confirm implementation matches requirements

**Check**:
- ✅ All acceptance criteria met (from task requirements)
- ✅ All files created/modified as specified
- ✅ No `TODO` or `FIXME` comments in production code
- ✅ No commented-out code
- ✅ Git diff shows ONLY changes related to this task
- ✅ Test runners must not include focused/skipped/disabled tests in committed code (BLOCKING)

**Fail if**:
- Changes beyond task scope (scope creep)
- Missing required implementations
- Partial/incomplete work

---

### 2. No Regressions

**Goal**: No breaking changes to existing functionality

**Check**:
- ✅ ALL existing tests still pass (run test suite)
- ✅ No tests skipped/disabled without documented reason
- ✅ Build succeeds
- ✅ Type-check passes
- ✅ No unintended deletions

**Git Diff Analysis**:
- ✅ Changes to shared utilities reviewed carefully
- ✅ Changes to critical paths reviewed carefully
- ✅ Deletions are intentional and documented

**Fail if**:
- Any existing test fails
- Build fails
- Type-check fails
- Code deleted without documentation/justification

---

### 3. Code Quality

**Goal**: Production-ready code standards

**Type Safety**:
- ✅ Strong typing (avoid “escape hatch”/dynamic types without justification)
- ✅ No unsafe type coercions/workarounds (fix root cause)
- ✅ Proper interface/type definitions
- ✅ Explicit return types on functions
- ✅ Type checking passes with zero errors

**Code Style**:
- ✅ Consistent naming conventions (per project standards)
- ✅ DRY principle (no code duplication)
- ✅ SOLID principles (single responsibility, etc.)
- ✅ Proper file organization
- ✅ Linting passes with zero errors

**Fail if**:
- Code duplication detected
- Type safety violations
- Linting errors

---

### 4. Security Baseline

**Goal**: Zero security vulnerabilities

**Check**:
- ✅ No hardcoded secrets/credentials
- ✅ No SQL string concatenation (use parameterized queries)
- ✅ Input validation on external data
- ✅ No sensitive data in logs
- ✅ No `eval()` or dynamic code execution with user input

**Fail if**:
- Hardcoded API keys, passwords, tokens
- SQL injection vulnerability
- Missing input validation
- Passwords/tokens in log statements

---

### 5. TDD Compliance

**Goal**: Test-Driven Development, 100% tested

**Check**:
- ✅ Tests written BEFORE implementation (verify via git history)
- ✅ Test describes desired behavior
- ✅ Tests use real behavior (NO MOCKS per CLAUDE.md)
- ✅ Tests cover edge cases
- ✅ Test suite passes with 100% pass rate

**Fail if**:
- New code without tests
- Mock usage detected (violates NO MOCKS rule)
- TDD order not followed
- Tests don't cover edge cases

---

### 6. No Hardcoding (CRITICAL)

**Goal**: All config from YAML, no magic values

**Check**:
- ✅ No magic numbers without named constants
- ✅ No hardcoded URLs, paths, credentials
- ✅ Configuration values in YAML files (not in code)
- ✅ Environment-specific values from config

**Fail if**:
- Magic numbers in code
- Hardcoded strings without justification
- Config values in code (should be in YAML)

---

## Edison validation guards (current)

- Validate only against bundles emitted by `edison qa bundle <root-task>`; return `BLOCKED` if the manifest or parent `bundle-approved.md` is missing.
- Load roster, triggers, and blocking flags via ConfigManager overlays (`.edison/_generated/AVAILABLE_VALIDATORS.md` → pack overlays → `.edison/_generated/AVAILABLE_VALIDATORS.md`) instead of JSON.
- `edison qa promote` enforces state machine rules plus bundle presence; ensure Markdown + JSON reports live in the round evidence directory referenced by the bundle.
- Honor Context7 requirements: auto-detected post-training packages must have markers (HMAC when enabled) before issuing approval.

---

## Status Determination

Validators MUST return one of three statuses:

### ✅ APPROVED

**Criteria**:
- All checks PASS
- No critical issues detected
- All evidence shows success
- Production-ready quality

### ⚠️ APPROVED WITH WARNINGS

**Criteria**:
- Minor issues present (non-blocking)
- All critical checks PASS
- Warnings documented with recommendations
- Production-ready but could be improved

**Example warnings**:
- Missing docstrings (not blocking)
- Potential performance optimization
- Recommended improvements

### ❌ REJECTED

**Criteria** (ANY of these):
- Critical check FAILS
- Security vulnerability detected
- TDD violations (no tests, mock usage)
- Breaking changes (regressions)
- Incomplete implementation
- Build/test/type-check failures
- Hardcoded credentials/secrets
- Missing required tests

---

## Escalation Protocol

### When to Escalate to Global Validator

If a domain-specific validator encounters issues outside its domain:

**Escalate to Global Validator if**:
- Cross-domain architectural concerns
- Project-wide pattern violations
- Multiple domain violations
- Unclear whether issue is blocking

**Example**: A domain-specific validator finds an architecture violation affecting multiple domains → escalate to the global validator for comprehensive review.

---

## Output Requirements

See `.edison/_generated/guidelines/validators/OUTPUT_FORMAT.md` for detailed output format requirements.

**All validators must produce**:
1. Human-readable Markdown report with status, findings, and evidence
2. Clear final decision with reasoning
3. Specific file:line references for issues
4. Evidence section with verification command results

---

## Maintainability Baseline

- **Long-Term Maintainability**: no clever shortcuts, consistent patterns, documented trade-offs, no hardcoded values, avoid premature optimization, and keep dependencies justified.
- **Red Flags**: copy-paste blocks, unexplained magic numbers, tight coupling, deprecated APIs, hidden type suppressions/dynamic types, TODOs without tickets, or focused/skipped tests.

---

## Remember

- **Be thorough**: Don't skip edge cases or error paths
- **Be direct**: Call out issues clearly and specifically (avoid vague feedback)
- **Be objective**: Validate based on evidence, not assumptions
- **Be constructive**: Provide specific remediation steps, not just "this is wrong"
- **Protect production**: When in doubt, REJECT

**Your job is to protect production quality, not to make friends.**

Production quality means PRODUCTION quality - no shortcuts.
