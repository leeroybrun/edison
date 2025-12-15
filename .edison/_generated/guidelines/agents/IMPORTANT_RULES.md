# Important Rules (Production-Critical)

<!-- MANDATORY: All agents MUST read this before implementation -->
<!-- Generated from pre-Edison agent content extraction -->

## Purpose

These rules are NON-NEGOTIABLE and apply to ALL agents. They represent production-critical standards that must be followed without exception. Violation of these rules will result in validation failures and blocked task promotion.

## Requirements

### Universal Rules (All Agents)

#### 1. SECURITY FIRST

**Every interaction with external data must be validated and sanitized.**

```pseudocode
// ✅ CORRECT - Validate all input
validated_data = schema_validator.validate(request_body)

// ✅ CORRECT - Authenticate all protected routes
user = authenticate_request(request)

// ✅ CORRECT - Sanitize error messages
return response({
  error: 'Invalid request',  // NOT the actual error details!
  status: 400
})

// ❌ WRONG - Raw input used directly
record = database.create(request_body)  // No validation!

// ❌ WRONG - Missing auth check
function handle_request(request) {
  records = database.find_all()  // No authentication!
}

// ❌ WRONG - Leaking internal errors
return response({
  error: error.message,
  stack: error.stack_trace,  // Exposes internals!
  status: 500
})
```

#### 2. NO TODOs

**Complete EVERYTHING before returning. No placeholders, no "TODO later".**

```pseudocode
// ❌ WRONG - TODO comments
function process_record(record) {
  // TODO: Add validation
  // TODO: Handle edge cases
  return record
}

// ❌ WRONG - Placeholder implementations
function export_data() {
  throw Error('Not implemented')  // NO!
}

// ✅ CORRECT - Complete implementation
function process_record(record) {
  validated = validate_schema(record)
  if (!validated.email) {
    // Handle missing email case
    validated.email = null
  }
  return validated
}
```

#### 3. TEST THOROUGHLY

**Follow TDD protocol religiously. Tests first, always.**

```pseudocode
// ✅ CORRECT workflow
// 1. Write test (RED)
test('creates record with valid data') {
  response = create_record(valid_request)
  assert response.status == 201
}

// 2. Run test - MUST FAIL
// run_tests → ❌ Expected to fail

// 3. Implement (GREEN)
function create_record(request) {
  // Implementation
}

// 4. Run test - MUST PASS
// run_tests → ✅ All passing

// ❌ WRONG workflow
// Write code first, then add tests later
// Skip test verification
// Mock everything unnecessarily
```

#### 4. ERROR HANDLING

**Every function must handle errors. Every endpoint must return appropriate status codes.**

```pseudocode
// ✅ CORRECT - Comprehensive error handling
function handle_create_request(request) {
  try {
    user = authenticate(request)
    body = parse_request_body(request)
    validated = validate_schema(body)
    record = database.create(validated)
    return response({ data: record }, status: 201)
  } catch (ValidationError as error) {
    return response(
      { error: 'Validation failed', details: error.details },
      status: 400
    )
  } catch (AuthenticationError as error) {
    return response(
      { error: 'Unauthorized' },
      status: 401
    )
  } catch (Exception as error) {
    log_error('API error:', error)
    return response(
      { error: 'Internal server error' },
      status: 500
    )
  }
}

// ❌ WRONG - No error handling
function handle_create_request(request) {
  body = parse_request_body(request)  // Could throw!
  record = database.create(body)  // Could throw!
  return response(record)  // Missing status code!
}
```

#### 5. TYPE SAFETY

**Use strict type checking. No loose types. No type checking suppressions.**

```pseudocode
// ✅ CORRECT - Strict typing
type Record {
  id: String
  name: String
  email: String | Null
  status: RecordStatus
}

function process_record(record: Record): ProcessedRecord {
  return {
    ...record,
    processed: true,
    processedAt: current_datetime()
  }
}

// ❌ WRONG - Using loose/any types
function process_record(record: Any): Any {  // NO!
  return record
}

// ❌ WRONG - Suppressing type checks
// [suppress-type-check]
data = untyped_function()  // NO!

// [ignore-error] - will fix later
result = broken_function()  // NO!
```

#### 6. LOGGING STANDARDS

**Use error logging for errors. Remove debug logs before completion.**

```pseudocode
// ✅ CORRECT - Error logging
try {
  some_operation()
} catch (error) {
  log_error('Operation failed:', error)
  throw error
}

// ❌ WRONG - Debug logs in production code
log_debug('data:', data)  // Remove before completion!
log_debug('here')  // NO debug breadcrumbs!
```

### Agent-Specific Rules

#### API Builder

1. **Authentication required**: All protected endpoints must authenticate requests (refer to active pack guidelines)
2. **Input validation**: All input must be validated with schema validators (refer to active pack guidelines)
3. **Status codes**: Use appropriate HTTP status codes (200, 201, 400, 401, 404, 500)
4. **Error sanitization**: Never expose internal error details

#### Component Builder

1. **Accessibility**: WCAG AA minimum (keyboard navigation, accessibility labels, color contrast)
2. **Responsive**: Mobile-first design, test all breakpoints
3. **Styling**: Follow active styling framework guidelines (refer to active pack guidelines)
4. **Theme support**: Support both light and dark modes using appropriate theming approach
5. **States**: Loading, error, and empty states for all data-driven components

#### Database Architect

1. **Naming conventions**: Follow project-specific naming conventions (refer to active pack guidelines)
2. **Primary keys**: Use appropriate identifier strategy (refer to active pack guidelines)
3. **Timestamps**: Always include creation and update timestamps
4. **Indexes**: Add indexes for foreign keys and frequently queried fields
5. **Zero-downtime**: Design migrations for zero-downtime deployment

#### Test Engineer

1. **Test first**: Write test before implementation (TDD)
2. **Verify failure**: Test must fail before implementation
3. **Real integration**: Test real dependencies when feasible (refer to TDD guidelines)
4. **Fast tests**: Unit tests <100ms, integration tests <1s
5. **Isolated tests**: Use unique identifiers, ensure proper cleanup

#### Feature Implementer

1. **Complete features only**: Don't return until entire feature works end-to-end
2. **Verify integration**: After delegation, verify parts integrate correctly
3. **Production ready**: No shortcuts, no placeholders

#### Code Reviewer

1. **Review only**: Provide feedback, don't implement fixes
2. **Never delegate**: Review requires YOUR expert judgment
3. **Documentation first**: Check documentation before flagging code as wrong

### The Golden Rule

**ABSOLUTELY MANDATORY AND CRITICAL:**

DO NOT rush and DO NOT mark tasks/work as completed if they are not REALLY finished. Instead, clearly summarize what is still needed to be done, if something was not completely finished, so that we can continue and finish the task fully in a subsequent chat.

```markdown
✅ CORRECT Status Report:
## Implementation Status: INCOMPLETE

### Completed:
- [x] API route structure
- [x] Input validation
- [x] Tests (15/15 passing)

### Remaining:
- [ ] Error handling for edge case X
- [ ] Loading state for slow connections
- [ ] Empty state UI

### Blockers:
- Need clarification on business logic for case Y

---

❌ WRONG Status Report:
## Implementation Status: COMPLETE

Everything done!

(Even though TODOs exist, tests are skipped, or features are incomplete)
```

## Evidence Required

For each rule, validators check:

| Rule | Evidence Required |
|------|-------------------|
| Security | Auth checks present, input validated, errors sanitized |
| No TODOs | Search for TODO/FIXME comments returns empty |
| Testing | TDD evidence in git history, all tests pass |
| Error Handling | Every endpoint has error handling, appropriate status codes |
| Type Safety | Type checking passes with 0 errors |
| Logging | No debug logs in production code |

## Validation Commands

Framework-specific commands depend on your project configuration. Common patterns:

```bash
# Check for TODOs/FIXMEs (adjust path patterns as needed)
grep -r "TODO\|FIXME" <source_directory>

# Check for debug logs (adjust pattern for your logging framework)
grep -r "<debug_log_pattern>" <source_directory>

# Type check (command varies by language/framework)
<type_check_command>

# Lint (command varies by language/framework)
<lint_command>

# Run all tests
<test_command>

# Build (catches many issues)
<build_command>
```

## References

- Quality standards: `.edison/_generated/guidelines/includes/QUALITY.md`
- Honest status guide: `.edison/_generated/guidelines/shared/HONEST_STATUS.md`

---

**Version**: 1.0 (Extracted from pre-Edison agents)
**Applies to**: ALL agents
**Enforcement**: Validators check compliance; violations block promotion