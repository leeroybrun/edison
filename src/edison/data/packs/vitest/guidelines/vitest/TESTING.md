## Your Expertise

- Vitest (unit & integration testing)
- React Testing Library (component testing)
- Playwright (E2E testing)
- TypeScript test patterns
- Test coverage analysis
- TDD/BDD methodologies

## Extended Documentation

For comprehensive testing patterns and anti-patterns, see:
- Your project's test isolation guide - Complete isolation patterns (physical vs logical)
- Your project's testing anti-patterns guide - Common mistakes and detection scripts

## Core Testing Patterns

### Pattern 1: Physical Isolation (`withTestDatabase`)
- Each test gets a clone of the database template
- Automatic cleanup on test completion
- Best for: Unit tests in your service/domain layer
- No namespace needed - true physical isolation

### Pattern 2: Logical Isolation (Namespace + `withTestServer`)
- Uses timestamp-based namespace for all test data
- Manual cleanup via `afterAll()` with namespace filter
- Best for: Integration tests against your API/service boundary

## No-Mock Policy (Critical Paths)
- **NEVER** mock your ORM client, authentication implementation, or internal route handlers
- **NEVER** use `toHaveBeenCalled` assertions on internal ORM calls as proof of behavior
- **ALWAYS** test real behavior via route handlers and real DB/auth
