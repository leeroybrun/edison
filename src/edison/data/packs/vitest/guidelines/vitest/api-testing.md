# API Testing Patterns

## Quick Reference
- Seed committed test data; prefer unique IDs per test.
- Assert status codes and response shapes; avoid over-mocking.
- Use real database connections in isolated contexts when feasible.

## Extended Documentation
See your project's test isolation guide for comprehensive patterns.

## Namespace Pattern (REQUIRED for Integration Tests)

```typescript
// PREFERRED: Use helper
import { getSuiteNamespace, uniqueId, nsCleanupWhere } from '../../utils/namespaces'
const SUITE_NS = getSuiteNamespace(__filename)

// ACCEPTABLE: Manual timestamp
const TEST_NS = `test-${Date.now()}`

// FORBIDDEN: Static namespace (NOT PARALLEL SAFE!)
const TEST_NS = 'my-test' // ❌ NEVER DO THIS
```

## Cleanup Order (Foreign Keys)
```typescript
afterAll(async () => {
  // 1. Children first
  await db.childEntity.deleteMany(nsCleanupWhere(SUITE_NS, '<foreign_key_path>'))
  await db.anotherChildEntity.deleteMany(nsCleanupWhere(SUITE_NS, '<foreign_key_path>'))
  // 2. Parents last
  await db.parentEntity.deleteMany(nsCleanupWhere(SUITE_NS, '<parent_unique_field>'))
})
```

## Performance Targets
- API route tests: < 50ms typical
- Services/hooks/utilities: < 20ms typical

