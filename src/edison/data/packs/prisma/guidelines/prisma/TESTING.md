# Prisma Testing (Pack Extension)

## Core Principle
- **NEVER** mock Prisma or critical auth flows in integration tests.
- **ALWAYS** use real database connections with proper isolation.

## Extended Documentation
See your project's test isolation guide for comprehensive patterns.

## PostgreSQL Template Pool Pattern

Use `withTestDatabase()` for isolated unit tests:

```typescript
import { withTestDatabase } from '<db-test-utils-module>'

it('tests business logic', async () => {
  await withTestDatabase(async (prisma) => {
    // Create test data
    await prisma.model.create({ data: { ... } })

    // Test logic
    const result = await businessLogic(prisma)

    // Assert
    expect(result).toBe(expected)

    // No cleanup needed - automatic
  })
})
```

### How Template Pool Works
1. A seeded "template" database is created once at test setup
2. Each test clones this template (fast - PostgreSQL `CREATE DATABASE ... TEMPLATE`)
3. Test runs in complete isolation
4. Clone is dropped after test

### Performance
- Clone creation: ~10-20ms
- True isolation: No namespace boilerplate needed
- Guaranteed cleanup: Even on test crash

## When to Use Template Pool vs Namespace
| Pattern | Use Case | Speed | Isolation |
|---------|----------|-------|-----------|
| `withTestDatabase()` | Unit tests in your service layer | Slower | Physical |
| Namespace + `withTestServer()` | Integration tests against your API service | Faster | Logical |
