# NO MOCKS Policy - Include-Only File

<!-- WARNING: This file is for {{include-section:}} only. DO NOT read directly. -->

<!-- section: philosophy -->
## NO MOCKS Philosophy (All Roles)

### Core Principle
Test real behavior, not mocked behavior. Mocking internal code means testing nothing.

### What This Means
- **Real databases**: Use real database with test isolation strategies (SQLite, template DBs, containerized)
- **Real auth**: Use real authentication implementations
- **Real HTTP**: Test with real HTTP requests (TestClient, fetch)
- **Real files**: Use tmp_path or temporary directories
- **Real services**: Use actual service implementations

### Why NO MOCKS
- Mocked tests prove nothing—they only prove the mock works
- Real behavior tests catch actual bugs
- Integration issues are caught early
- Confidence in production behavior

### Only Mock at System Boundaries
External APIs you don't control (third-party services, payment gateways, email providers) may be mocked at the boundary. Everything internal must be real.
<!-- /section: philosophy -->

<!-- section: agent-implementation -->
## NO MOCKS Implementation (Agents)

### Allowed Testing Patterns

#### Database Testing
```pseudocode
// ✅ CORRECT: Use real database
test("stores data correctly", async function() {
  record = create_in_real_database({ name: "Test" })
  assert_exists(record.id)
  
  fetched = fetch_from_real_database(record.id)
  assert_equals(fetched.name, "Test")
})
```

#### File System Testing
```pseudocode
// ✅ CORRECT: Use real temporary files
test("writes file correctly", function(tmp_path) {
  file_path = tmp_path / "test.txt"
  write_file(file_path, "content")
  
  content = read_file(file_path)
  assert_equals(content, "content")
})
```

#### HTTP/API Testing
```pseudocode
// ✅ CORRECT: Use real HTTP client
test("returns correct response", async function() {
  response = await test_client.get("/api/users")
  
  assert_equals(response.status, 200)
  assert_is_array(response.data)
})
```

### Forbidden Patterns

❌ **NEVER mock internal services**:
```pseudocode
// ❌ WRONG: Mocking database client
mock(database_client).return_value({ id: 1 })

// ❌ WRONG: Mocking auth service
mock(auth_service).is_authenticated.return_value(true)

// ❌ WRONG: Mocking internal modules
mock("./user-service").return_value(fake_service)
```

❌ **NEVER use mock verifications as proof**:
```pseudocode
// ❌ WRONG: Spying on internal calls
assert(database_client.save).was_called_with(data)
```

### Test Isolation Strategies

1. **Unique Identifiers**: Generate unique IDs for test entities
2. **Transaction Rollback**: Wrap tests in transactions
3. **Template Databases**: Clone fresh database per test
4. **Cleanup Hooks**: Clean up after each test
<!-- /section: agent-implementation -->

<!-- section: validator-flags -->
## NO MOCKS Validation (Validators)

### Patterns to Flag (Blocking)

Flag any use of mocking/stubbing/spying facilities applied to **internal code** (data access, authentication, business logic, domain services).

Examples of what to flag (language-agnostic):
- Importing a mocking library and substituting internal modules/classes/functions
- Stubbing/spying on internal service methods as “proof” instead of asserting outcomes
- Replacing the real database/data-layer client with a fake object
- Replacing real authentication/authorization with fakes

### Immediate Rejection Triggers
🚩 **Reject if found:**
- Database client mocked
- Authentication flows mocked
- Internal service modules mocked
- Using `toHaveBeenCalled` on internal methods as proof

### Acceptable Exceptions
✅ **May allow:**
- External API mocks (payment gateways, email services)
- Third-party service mocks at boundaries
- Clock/timer mocks for time-sensitive tests

### Validation Questions
1. Does this test exercise real code paths?
2. Would this test catch a real production bug?
3. Is the mock at a true system boundary?
<!-- /section: validator-flags -->
