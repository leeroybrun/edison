# TDD Requirement (MANDATORY)

<!-- MANDATORY: All agents MUST read this before implementation -->
<!-- Technology-agnostic TDD guidelines -->

## Purpose

Test-Driven Development (TDD) is NON-NEGOTIABLE for all implementation work. This document defines the RED-GREEN-REFACTOR cycle that all agents must follow. TDD ensures code quality, catches regressions, and provides documentation through tests.

**Framework-specific test patterns**: Consult active test framework packs for concrete implementations.

## Requirements

### The TDD Cycle: RED-GREEN-REFACTOR

**YOU MUST FOLLOW TEST-DRIVEN DEVELOPMENT (TDD)** - This is NON-NEGOTIABLE.

#### 1. RED Phase: Write Tests First

Write tests BEFORE any implementation code. Tests MUST fail initially.

```pseudocode
// Generic pattern: Test behavior before implementation exists
test_suite("Feature Under Test", function() {
  test("behavior description", function() {
    // Arrange: Set up test conditions
    input = create_test_input()

    // Act: Execute the feature
    result = execute_feature(input)

    // Assert: Verify expected behavior
    assert_equals(result.status, SUCCESS)
    assert_defined(result.id)
  })
})
```

**Verify RED Phase**:
```bash
<run test command from active test framework>
# Expected: Test FAILS (implementation not written yet)
```

**RED Phase Checklist**:
- [ ] Test written BEFORE implementation
- [ ] Test fails when run
- [ ] Test failure message is clear
- [ ] Test covers the specific functionality

#### 2. GREEN Phase: Minimal Implementation

Write the MINIMUM code needed to make the test pass.

```pseudocode
// Implement just enough to satisfy the test
function execute_feature(input) {
  // Parse input
  data = parse(input)

  // Execute minimal logic
  result = create_resource(data)

  // Return expected format
  return success_response(result)
}
```

**Verify GREEN Phase**:
```bash
<run test command from active test framework>
# Expected: Test PASSES
```

**GREEN Phase Checklist**:
- [ ] Implementation makes test pass
- [ ] No extra code beyond what's needed
- [ ] Test passes consistently

#### 3. REFACTOR Phase: Clean Up

Improve code quality while keeping tests passing.

```pseudocode
// Add validation, error handling, robustness
function execute_feature(input) {
  try {
    // Validate input against schema
    data = validate_against_schema(input)

    // Execute with error handling
    result = create_resource(data)

    // Return structured response
    return success_response({ data: result })

  } catch (validation_error) {
    return error_response(
      message: "Validation failed",
      details: validation_error.details,
      status: 400
    )
  } catch (error) {
    throw error  // Let global handler manage unexpected errors
  }
}
```

**Verify REFACTOR Phase**:
```bash
<run test command from active test framework>
# Expected: ALL tests still PASS
```

**REFACTOR Phase Checklist**:
- [ ] Code is cleaner/more readable
- [ ] Error handling added
- [ ] Validation added
- [ ] ALL tests still pass

### Testing Patterns by Agent Type

**Note**: For framework-specific implementations, consult active pack guidelines (e.g., vitest pack for test runner syntax, prisma pack for database testing patterns, react pack for component testing).

#### API/Service Layer Testing (api-builder)

**Pattern**: Test real behavior with committed data and isolated test namespaces.

```pseudocode
// Generate unique test identifiers to avoid collisions
TEST_NAMESPACE = "test-" + current_timestamp()
generate_unique_id() {
  return TEST_NAMESPACE + "-" + random_string()
}

test_suite("API Endpoint: GET /resources", function() {
  // Cleanup after tests complete
  after_all_tests(function() {
    delete_all_records_where(field_contains: TEST_NAMESPACE)
  })

  test("filters by status parameter", async function() {
    // Arrange: Create real test data in storage
    test_resource = create_resource({
      identifier: "https://" + generate_unique_id() + ".com",
      name: "Test Resource",
      status: "ACTIVE"
    })

    // Act: Call real API endpoint
    response = call_api_endpoint(GET, "/resources?status=ACTIVE")

    // Assert: Verify response
    assert_equals(response.status, 200)
    assert_contains(response.data, test_resource)
  })
})
```

**Key Principles**:
- Use real data stores (no mocks for storage layer)
- Generate unique identifiers for test isolation
- Clean up test data after completion
- Test actual API behavior, not mocked behavior

#### Component/UI Testing (component-builder)

**Pattern**: Test component rendering and user interactions.

```pseudocode
// Import component testing utilities from active test framework pack
import { render, find_element, simulate_event } from "test_framework"

test_suite("DisplayCard Component", function() {
  test("renders content correctly", function() {
    // Arrange: Prepare component props
    test_data = { name: "Test Item", status: "ACTIVE" }

    // Act: Render component
    rendered = render(Component, props: test_data)

    // Assert: Verify rendered content
    assert_element_exists(rendered, text: "Test Item")
  })

  test("handles user interaction", async function() {
    // Arrange: Create mock callback
    callback_spy = create_spy_function()
    test_data = { name: "Test Item" }

    // Act: Render and simulate interaction
    rendered = render(Component, props: { data: test_data, on_click: callback_spy })
    button = find_element(rendered, role: "button")
    simulate_event(button, "click")

    // Assert: Verify callback was invoked
    assert_called_once(callback_spy)
  })
})
```

**Key Principles**:
- Test from user perspective (render, find, interact)
- Verify visual output and behavior
- Use spy functions for callback verification
- Avoid testing implementation details

#### Database/Schema Testing (database-architect)

**Pattern**: Test schema constraints, relationships, and data integrity.

```pseudocode
test_suite("Resource Model", function() {
  test("enforces unique constraint on identifier", async function() {
    // Arrange: Create first record
    unique_identifier = "unique-" + generate_unique_id()
    create_record("Resource", { identifier: unique_identifier, name: "First" })

    // Act & Assert: Attempt duplicate creation
    expect_error_thrown(function() {
      create_record("Resource", { identifier: unique_identifier, name: "Second" })
    }, error_type: "UNIQUE_CONSTRAINT_VIOLATION")
  })

  test("cascades delete to related records", async function() {
    // Arrange: Create parent and child records
    parent = create_record("Resource", { name: "Parent" })
    child = create_record("Note", { resource_id: parent.id, content: "Note 1" })

    // Act: Delete parent
    delete_record("Resource", id: parent.id)

    // Assert: Verify child was also deleted
    remaining_children = find_all_records("Note", where: { resource_id: parent.id })
    assert_equals(remaining_children.length, 0)
  })
})
```

**Key Principles**:
- Test schema constraints (unique, foreign keys, etc.)
- Test relationship behavior (cascade, set null, etc.)
- Use real database operations
- Verify data integrity rules

### What NOT To Do

**NEVER**:
- Implement before writing tests
- "I'll add tests later" - NO!
- Skip test verification (RED phase must fail)
- Use excessive mocking (test real behavior)
- Leave skipped tests (`.skip()`)
- Commit with failing tests

**Red Flags**:
- Tests written AFTER code (check git history)
- No tests at all
- All tests use mocks (not testing reality)
- Multiple skipped tests
- Tests have TODO comments

### Performance Targets

**General Guidelines**: Fast tests enable rapid TDD cycles.

| Test Type | Target Time | Description |
|-----------|-------------|-------------|
| Unit tests | <100ms each | Pure logic, no external dependencies |
| Integration tests | <1s each | Multiple components working together |
| API/Service tests | <100ms each | Service layer with real dependencies |
| UI/Component tests | <200ms each | Rendering and interaction tests |
| End-to-End tests | <5s each | Full user journey tests |

**Note**: Actual performance depends on test framework, hardware, and dependencies. Consult active test framework pack for optimization strategies.

## Evidence Required

TDD evidence must be provided for every implementation:

1. **Git History**: Test commit BEFORE implementation commit
   ```bash
   git log --oneline path/to/test_file
   git log --oneline path/to/implementation_file
   # Test commit MUST precede implementation commit
   ```

2. **RED Phase Evidence**: Screenshot or log of failing tests
   ```bash
   # Save test failure output to evidence directory
   <test_command> 2>&1 > .project/qa/validation-evidence/<task-id>/red-phase.txt
   ```

3. **GREEN Phase Evidence**: All tests passing
   ```bash
   # Save test success output to evidence directory
   <test_command> 2>&1 > .project/qa/validation-evidence/<task-id>/green-phase.txt
   ```

4. **Coverage Report**: Minimum 80% coverage on critical paths
   ```bash
   <test_command_with_coverage>
   # Save coverage report to evidence directory
   ```

## CLI Commands

**Note**: Actual commands depend on your active test framework pack. Examples below use generic placeholders.

```bash
# Run all tests
<test_command>

# Run specific test file
<test_command> <path/to/test_file>

# Run tests with coverage report
<test_command_with_coverage>

# Run tests in watch/interactive mode
<test_command> --watch

# Check for skipped/disabled tests
grep -r "<skip_pattern>" <test_directory>/
# Examples: ".skip(", "xit(", "@Ignore", "pytest.mark.skip"
```

**Consult active test framework pack** for specific commands (e.g., vitest pack provides `npm test`, jest provides `npm test`, pytest provides `pytest`).

## Test Types Explained

### Unit Tests
- Test single functions/methods in isolation
- No external dependencies (databases, APIs, file systems)
- Fast execution (<100ms)
- High coverage (aim for 100% of critical logic)

### Integration Tests
- Test multiple components working together
- May include real dependencies (databases, services)
- Moderate execution time (<1s)
- Focus on component boundaries and data flow

### End-to-End (E2E) Tests
- Test complete user workflows
- Include all system layers (UI, API, database)
- Slower execution (<5s)
- Cover critical user paths

## References

**Core TDD Principles**: This document
**Framework-specific patterns**: Consult active pack guidelines:
- Test runner syntax: Active test framework pack (e.g., vitest, jest, pytest)
- Database testing: Active database pack (e.g., prisma, sqlalchemy)
- Component testing: Active UI framework pack (e.g., react, vue, angular)
- API testing: Active API framework pack (e.g., fastify, express, flask)

---

**Version**: 2.0 (Technology-agnostic refactor)
**Applies to**: ALL implementing agents
**Enforcement**: Validators check TDD compliance via git history
