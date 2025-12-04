# Test Isolation - Include-Only File

<!-- WARNING: This file is for {{include-section:}} only. DO NOT read directly. -->

<!-- SECTION: principles -->
## Test Isolation Principles (All Roles)

### Core Rules
- Tests must not depend on each other
- Tests must not share mutable state
- Tests must be runnable in any order
- Tests must be runnable in parallel

### Why Isolation Matters
- Flaky tests indicate isolation problems
- Parallel execution speeds up CI
- Debugging is easier when tests are independent
- Confidence in results

### Common Isolation Problems
- Shared database state between tests
- Global variables modified by tests
- File system artifacts left behind
- External service state
<!-- /SECTION: principles -->

<!-- SECTION: agent-implementation -->
## Test Isolation Implementation (Agents)

### Pattern 1: Unique Identifiers
```pseudocode
// Generate unique IDs to prevent collisions
TEST_NAMESPACE = "test-" + timestamp()

function generate_test_id():
  return TEST_NAMESPACE + "-" + random_string()

test("creates resource"):
  // Use unique identifier
  resource = create_resource({
    identifier: generate_test_id(),
    name: "Test Resource"
  })
  // Test assertions...
```

### Pattern 2: Database Cleanup
```pseudocode
test_suite("Resource Tests"):
  // Clean up namespace after all tests
  after_all():
    delete_where(identifier.contains(TEST_NAMESPACE))
  
  test("creates resource"):
    // Safe to run in parallel with other test suites
```

### Pattern 3: Template Databases
```pseudocode
// Create template once with migrations
setup_once():
  template_db = create_database("template_test")
  run_migrations(template_db)

// Clone for each test
before_each():
  test_db = clone_database(template_db)
  
after_each():
  drop_database(test_db)
```

### Pattern 4: Transaction Rollback
```pseudocode
before_each():
  start_transaction()

after_each():
  rollback_transaction()  // All changes undone
```

### Pattern 5: Temporary Files
```pseudocode
test("writes file", tmp_path):
  // tmp_path is unique per test, auto-cleaned
  file = tmp_path / "test.txt"
  write_file(file, "content")
  // tmp_path deleted after test
```

### Anti-Patterns to Avoid
❌ Sharing database records between tests
❌ Relying on test execution order
❌ Using fixed IDs that can collide
❌ Not cleaning up after tests
<!-- /SECTION: agent-implementation -->

<!-- SECTION: validator-check -->
## Test Isolation Validation (Validators)

### Checklist
- [ ] Tests use unique identifiers
- [ ] No shared mutable state
- [ ] Cleanup in afterEach/afterAll hooks
- [ ] No test order dependencies
- [ ] Parallel-safe (can run with `--parallel`)

### Red Flags
🚩 **Immediate rejection:**
- Fixed IDs that will collide in parallel runs
- Tests that fail when run out of order
- No cleanup hooks
- Global state modified without restore

🟡 **Needs review:**
- Flaky test history
- Long test setup times (isolation overhead)
- External service dependencies
<!-- /SECTION: validator-check -->
