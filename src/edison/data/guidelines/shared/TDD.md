# Test-Driven Development (TDD)

This is the shared, technology-agnostic TDD workflow used across Edison.

## Core Rule

For every change:
1. **RED**: write a test that fails for the right reason
2. **GREEN**: implement the smallest change to pass
3. **REFACTOR**: improve design without changing behavior (tests stay green)

## Evidence Requirements

When you claim TDD was followed, evidence must show:
- The failing test output (RED)
- The passing test output (GREEN)
- Confirmation tests still pass after refactor (REFACTOR)

## Red Flags (TDD Violations)

🚩 **Immediate rejection**:
- Tests written after implementation
- Tests that always pass (no assertions)
- Tests removed/disabled to “make it pass”
- “Mocks everywhere” that bypass real behavior

🟡 **Needs review**:
- Coverage barely meets threshold with no justification
- Tests tightly coupled to implementation details
- Missing edge case coverage

---

## TDD When Delegating to Sub-Agents

When delegating, you must explicitly require TDD and demand evidence for each phase.

### Template: Component Builder

```
Task(subagent_type='component-builder', prompt=`
Build <ComponentName> using strict TDD (RED-GREEN-REFACTOR).

1) RED
- Create a failing test file: <component-test-file>
- Run tests and capture the failing output (prove it fails for the right reason)

2) GREEN
- Implement the component: <component-impl-file>
- Run tests and capture passing output

3) REFACTOR
- Refactor for clarity/DRY/structure without changing behavior
- Re-run tests and capture passing output

Return:
- Implementation diff
- Test diff
- RED/GREEN/REFACTOR evidence
`)
```

### Template: API Builder

```
Task(subagent_type='api-builder', prompt=`
Implement <HTTP_METHOD> <endpoint> using strict TDD (RED-GREEN-REFACTOR).

1) RED
- Write an integration test: <api-test-file>
- Run tests and capture failing output

2) GREEN
- Implement the route/handler: <route-file>
- Run tests and capture passing output

3) REFACTOR
- Extract shared logic, improve naming, harden error handling
- Re-run tests and capture passing output

Return:
- Route/handler diff
- Test diff
- RED/GREEN/REFACTOR evidence
`)
```

### Template: Database Architect

```
Task(subagent_type='database-architect', prompt=`
Implement schema/migrations and data access using strict TDD (RED-GREEN-REFACTOR).

Schema/Migrations:
- RED: schema/migration validation test fails
- GREEN: schema + migration passes
- REFACTOR: improve indexes/constraints; tests still pass

Data Access:
- RED: repository/query test fails
- GREEN: implement data access; test passes
- REFACTOR: optimize queries/structure; tests still pass

Integration:
- RED: end-to-end integration test fails
- GREEN: connect layers; passes
- REFACTOR: cleanup; passes

Return:
- Schema/migration diffs
- Data-access diffs
- Test diffs
- Evidence for each TDD cycle
`)
```

---

## TDD Troubleshooting

### Test Won't Fail (RED phase)
- **Symptom**: The test passes even though the behavior is not implemented (or is broken).
- **Cause**: The test is not asserting the intended behavior (wrong setup, missing assertions, asserting a stub/default).
- **Fix**: Tighten the assertion to the externally-visible outcome, verify the test targets the right function/module, and remove accidental stubbing.

### Test Won't Pass (GREEN phase)
- **Symptom**: The test fails, but changes you make do not move it toward green.
- **Cause**: Misread requirements, incorrect assumptions about inputs/outputs, or implementation is in the wrong place.
- **Fix**: Re-read the test as the spec, log/inspect inputs at the boundary, implement the smallest change that satisfies the failing assertion, then rerun.

### Refactor Breaks Tests
- **Symptom**: Tests were green, refactor caused failures without intended behavior change.
- **Cause**: The refactor unintentionally changed behavior, contracts, or data shape (often due to hidden coupling).
- **Fix**: Revert to last green, refactor in smaller steps, and ensure each step preserves behavior with a full test run.

### Flaky Tests
- **Symptom**: The same tests sometimes pass and sometimes fail.
- **Cause**: Hidden shared state, time/race sensitivity, external dependencies, or nondeterministic data.
- **Fix**: Isolate state per test, control time, avoid sleeps, and replace external dependencies with real-but-controlled test resources.
