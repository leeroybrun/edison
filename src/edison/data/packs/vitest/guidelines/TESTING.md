## Your Expertise

- Vitest (unit & integration testing)
- React Testing Library (component testing)
- Playwright (E2E testing)
- TypeScript test patterns
- Test coverage analysis
- Mocking & stubbing
- TDD/BDD methodologies

## Extended Documentation

For comprehensive testing patterns and anti-patterns, see:
- `docs/testing/TEST_ISOLATION_GUIDE.md` - Complete isolation patterns (Physical vs Logical)
- `docs/testing/TEST_ANTI_PATTERNS.md` - Common mistakes and detection scripts

## Core Testing Patterns

### Pattern 1: Physical Isolation (`withTestDatabase`)
- Each test gets a clone of the database template
- Automatic cleanup on test completion
- Best for: Unit tests in `packages/api-core`
- No namespace needed - true physical isolation

### Pattern 2: Logical Isolation (Namespace + `withTestServer`)
- Uses timestamp-based namespace for all test data
- Manual cleanup via `afterAll()` with namespace filter
- Best for: Integration tests in `apps/api`
- Use `getSuiteNamespace(__filename)` helper

## No-Mock Policy (Critical Paths)
- **NEVER** mock `@/lib/prisma`, `@/lib/auth/*`, or route handlers
- **NEVER** use `toHaveBeenCalled` assertions on internal Prisma calls
- **ALWAYS** test real behavior via route handlers and real DB/auth
