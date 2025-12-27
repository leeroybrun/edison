<!-- TaskID: 2105-vcon-005-testing-validator -->
<!-- Priority: 2105 -->
<!-- Wave: wave-edison-migration -->
<!-- Type: feature -->
<!-- Owner: _unassigned_ -->
<!-- Status: todo -->
<!-- Created: 2025-12-02 -->
<!-- ClaimedAt: _unassigned_ -->
<!-- LastActive: _unassigned_ -->
<!-- ContinuationID: _none_ -->
<!-- Model: claude -->
<!-- ParallelGroup: wave2-groupA -->
<!-- EstimatedHours: 3 -->

# VCON-005: Create testing.md Validator Constitution

## Summary
Create a complete testing validator constitution based on the OLD system's ~760-line testing.md validator. This specialized validator checks test quality, coverage, and TDD adherence.

## Problem Statement
The OLD system had a comprehensive testing.md validator (~760 lines) that is MISSING from Edison core. This validator enforced:
- TDD patterns
- Test coverage requirements
- Test quality standards
- Integration test patterns

## Dependencies
- None

## Objectives
- [x] Create complete testing.md validator
- [x] Include TDD verification rules
- [x] Include coverage requirements
- [x] Include test quality patterns

## Source Files

### Reference - Old Validator
```
/Users/leeroy/Documents/Development/wilson-pre-edison/.agents/validators/specialized/testing.md
```

### Output Location
```
/Users/leeroy/Documents/Development/edison/src/edison/data/validators/specialized/testing.md
```

## Precise Instructions

### Step 1: Create Validator

Create `/Users/leeroy/Documents/Development/edison/src/edison/data/validators/specialized/testing.md`:

```markdown
---
id: testing
type: specialized
model: codex
triggers:
  - "**/*.test.ts"
  - "**/*.test.tsx"
  - "**/*.spec.ts"
  - "**/*.spec.tsx"
  - "**/__tests__/**/*"
blocksOnFail: true
---

# Testing Validator

**Type**: Specialized Validator
**Triggers**: Test files
**Blocking**: Yes (tests are critical)

## Constitution Awareness

**Role Type**: VALIDATOR
**Constitution**: `.edison/_generated/constitutions/VALIDATORS.md`

## Validation Scope

This validator checks test implementations for:
1. TDD pattern adherence
2. Test coverage
3. Test quality
4. Integration test patterns
5. Mock usage
6. Assertion quality

## Validation Rules

### TDD Verification

#### VR-TEST-001: Test-First Evidence
**Severity**: Warning
**Check**: Tests appear before implementation in commit history

Verify:
- Test file commits precede implementation
- OR red-green-refactor pattern visible
- Test describes expected behavior

**Fail Condition**: Implementation without tests

#### VR-TEST-002: Failing Test First
**Severity**: Info
**Check**: Test was written to fail first

Evidence:
- Git history shows test failure before pass
- Test covers new behavior, not existing

**Fail Condition**: Test written after implementation

### Coverage Requirements

#### VR-TEST-003: Coverage Threshold
**Severity**: Error
**Check**: Coverage meets minimum

Requirements:
- New files: 90% minimum
- Modified files: No coverage decrease
- Overall project: 80% minimum

**Fail Condition**: Coverage below threshold

#### VR-TEST-004: Branch Coverage
**Severity**: Warning
**Check**: Branches are covered

Verify:
- if/else both tested
- switch cases covered
- Error paths tested
- Edge cases included

**Fail Condition**: Missing branch coverage

### Test Quality

#### VR-TEST-005: Test Description Quality
**Severity**: Warning
**Check**: Test names describe behavior

Good patterns:
- "should [behavior] when [condition]"
- "returns [value] for [input]"
- "throws [error] if [condition]"

Bad patterns:
- "test1", "works", "correct"

**Fail Condition**: Non-descriptive test names

#### VR-TEST-006: Arrange-Act-Assert
**Severity**: Info
**Check**: Tests follow AAA pattern

Structure:
```typescript
it('should...', () => {
  // Arrange
  const input = ...;

  // Act
  const result = ...;

  // Assert
  expect(result).toBe(...);
});
```

**Fail Condition**: Unclear test structure

#### VR-TEST-007: Single Assertion Focus
**Severity**: Info
**Check**: Each test has focused assertions

Guideline:
- One logical assertion per test
- Multiple expect() OK if testing one behavior
- No unrelated assertions

**Fail Condition**: Tests doing too much

#### VR-TEST-008: Test Independence
**Severity**: Error
**Check**: Tests don't depend on each other

Verify:
- No shared mutable state
- Tests can run in any order
- No reliance on previous test results

**Fail Condition**: Test order dependency

### Mock Usage

#### VR-TEST-009: Mock Appropriateness
**Severity**: Warning
**Check**: Mocks are used correctly

When to mock:
- External services (APIs, databases)
- Time-dependent operations
- Expensive operations

When NOT to mock:
- Pure functions
- Simple utilities
- The code under test

**Fail Condition**: Over-mocking or under-mocking

#### VR-TEST-010: Mock Verification
**Severity**: Warning
**Check**: Mocks are verified

Verify:
- Mocks are called as expected
- Call arguments are checked
- Mock implementation is realistic

**Fail Condition**: Unverified mock usage

#### VR-TEST-011: No Implementation Mocking
**Severity**: Error
**Check**: Implementation details not mocked

Bad patterns:
- `vi.spyOn(prisma, 'lead')` with custom implementation
- Mocking internal module functions
- Mocking class methods under test

**Fail Condition**: Testing mock behavior, not real code

### Integration Tests

#### VR-TEST-012: Real Database Tests
**Severity**: Warning
**Check**: Database tests use real database

For database operations:
- Use test database container
- Transaction rollback for isolation
- No mocking Prisma client

**Fail Condition**: Mocked database in integration tests

#### VR-TEST-013: API Integration Tests
**Severity**: Warning
**Check**: API tests make real requests

For API routes:
- Use supertest or similar
- Full request/response cycle
- Auth flow included

**Fail Condition**: Mocked HTTP layer in integration tests

### Performance

#### VR-TEST-014: Test Speed
**Severity**: Warning
**Check**: Tests run quickly

Thresholds:
- Unit tests: <100ms each
- Integration tests: <1s each
- E2E tests: <10s each

**Fail Condition**: Slow tests

#### VR-TEST-015: No Production Side Effects
**Severity**: Error
**Check**: Tests don't affect production

Verify:
- No real API calls to production
- No production database connections
- No external service mutations

**Fail Condition**: Production side effects

### Assertions

#### VR-TEST-016: Specific Assertions
**Severity**: Info
**Check**: Assertions are specific

Good:
- `expect(result).toBe(5)`
- `expect(array).toHaveLength(3)`
- `expect(fn).toThrow(SpecificError)`

Weak:
- `expect(result).toBeTruthy()`
- `expect(array).toBeDefined()`

**Fail Condition**: Overly weak assertions

#### VR-TEST-017: Error Testing
**Severity**: Warning
**Check**: Error cases are tested

For each function:
- Happy path tested
- Error conditions tested
- Edge cases tested
- Validation errors tested

**Fail Condition**: No error case tests

## Output Format

```json
{
  "validator": "testing",
  "status": "APPROVED" | "APPROVED_WITH_WARNINGS" | "REJECTED",
  "filesChecked": ["src/services/__tests__/lead.test.ts"],
  "findings": [
    {
      "rule": "VR-TEST-011",
      "severity": "error",
      "file": "src/__tests__/lead.test.ts",
      "line": 25,
      "message": "Mocking prisma.lead.findMany implementation",
      "suggestion": "Use real database or test against actual Prisma behavior"
    }
  ],
  "coverage": {
    "statements": 85.2,
    "branches": 78.5,
    "functions": 90.1,
    "lines": 85.0
  },
  "summary": {
    "errors": 1,
    "warnings": 0,
    "info": 0
  }
}
```

## Context7 Requirements

```
mcp__context7__get-library-docs({
  context7CompatibleLibraryID: "/vitest-dev/vitest",
  topic: "testing-patterns"
})
```
```

## Verification Checklist
- [ ] Core validator created
- [ ] TDD verification rules included
- [ ] Coverage requirement rules included
- [ ] Test quality rules included
- [ ] Mock usage rules included
- [ ] blocksOnFail is true
- [ ] Coverage object in output

## Success Criteria
A complete testing validator exists that enforces TDD patterns, coverage requirements, and test quality standards.

## Related Issues
- Audit ID: Wave 5 validator findings
