# API Testing Patterns

## Quick Reference
- Seed committed test data; prefer unique IDs per test.
- Assert status codes and response shapes; avoid over-mocking.
- Use real database connections in isolated contexts when feasible.

## Extended Documentation
See `docs/testing/TEST_ISOLATION_GUIDE.md` for comprehensive patterns.

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
  await prisma.leadEvent.deleteMany(nsCleanupWhere(SUITE_NS, 'lead.sourceUrl'))
  await prisma.aIFeedback.deleteMany(nsCleanupWhere(SUITE_NS, 'lead.sourceUrl'))
  // 2. Parents last
  await prisma.lead.deleteMany(nsCleanupWhere(SUITE_NS, 'sourceUrl'))
})
```

## Performance Targets
- API route tests: < 50ms typical
- Services/hooks/utilities: < 20ms typical

